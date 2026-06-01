from datetime import UTC, datetime
import difflib
import logging

from app.core.config import settings
from app.integrations.mattin_client import MattinClient, MattinClientError
from app.models.block import Block
from app.models.impact_suggestion import ImpactSuggestionRecord
from app.repositories.workspace_repository import WorkspaceRepository
from app.utils.json_payload import extract_json_object
from app.utils.ids import new_id

logger = logging.getLogger(__name__)


class BlockImpactService:
    def __init__(self, repository: WorkspaceRepository, mattin_client: MattinClient) -> None:
        self.repository = repository
        self.mattin_client = mattin_client
        self.impact_agent_id = settings.mattin_block_impact_agent_id

    def check_impact(
        self,
        run_id: str,
        block_id: str,
        original_content: str,
        new_content: str,
        conversation_id: int | None = None,
    ) -> list[ImpactSuggestionRecord]:
        if self.impact_agent_id is None:
            logger.info("Impact agent not configured (MATTIN_BLOCK_IMPACT_AGENT_ID). Skipping impact checks.")
            return []

        from sqlalchemy import select
        from app.models.block_relationship import BlockRelationship

        stmt = select(BlockRelationship).where(
            (BlockRelationship.target_block_id == block_id)
            & (BlockRelationship.relationship_type.in_(["references", "depends_on"]))
        )
        incoming_rels = list(self.repository.db.scalars(stmt))

        if not incoming_rels:
            logger.info("No incoming relationships for block %s. Impact check skipped.", block_id)
            self.repository.delete_pending_impact_suggestions(run_id, block_id)
            return []

        diff = self._compute_diff(original_content, new_content)
        if not diff:
            logger.info("No diff detected for block %s. Impact check skipped.", block_id)
            self.repository.delete_pending_impact_suggestions(run_id, block_id)
            return []

        all_blocks = self.repository.list_blocks(run_id)
        block_by_id = {b.id: b for b in all_blocks}
        changed_block = block_by_id.get(block_id)
        if changed_block is None:
            logger.info("Changed block %s not found in run %s. Impact check skipped.", block_id, run_id)
            return []

        self.repository.delete_pending_impact_suggestions(run_id, block_id)
        suggestions: list[ImpactSuggestionRecord] = []

        # Group relationships by affected block to avoid duplicate suggestions
        rels_by_block: dict[str, list] = {}
        for rel in incoming_rels:
            source_block = block_by_id.get(rel.source_block_id)
            if source_block is None:
                continue
            rels_by_block.setdefault(rel.source_block_id, []).append(rel)

        for affected_block_id, rels in rels_by_block.items():
            source_block = block_by_id[affected_block_id]
            combined_type = ", ".join(sorted({r.relationship_type for r in rels}))
            combined_description = "; ".join(r.description for r in rels if r.description)

            try:
                suggestion_text = self._generate_suggestion_with_ai(
                    changed_block=changed_block,
                    affected_block=source_block,
                    diff=diff,
                    relationship_type=combined_type,
                    relationship_description=combined_description,
                )
                if suggestion_text:
                    if suggestion_text.strip().lower() in {"no update required", "No update required"}:
                        continue
                    suggestions.append(ImpactSuggestionRecord(
                        id=new_id(),
                        workspace_run_id=run_id,
                        source_block_id=block_id,
                        affected_block_id=source_block.id,
                        relationship_type=combined_type,
                        reason=f"This block {combined_type} '{changed_block.title}' which has changed.",
                        suggestion=suggestion_text,
                        status="pending",
                        conversation_id=conversation_id,
                        created_at=datetime.now(UTC),
                    ))
            except Exception as exc:
                logger.warning("Failed to generate impact suggestion: %s", exc)

        logger.info(
            "Impact check completed for block %s. relationships=%s suggestions=%s",
            block_id,
            len(incoming_rels),
            len(suggestions),
        )
        return self.repository.create_impact_suggestions(suggestions)

    def apply_suggestion(
        self,
        run_id: str,
        block_id: str,
        suggestion: str,
    ) -> Block | None:
        block = self.repository.get_block(run_id, block_id)
        if block is None:
            return None

        if self.impact_agent_id is None:
            logger.warning("Impact agent is not configured (MATTIN_BLOCK_IMPACT_AGENT_ID)")
            return None

        try:
            prompt = (
                "Apply this suggested change to the following markdown content.\n\n"
                f"Suggestion: {suggestion}\n\n"
                f"Current content:\n{block.content}\n\n"
                "Return ONLY the updated markdown content, nothing else."
            )
            response_text = self._call_agent_text(agent_id=self.impact_agent_id, message=prompt)
            parsed = extract_json_object(response_text)
            if parsed is not None:
                candidate = parsed.get("updated_markdown") or parsed.get("markdown") or parsed.get("content")
                new_content = str(candidate).strip() if candidate is not None else response_text.strip()
            else:
                new_content = response_text.strip()

            if not new_content:
                return None

            block.content = new_content
            block.refresh_meta_on_save()
            self.repository.db.add(block)
            self.repository.db.commit()
            self.repository.db.refresh(block)
            return block
        except MattinClientError as exc:
            logger.error("Failed to apply suggestion: %s", exc)
            return None

    def _compute_diff(self, old: str, new: str) -> str:
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        diff = difflib.unified_diff(old_lines, new_lines, lineterm="", n=3)
        return "".join(diff)

    def _generate_suggestion_with_ai(
        self,
        changed_block: Block,
        affected_block: Block,
        diff: str,
        relationship_type: str,
        relationship_description: str,
    ) -> str:
        prompt = (
            f"A document block has been modified. Another block references it and may need updating.\n\n"
            f"Changed block: '{changed_block.title}' ({changed_block.block_type})\n"
            f"Affected block: '{affected_block.title}' ({affected_block.block_type})\n"
            f"Relationship: {relationship_type} - {relationship_description}\n\n"
            f"Changes made:\n{diff[:2000]}\n\n"
            f"Affected block current content:\n{affected_block.content[:1000]}\n\n"
            f"Based on the changes, provide a specific suggestion for how the affected block should be updated. "
            f"Be concise and actionable. Return ONLY the suggestion text."
            f"If no update is needed, respond with 'No update required'."
        )

        if self.impact_agent_id is None:
            return ""

        return self._call_agent_text(agent_id=self.impact_agent_id, message=prompt)

    def _call_agent_text(self, *, agent_id: int, message: str) -> str:
        payload = self.mattin_client.call_agent(
            agent_id=agent_id,
            message=message,
            timeout=30,
        )
        response_value = payload.get("response")
        if response_value is None:
            return ""
        return str(response_value).strip()

from datetime import UTC, datetime
import logging
from typing import Any

from app.core.config import settings
from app.integrations.mattin_client import MattinClient, MattinClientError
from app.models.block import Block
from app.models.block_relationship import BlockRelationship
from app.repositories.workspace_repository import WorkspaceRepository
from app.utils.block_reference_parser import build_block_metadata
from app.utils.ids import new_id

logger = logging.getLogger(__name__)


class BlockRelationshipService:
    def __init__(self, repository: WorkspaceRepository, mattin_client: MattinClient) -> None:
        self.repository = repository
        self.mattin_client = mattin_client
        self.relationship_agent_id = settings.mattin_block_relationship_agent_id

    def create_relationship(
        self,
        workspace_run_id: str,
        source_block_id: str,
        target_block_id: str,
        relationship_type: str,
        description: str = "",
        auto_created: bool = False,
    ) -> BlockRelationship:
        rel = BlockRelationship(
            id=new_id(),
            workspace_run_id=workspace_run_id,
            source_block_id=source_block_id,
            target_block_id=target_block_id,
            relationship_type=relationship_type,
            description=description,
            auto_created=auto_created,
            created_at=datetime.now(UTC),
        )
        self.repository.db.add(rel)
        self.repository.db.commit()
        self.repository.db.refresh(rel)
        return rel

    def get_relationships_for_block(self, block_id: str) -> list[BlockRelationship]:
        from sqlalchemy import select
        stmt = (
            select(BlockRelationship)
            .where(
                (BlockRelationship.source_block_id == block_id)
                | (BlockRelationship.target_block_id == block_id)
            )
        )
        return list(self.repository.db.scalars(stmt))

    def get_incoming_relationships(self, block_id: str) -> list[BlockRelationship]:
        from sqlalchemy import select
        stmt = select(BlockRelationship).where(
            BlockRelationship.target_block_id == block_id
        )
        return list(self.repository.db.scalars(stmt))

    def get_outgoing_relationships(self, block_id: str) -> list[BlockRelationship]:
        from sqlalchemy import select
        stmt = select(BlockRelationship).where(
            BlockRelationship.source_block_id == block_id
        )
        return list(self.repository.db.scalars(stmt))

    def delete_relationship(self, relationship_id: str) -> bool:
        from sqlalchemy import delete
        stmt = delete(BlockRelationship).where(BlockRelationship.id == relationship_id)
        result = self.repository.db.execute(stmt)
        self.repository.db.commit()
        return result.rowcount > 0

    def update_block_metadata(self, block: Block) -> None:
        meta = build_block_metadata(block.content)
        block.update_meta(meta)
        block.refresh_meta_on_save()
        self.repository.db.add(block)
        self.repository.db.commit()

    def detect_relationships_from_generation(
        self,
        run_id: str,
        blocks: list[Block],
    ) -> list[BlockRelationship]:
        created: list[BlockRelationship] = []

        block_contexts = []
        for block in blocks:
            block_contexts.append({
                "id": block.id,
                "title": block.title,
                "type": block.block_type,
                "summary": block.summary,
                "content_preview": block.content[:500],
            })

        if self.relationship_agent_id is not None:
            try:
                prompt = self._build_detection_prompt(block_contexts)
                payload = self.mattin_client.call_agent(
                    agent_id=self.relationship_agent_id,
                    message=prompt,
                    timeout=30,
                )
                relationships = self._parse_detection_response(payload.get("response"))

                block_ids = {b.id for b in blocks}
                for rel_data in relationships:
                    src = rel_data.get("source_block_id")
                    tgt = rel_data.get("target_block_id")
                    rel_type = rel_data.get("relationship_type", "references")
                    desc = rel_data.get("description", "")

                    if src in block_ids and tgt in block_ids and src != tgt:
                        existing = self._find_relationship(src, tgt, rel_type)
                        if existing is None:
                            rel = self.create_relationship(
                                workspace_run_id=run_id,
                                source_block_id=src,
                                target_block_id=tgt,
                                relationship_type=rel_type,
                                description=desc,
                                auto_created=True,
                            )
                            created.append(rel)
            except (MattinClientError, Exception) as exc:
                logger.warning("AI relationship detection failed: %s", exc)

        for block in blocks:
            self.update_block_metadata(block)

        return created

    def _find_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
    ) -> BlockRelationship | None:
        from sqlalchemy import select
        stmt = select(BlockRelationship).where(
            BlockRelationship.source_block_id == source_id,
            BlockRelationship.target_block_id == target_id,
            BlockRelationship.relationship_type == relationship_type,
        )
        return self.repository.db.scalar(stmt)

    def _build_detection_prompt(self, block_contexts: list[dict]) -> str:
        blocks_text = "\n".join(
            f"- ID: {b['id']}, Title: {b['title']}, Type: {b['type']}, Summary: {b['summary']}"
            for b in block_contexts
        )
        return (
            f"Analyze the following document blocks and identify relationships between them.\n\n"
            f"Blocks:\n{blocks_text}\n\n"
            f"Return a JSON array of relationships with this structure:\n"
            f'[\n  {{"source_block_id": "...", "target_block_id": "...", "relationship_type": "references|depends_on|contradicts|extends", "description": "..."}}\n]\n\n'
            f"Relationship types:\n"
            f"- references: block A mentions or refers to content in block B\n"
            f"- depends_on: block A needs information from block B to make sense\n"
            f"- contradicts: block A has information that conflicts with block B\n"
            f"- extends: block A expands on or adds detail to block B\n\n"
            f"Return ONLY the JSON array, no other text."
        )

    def _parse_detection_response(self, response: Any) -> list[dict]:
        import json
        import re

        try:
            if isinstance(response, str):
                json_match = re.search(r"\[.*\]", response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            if isinstance(response, list):
                return response
            if isinstance(response, dict):
                return response.get("relationships", [])
        except json.JSONDecodeError as exc:
            logger.warning("Failed to parse AI relationship detection response: %s", exc)
        return []

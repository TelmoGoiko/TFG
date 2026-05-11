from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any

from app.core.config import settings
from app.integrations.mattin_client import MattinClient, MattinClientError
from app.models.chat_message import ChatMessage
from app.repositories.workspace_repository import WorkspaceRepository
from app.utils.ids import new_id
from app.utils.json_payload import extract_json_object


logger = logging.getLogger(__name__)


class WorkspaceBlockChatAgentService:
    def __init__(self, repository: WorkspaceRepository, mattin_client: MattinClient) -> None:
        self.repository = repository
        self.mattin_client = mattin_client

    def _create_message(
        self,
        block_id: str,
        role: str,
        content: str,
        mentions: list[str],
    ) -> ChatMessage:
        model = ChatMessage(
            id=new_id(),
            block_id=block_id,
            role=role,
            content=content,
            mentions=mentions,
            created_at=datetime.now(UTC),
        )
        return self.repository.create_message(model)

    def _build_block_chat_message(
        self,
        workspace_id: str,
        run_id: str,
        block_id: str,
        block_title: str,
        block_type: str,
        block_content: str,
        user_message: str,
        selected_snippet: str | None,
    ) -> str:
        outline = self.repository.list_blocks(run_id)
        outline_text = "\n".join(
            f"- [{item.order_index + 1}] {item.title} (block_id: {item.id}): {item.summary}"
            for item in outline
        )
        snippet_text = selected_snippet.strip() if selected_snippet else ""

        related_context = self._build_related_blocks_context(run_id, block_id, block_title)

        return (
            "You are an editing assistant for a multi-block markdown document. "
            "Return ONLY valid JSON with this shape:\n"
            "{\n"
            '  "assistant_message": "string",\n'
            '  "updated_markdown": "string or null"\n'
            "}\n\n"
            "Rules:\n"
            "- assistant_message: concise explanation of proposed changes.\n"
            "- updated_markdown: full rewritten markdown only if a rewrite is requested; otherwise null.\n"
            "- When a rewrite is requested, produce the final markdown directly.\n"
            "- When no rewrite is requested, set updated_markdown to null and reply only via assistant_message.\n"
            "- If the user wants changes in other blocks, identify relevant blocks from the outline or call MCP tool 'workspace_list_blocks' to find them, then apply using MCP tool 'workspace_propose_block_rewrite' with workspace_id, run_id, block_id, updated_markdown, and assistant_message.\n"
            "- If the user requests document-wide edits, do not ask for per-block instructions; apply reasonable updates across the necessary blocks and keep data consistent.\n"
            "- If the user wants a new block, call MCP tool 'workspace_create_block' with workspace_id, run_id, title, summary, content, block_type, and an insert position (insert_before_block_id, insert_after_block_id, or order_index).\n"
            "- If the user wants to delete a block, call MCP tool 'workspace_delete_block' with workspace_id, run_id, and block_id.\n"
            "- You already have the current block markdown; do not call MCP tool 'workspace_get_block' for it.\n"
            "- If you need another block, use the block_id from the outline or call MCP tool 'workspace_list_blocks' to identify it.\n"
            "- Do not delegate to other agents.\n"
            "- Keep consistency with the document outline.\n"
            "- Do not add markdown fences around JSON.\n\n"
            f"Workspace id: {workspace_id}\n"
            f"Run id: {run_id}\n"
            f"Current block id: {block_id}\n\n"
            f"Document outline:\n{outline_text}\n\n"
            f"{related_context}\n\n"
            f"Current block title: {block_title}\n"
            f"Current block type: {block_type}\n"
            f"Current block markdown:\n{block_content}\n\n"
            f"Selected snippet (if any):\n{snippet_text or 'none'}\n\n"
            f"User request:\n{user_message.strip()}"
        )

    def _build_related_blocks_context(self, run_id: str, block_id: str, block_title: str) -> str:
        from sqlalchemy import select
        from app.models.block_relationship import BlockRelationship

        run_blocks = self.repository.list_blocks(run_id)
        run_block_ids = {b.id for b in run_blocks}
        all_blocks = {b.id: b for b in run_blocks}

        stmt = select(BlockRelationship).where(
            BlockRelationship.relationship_type.in_(["references", "depends_on"]),
            BlockRelationship.source_block_id.in_(run_block_ids),
            BlockRelationship.target_block_id.in_(run_block_ids),
        )
        all_rels = list(self.repository.db.scalars(stmt))

        related = []
        for rel in all_rels:
            if rel.source_block_id == block_id:
                target = all_blocks.get(rel.target_block_id)
                if target:
                    related.append(f"- This block {rel.relationship_type} '{target.title}': {target.summary}")
            elif rel.target_block_id == block_id:
                source = all_blocks.get(rel.source_block_id)
                if source:
                    related.append(f"- '{source.title}' {rel.relationship_type} this block: {source.summary}")

        if not related:
            return ""

        return "Related blocks context:\n" + "\n".join(related)

    def _extract_assistant_result(self, payload: Any) -> tuple[str, str | None]:
        if isinstance(payload, dict):
            assistant_message = str(
                payload.get("assistant_message")
                or payload.get("message")
                or payload.get("response")
                or ""
            ).strip()

            updated_markdown = payload.get("updated_markdown")
            if updated_markdown is None:
                updated_markdown = payload.get("markdown")

            if updated_markdown is not None:
                return assistant_message, str(updated_markdown)

            return assistant_message, None

        if isinstance(payload, str):
            parsed = extract_json_object(payload)
            if parsed is not None:
                return self._extract_assistant_result(parsed)
            return payload.strip(), None

        return "", None

    def chat_with_block_agent(
        self,
        workspace_id: str,
        run_id: str,
        block_id: str,
        user_message: str,
        *,
        selected_snippet: str | None = None,
        auto_apply: bool = True,
        conversation_id: int | None = None,
        chat_agent_id: int | None = None,
    ) -> dict[str, Any]:
        run = self.repository.get_run(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Generated run not found")

        block = self.repository.get_block(run_id, block_id)
        if block is None:
            raise ValueError("Block not found")

        mentions = [selected_snippet] if selected_snippet else []
        self._create_message(block_id=block_id, role="user", content=user_message, mentions=mentions)

        agent_id = chat_agent_id if chat_agent_id is not None else settings.mattin_block_chat_agent_id
        assistant_message = ""
        proposed_content: str | None = None
        updated_content: str | None = None
        applied = False
        final_conversation_id = conversation_id

        if agent_id is None:
            assistant_message = (
                "Block chat agent is not configured. "
                "Set MATTIN_BLOCK_CHAT_AGENT_ID to enable assisted edits."
            )
        else:
            message = self._build_block_chat_message(
                workspace_id=workspace_id,
                run_id=run_id,
                block_id=block_id,
                block_title=block.title,
                block_type=block.block_type,
                block_content=block.content,
                user_message=user_message,
                selected_snippet=selected_snippet,
            )

            try:
                response = self.mattin_client.call_agent(
                    agent_id=agent_id,
                    message=message,
                    conversation_id=conversation_id,
                )
                response_conversation_id = response.get("conversation_id")
                if isinstance(response_conversation_id, int):
                    final_conversation_id = response_conversation_id

                assistant_message, candidate_markdown = self._extract_assistant_result(
                    response.get("response")
                )
                if candidate_markdown and candidate_markdown.strip():
                    proposed_content = candidate_markdown.strip()

                if auto_apply and proposed_content:
                    block.content = proposed_content
                    saved_block = self.repository.save_block(block)
                    applied = True
                    updated_content = saved_block.content
            except MattinClientError as exc:
                logger.warning("Block chat agent call failed. run_id=%s block_id=%s error=%s", run_id, block_id, exc)
                assistant_message = f"Mattin agent call failed: {exc}"

        if not assistant_message:
            assistant_message = "The assistant did not return any actionable response."

        self._create_message(block_id=block_id, role="assistant", content=assistant_message, mentions=[])

        return {
            "assistant_message": assistant_message,
            "conversation_id": final_conversation_id,
            "applied": applied,
            "proposed_content": proposed_content,
            "updated_content": updated_content,
        }

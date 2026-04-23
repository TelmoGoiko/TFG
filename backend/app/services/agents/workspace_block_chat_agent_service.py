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
        run_id: str,
        block_title: str,
        block_type: str,
        block_content: str,
        user_message: str,
        selected_snippet: str | None,
    ) -> str:
        outline = self.repository.list_blocks(run_id)
        outline_text = "\n".join(
            f"- [{item.order_index + 1}] {item.title}: {item.summary}" for item in outline
        )
        snippet_text = selected_snippet.strip() if selected_snippet else ""

        return (
            "You are an editing assistant for one markdown block of a bigger document. "
            "Return ONLY valid JSON with this shape:\n"
            "{\n"
            '  "assistant_message": "string",\n'
            '  "updated_markdown": "string or null"\n'
            "}\n\n"
            "Rules:\n"
            "- assistant_message: concise explanation of proposed changes.\n"
            "- updated_markdown: full rewritten markdown only if a rewrite is requested; otherwise null.\n"
            "- Keep consistency with the document outline.\n"
            "- Do not add markdown fences around JSON.\n\n"
            f"Document outline:\n{outline_text}\n\n"
            f"Current block title: {block_title}\n"
            f"Current block type: {block_type}\n"
            f"Current block markdown:\n{block_content}\n\n"
            f"Selected snippet (if any):\n{snippet_text or 'none'}\n\n"
            f"User request:\n{user_message.strip()}"
        )

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
                run_id=run_id,
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

                if auto_apply and candidate_markdown and candidate_markdown.strip():
                    block.content = candidate_markdown.strip()
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
            "updated_content": updated_content,
        }

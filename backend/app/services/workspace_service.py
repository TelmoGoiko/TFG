from datetime import UTC, datetime
from io import BytesIO
import json
import logging
import re
from typing import Any
import zipfile

from app.core.config import settings
from app.integrations.mattin_client import MattinClient, MattinClientError
from app.models.block import Block
from app.models.chat_message import ChatMessage
from app.models.document import Document
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_file import WorkspaceFile
from app.models.workspace_run import WorkspaceRun
from app.repositories.workspace_repository import WorkspaceRepository
from app.utils.ids import new_id
from app.utils.json_payload import extract_json_object
from app.utils.markdown_blocks import build_default_blocks, create_file_name


logger = logging.getLogger(__name__)

class WorkspaceService:
    def __init__(self, repository: WorkspaceRepository, mattin_client: MattinClient) -> None:
        self.repository = repository
        self.mattin_client = mattin_client

    def list_workspaces(self, owner_id: str) -> list[Workspace]:
        # Keep workspace CRUD in local DB so list/create/get/delete stay consistent.
        return self.repository.list_workspaces(owner_id)

    def create_workspace(self, owner_id: str, name: str, description: str) -> Workspace:
        if not name.strip():
            raise ValueError("Workspace name is required")

        owner = self.repository.get_user_by_id(owner_id)
        if owner is None:
            synthetic_email = f"{owner_id.strip().lower()}@external.local"
            owner = User(
                id=owner_id,
                email=synthetic_email,
                password_hash="external-owner",
                created_at=datetime.now(UTC),
            )
            self.repository.create_user(owner)

        model = Workspace(
            id=new_id(),
            owner_id=owner_id,
            name=name.strip(),
            description=description.strip(),
            created_at=datetime.now(UTC),
        )
        return self.repository.create_workspace(model)

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        return self.repository.get_workspace(workspace_id)

    def delete_workspace(self, workspace_id: str) -> bool:
        return self.repository.delete_workspace(workspace_id)

    def list_documents(self, workspace_id: str) -> list[Document]:
        return self.repository.list_documents(workspace_id)

    def create_document(self, workspace_id: str, title: str, content: str) -> Document:
        if not title.strip():
            raise ValueError("Document title is required")

        model = Document(
            id=new_id(),
            workspace_id=workspace_id,
            title=title.strip(),
            content=content,
            created_at=datetime.now(UTC),
        )
        return self.repository.create_document(model)

    def delete_document(self, document_id: str) -> bool:
        return self.repository.delete_document(document_id)

    def list_files(self, workspace_id: str) -> list[WorkspaceFile]:
        return self.repository.list_files(workspace_id)

    def create_file(
        self,
        workspace_id: str,
        file_name: str,
        mime_type: str,
        content_bytes: bytes,
    ) -> WorkspaceFile:
        if not file_name.strip():
            raise ValueError("File name is required")

        model = WorkspaceFile(
            id=new_id(),
            workspace_id=workspace_id,
            file_name=file_name,
            mime_type=mime_type or "application/octet-stream",
            size_bytes=len(content_bytes),
            content_bytes=content_bytes,
            created_at=datetime.now(UTC),
        )
        return self.repository.create_file(model)

    def delete_file(self, file_id: str) -> bool:
        return self.repository.delete_file(file_id)

    def get_file(self, workspace_id: str, file_id: str) -> WorkspaceFile | None:
        return self.repository.get_file(workspace_id, file_id)

    def build_workspace_zip(self, workspace_id: str) -> tuple[str, bytes] | None:
        workspace = self.repository.get_workspace(workspace_id)
        if workspace is None:
            return None

        workspace_files = self.repository.list_files(workspace_id)
        documents = self.repository.list_documents(workspace_id)

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for workspace_file in workspace_files:
                zip_file.writestr(workspace_file.file_name, workspace_file.content_bytes)

            for document in documents:
                doc_name = f"generated-documents/{document.title}.md"
                zip_file.writestr(doc_name, document.content)

        archive_name = f"{workspace.name.replace(' ', '_') or 'workspace'}_bundle.zip"
        return archive_name, zip_buffer.getvalue()

    def _build_generation_message(self, prompt: str, reference_titles: list[str]) -> str:
        references_section = (
            "\n".join(f"- {title}" for title in reference_titles)
            if reference_titles
            else "- No references available"
        )

        return (
            "You generate a technical document split into markdown blocks. "
            "Return ONLY valid JSON with this exact shape:\n"
            "{\n"
            '  "blocks": [\n'
            "    {\n"
            '      "title": "string",\n'
            '      "block_type": "index|chapter|closing",\n'
            '      "summary": "string",\n'
            '      "markdown": "full markdown content"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- Include between 4 and 8 blocks.\n"
            "- First block should be an index block with links to chapter files.\n"
            "- Keep markdown practical and directly editable.\n"
            "- Do not wrap JSON in markdown fences.\n\n"
            f"User request:\n{prompt.strip()}\n\n"
            f"Known references:\n{references_section}"
        )

    def _normalize_agent_generated_blocks(self, payload: dict[str, Any]) -> list[dict[str, Any]] | None:
        blocks_raw = payload.get("blocks")
        if not isinstance(blocks_raw, list) or not blocks_raw:
            return None

        normalized_blocks: list[dict[str, Any]] = []
        for order_index, item in enumerate(blocks_raw):
            if not isinstance(item, dict):
                continue

            title = str(item.get("title", "")).strip() or f"Block {order_index + 1}"
            block_type = str(item.get("block_type", "chapter")).strip() or "chapter"
            summary = str(item.get("summary", "")).strip()

            markdown_content = item.get("markdown")
            if markdown_content is None:
                markdown_content = item.get("content", "")

            normalized_blocks.append(
                {
                    "id": new_id(),
                    "order_index": order_index,
                    "title": title,
                    "block_type": block_type,
                    "summary": summary,
                    "file_name": create_file_name(order_index, title),
                    "content": str(markdown_content),
                }
            )

        return normalized_blocks or None

    def _coerce_generation_payload(self, payload: Any) -> dict[str, Any] | None:
        if payload is None:
            return None

        if isinstance(payload, str):
            parsed = extract_json_object(payload)
            if parsed is not None:
                return parsed

            # Some providers return a JSON-stringified value inside another string.
            try:
                decoded = json.loads(payload)
            except json.JSONDecodeError:
                decoded = None

            if decoded is not None:
                nested = self._coerce_generation_payload(decoded)
            else:
                nested = None

            return nested

        if isinstance(payload, dict):
            if isinstance(payload.get("blocks"), list):
                return payload

            for key in (
                "response",
                "output",
                "content",
                "text",
                "message",
                "result",
                "data",
                "assistant_response",
            ):
                nested = self._coerce_generation_payload(payload.get(key))
                if nested is not None and isinstance(nested.get("blocks"), list):
                    return nested

            choices = payload.get("choices")
            if isinstance(choices, list):
                for choice in choices:
                    nested = self._coerce_generation_payload(choice)
                    if nested is not None and isinstance(nested.get("blocks"), list):
                        return nested

            return None

        if isinstance(payload, list):
            for item in payload:
                nested = self._coerce_generation_payload(item)
                if nested is not None and isinstance(nested.get("blocks"), list):
                    return nested

        return None

    def _generate_blocks_with_agent(
        self,
        prompt: str,
        reference_titles: list[str],
    ) -> list[dict[str, Any]] | None:
        agent_id = settings.mattin_generation_agent_id
        if agent_id is None:
            return None

        timeout_seconds = max(5, settings.mattin_generation_timeout_seconds)
        max_retries = max(0, settings.mattin_generation_max_retries)
        total_attempts = max_retries + 1

        message = self._build_generation_message(prompt=prompt, reference_titles=reference_titles)
        logger.info(
            "Generation run started. agent_id=%s prompt_len=%s references=%s timeout_s=%s retries=%s",
            agent_id,
            len(prompt.strip()),
            reference_titles,
            timeout_seconds,
            max_retries,
        )

        response: dict[str, Any] | None = None
        for attempt in range(1, total_attempts + 1):
            try:
                response = self.mattin_client.call_agent(
                    agent_id=agent_id,
                    message=message,
                    timeout=timeout_seconds,
                )
                break
            except MattinClientError as exc:
                logger.warning(
                    "Generation agent call failed. agent_id=%s attempt=%s/%s error=%s",
                    agent_id,
                    attempt,
                    total_attempts,
                    exc,
                )
                if attempt == total_attempts:
                    return None

        if response is None:
            return None

        response_payload = response.get("response")
        logger.info(
            "Generation agent raw response received. keys=%s response_type=%s",
            sorted(response.keys()),
            type(response_payload).__name__,
        )

        parsed_payload = self._coerce_generation_payload(response_payload)

        if parsed_payload is None:
            logger.warning(
                "Generation agent response could not be parsed into blocks payload. response_keys=%s",
                sorted(response.keys()),
            )
            return None

        blocks = parsed_payload.get("blocks")
        logger.info(
            "Generation payload parsed. blocks_count=%s first_title=%s",
            len(blocks) if isinstance(blocks, list) else 0,
            blocks[0].get("title") if isinstance(blocks, list) and blocks and isinstance(blocks[0], dict) else None,
        )

        return self._normalize_agent_generated_blocks(parsed_payload)

    def create_run(
        self,
        workspace_id: str,
        prompt: str,
        reference_document_ids: list[str],
        reference_file_ids: list[str],
    ) -> WorkspaceRun:
        if not prompt.strip():
            raise ValueError("Prompt is required")

        references = self.repository.get_documents_by_ids(workspace_id, reference_document_ids)
        reference_files = self.repository.get_files_by_ids(workspace_id, reference_file_ids)
        reference_titles = [doc.title for doc in references] + [
            file.file_name for file in reference_files
        ]

        workspace_run = WorkspaceRun(
            id=new_id(),
            workspace_id=workspace_id,
            prompt=prompt,
            status="draft",
            created_at=datetime.now(UTC),
        )

        logger.info(
            "Creating run. run_id=%s workspace_id=%s reference_docs=%s reference_files=%s",
            workspace_run.id,
            workspace_id,
            len(reference_document_ids),
            len(reference_file_ids),
        )

        generated_blocks = self._generate_blocks_with_agent(
            prompt=prompt,
            reference_titles=reference_titles,
        )
        if generated_blocks is None:
            logger.warning(
                "Falling back to default blocks for run=%s workspace=%s",
                workspace_run.id,
                workspace_id,
            )
            generated_blocks = build_default_blocks(prompt=prompt, reference_titles=reference_titles)
            workspace_run.status = "fallback"
        else:
            workspace_run.status = "generated"

        logger.info(
            "Run generation status decided. run_id=%s status=%s blocks_count=%s",
            workspace_run.id,
            workspace_run.status,
            len(generated_blocks),
        )

        block_models = [
            Block(
                id=data["id"],
                workspace_run_id=workspace_run.id,
                order_index=data["order_index"],
                title=data["title"],
                block_type=data["block_type"],
                summary=data["summary"],
                file_name=data["file_name"],
                content=data["content"],
            )
            for data in generated_blocks
        ]

        created_run = self.repository.create_run_with_blocks(workspace_run, block_models)
        persisted_blocks = self.repository.list_blocks(created_run.id)
        logger.info(
            "Run persisted. run_id=%s persisted_blocks=%s persisted_titles=%s",
            created_run.id,
            len(persisted_blocks),
            [block.title for block in persisted_blocks],
        )
        return created_run

    def get_run(self, run_id: str) -> WorkspaceRun | None:
        return self.repository.get_run(run_id)

    def delete_run(self, workspace_id: str, run_id: str) -> bool:
        run = self.repository.get_run(run_id)
        if run is None or run.workspace_id != workspace_id:
            return False

        return self.repository.delete_run(run_id)

    def list_runs(self, workspace_id: str) -> list[WorkspaceRun]:
        return self.repository.list_runs(workspace_id=workspace_id)

    def list_blocks(self, run_id: str) -> list[Block]:
        return self.repository.list_blocks(run_id)

    def get_block(self, run_id: str, block_id: str) -> Block | None:
        return self.repository.get_block(run_id, block_id)

    def update_block_content(self, run_id: str, block_id: str, content: str) -> Block | None:
        block = self.repository.get_block(run_id, block_id)
        if block is None:
            return None

        block.content = content
        return self.repository.save_block(block)

    def list_messages(self, block_id: str) -> list[ChatMessage]:
        return self.repository.list_messages(block_id)

    def create_message(
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

    def clear_block_messages(self, workspace_id: str, run_id: str, block_id: str) -> int:
        run = self.repository.get_run(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Generated run not found")

        block = self.repository.get_block(run_id, block_id)
        if block is None:
            raise ValueError("Block not found")

        return self.repository.delete_messages_by_block(block_id)

    def _build_block_chat_message(
        self,
        run_id: str,
        block: Block,
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
            f"Current block title: {block.title}\n"
            f"Current block type: {block.block_type}\n"
            f"Current block markdown:\n{block.content}\n\n"
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
        self.create_message(block_id=block_id, role="user", content=user_message, mentions=mentions)

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
                block=block,
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
                    saved_block = self.update_block_content(
                        run_id=run_id,
                        block_id=block_id,
                        content=candidate_markdown.strip(),
                    )
                    if saved_block is not None:
                        applied = True
                        updated_content = saved_block.content
            except MattinClientError as exc:
                assistant_message = f"Mattin agent call failed: {exc}"

        if not assistant_message:
            assistant_message = "The assistant did not return any actionable response."

        self.create_message(block_id=block_id, role="assistant", content=assistant_message, mentions=[])

        return {
            "assistant_message": assistant_message,
            "conversation_id": final_conversation_id,
            "applied": applied,
            "updated_content": updated_content,
        }

    def get_run_outline(self, workspace_id: str, run_id: str) -> list[dict[str, Any]]:
        run = self.repository.get_run(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Generated run not found")

        return [
            {
                "block_id": block.id,
                "order_index": block.order_index,
                "title": block.title,
                "summary": block.summary,
                "file_name": block.file_name,
            }
            for block in self.repository.list_blocks(run_id)
        ]

    def review_run_consistency(self, workspace_id: str, run_id: str) -> dict[str, Any]:
        run = self.repository.get_run(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Generated run not found")

        blocks = self.repository.list_blocks(run_id)
        issues: list[dict[str, str]] = []

        seen_titles: dict[str, str] = {}
        file_names = {block.file_name for block in blocks}

        for block in blocks:
            title_key = block.title.strip().lower()
            if title_key in seen_titles:
                issues.append(
                    {
                        "type": "duplicate_title",
                        "message": (
                            f"Block '{block.title}' duplicates title from block {seen_titles[title_key]}."
                        ),
                    }
                )
            else:
                seen_titles[title_key] = block.id

            linked_files = re.findall(r"\((?:\./)?([^\)\s]+\.md)\)", block.content)
            for linked_file in linked_files:
                if linked_file not in file_names:
                    issues.append(
                        {
                            "type": "broken_block_link",
                            "message": (
                                f"Block '{block.title}' links to '{linked_file}', but no block has that file name."
                            ),
                        }
                    )

        return {
            "run_id": run_id,
            "issue_count": len(issues),
            "issues": issues,
        }

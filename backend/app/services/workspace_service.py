from datetime import UTC, datetime
from io import BytesIO
import logging
import os
import re
from typing import Any
import zipfile

from app.core.config import settings
from app.integrations.mattin_client import MattinClient, MattinClientError
from app.models.block import Block
from app.models.chat_message import ChatMessage
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_file import WorkspaceFile
from app.models.workspace_run import WorkspaceRun
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.agents.workspace_block_chat_agent_service import WorkspaceBlockChatAgentService
from app.services.agents.workspace_generation_agent_service import WorkspaceGenerationAgentService
from app.services.block_impact_service import BlockImpactService
from app.services.block_relationship_service import BlockRelationshipService
from app.utils.ids import new_id
from app.utils.markdown_blocks import build_default_blocks, create_file_name


logger = logging.getLogger(__name__)

class WorkspaceService:
    def __init__(self, repository: WorkspaceRepository, mattin_client: MattinClient) -> None:
        self.repository = repository
        self.mattin_client = mattin_client
        self.generation_agent_service = WorkspaceGenerationAgentService(mattin_client=mattin_client)
        self.block_chat_agent_service = WorkspaceBlockChatAgentService(
            repository=repository,
            mattin_client=mattin_client,
        )
        self.relationship_service = BlockRelationshipService(
            repository=repository,
            mattin_client=mattin_client,
        )
        self.impact_service = BlockImpactService(
            repository=repository,
            mattin_client=mattin_client,
        )

    def list_workspaces(self, owner_id: str) -> list[Workspace]:
        self._sync_workspaces_from_mattin(owner_id=owner_id)
        return self.repository.list_workspaces(owner_id)

    def _parse_mattin_datetime(self, value: Any) -> datetime:
        if isinstance(value, str) and value.strip():
            normalized = value.strip().replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(normalized)
                if parsed.tzinfo is None:
                    return parsed.replace(tzinfo=UTC)
                return parsed
            except ValueError:
                pass
        return datetime.now(UTC)

    def _sync_workspaces_from_mattin(self, owner_id: str) -> None:
        try:
            repositories = self.mattin_client.get_all_repositories()
        except MattinClientError as exc:
            logger.warning("Could not sync workspaces from Mattin: %s", exc)
            return

        synced = 0
        for repository in repositories:
            if not isinstance(repository, dict):
                continue

            repository_id = self._extract_mattin_identifier(repository)
            if repository_id is None:
                continue

            workspace = self.repository.get_workspace_by_mattin_repository_id(repository_id)
            if workspace is None:
                workspace = Workspace(
                    id=new_id(),
                    owner_id=owner_id,
                    name=str(repository.get("name") or f"Repository {repository_id}"),
                    description=str(repository.get("description") or ""),
                    mattin_repository_id=repository_id,
                    created_at=self._parse_mattin_datetime(repository.get("create_date")),
                )
                self.repository.create_workspace(workspace)
                synced += 1
                continue

            updated = False
            next_name = str(repository.get("name") or workspace.name)
            next_description = str(repository.get("description") or workspace.description)
            if workspace.name != next_name:
                workspace.name = next_name
                updated = True
            if workspace.description != next_description:
                workspace.description = next_description
                updated = True
            if updated:
                self.repository.save_workspace(workspace)
                synced += 1

        if synced:
            logger.info("Synced workspaces from Mattin. owner_id=%s changed=%s", owner_id, synced)

    def _extract_nested_identifier(self, payload: Any, keys: tuple[str, ...]) -> str | None:
        if isinstance(payload, dict):
            for key in keys:
                value = payload.get(key)
                if value is None:
                    continue
                if isinstance(value, (str, int)):
                    value_text = str(value).strip()
                    if value_text:
                        return value_text

            for value in payload.values():
                nested = self._extract_nested_identifier(value, keys)
                if nested is not None:
                    return nested

        if isinstance(payload, list):
            for item in payload:
                nested = self._extract_nested_identifier(item, keys)
                if nested is not None:
                    return nested

        return None

    def _extract_mattin_identifier(self, payload: dict[str, Any]) -> str | None:
        return self._extract_nested_identifier(payload, ("id", "repository_id", "repo_id"))

    def _extract_mattin_file_identifier(self, payload: dict[str, Any]) -> int | None:
        value = self._extract_nested_identifier(
            payload,
            ("id", "doc_id", "file_id", "document_id", "resource_id"),
        )
        if value is None or not value.isdigit():
            return None
        return int(value)

    def _ensure_workspace_mattin_repository(self, workspace: Workspace) -> Workspace:
        if workspace.mattin_repository_id:
            return workspace

        try:
            created_repository = self.mattin_client.create_repository(workspace.name)
        except MattinClientError as exc:
            raise ValueError(f"Could not create Mattin repository for workspace: {exc}") from exc

        repository_id = self._extract_mattin_identifier(created_repository)
        if repository_id is None:
            logger.warning(
                "Mattin repository creation payload without id. keys=%s payload=%s",
                sorted(created_repository.keys()),
                created_repository,
            )
            raise ValueError("Mattin repository creation did not return a repository id")

        workspace.mattin_repository_id = repository_id
        saved_workspace = self.repository.save_workspace(workspace)
        logger.info(
            "Workspace linked to Mattin repository. workspace_id=%s mattin_repository_id=%s",
            saved_workspace.id,
            saved_workspace.mattin_repository_id,
        )
        return saved_workspace

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

        # Create Mattin repository first — if it fails, nothing is persisted locally
        try:
            created_repository = self.mattin_client.create_repository(name.strip())
        except MattinClientError as exc:
            raise ValueError(f"Could not create Mattin repository for workspace: {exc}") from exc

        repository_id = self._extract_mattin_identifier(created_repository)
        if repository_id is None:
            logger.warning(
                "Mattin repository creation payload without id. keys=%s payload=%s",
                sorted(created_repository.keys()),
                created_repository,
            )
            raise ValueError("Mattin repository creation did not return a repository id")

        model = Workspace(
            id=new_id(),
            owner_id=owner_id,
            name=name.strip(),
            description=description.strip(),
            mattin_repository_id=repository_id,
            created_at=datetime.now(UTC),
        )
        return self.repository.create_workspace(model)

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        return self.repository.get_workspace(workspace_id)

    def delete_workspace(self, workspace_id: str) -> bool:
        workspace = self.repository.get_workspace(workspace_id)
        if workspace is None:
            return False

        if workspace.mattin_repository_id:
            try:
                self.mattin_client.delete_repository(workspace.mattin_repository_id)
            except MattinClientError as exc:
                logger.warning(
                    "Could not delete Mattin repository %s: %s",
                    workspace.mattin_repository_id,
                    exc,
                )

        return self.repository.delete_workspace(workspace_id)

    def list_files(self, workspace_id: str) -> list[WorkspaceFile]:
        self._sync_workspace_files_from_mattin(workspace_id=workspace_id)
        return self.repository.list_files(workspace_id)

    def _extract_resource_file_name(self, payload: dict[str, Any]) -> str | None:
        for key in ("uri", "file_name", "name", "title", "filename"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _normalize_resource_mime(self, payload: dict[str, Any]) -> str:
        for key in ("mime_type", "content_type", "type"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                text = value.strip()
                if text.startswith("."):
                    return {
                        ".pdf": "application/pdf",
                        ".txt": "text/plain",
                        ".md": "text/markdown",
                    }.get(text.lower(), "application/octet-stream")
                return text
        return "application/octet-stream"

    def _extract_resource_size(self, payload: dict[str, Any]) -> int:
        value = payload.get("size")
        if isinstance(value, int) and value >= 0:
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return 0

    def _sync_workspace_files_from_mattin(self, workspace_id: str) -> None:
        workspace = self.repository.get_workspace(workspace_id)
        if workspace is None or not workspace.mattin_repository_id:
            return

        try:
            resources = self.mattin_client.get_repository_resources(workspace.mattin_repository_id)
        except MattinClientError as exc:
            logger.warning(
                "Could not sync files from Mattin. workspace_id=%s repository_id=%s error=%s",
                workspace_id,
                workspace.mattin_repository_id,
                exc,
            )
            return

        remote_file_ids: set[int] = set()
        changed = 0
        for resource in resources:
            if not isinstance(resource, dict):
                continue

            mattin_file_id = self._extract_mattin_file_identifier(resource)
            file_name = self._extract_resource_file_name(resource)
            if mattin_file_id is None or not file_name:
                continue

            remote_file_ids.add(mattin_file_id)

            local_file = self.repository.get_file_by_mattin_file_id(workspace_id, mattin_file_id)
            if local_file is None:
                model = WorkspaceFile(
                    id=new_id(),
                    workspace_id=workspace_id,
                    file_name=file_name,
                    mime_type=self._normalize_resource_mime(resource),
                    size_bytes=self._extract_resource_size(resource),
                    mattin_file_id=mattin_file_id,
                    content_bytes=b"",
                    created_at=self._parse_mattin_datetime(resource.get("create_date")),
                )
                self.repository.create_file(model)
                changed += 1
                continue

            updated = False
            next_name = file_name
            next_mime = self._normalize_resource_mime(resource)
            next_size = self._extract_resource_size(resource)
            if local_file.file_name != next_name:
                local_file.file_name = next_name
                updated = True
            if local_file.mime_type != next_mime:
                local_file.mime_type = next_mime
                updated = True
            if local_file.size_bytes != next_size:
                local_file.size_bytes = next_size
                updated = True
            if updated:
                self.repository.save_file(local_file)
                changed += 1

        # Remove stale Mattin-backed entries so the workspace file list mirrors Mattin.
        for local_file in self.repository.list_files(workspace_id):
            if not isinstance(local_file.mattin_file_id, int):
                continue
            if local_file.mattin_file_id not in remote_file_ids:
                self.repository.delete_file(local_file.id)
                changed += 1

        if changed:
            logger.info(
                "Synced workspace files from Mattin. workspace_id=%s repository_id=%s changed=%s",
                workspace_id,
                workspace.mattin_repository_id,
                changed,
            )

    def create_file(
        self,
        workspace_id: str,
        file_name: str,
        mime_type: str,
        content_bytes: bytes,
    ) -> WorkspaceFile:
        if not file_name.strip():
            raise ValueError("File name is required")

        workspace = self.repository.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError("Workspace not found")

        workspace = self._ensure_workspace_mattin_repository(workspace)

        resolved_mime_type = mime_type or "application/octet-stream"
        try:
            mattin_payload = self.mattin_client.upload_repository_file(
                repository_id=workspace.mattin_repository_id or "",
                file_name=file_name,
                content_bytes=content_bytes,
                mime_type=resolved_mime_type,
            )
        except MattinClientError as exc:
            raise ValueError(f"Could not upload file to Mattin repository: {exc}") from exc

        mattin_file_id = self._extract_mattin_file_identifier(mattin_payload)
        if mattin_file_id is None:
            logger.warning(
                "Mattin file upload payload without file id. keys=%s payload=%s",
                sorted(mattin_payload.keys()),
                mattin_payload,
            )
            raise ValueError("Mattin file upload did not return a file id")

        model = WorkspaceFile(
            id=new_id(),
            workspace_id=workspace_id,
            file_name=file_name,
            mime_type=resolved_mime_type,
            size_bytes=len(content_bytes),
            mattin_file_id=mattin_file_id,
            content_bytes=b"",
            created_at=datetime.now(UTC),
        )
        logger.info(
            "Workspace file uploaded to Mattin. workspace_id=%s file_name=%s mattin_file_id=%s",
            workspace_id,
            file_name,
            mattin_file_id,
        )
        return self.repository.create_file(model)

    def persist_chart_images_in_markdown(self, workspace_id: str, markdown: str) -> str:
        return self.block_chat_agent_service.persist_chart_images_in_markdown(workspace_id, markdown)

    def delete_file(self, workspace_id: str, file_id: str) -> bool:
        workspace_file = self.repository.get_file(workspace_id, file_id)
        if workspace_file is None:
            return False

        workspace = self.repository.get_workspace(workspace_id)
        if workspace is None:
            return False

        if workspace.mattin_repository_id and isinstance(workspace_file.mattin_file_id, int):
            try:
                self.mattin_client.delete_repository_resource(
                    repository_id=workspace.mattin_repository_id,
                    resource_id=workspace_file.mattin_file_id,
                )
            except MattinClientError as exc:
                if "status 404" not in str(exc):
                    raise ValueError(f"Could not delete file from Mattin repository: {exc}") from exc
                logger.warning(
                    "Mattin file not found while deleting. workspace_id=%s file_id=%s mattin_file_id=%s",
                    workspace_id,
                    file_id,
                    workspace_file.mattin_file_id,
                )

        return self.repository.delete_file(file_id)

    def get_file(self, workspace_id: str, file_id: str) -> WorkspaceFile | None:
        return self.repository.get_file(workspace_id, file_id)

    def build_workspace_zip(self, workspace_id: str) -> tuple[str, bytes] | None:
        workspace = self.repository.get_workspace(workspace_id)
        if workspace is None:
            return None

        workspace_files = self.repository.list_files(workspace_id)

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for workspace_file in workspace_files:
                file_bytes = workspace_file.content_bytes
                if (
                    not file_bytes
                    and isinstance(workspace_file.mattin_file_id, int)
                    and workspace.mattin_repository_id
                ):
                    try:
                        file_bytes, _content_type = self.mattin_client.fetch_resource_view(
                            repository_id=workspace.mattin_repository_id,
                            resource_id=workspace_file.mattin_file_id,
                        )
                    except MattinClientError as exc:
                        logger.warning(
                            "build_workspace_zip: Mattin fetch failed. file_id=%s error=%s",
                            workspace_file.id, exc,
                        )
                        file_bytes = workspace_file.content_bytes
                zip_file.writestr(workspace_file.file_name, file_bytes)

        archive_name = f"{workspace.name.replace(' ', '_') or 'workspace'}_bundle.zip"
        return archive_name, zip_buffer.getvalue()

    def create_run(
        self,
        workspace_id: str,
        prompt: str,
        reference_file_ids: list[str],
    ) -> WorkspaceRun:
        if not prompt.strip():
            raise ValueError("Prompt is required")

        reference_files = self.repository.get_files_by_ids(workspace_id, reference_file_ids)
        reference_titles = [file.file_name for file in reference_files]

        image_files = [file for file in reference_files if file.mime_type.startswith("image/")]
        file_uploads = [
            ("files", (file.file_name, file.content_bytes, file.mime_type))
            for file in image_files
            if file.content_bytes
        ]

        workspace_run = WorkspaceRun(
            id=new_id(),
            workspace_id=workspace_id,
            prompt=prompt,
            status="draft",
            created_at=datetime.now(UTC),
        )

        logger.info(
            "Creating run. run_id=%s workspace_id=%s reference_files=%s",
            workspace_run.id,
            workspace_id,
            len(reference_file_ids),
        )

        mattin_reference_file_ids = [
            file.mattin_file_id
            for file in reference_files
            if not file.mime_type.startswith("image/") and isinstance(file.mattin_file_id, int)
        ]

        generated_blocks = self.generation_agent_service.generate_blocks(
            prompt=prompt,
            reference_titles=reference_titles,
            reference_file_ids=mattin_reference_file_ids,
            file_uploads=file_uploads or None,
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

        block_models = []
        for data in generated_blocks:
            raw_content = str(data.get("content") or "")
            content = self.persist_chart_images_in_markdown(workspace_id, raw_content)
            block_models.append(
                Block(
                    id=data["id"],
                    workspace_run_id=workspace_run.id,
                    order_index=data["order_index"],
                    title=data["title"],
                    block_type=data["block_type"],
                    summary=data["summary"],
                    file_name=data["file_name"],
                    content=content,
                )
            )

        created_run = self.repository.create_run_with_blocks(workspace_run, block_models)
        persisted_blocks = self.repository.list_blocks(created_run.id)
        logger.info(
            "Run persisted. run_id=%s persisted_blocks=%s persisted_titles=%s",
            created_run.id,
            len(persisted_blocks),
            [block.title for block in persisted_blocks],
        )

        self.relationship_service.detect_relationships_from_generation(
            run_id=created_run.id,
            blocks=persisted_blocks,
        )
        logger.info(
            "Block relationships detected. run_id=%s relationships_count=%s",
            created_run.id,
            len(self.relationship_service.get_relationships_for_block(persisted_blocks[0].id)) if persisted_blocks else 0,
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

    def update_block_content(self, workspace_id: str, run_id: str, block_id: str, content: str) -> Block | None:
        block = self.repository.get_block(run_id, block_id)
        if block is None:
            return None

        block.content = self.persist_chart_images_in_markdown(workspace_id, content)
        block.refresh_meta_on_save()
        saved_block = self.repository.save_block(block)
        self.relationship_service.update_block_metadata(block)
        self._refresh_relationships_for_run(run_id)

        return saved_block

    def _refresh_relationships_for_run(self, run_id: str) -> None:
        blocks = self.repository.list_blocks(run_id)
        if not blocks:
            return

        self.relationship_service.detect_relationships_from_generation(
            run_id=run_id,
            blocks=blocks,
        )
        logger.info("Block relationships refreshed. run_id=%s blocks=%s", run_id, len(blocks))

    def _normalize_insert_index(self, blocks: list[Block], desired_index: int | None) -> int:
        if desired_index is None:
            return len(blocks)
        if desired_index < 0:
            return 0
        if desired_index > len(blocks):
            return len(blocks)
        return desired_index

    def _build_unique_file_name(self, run_id: str, order_index: int, title: str) -> str:
        base_name = create_file_name(order_index, title)
        existing = {block.file_name for block in self.repository.list_blocks(run_id)}
        if base_name not in existing:
            return base_name

        if base_name.endswith(".md"):
            stem = base_name[:-3]
            ext = ".md"
        else:
            stem = base_name
            ext = ""

        counter = 2
        while counter < 1000:
            candidate = f"{stem}-{counter}{ext}"
            if candidate not in existing:
                return candidate
            counter += 1

        return f"{stem}-{new_id()[:8]}{ext}"

    def create_block(
        self,
        workspace_id: str,
        run_id: str,
        title: str,
        summary: str,
        content: str,
        block_type: str,
        file_name: str | None = None,
        order_index: int | None = None,
        insert_before_block_id: str | None = None,
        insert_after_block_id: str | None = None,
    ) -> Block:
        run = self.repository.get_run(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Generated run not found")

        if insert_before_block_id and insert_after_block_id:
            raise ValueError("Provide only one insert position")

        blocks = self.repository.list_blocks(run_id)
        target_index = None

        if insert_before_block_id:
            before_block = next((b for b in blocks if b.id == insert_before_block_id), None)
            if before_block is None:
                raise ValueError("Insert-before block not found")
            target_index = before_block.order_index

        if insert_after_block_id:
            after_block = next((b for b in blocks if b.id == insert_after_block_id), None)
            if after_block is None:
                raise ValueError("Insert-after block not found")
            target_index = after_block.order_index + 1

        if target_index is None:
            target_index = order_index

        insert_index = self._normalize_insert_index(blocks, target_index)

        for block in blocks:
            if block.order_index >= insert_index:
                block.order_index += 1
                self.repository.save_block(block)

        resolved_title = title.strip() or "Untitled block"
        resolved_summary = summary.strip()
        resolved_content = content or ""
        resolved_content = self.persist_chart_images_in_markdown(workspace_id, resolved_content)
        resolved_block_type = block_type.strip() or "chapter"
        resolved_file_name = (file_name or "").strip()
        if not resolved_file_name:
            resolved_file_name = self._build_unique_file_name(run_id, insert_index, resolved_title)
        else:
            existing_names = {block.file_name for block in blocks}
            if resolved_file_name in existing_names:
                resolved_file_name = self._build_unique_file_name(run_id, insert_index, resolved_title)

        model = Block(
            id=new_id(),
            workspace_run_id=run_id,
            order_index=insert_index,
            title=resolved_title,
            block_type=resolved_block_type,
            summary=resolved_summary,
            file_name=resolved_file_name,
            content=resolved_content,
        )
        model.refresh_meta_on_save()
        return self.repository.create_block(model)

    def delete_block(self, workspace_id: str, run_id: str, block_id: str) -> bool:
        run = self.repository.get_run(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Generated run not found")

        block = self.repository.get_block(run_id, block_id)
        if block is None:
            raise ValueError("Block not found")

        deleted_order = block.order_index
        deleted = self.repository.delete_block(block_id)

        if not deleted:
            return False

        blocks = self.repository.list_blocks(run_id)
        for remaining in blocks:
            if remaining.order_index > deleted_order:
                remaining.order_index -= 1
                self.repository.save_block(remaining)

        return True

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

    def chat_with_block_agent(
        self,
        workspace_id: str,
        run_id: str,
        block_id: str,
        user_message: str,
        *,
        selected_snippet: str | None = None,
        conversation_id: int | None = None,
        chat_agent_id: int | None = None,
    ) -> dict[str, Any]:
        run = self.repository.get_run(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Generated run not found")

        block = self.repository.get_block(run_id, block_id)
        if block is None:
            raise ValueError("Block not found")

        original_content = block.content

        result = self.block_chat_agent_service.chat_with_block_agent(
            workspace_id=workspace_id,
            run_id=run_id,
            block_id=block_id,
            user_message=user_message,
            selected_snippet=selected_snippet,
            conversation_id=conversation_id,
            chat_agent_id=chat_agent_id,
        )

        if result.get("blocks_modified"):
            self._refresh_relationships_for_run(run_id)

        candidate_content = (
            result.get("updated_content") if result.get("applied") else result.get("proposed_content")
        )
        if isinstance(candidate_content, str) and candidate_content.strip() and candidate_content != original_content:
            logger.info(f"Content updated for block {block_id}")
            impact_suggestions = self.impact_service.check_impact(
                run_id=run_id,
                block_id=block_id,
                original_content=original_content,
                new_content=candidate_content,
                conversation_id=result.get("conversation_id"),
            )
        else:
            impact_suggestions = []

        if result.get("applied") and impact_suggestions:
            for suggestion in impact_suggestions:
                logger.info(f"Applying impact suggestion to block {suggestion.affected_block_id} due to changes in block {block_id}")
                updated_block = self.impact_service.apply_suggestion(
                    run_id=run_id,
                    block_id=suggestion.affected_block_id,
                    suggestion=suggestion.suggestion,
                )
                if updated_block is not None:
                    self.repository.delete_impact_suggestion(suggestion.id)

        if impact_suggestions:
            block_by_id = {b.id: b for b in self.repository.list_blocks(run_id)}
        else:
            block_by_id = {}

        result["impact_suggestions"] = [
            {
                "id": s.id,
                "source_block_id": s.source_block_id,
                "affected_block_id": s.affected_block_id,
                "affected_block_title": block_by_id.get(s.affected_block_id).title if block_by_id.get(s.affected_block_id) else "",
                "suggestion": s.suggestion,
                "reason": s.reason,
                "relationship_type": s.relationship_type,
                "status": s.status,
                "conversation_id": s.conversation_id,
                "created_at": s.created_at,
            }
            for s in impact_suggestions
        ]
        return result

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

    def get_blocks_content(
        self,
        workspace_id: str,
        run_id: str,
        block_ids: list[str],
    ) -> list[dict[str, Any]]:
        run = self.repository.get_run(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Generated run not found")

        blocks = self.repository.get_blocks_by_ids(run_id, block_ids)
        return [
            {
                "block_id": b.id,
                "order_index": b.order_index,
                "title": b.title,
                "summary": b.summary,
                "block_type": b.block_type,
                "file_name": b.file_name,
                "content": b.content,
            }
            for b in blocks
        ]

    def review_run_consistency(self, workspace_id: str, run_id: str) -> dict[str, Any]:
        run = self.repository.get_run(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Generated run not found")

        blocks = self.repository.list_blocks(run_id)
        issues: list[dict[str, str]] = []

        seen_titles: dict[str, str] = {}

        def _normalize_file_name(value: str) -> str:
            trimmed = value.strip()
            trimmed = re.sub(r"^[./]+", "", trimmed)
            return os.path.basename(trimmed).lower()

        normalized_file_names: set[str] = set()
        for block in blocks:
            if not block.file_name:
                continue
            normalized = _normalize_file_name(block.file_name)
            normalized_file_names.add(normalized)
            if not normalized.endswith(".md"):
                normalized_file_names.add(f"{normalized}.md")

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
                normalized_link = _normalize_file_name(linked_file)
                if normalized_link not in normalized_file_names:
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

    def get_block_relationships(
        self,
        workspace_id: str,
        run_id: str,
        block_id: str,
    ) -> list[dict[str, Any]]:
        run = self.repository.get_run(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Generated run not found")

        block = self.repository.get_block(run_id, block_id)
        if block is None:
            raise ValueError("Block not found")

        relationships = self.relationship_service.get_relationships_for_block(block_id)
        blocks_map = {b.id: b for b in self.repository.list_blocks(run_id)}

        result = []
        for rel in relationships:
            if rel.source_block_id == block_id:
                other = blocks_map.get(rel.target_block_id)
                direction = "outgoing"
            else:
                other = blocks_map.get(rel.source_block_id)
                direction = "incoming"

            result.append({
                "id": rel.id,
                "source_block_id": rel.source_block_id,
                "target_block_id": rel.target_block_id,
                "relationship_type": rel.relationship_type,
                "description": rel.description,
                "auto_created": rel.auto_created,
                "created_at": rel.created_at,
                "direction": direction,
                "other_block": {
                    "id": other.id if other else None,
                    "title": other.title if other else "Unknown",
                    "file_name": other.file_name if other else None,
                } if other else None,
            })

        return result

    def create_block_relationship(
        self,
        workspace_id: str,
        run_id: str,
        block_id: str,
        target_block_id: str,
        relationship_type: str,
        description: str = "",
    ) -> dict[str, Any]:
        run = self.repository.get_run(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Generated run not found")

        block = self.repository.get_block(run_id, block_id)
        if block is None:
            raise ValueError("Block not found")

        target = self.repository.get_block(run_id, target_block_id)
        if target is None:
            raise ValueError("Target block not found")

        rel = self.relationship_service.create_relationship(
            workspace_run_id=run_id,
            source_block_id=block_id,
            target_block_id=target_block_id,
            relationship_type=relationship_type,
            description=description,
            auto_created=False,
        )

        return {
            "id": rel.id,
            "source_block_id": rel.source_block_id,
            "target_block_id": rel.target_block_id,
            "relationship_type": rel.relationship_type,
            "description": rel.description,
            "auto_created": rel.auto_created,
            "created_at": rel.created_at,
        }

    def delete_block_relationship(
        self,
        workspace_id: str,
        run_id: str,
        block_id: str,
        relationship_id: str,
    ) -> bool:
        run = self.repository.get_run(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Generated run not found")

        block = self.repository.get_block(run_id, block_id)
        if block is None:
            raise ValueError("Block not found")

        from sqlalchemy import select
        from app.models.block_relationship import BlockRelationship

        stmt = select(BlockRelationship).where(BlockRelationship.id == relationship_id)
        rel = self.repository.db.scalar(stmt)
        if rel is None:
            raise ValueError("Relationship not found")

        if rel.source_block_id != block_id and rel.target_block_id != block_id:
            raise ValueError("Relationship does not belong to this block")

        return self.relationship_service.delete_relationship(relationship_id)

    def check_block_impact(
        self,
        workspace_id: str,
        run_id: str,
        block_id: str,
        new_content: str,
    ) -> list[dict[str, Any]]:
        run = self.repository.get_run(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Generated run not found")

        block = self.repository.get_block(run_id, block_id)
        if block is None:
            raise ValueError("Block not found")

        suggestions = self.impact_service.check_impact(
            run_id=run_id,
            block_id=block_id,
            original_content=block.content,
            new_content=new_content,
        )

        block_by_id = {b.id: b for b in self.repository.list_blocks(run_id)}

        return [
            {
                "id": s.id,
                "source_block_id": s.source_block_id,
                "affected_block_id": s.affected_block_id,
                "affected_block_title": block_by_id.get(s.affected_block_id).title if block_by_id.get(s.affected_block_id) else "",
                "suggestion": s.suggestion,
                "reason": s.reason,
                "relationship_type": s.relationship_type,
                "status": s.status,
                "conversation_id": s.conversation_id,
                "created_at": s.created_at,
            }
            for s in suggestions
        ]

    def apply_impact_suggestion(
        self,
        workspace_id: str,
        run_id: str,
        block_id: str,
        suggestion: str,
        suggestion_id: str | None = None,
    ) -> dict[str, Any] | None:
        run = self.repository.get_run(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Generated run not found")

        block = self.repository.get_block(run_id, block_id)
        if block is None:
            raise ValueError("Block not found")

        updated_block = self.impact_service.apply_suggestion(
            run_id=run_id,
            block_id=block_id,
            suggestion=suggestion,
        )

        if updated_block is None:
            return None

        if suggestion_id:
            self.repository.delete_impact_suggestion(suggestion_id)

        return {
            "id": updated_block.id,
            "workspace_run_id": updated_block.workspace_run_id,
            "order_index": updated_block.order_index,
            "title": updated_block.title,
            "block_type": updated_block.block_type,
            "summary": updated_block.summary,
            "file_name": updated_block.file_name,
            "content": updated_block.content,
            "meta": updated_block.meta,
        }

    def list_impact_suggestions(
        self,
        workspace_id: str,
        run_id: str,
        block_id: str,
        status: str = "pending",
    ) -> list[dict[str, Any]]:
        run = self.repository.get_run(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Generated run not found")

        block = self.repository.get_block(run_id, block_id)
        if block is None:
            raise ValueError("Block not found")

        suggestions = self.repository.list_impact_suggestions(
            run_id=run_id,
            source_block_id=block_id,
            status=status,
        )
        block_by_id = {b.id: b for b in self.repository.list_blocks(run_id)}

        return [
            {
                "id": s.id,
                "source_block_id": s.source_block_id,
                "affected_block_id": s.affected_block_id,
                "affected_block_title": block_by_id.get(s.affected_block_id).title if block_by_id.get(s.affected_block_id) else "",
                "suggestion": s.suggestion,
                "reason": s.reason,
                "relationship_type": s.relationship_type,
                "status": s.status,
                "conversation_id": s.conversation_id,
                "created_at": s.created_at,
            }
            for s in suggestions
        ]

    def dismiss_impact_suggestion(
        self,
        workspace_id: str,
        run_id: str,
        block_id: str,
        suggestion_id: str,
    ) -> bool:
        run = self.repository.get_run(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Generated run not found")

        block = self.repository.get_block(run_id, block_id)
        if block is None:
            raise ValueError("Block not found")

        suggestion = self.repository.get_impact_suggestion(suggestion_id)
        if suggestion is None:
            raise ValueError("Impact suggestion not found")

        if suggestion.workspace_run_id != run_id or suggestion.source_block_id != block_id:
            raise ValueError("Impact suggestion does not belong to this block")

        self.repository.delete_impact_suggestion(suggestion_id)
        return True

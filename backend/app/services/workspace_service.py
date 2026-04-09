from datetime import UTC, datetime

from app.models.block import Block
from app.models.chat_message import ChatMessage
from app.models.workspace import Workspace
from app.repositories.workspace_repository import WorkspaceRepository
from app.utils.ids import new_id
from app.utils.markdown_blocks import build_default_blocks


class WorkspaceService:
    def __init__(self, repository: WorkspaceRepository) -> None:
        self.repository = repository

    def create_workspace(
        self,
        repository_id: str,
        prompt: str,
        reference_document_ids: list[str],
        reference_file_ids: list[str],
    ) -> Workspace:
        if not prompt.strip():
            raise ValueError("Prompt is required")

        references = self.repository.get_documents_by_ids(repository_id, reference_document_ids)
        reference_files = self.repository.get_files_by_ids(repository_id, reference_file_ids)
        reference_titles = [doc.title for doc in references] + [
            file.file_name for file in reference_files
        ]

        workspace = Workspace(
            id=new_id(),
            repository_id=repository_id,
            prompt=prompt,
            status="draft",
            created_at=datetime.now(UTC),
        )

        generated_blocks = build_default_blocks(prompt=prompt, reference_titles=reference_titles)
        block_models = [
            Block(
                id=data["id"],
                workspace_id=workspace.id,
                order_index=data["order_index"],
                title=data["title"],
                block_type=data["block_type"],
                summary=data["summary"],
                file_name=data["file_name"],
                content=data["content"],
            )
            for data in generated_blocks
        ]

        return self.repository.create_workspace_with_blocks(workspace, block_models)

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        return self.repository.get_workspace(workspace_id)

    def list_workspaces(self, repository_id: str | None = None) -> list[Workspace]:
        return self.repository.list_workspaces(repository_id=repository_id)

    def list_blocks(self, workspace_id: str) -> list[Block]:
        return self.repository.list_blocks(workspace_id)

    def get_block(self, workspace_id: str, block_id: str) -> Block | None:
        return self.repository.get_block(workspace_id, block_id)

    def update_block_content(self, workspace_id: str, block_id: str, content: str) -> Block | None:
        block = self.repository.get_block(workspace_id, block_id)
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

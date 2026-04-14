from datetime import UTC, datetime
from io import BytesIO
import zipfile

from app.models.block import Block
from app.models.chat_message import ChatMessage
from app.models.document import Document
from app.models.workspace import Workspace
from app.models.workspace_file import WorkspaceFile
from app.models.workspace_run import WorkspaceRun
from app.repositories.workspace_repository import WorkspaceRepository
from app.utils.ids import new_id
from app.utils.markdown_blocks import build_default_blocks
from app.integrations.mattin_client import MattinClient

class WorkspaceService:
    def __init__(self, repository: WorkspaceRepository, mattin_client: MattinClient) -> None:
        self.repository = repository
        self.mattin_client = mattin_client

    def list_workspaces(self, owner_id: str) -> list[Workspace]:
        return self.mattin_client.get_all_repositories()
        #return self.repository.list_workspaces(owner_id)

    def create_workspace(self, owner_id: str, name: str, description: str) -> Workspace:
        if not name.strip():
            raise ValueError("Workspace name is required")

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

        generated_blocks = build_default_blocks(prompt=prompt, reference_titles=reference_titles)
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

        return self.repository.create_run_with_blocks(workspace_run, block_models)

    def get_run(self, run_id: str) -> WorkspaceRun | None:
        return self.repository.get_run(run_id)

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

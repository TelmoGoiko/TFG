from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.block import Block
from app.models.chat_message import ChatMessage
from app.models.document import Document
from app.models.repository_file import RepositoryFile
from app.models.workspace import Workspace


class WorkspaceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_documents_by_ids(self, repository_id: str, document_ids: list[str]) -> list[Document]:
        if not document_ids:
            return []

        statement = select(Document).where(
            Document.repository_id == repository_id,
            Document.id.in_(document_ids),
        )
        return list(self.db.scalars(statement))

    def get_files_by_ids(self, repository_id: str, file_ids: list[str]) -> list[RepositoryFile]:
        if not file_ids:
            return []

        statement = select(RepositoryFile).where(
            RepositoryFile.repository_id == repository_id,
            RepositoryFile.id.in_(file_ids),
        )
        return list(self.db.scalars(statement))

    def create_workspace_with_blocks(self, workspace: Workspace, blocks: list[Block]) -> Workspace:
        self.db.add(workspace)
        for block in blocks:
            self.db.add(block)

        self.db.commit()
        self.db.refresh(workspace)
        return workspace

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        statement = select(Workspace).where(Workspace.id == workspace_id)
        return self.db.scalar(statement)

    def list_workspaces(self, repository_id: str | None = None) -> list[Workspace]:
        statement = select(Workspace).order_by(Workspace.created_at.desc())
        if repository_id:
            statement = statement.where(Workspace.repository_id == repository_id)
        return list(self.db.scalars(statement))

    def list_blocks(self, workspace_id: str) -> list[Block]:
        statement = (
            select(Block)
            .where(Block.workspace_id == workspace_id)
            .order_by(Block.order_index.asc())
        )
        return list(self.db.scalars(statement))

    def get_block(self, workspace_id: str, block_id: str) -> Block | None:
        statement = select(Block).where(
            Block.workspace_id == workspace_id,
            Block.id == block_id,
        )
        return self.db.scalar(statement)

    def save_block(self, block: Block) -> Block:
        self.db.add(block)
        self.db.commit()
        self.db.refresh(block)
        return block

    def list_messages(self, block_id: str) -> list[ChatMessage]:
        statement = (
            select(ChatMessage)
            .where(ChatMessage.block_id == block_id)
            .order_by(ChatMessage.created_at.asc())
        )
        return list(self.db.scalars(statement))

    def create_message(self, message: ChatMessage) -> ChatMessage:
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

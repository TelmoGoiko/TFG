from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.block import Block
from app.models.chat_message import ChatMessage
from app.models.document import Document
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_file import WorkspaceFile
from app.models.workspace_run import WorkspaceRun


class WorkspaceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_workspaces(self, owner_id: str) -> list[Workspace]:
        statement = (
            select(Workspace)
            .where(Workspace.owner_id == owner_id)
            .order_by(Workspace.created_at.desc())
        )
        return list(self.db.scalars(statement))

    def get_user_by_id(self, user_id: str) -> User | None:
        statement = select(User).where(User.id == user_id)
        return self.db.scalar(statement)

    def create_user(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        statement = select(Workspace).where(Workspace.id == workspace_id)
        return self.db.scalar(statement)

    def get_workspace_by_mattin_repository_id(self, mattin_repository_id: str) -> Workspace | None:
        statement = select(Workspace).where(Workspace.mattin_repository_id == mattin_repository_id)
        return self.db.scalar(statement)

    def create_workspace(self, workspace: Workspace) -> Workspace:
        self.db.add(workspace)
        self.db.commit()
        self.db.refresh(workspace)
        return workspace

    def save_workspace(self, workspace: Workspace) -> Workspace:
        self.db.add(workspace)
        self.db.commit()
        self.db.refresh(workspace)
        return workspace

    def delete_workspace(self, workspace_id: str) -> bool:
        statement = delete(Workspace).where(Workspace.id == workspace_id)
        result = self.db.execute(statement)
        self.db.commit()
        return result.rowcount > 0

    def list_documents(self, workspace_id: str) -> list[Document]:
        statement = (
            select(Document)
            .where(Document.workspace_id == workspace_id)
            .order_by(Document.created_at.desc())
        )
        return list(self.db.scalars(statement))

    def create_document(self, document: Document) -> Document:
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def delete_document(self, document_id: str) -> bool:
        statement = delete(Document).where(Document.id == document_id)
        result = self.db.execute(statement)
        self.db.commit()
        return result.rowcount > 0

    def list_files(self, workspace_id: str) -> list[WorkspaceFile]:
        statement = (
            select(WorkspaceFile)
            .where(WorkspaceFile.workspace_id == workspace_id)
            .order_by(WorkspaceFile.created_at.desc())
        )
        return list(self.db.scalars(statement))

    def create_file(self, workspace_file: WorkspaceFile) -> WorkspaceFile:
        self.db.add(workspace_file)
        self.db.commit()
        self.db.refresh(workspace_file)
        return workspace_file

    def save_file(self, workspace_file: WorkspaceFile) -> WorkspaceFile:
        self.db.add(workspace_file)
        self.db.commit()
        self.db.refresh(workspace_file)
        return workspace_file

    def get_file_by_mattin_file_id(
        self,
        workspace_id: str,
        mattin_file_id: int,
    ) -> WorkspaceFile | None:
        statement = select(WorkspaceFile).where(
            WorkspaceFile.workspace_id == workspace_id,
            WorkspaceFile.mattin_file_id == mattin_file_id,
        )
        return self.db.scalar(statement)

    def get_file(self, workspace_id: str, file_id: str) -> WorkspaceFile | None:
        statement = select(WorkspaceFile).where(
            WorkspaceFile.workspace_id == workspace_id,
            WorkspaceFile.id == file_id,
        )
        return self.db.scalar(statement)

    def delete_file(self, file_id: str) -> bool:
        statement = delete(WorkspaceFile).where(WorkspaceFile.id == file_id)
        result = self.db.execute(statement)
        self.db.commit()
        return result.rowcount > 0

    def get_documents_by_ids(self, workspace_id: str, document_ids: list[str]) -> list[Document]:
        if not document_ids:
            return []

        statement = select(Document).where(
            Document.workspace_id == workspace_id,
            Document.id.in_(document_ids),
        )
        return list(self.db.scalars(statement))

    def get_files_by_ids(self, workspace_id: str, file_ids: list[str]) -> list[WorkspaceFile]:
        if not file_ids:
            return []

        statement = select(WorkspaceFile).where(
            WorkspaceFile.workspace_id == workspace_id,
            WorkspaceFile.id.in_(file_ids),
        )
        return list(self.db.scalars(statement))

    def create_run_with_blocks(self, run: WorkspaceRun, blocks: list[Block]) -> WorkspaceRun:
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        for block in blocks:
            self.db.add(block)

        self.db.commit()
        return run

    def get_run(self, run_id: str) -> WorkspaceRun | None:
        statement = select(WorkspaceRun).where(WorkspaceRun.id == run_id)
        return self.db.scalar(statement)

    def delete_run(self, run_id: str) -> bool:
        statement = delete(WorkspaceRun).where(WorkspaceRun.id == run_id)
        result = self.db.execute(statement)
        self.db.commit()
        return result.rowcount > 0

    def list_runs(self, workspace_id: str) -> list[WorkspaceRun]:
        statement = (
            select(WorkspaceRun)
            .where(WorkspaceRun.workspace_id == workspace_id)
            .order_by(WorkspaceRun.created_at.desc())
        )
        return list(self.db.scalars(statement))

    def list_blocks(self, run_id: str) -> list[Block]:
        statement = (
            select(Block)
            .where(Block.workspace_run_id == run_id)
            .order_by(Block.order_index.asc())
        )
        return list(self.db.scalars(statement))

    def get_block(self, run_id: str, block_id: str) -> Block | None:
        statement = select(Block).where(
            Block.workspace_run_id == run_id,
            Block.id == block_id,
        )
        return self.db.scalar(statement)

    def save_block(self, block: Block) -> Block:
        self.db.add(block)
        self.db.commit()
        self.db.refresh(block)
        return block

    def create_block(self, block: Block) -> Block:
        self.db.add(block)
        self.db.commit()
        self.db.refresh(block)
        return block

    def delete_block(self, block_id: str) -> bool:
        statement = delete(Block).where(Block.id == block_id)
        result = self.db.execute(statement)
        self.db.commit()
        return result.rowcount > 0

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

    def delete_messages_by_block(self, block_id: str) -> int:
        statement = delete(ChatMessage).where(ChatMessage.block_id == block_id)
        result = self.db.execute(statement)
        self.db.commit()
        return result.rowcount or 0

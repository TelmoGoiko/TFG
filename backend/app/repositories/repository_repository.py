from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile


class RepositoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_repositories(self, owner_id: str) -> list[Repository]:
        statement = (
            select(Repository)
            .where(Repository.owner_id == owner_id)
            .order_by(Repository.created_at.desc())
        )
        return list(self.db.scalars(statement))

    def get_repository(self, repository_id: str) -> Repository | None:
        statement = select(Repository).where(Repository.id == repository_id)
        return self.db.scalar(statement)

    def create_repository(self, repository: Repository) -> Repository:
        self.db.add(repository)
        self.db.commit()
        self.db.refresh(repository)
        return repository

    def delete_repository(self, repository_id: str) -> bool:
        statement = delete(Repository).where(Repository.id == repository_id)
        result = self.db.execute(statement)
        self.db.commit()
        return result.rowcount > 0

    def list_documents(self, repository_id: str) -> list[Document]:
        statement = (
            select(Document)
            .where(Document.repository_id == repository_id)
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

    def list_files(self, repository_id: str) -> list[RepositoryFile]:
        statement = (
            select(RepositoryFile)
            .where(RepositoryFile.repository_id == repository_id)
            .order_by(RepositoryFile.created_at.desc())
        )
        return list(self.db.scalars(statement))

    def create_file(self, repository_file: RepositoryFile) -> RepositoryFile:
        self.db.add(repository_file)
        self.db.commit()
        self.db.refresh(repository_file)
        return repository_file

    def get_file(self, repository_id: str, file_id: str) -> RepositoryFile | None:
        statement = select(RepositoryFile).where(
            RepositoryFile.repository_id == repository_id,
            RepositoryFile.id == file_id,
        )
        return self.db.scalar(statement)

    def delete_file(self, file_id: str) -> bool:
        statement = delete(RepositoryFile).where(RepositoryFile.id == file_id)
        result = self.db.execute(statement)
        self.db.commit()
        return result.rowcount > 0

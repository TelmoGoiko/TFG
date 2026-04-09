from datetime import UTC, datetime
from io import BytesIO
import zipfile

from app.models.document import Document
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.repositories.repository_repository import RepositoryRepository
from app.utils.ids import new_id


class RepositoryService:
    def __init__(self, repository: RepositoryRepository) -> None:
        self.repository = repository

    def list_repositories(self, owner_id: str) -> list[Repository]:
        return self.repository.list_repositories(owner_id)

    def create_repository(self, owner_id: str, name: str, description: str) -> Repository:
        if not name.strip():
            raise ValueError("Repository name is required")

        model = Repository(
            id=new_id(),
            owner_id=owner_id,
            name=name.strip(),
            description=description.strip(),
            created_at=datetime.now(UTC),
        )
        return self.repository.create_repository(model)

    def get_repository(self, repository_id: str) -> Repository | None:
        return self.repository.get_repository(repository_id)

    def delete_repository(self, repository_id: str) -> bool:
        return self.repository.delete_repository(repository_id)

    def list_documents(self, repository_id: str) -> list[Document]:
        return self.repository.list_documents(repository_id)

    def create_document(self, repository_id: str, title: str, content: str) -> Document:
        if not title.strip():
            raise ValueError("Document title is required")

        model = Document(
            id=new_id(),
            repository_id=repository_id,
            title=title.strip(),
            content=content,
            created_at=datetime.now(UTC),
        )
        return self.repository.create_document(model)

    def delete_document(self, document_id: str) -> bool:
        return self.repository.delete_document(document_id)

    def list_files(self, repository_id: str) -> list[RepositoryFile]:
        return self.repository.list_files(repository_id)

    def create_file(
        self,
        repository_id: str,
        file_name: str,
        mime_type: str,
        content_bytes: bytes,
    ) -> RepositoryFile:
        if not file_name.strip():
            raise ValueError("File name is required")

        model = RepositoryFile(
            id=new_id(),
            repository_id=repository_id,
            file_name=file_name,
            mime_type=mime_type or "application/octet-stream",
            size_bytes=len(content_bytes),
            content_bytes=content_bytes,
            created_at=datetime.now(UTC),
        )
        return self.repository.create_file(model)

    def delete_file(self, file_id: str) -> bool:
        return self.repository.delete_file(file_id)

    def get_file(self, repository_id: str, file_id: str) -> RepositoryFile | None:
        return self.repository.get_file(repository_id, file_id)

    def build_repository_zip(self, repository_id: str) -> tuple[str, bytes] | None:
        repository = self.repository.get_repository(repository_id)
        if repository is None:
            return None

        repository_files = self.repository.list_files(repository_id)
        documents = self.repository.list_documents(repository_id)

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for repository_file in repository_files:
                zip_file.writestr(repository_file.file_name, repository_file.content_bytes)

            for document in documents:
                doc_name = f"generated-documents/{document.title}.md"
                zip_file.writestr(doc_name, document.content)

        archive_name = f"{repository.name.replace(' ', '_') or 'repository'}_bundle.zip"
        return archive_name, zip_buffer.getvalue()

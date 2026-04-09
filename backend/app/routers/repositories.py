from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.repository import (
    DocumentCreate,
    DocumentResponse,
    RepositoryFileResponse,
    RepositoryCreate,
    RepositoryResponse,
)
from app.services.repository_service import RepositoryService

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("", response_model=list[RepositoryResponse])
def list_repositories(owner_id: str, db: Session = Depends(get_db)) -> list[RepositoryResponse]:
    service = RepositoryService(RepositoryRepository(db))
    repositories = service.list_repositories(owner_id=owner_id)
    return [RepositoryResponse.model_validate(repository, from_attributes=True) for repository in repositories]


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
def create_repository(payload: RepositoryCreate, db: Session = Depends(get_db)) -> RepositoryResponse:
    service = RepositoryService(RepositoryRepository(db))

    try:
        repository = service.create_repository(
            owner_id=payload.owner_id,
            name=payload.name,
            description=payload.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return RepositoryResponse.model_validate(repository, from_attributes=True)


@router.get("/{repository_id}", response_model=RepositoryResponse)
def get_repository(repository_id: str, db: Session = Depends(get_db)) -> RepositoryResponse:
    service = RepositoryService(RepositoryRepository(db))
    repository = service.get_repository(repository_id)

    if repository is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    return RepositoryResponse.model_validate(repository, from_attributes=True)


@router.delete("/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repository(repository_id: str, db: Session = Depends(get_db)) -> None:
    service = RepositoryService(RepositoryRepository(db))
    deleted = service.delete_repository(repository_id)

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")


@router.get("/{repository_id}/documents", response_model=list[DocumentResponse])
def list_documents(repository_id: str, db: Session = Depends(get_db)) -> list[DocumentResponse]:
    service = RepositoryService(RepositoryRepository(db))
    documents = service.list_documents(repository_id)
    return [DocumentResponse.model_validate(document, from_attributes=True) for document in documents]


@router.post(
    "/{repository_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_document(
    repository_id: str,
    payload: DocumentCreate,
    db: Session = Depends(get_db),
) -> DocumentResponse:
    service = RepositoryService(RepositoryRepository(db))

    try:
        document = service.create_document(
            repository_id=repository_id,
            title=payload.title,
            content=payload.content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return DocumentResponse.model_validate(document, from_attributes=True)


@router.delete("/{repository_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(repository_id: str, document_id: str, db: Session = Depends(get_db)) -> None:
    service = RepositoryService(RepositoryRepository(db))
    deleted = service.delete_document(document_id)

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")


@router.get("/{repository_id}/files", response_model=list[RepositoryFileResponse])
def list_files(repository_id: str, db: Session = Depends(get_db)) -> list[RepositoryFileResponse]:
    service = RepositoryService(RepositoryRepository(db))
    files = service.list_files(repository_id)
    return [RepositoryFileResponse.model_validate(file, from_attributes=True) for file in files]


@router.post(
    "/{repository_id}/files",
    response_model=RepositoryFileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    repository_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> RepositoryFileResponse:
    service = RepositoryService(RepositoryRepository(db))

    try:
        content_bytes = await file.read()
        repository_file = service.create_file(
            repository_id=repository_id,
            file_name=file.filename or "unnamed_file",
            mime_type=file.content_type or "application/octet-stream",
            content_bytes=content_bytes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return RepositoryFileResponse.model_validate(repository_file, from_attributes=True)


@router.delete("/{repository_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(repository_id: str, file_id: str, db: Session = Depends(get_db)) -> None:
    service = RepositoryService(RepositoryRepository(db))
    deleted = service.delete_file(file_id)

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")


@router.get("/{repository_id}/files/{file_id}/download")
def download_file(repository_id: str, file_id: str, db: Session = Depends(get_db)) -> Response:
    service = RepositoryService(RepositoryRepository(db))
    repository_file = service.get_file(repository_id, file_id)

    if repository_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    return Response(
        content=repository_file.content_bytes,
        media_type=repository_file.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{repository_file.file_name}"',
        },
    )


@router.get("/{repository_id}/download")
def download_repository(repository_id: str, db: Session = Depends(get_db)) -> Response:
    service = RepositoryService(RepositoryRepository(db))
    archive = service.build_repository_zip(repository_id)

    if archive is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    archive_name, archive_bytes = archive
    return Response(
        content=archive_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{archive_name}"',
        },
    )

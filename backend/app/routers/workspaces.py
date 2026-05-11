import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import File, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import (
    DocumentCreate,
    DocumentResponse,
    BlockResponse,
    BlockUpdateRequest,
    BlockCreateRequest,
    WorkspaceFileResponse,
    WorkspaceCreate,
    WorkspaceRunCreate,
    WorkspaceRunResponse,
    WorkspaceResponse,
    BlockRelationshipCreate,
    BlockRelationshipResponse,
)
from app.services.workspace_service import WorkspaceService
from app.integrations.mattin_client import MattinClient

router = APIRouter(prefix="/workspaces", tags=["workspaces"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(
    owner_id: str,
    db: Session = Depends(get_db),
) -> list[WorkspaceResponse]:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())
    return service.list_workspaces(owner_id=owner_id)
     


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(payload: WorkspaceCreate, db: Session = Depends(get_db)) -> WorkspaceResponse:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())

    try:
        workspace = service.create_workspace(
            owner_id=payload.owner_id,
            name=payload.name,
            description=payload.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return WorkspaceResponse.model_validate(workspace, from_attributes=True)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(workspace_id: str, db: Session = Depends(get_db)) -> WorkspaceResponse:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())
    workspace = service.get_workspace(workspace_id)

    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    return WorkspaceResponse.model_validate(workspace, from_attributes=True)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(workspace_id: str, db: Session = Depends(get_db)) -> None:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())
    deleted = service.delete_workspace(workspace_id)

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")


@router.get("/{workspace_id}/documents", response_model=list[DocumentResponse])
def list_documents(workspace_id: str, db: Session = Depends(get_db)) -> list[DocumentResponse]:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())
    documents = service.list_documents(workspace_id)
    return [DocumentResponse.model_validate(document, from_attributes=True) for document in documents]


@router.post(
    "/{workspace_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_document(
    workspace_id: str,
    payload: DocumentCreate,
    db: Session = Depends(get_db),
) -> DocumentResponse:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())

    try:
        document = service.create_document(
            workspace_id=workspace_id,
            title=payload.title,
            content=payload.content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return DocumentResponse.model_validate(document, from_attributes=True)


@router.delete("/{workspace_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(workspace_id: str, document_id: str, db: Session = Depends(get_db)) -> None:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())
    deleted = service.delete_document(document_id)

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")


@router.get("/{workspace_id}/files", response_model=list[WorkspaceFileResponse])
def list_files(workspace_id: str, db: Session = Depends(get_db)) -> list[WorkspaceFileResponse]:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())
    files = service.list_files(workspace_id)
    return [WorkspaceFileResponse.model_validate(file, from_attributes=True) for file in files]


@router.post(
    "/{workspace_id}/files",
    response_model=WorkspaceFileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    workspace_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> WorkspaceFileResponse:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())

    try:
        content_bytes = await file.read()
        workspace_file = service.create_file(
            workspace_id=workspace_id,
            file_name=file.filename or "unnamed_file",
            mime_type=file.content_type or "application/octet-stream",
            content_bytes=content_bytes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return WorkspaceFileResponse.model_validate(workspace_file, from_attributes=True)


@router.delete("/{workspace_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(workspace_id: str, file_id: str, db: Session = Depends(get_db)) -> None:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())
    try:
        deleted = service.delete_file(workspace_id=workspace_id, file_id=file_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")


@router.get("/{workspace_id}/files/{file_id}/download")
def download_file(workspace_id: str, file_id: str, db: Session = Depends(get_db)) -> Response:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())
    workspace_file = service.get_file(workspace_id, file_id)

    if workspace_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    return Response(
        content=workspace_file.content_bytes,
        media_type=workspace_file.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{workspace_file.file_name}"',
        },
    )


@router.get("/{workspace_id}/download")
def download_workspace(workspace_id: str, db: Session = Depends(get_db)) -> Response:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())
    archive = service.build_workspace_zip(workspace_id)

    if archive is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    archive_name, archive_bytes = archive
    return Response(
        content=archive_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{archive_name}"',
        },
    )


@router.get("/{workspace_id}/generated", response_model=list[WorkspaceRunResponse])
def list_generated_runs(workspace_id: str, db: Session = Depends(get_db)) -> list[WorkspaceRunResponse]:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())
    runs = service.list_runs(workspace_id)
    return [WorkspaceRunResponse.model_validate(run, from_attributes=True) for run in runs]


@router.post(
    "/{workspace_id}/generated",
    response_model=WorkspaceRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_generated_run(
    workspace_id: str,
    payload: WorkspaceRunCreate,
    db: Session = Depends(get_db),
) -> WorkspaceRunResponse:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())

    try:
        run = service.create_run(
            workspace_id=workspace_id,
            prompt=payload.prompt,
            reference_document_ids=payload.reference_document_ids,
            reference_file_ids=payload.reference_file_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    logger.info(
        "POST generated run completed. workspace_id=%s run_id=%s status=%s",
        workspace_id,
        run.id,
        run.status,
    )

    return WorkspaceRunResponse.model_validate(run, from_attributes=True)


@router.get("/{workspace_id}/generated/{run_id}", response_model=WorkspaceRunResponse)
def get_generated_run(workspace_id: str, run_id: str, db: Session = Depends(get_db)) -> WorkspaceRunResponse:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())
    run = service.get_run(run_id)

    if run is None or run.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated run not found")

    logger.info(
        "GET generated run. workspace_id=%s run_id=%s status=%s",
        workspace_id,
        run.id,
        run.status,
    )

    return WorkspaceRunResponse.model_validate(run, from_attributes=True)


@router.delete("/{workspace_id}/generated/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_generated_run(workspace_id: str, run_id: str, db: Session = Depends(get_db)) -> None:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())
    deleted = service.delete_run(workspace_id=workspace_id, run_id=run_id)

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated run not found")


@router.get("/{workspace_id}/generated/{run_id}/blocks", response_model=list[BlockResponse])
def list_blocks(workspace_id: str, run_id: str, db: Session = Depends(get_db)) -> list[BlockResponse]:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())
    run = service.get_run(run_id)
    if run is None or run.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated run not found")

    blocks = service.list_blocks(run_id)
    logger.info(
        "GET generated blocks. workspace_id=%s run_id=%s blocks=%s titles=%s",
        workspace_id,
        run_id,
        len(blocks),
        [block.title for block in blocks],
    )
    return [BlockResponse.model_validate(block, from_attributes=True) for block in blocks]


@router.get("/{workspace_id}/generated/{run_id}/blocks/{block_id}", response_model=BlockResponse)
def get_block(workspace_id: str, run_id: str, block_id: str, db: Session = Depends(get_db)) -> BlockResponse:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())
    run = service.get_run(run_id)
    if run is None or run.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated run not found")

    block = service.get_block(run_id, block_id)

    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")

    return BlockResponse.model_validate(block, from_attributes=True)


@router.patch("/{workspace_id}/generated/{run_id}/blocks/{block_id}", response_model=BlockResponse)
def update_block(
    workspace_id: str,
    run_id: str,
    block_id: str,
    payload: BlockUpdateRequest,
    db: Session = Depends(get_db),
) -> BlockResponse:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())
    run = service.get_run(run_id)
    if run is None or run.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated run not found")

    block = service.update_block_content(run_id, block_id, payload.content)

    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")

    return BlockResponse.model_validate(block, from_attributes=True)


@router.post(
    "/{workspace_id}/generated/{run_id}/blocks",
    response_model=BlockResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_block(
    workspace_id: str,
    run_id: str,
    payload: BlockCreateRequest,
    db: Session = Depends(get_db),
) -> BlockResponse:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())

    try:
        block = service.create_block(
            workspace_id=workspace_id,
            run_id=run_id,
            title=payload.title,
            summary=payload.summary,
            content=payload.content,
            block_type=payload.block_type,
            file_name=payload.file_name,
            order_index=payload.order_index,
            insert_before_block_id=payload.insert_before_block_id,
            insert_after_block_id=payload.insert_after_block_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return BlockResponse.model_validate(block, from_attributes=True)


@router.delete(
    "/{workspace_id}/generated/{run_id}/blocks/{block_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_block(
    workspace_id: str,
    run_id: str,
    block_id: str,
    db: Session = Depends(get_db),
) -> None:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())

    try:
        deleted = service.delete_block(
            workspace_id=workspace_id,
            run_id=run_id,
            block_id=block_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")


@router.get(
    "/{workspace_id}/generated/{run_id}/blocks/{block_id}/relationships",
    response_model=list[BlockRelationshipResponse],
)
def list_block_relationships(
    workspace_id: str,
    run_id: str,
    block_id: str,
    db: Session = Depends(get_db),
) -> list[BlockRelationshipResponse]:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())

    try:
        relationships = service.get_block_relationships(
            workspace_id=workspace_id,
            run_id=run_id,
            block_id=block_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [BlockRelationshipResponse.model_validate(r) for r in relationships]


@router.post(
    "/{workspace_id}/generated/{run_id}/blocks/{block_id}/relationships",
    response_model=BlockRelationshipResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_block_relationship(
    workspace_id: str,
    run_id: str,
    block_id: str,
    payload: BlockRelationshipCreate,
    db: Session = Depends(get_db),
) -> BlockRelationshipResponse:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())

    try:
        relationship = service.create_block_relationship(
            workspace_id=workspace_id,
            run_id=run_id,
            block_id=block_id,
            target_block_id=payload.target_block_id,
            relationship_type=payload.relationship_type,
            description=payload.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return BlockRelationshipResponse.model_validate(relationship)


@router.delete(
    "/{workspace_id}/generated/{run_id}/blocks/{block_id}/relationships/{relationship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_block_relationship(
    workspace_id: str,
    run_id: str,
    block_id: str,
    relationship_id: str,
    db: Session = Depends(get_db),
) -> None:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())

    try:
        deleted = service.delete_block_relationship(
            workspace_id=workspace_id,
            run_id=run_id,
            block_id=block_id,
            relationship_id=relationship_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found")



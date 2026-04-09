from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import (
    BlockResponse,
    BlockUpdateRequest,
    ChatMessageCreate,
    ChatMessageResponse,
    WorkspaceCreate,
    WorkspaceResponse,
)
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(
    repository_id: str | None = None,
    db: Session = Depends(get_db),
) -> list[WorkspaceResponse]:
    service = WorkspaceService(WorkspaceRepository(db))
    workspaces = service.list_workspaces(repository_id=repository_id)
    return [WorkspaceResponse.model_validate(workspace, from_attributes=True) for workspace in workspaces]


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(payload: WorkspaceCreate, db: Session = Depends(get_db)) -> WorkspaceResponse:
    service = WorkspaceService(WorkspaceRepository(db))

    try:
        workspace = service.create_workspace(
            repository_id=payload.repository_id,
            prompt=payload.prompt,
            reference_document_ids=payload.reference_document_ids,
            reference_file_ids=payload.reference_file_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return WorkspaceResponse.model_validate(workspace, from_attributes=True)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(workspace_id: str, db: Session = Depends(get_db)) -> WorkspaceResponse:
    service = WorkspaceService(WorkspaceRepository(db))
    workspace = service.get_workspace(workspace_id)

    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    return WorkspaceResponse.model_validate(workspace, from_attributes=True)


@router.get("/{workspace_id}/blocks", response_model=list[BlockResponse])
def list_blocks(workspace_id: str, db: Session = Depends(get_db)) -> list[BlockResponse]:
    service = WorkspaceService(WorkspaceRepository(db))
    blocks = service.list_blocks(workspace_id)
    return [BlockResponse.model_validate(block, from_attributes=True) for block in blocks]


@router.get("/{workspace_id}/blocks/{block_id}", response_model=BlockResponse)
def get_block(workspace_id: str, block_id: str, db: Session = Depends(get_db)) -> BlockResponse:
    service = WorkspaceService(WorkspaceRepository(db))
    block = service.get_block(workspace_id, block_id)

    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")

    return BlockResponse.model_validate(block, from_attributes=True)


@router.patch("/{workspace_id}/blocks/{block_id}", response_model=BlockResponse)
def update_block(
    workspace_id: str,
    block_id: str,
    payload: BlockUpdateRequest,
    db: Session = Depends(get_db),
) -> BlockResponse:
    service = WorkspaceService(WorkspaceRepository(db))
    block = service.update_block_content(workspace_id, block_id, payload.content)

    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")

    return BlockResponse.model_validate(block, from_attributes=True)


@router.get("/{workspace_id}/blocks/{block_id}/messages", response_model=list[ChatMessageResponse])
def list_messages(
    workspace_id: str,
    block_id: str,
    db: Session = Depends(get_db),
) -> list[ChatMessageResponse]:
    service = WorkspaceService(WorkspaceRepository(db))

    block = service.get_block(workspace_id, block_id)
    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")

    messages = service.list_messages(block_id)
    return [ChatMessageResponse.model_validate(message, from_attributes=True) for message in messages]


@router.post(
    "/{workspace_id}/blocks/{block_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    workspace_id: str,
    block_id: str,
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
) -> ChatMessageResponse:
    service = WorkspaceService(WorkspaceRepository(db))

    block = service.get_block(workspace_id, block_id)
    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")

    message = service.create_message(
        block_id=block_id,
        role=payload.role,
        content=payload.content,
        mentions=payload.mentions,
    )

    return ChatMessageResponse.model_validate(message, from_attributes=True)

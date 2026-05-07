from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.integrations.mattin_client import MattinClient
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import (
    BlockAgentChatRequest,
    BlockAgentChatResponse,
    BlockResponse,
    BlockUpdateRequest,
    ChatMessageCreate,
    ChatMessageResponse,
    ImpactSuggestion,
    ImpactSuggestionApplyRequest,
)
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["agents"])


@router.get(
    "/{workspace_id}/generated/{run_id}/blocks/{block_id}/messages",
    response_model=list[ChatMessageResponse],
)
def list_messages(
    workspace_id: str,
    run_id: str,
    block_id: str,
    db: Session = Depends(get_db),
) -> list[ChatMessageResponse]:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())

    run = service.get_run(run_id)
    if run is None or run.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated run not found")

    block = service.get_block(run_id, block_id)
    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")

    messages = service.list_messages(block_id)
    return [ChatMessageResponse.model_validate(message, from_attributes=True) for message in messages]


@router.post(
    "/{workspace_id}/generated/{run_id}/blocks/{block_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    workspace_id: str,
    run_id: str,
    block_id: str,
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
) -> ChatMessageResponse:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())

    run = service.get_run(run_id)
    if run is None or run.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated run not found")

    block = service.get_block(run_id, block_id)
    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")

    message = service.create_message(
        block_id=block_id,
        role=payload.role,
        content=payload.content,
        mentions=payload.mentions,
    )

    return ChatMessageResponse.model_validate(message, from_attributes=True)


@router.delete(
    "/{workspace_id}/generated/{run_id}/blocks/{block_id}/messages",
    status_code=status.HTTP_204_NO_CONTENT,
)
def clear_messages(
    workspace_id: str,
    run_id: str,
    block_id: str,
    db: Session = Depends(get_db),
) -> None:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())

    try:
        service.clear_block_messages(
            workspace_id=workspace_id,
            run_id=run_id,
            block_id=block_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{workspace_id}/generated/{run_id}/blocks/{block_id}/agent-chat",
    response_model=BlockAgentChatResponse,
)
def chat_with_block_agent(
    workspace_id: str,
    run_id: str,
    block_id: str,
    payload: BlockAgentChatRequest,
    db: Session = Depends(get_db),
) -> BlockAgentChatResponse:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())

    try:
        result = service.chat_with_block_agent(
            workspace_id=workspace_id,
            run_id=run_id,
            block_id=block_id,
            user_message=payload.user_message,
            selected_snippet=payload.selected_snippet,
            auto_apply=payload.auto_apply,
            conversation_id=payload.conversation_id,
            chat_agent_id=payload.chat_agent_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return BlockAgentChatResponse.model_validate(result)


@router.post(
    "/{workspace_id}/generated/{run_id}/blocks/{block_id}/check-impact",
    response_model=list[ImpactSuggestion],
)
def check_block_impact(
    workspace_id: str,
    run_id: str,
    block_id: str,
    payload: BlockUpdateRequest,
    db: Session = Depends(get_db),
) -> list[ImpactSuggestion]:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())

    try:
        suggestions = service.check_block_impact(
            workspace_id=workspace_id,
            run_id=run_id,
            block_id=block_id,
            new_content=payload.content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [ImpactSuggestion.model_validate(s) for s in suggestions]


@router.post(
    "/{workspace_id}/generated/{run_id}/blocks/{block_id}/apply-suggestion",
    response_model=BlockResponse,
)
def apply_impact_suggestion(
    workspace_id: str,
    run_id: str,
    block_id: str,
    payload: ImpactSuggestionApplyRequest,
    db: Session = Depends(get_db),
) -> BlockResponse:
    service = WorkspaceService(WorkspaceRepository(db), MattinClient())

    try:
        result = service.apply_impact_suggestion(
            workspace_id=workspace_id,
            run_id=run_id,
            block_id=block_id,
            suggestion=payload.suggestion,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to apply suggestion")

    return BlockResponse.model_validate(result)

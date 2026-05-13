from fastapi import APIRouter

from app.schemas.agent import AgentSuggestRequest, AgentSuggestResponse
from app.services.agent_service import AgentService
from app.tools.agent_placeholder_tool import AgentPlaceholderTool

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/blocks/{block_id}/suggest-edit", response_model=AgentSuggestResponse)
def suggest_edit(block_id: str, payload: AgentSuggestRequest) -> AgentSuggestResponse:
    del block_id
    service = AgentService(AgentPlaceholderTool())
    assistant_message = service.suggest_block_edit(
        user_message=payload.user_message,
        selected_snippet=payload.selected_snippet,
    )
    return AgentSuggestResponse(assistant_message=assistant_message)

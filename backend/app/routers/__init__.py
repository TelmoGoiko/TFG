from fastapi import APIRouter

from app.routers.agents import router as agents_router
from app.routers.auth import router as auth_router
from app.routers.workspace_agents import router as workspace_agents_router
from app.routers.workspaces import router as workspaces_router

api_router = APIRouter()
api_router.include_router(agents_router)
api_router.include_router(auth_router)
api_router.include_router(workspace_agents_router)
api_router.include_router(workspaces_router)

__all__ = ["api_router"]

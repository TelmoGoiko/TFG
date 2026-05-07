from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.mcp_handler.server_handler import handle_mcp_request

router = APIRouter(tags=["mcp"])


@router.post("/mcp/v1/id/{app_id}/{server_id}")
def mcp_endpoint_by_id(
    app_id: str,
    server_id: str,
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    del app_id, server_id
    return handle_mcp_request(payload=payload, request=request, db=db)


@router.post("/mcp/v1/{app_slug}/{server_slug}")
def mcp_endpoint_by_slug(
    app_slug: str,
    server_slug: str,
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    del app_slug, server_slug
    return handle_mcp_request(payload=payload, request=request, db=db)


@router.get("/mcp/v1/id/{app_id}/{server_id}/sse")
def mcp_sse_endpoint_by_id(app_id: str, server_id: str) -> None:
    del app_id, server_id
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="SSE transport is not implemented yet. Use HTTP JSON-RPC POST endpoint.",
    )


@router.get("/mcp/v1/{app_slug}/{server_slug}/sse")
def mcp_sse_endpoint_by_slug(app_slug: str, server_slug: str) -> None:
    del app_slug, server_slug
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="SSE transport is not implemented yet. Use HTTP JSON-RPC POST endpoint.",
    )

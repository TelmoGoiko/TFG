import json
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.mattin_client import MattinClient
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.workspace_service import WorkspaceService



def _build_service(db: Session) -> WorkspaceService:
    return WorkspaceService(WorkspaceRepository(db), MattinClient())


def _jsonrpc_success(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    }


def _jsonrpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


def _authorize_mcp(request: Request) -> None:
    expected_token = settings.mcp_server_token
    if not expected_token:
        return

    header_token = request.headers.get("x-mcp-token")
    authorization = request.headers.get("authorization", "")

    bearer_token = None
    if authorization.lower().startswith("bearer "):
        bearer_token = authorization[7:].strip()

    provided_token = header_token or bearer_token
    if provided_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MCP token",
        )


def _tool_descriptors() -> list[dict[str, Any]]:
    return [
        {
            "name": "get_document_outline",
            "description": "Get ordered block metadata for a generated run.",
            "inputSchema": {
                "type": "object",
                "required": ["workspace_id", "run_id"],
                "properties": {
                    "workspace_id": {"type": "string"},
                    "run_id": {"type": "string"},
                },
            },
        },
        {
            "name": "rewrite_block",
            "description": "Rewrite a block using the configured Mattin editor agent.",
            "inputSchema": {
                "type": "object",
                "required": ["workspace_id", "run_id", "block_id", "instructions"],
                "properties": {
                    "workspace_id": {"type": "string"},
                    "run_id": {"type": "string"},
                    "block_id": {"type": "string"},
                    "instructions": {"type": "string"},
                    "selected_snippet": {"type": "string"},
                    "auto_apply": {"type": "boolean"},
                    "conversation_id": {"type": "integer"},
                    "chat_agent_id": {"type": "integer"},
                },
            },
        },
        {
            "name": "review_consistency",
            "description": "Check duplicate titles and broken markdown links between blocks.",
            "inputSchema": {
                "type": "object",
                "required": ["workspace_id", "run_id"],
                "properties": {
                    "workspace_id": {"type": "string"},
                    "run_id": {"type": "string"},
                },
            },
        },
    ]


def _require_string(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing required argument '{key}'")
    return value


def _call_tool(
    service: WorkspaceService,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    if tool_name == "get_document_outline":
        workspace_id = _require_string(arguments, "workspace_id")
        run_id = _require_string(arguments, "run_id")
        outline = service.get_run_outline(workspace_id=workspace_id, run_id=run_id)
        return {
            "workspace_id": workspace_id,
            "run_id": run_id,
            "blocks": outline,
        }

    if tool_name == "rewrite_block":
        workspace_id = _require_string(arguments, "workspace_id")
        run_id = _require_string(arguments, "run_id")
        block_id = _require_string(arguments, "block_id")
        instructions = _require_string(arguments, "instructions")

        auto_apply = arguments.get("auto_apply", True)
        if not isinstance(auto_apply, bool):
            auto_apply = True

        conversation_id = arguments.get("conversation_id")
        if not isinstance(conversation_id, int):
            conversation_id = None

        chat_agent_id = arguments.get("chat_agent_id")
        if not isinstance(chat_agent_id, int):
            chat_agent_id = None

        selected_snippet = arguments.get("selected_snippet")
        if not isinstance(selected_snippet, str):
            selected_snippet = None

        return service.chat_with_block_agent(
            workspace_id=workspace_id,
            run_id=run_id,
            block_id=block_id,
            user_message=instructions,
            selected_snippet=selected_snippet,
            auto_apply=auto_apply,
            conversation_id=conversation_id,
            chat_agent_id=chat_agent_id,
        )

    if tool_name == "review_consistency":
        workspace_id = _require_string(arguments, "workspace_id")
        run_id = _require_string(arguments, "run_id")
        return service.review_run_consistency(workspace_id=workspace_id, run_id=run_id)

    raise ValueError(f"Unknown tool '{tool_name}'")


def _handle_jsonrpc(
    payload: dict[str, Any],
    service: WorkspaceService,
) -> dict[str, Any]:
    request_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}

    if not isinstance(method, str):
        return _jsonrpc_error(request_id, -32600, "Invalid request method")

    if not isinstance(params, dict):
        return _jsonrpc_error(request_id, -32602, "Invalid params")

    if method == "initialize":
        return _jsonrpc_success(
            request_id,
            {
                "protocolVersion": "2025-03-26",
                "serverInfo": {
                    "name": settings.mcp_server_name,
                    "version": "0.1.0",
                },
                "capabilities": {
                    "tools": {
                        "listChanged": False,
                    }
                },
            },
        )

    if method in {"notifications/initialized", "ping"}:
        return _jsonrpc_success(request_id, {})

    if method == "tools/list":
        return _jsonrpc_success(request_id, {"tools": _tool_descriptors()})

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}

        if not isinstance(tool_name, str):
            return _jsonrpc_error(request_id, -32602, "Invalid tool name")
        if not isinstance(arguments, dict):
            return _jsonrpc_error(request_id, -32602, "Invalid tool arguments")

        try:
            tool_result = _call_tool(service=service, tool_name=tool_name, arguments=arguments)
        except ValueError as exc:
            return _jsonrpc_error(request_id, -32000, str(exc))

        return _jsonrpc_success(
            request_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(tool_result, ensure_ascii=True),
                    }
                ],
                "structuredContent": tool_result,
            },
        )

    return _jsonrpc_error(request_id, -32601, f"Method '{method}' not found")


def handle_mcp_request(
    payload: dict[str, Any],
    request: Request,
    db: Session,
) -> dict[str, Any]:
    _authorize_mcp(request)
    service = _build_service(db)
    return _handle_jsonrpc(payload=payload, service=service)
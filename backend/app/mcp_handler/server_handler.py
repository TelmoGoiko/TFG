import json
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.mattin_client import MattinClient
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.workspace_service import WorkspaceService


_MCP_TOOL_ALIASES: dict[str, str] = {
    "get_document_outline": "workspace_get_run_outline",
    "review_consistency": "workspace_review_consistency",
    "workspace.list_blocks": "workspace_list_blocks",
    "workspace.get_block": "workspace_get_block",
    "workspace.propose_block_rewrite": "workspace_propose_block_rewrite",
    "workspace.review_consistency": "workspace_review_consistency",
}

_MCP_TOOLS: dict[str, dict[str, Any]] = {
    "workspace_list_blocks": {
        "name": "workspace_list_blocks",
        "description": "List all blocks and metadata for a generated run.",
        "inputSchema": {
            "type": "object",
            "required": ["workspace_id", "run_id"],
            "properties": {
                "workspace_id": {"type": "string"},
                "run_id": {"type": "string"},
            },
        },
    },
    "workspace_get_block": {
        "name": "workspace_get_block",
        "description": "Get one block with full markdown content.",
        "inputSchema": {
            "type": "object",
            "required": ["workspace_id", "run_id", "block_id"],
            "properties": {
                "workspace_id": {"type": "string"},
                "run_id": {"type": "string"},
                "block_id": {"type": "string"},
            },
        },
    },
    "workspace_propose_block_rewrite": {
        "name": "workspace_propose_block_rewrite",
        "description": "Ask the block chat agent for a rewrite proposal without applying changes.",
        "inputSchema": {
            "type": "object",
            "required": ["workspace_id", "run_id", "block_id", "instructions"],
            "properties": {
                "workspace_id": {"type": "string"},
                "run_id": {"type": "string"},
                "block_id": {"type": "string"},
                "instructions": {"type": "string"},
                "selected_snippet": {"type": "string"},
                "conversation_id": {"type": "integer"},
                "chat_agent_id": {"type": "integer"},
            },
        },
    },
    "workspace_review_consistency": {
        "name": "workspace_review_consistency",
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
}

_ALLOWED_TOOLS_BY_ROLE: dict[str, set[str]] = {
    "writer": {
        "workspace_list_blocks",
        "workspace_get_block",
    },
    "splitter": {
        "workspace_list_blocks",
        "workspace_get_block",
    },
    "chat": {
        "workspace_list_blocks",
        "workspace_get_block",
        "workspace_propose_block_rewrite",
        "workspace_review_consistency",
    },
}



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


def _normalize_role(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in _ALLOWED_TOOLS_BY_ROLE:
        return normalized
    return None


def _resolve_role_from_request(request: Request) -> str | None:
    role = _normalize_role(request.headers.get("x-mcp-agent-role"))
    if role is not None:
        return role

    agent_id_header = request.headers.get("x-mcp-agent-id")
    if agent_id_header and agent_id_header.isdigit():
        agent_id = int(agent_id_header)
        if settings.mattin_document_writer_agent_id is not None and agent_id == settings.mattin_document_writer_agent_id:
            return "writer"
        if settings.mattin_document_splitter_agent_id is not None and agent_id == settings.mattin_document_splitter_agent_id:
            return "splitter"
        if settings.mattin_block_chat_agent_id is not None and agent_id == settings.mattin_block_chat_agent_id:
            return "chat"

    return None


def _is_tool_allowed(tool_name: str, role: str | None) -> bool:
    if role is None:
        return True
    return tool_name in _ALLOWED_TOOLS_BY_ROLE.get(role, set())


def _tool_descriptors(role: str | None) -> list[dict[str, Any]]:
    tools = []
    for name, descriptor in _MCP_TOOLS.items():
        if _is_tool_allowed(name, role):
            tools.append(descriptor)
    return tools


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
    resolved_tool_name = _MCP_TOOL_ALIASES.get(tool_name, tool_name)

    if resolved_tool_name == "workspace_list_blocks":
        workspace_id = _require_string(arguments, "workspace_id")
        run_id = _require_string(arguments, "run_id")
        outline = service.get_run_outline(workspace_id=workspace_id, run_id=run_id)
        return {
            "workspace_id": workspace_id,
            "run_id": run_id,
            "blocks": outline,
        }


    if resolved_tool_name == "workspace_get_block":
        workspace_id = _require_string(arguments, "workspace_id")
        run_id = _require_string(arguments, "run_id")
        block_id = _require_string(arguments, "block_id")

        run = service.get_run(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Generated run not found")

        block = service.get_block(run_id=run_id, block_id=block_id)
        if block is None:
            raise ValueError("Block not found")

        return {
            "workspace_id": workspace_id,
            "run_id": run_id,
            "block": {
                "id": block.id,
                "order_index": block.order_index,
                "title": block.title,
                "summary": block.summary,
                "block_type": block.block_type,
                "file_name": block.file_name,
                "content": block.content,
            },
        }

    if resolved_tool_name == "workspace_propose_block_rewrite":
        workspace_id = _require_string(arguments, "workspace_id")
        run_id = _require_string(arguments, "run_id")
        block_id = _require_string(arguments, "block_id")
        instructions = _require_string(arguments, "instructions")

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
            auto_apply=False,
            conversation_id=conversation_id,
            chat_agent_id=chat_agent_id,
        )

    if resolved_tool_name == "workspace_review_consistency":
        workspace_id = _require_string(arguments, "workspace_id")
        run_id = _require_string(arguments, "run_id")
        return service.review_run_consistency(workspace_id=workspace_id, run_id=run_id)

    raise ValueError(f"Unknown tool '{resolved_tool_name}'")


def _handle_jsonrpc(
    payload: dict[str, Any],
    request: Request,
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

    role = _resolve_role_from_request(request)

    if method == "tools/list":
        return _jsonrpc_success(
            request_id,
            {
                "tools": _tool_descriptors(role),
                "_meta": {
                    "resolved_role": role,
                },
            },
        )

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}

        if not isinstance(tool_name, str):
            return _jsonrpc_error(request_id, -32602, "Invalid tool name")
        if not isinstance(arguments, dict):
            return _jsonrpc_error(request_id, -32602, "Invalid tool arguments")

        resolved_tool_name = _MCP_TOOL_ALIASES.get(tool_name, tool_name)
        if not _is_tool_allowed(resolved_tool_name, role):
            return _jsonrpc_error(
                request_id,
                -32001,
                f"Tool '{resolved_tool_name}' is not allowed for role '{role}'",
            )

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
    return _handle_jsonrpc(payload=payload, request=request, service=service)
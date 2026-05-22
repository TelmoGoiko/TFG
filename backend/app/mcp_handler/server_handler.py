import json
import logging
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.mattin_client import MattinClient
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.workspace_service import WorkspaceService


logger = logging.getLogger(__name__)


_MCP_TOOL_ALIASES: dict[str, str] = {
    "review_consistency": "workspace_review_consistency",
    "workspace.list_blocks": "workspace_list_blocks",
    "workspace.get_block": "workspace_get_block",
    "workspace.review_consistency": "workspace_review_consistency",
    "workspace.create_block": "workspace_create_block",
    "workspace.delete_block": "workspace_delete_block",
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
    "workspace_create_block": {
        "name": "workspace_create_block",
        "description": "Create a new block and optionally insert it before or after another block.",
        "inputSchema": {
            "type": "object",
            "required": ["workspace_id", "run_id", "title"],
            "properties": {
                "workspace_id": {"type": "string"},
                "run_id": {"type": "string"},
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "content": {"type": "string"},
                "block_type": {"type": "string"},
                "file_name": {"type": "string"},
                "order_index": {"type": "integer"},
                "insert_before_block_id": {"type": "string"},
                "insert_after_block_id": {"type": "string"},
            },
        },
    },
    "workspace_delete_block": {
        "name": "workspace_delete_block",
        "description": "Delete a block and reindex the remaining blocks.",
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
    "workspace_get_block_relationships": {
        "name": "workspace_get_block_relationships",
        "description": "Get semantic relationships (references, depends_on, contradicts, extends) for a specific block. Use this to discover which other blocks are related before deciding which ones to update.",
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
    "workspace_get_blocks_content": {
        "name": "workspace_get_blocks_content",
        "description": "Batch-fetch the full markdown content of multiple blocks by their IDs. Use this after workspace_get_block_relationships to read the actual content of related blocks.",
        "inputSchema": {
            "type": "object",
            "required": ["workspace_id", "run_id", "block_ids"],
            "properties": {
                "workspace_id": {"type": "string"},
                "run_id": {"type": "string"},
                "block_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of block IDs to fetch.",
                },
            },
        },
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



def _tool_descriptors() -> list[dict[str, Any]]:
    tools = []
    for descriptor in _MCP_TOOLS.values():
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

    if resolved_tool_name == "workspace_review_consistency":
        workspace_id = _require_string(arguments, "workspace_id")
        run_id = _require_string(arguments, "run_id")
        return service.review_run_consistency(workspace_id=workspace_id, run_id=run_id)

    if resolved_tool_name == "workspace_create_block":
        workspace_id = _require_string(arguments, "workspace_id")
        run_id = _require_string(arguments, "run_id")
        title = _require_string(arguments, "title")

        summary = arguments.get("summary")
        if not isinstance(summary, str):
            summary = ""

        content = arguments.get("content")
        if not isinstance(content, str):
            content = ""

        block_type = arguments.get("block_type")
        if not isinstance(block_type, str):
            block_type = "chapter"

        file_name = arguments.get("file_name")
        if not isinstance(file_name, str):
            file_name = None

        order_index = arguments.get("order_index")
        if not isinstance(order_index, int):
            order_index = None

        insert_before_block_id = arguments.get("insert_before_block_id")
        if not isinstance(insert_before_block_id, str):
            insert_before_block_id = None

        insert_after_block_id = arguments.get("insert_after_block_id")
        if not isinstance(insert_after_block_id, str):
            insert_after_block_id = None

        block = service.create_block(
            workspace_id=workspace_id,
            run_id=run_id,
            title=title,
            summary=summary,
            content=content,
            block_type=block_type,
            file_name=file_name,
            order_index=order_index,
            insert_before_block_id=insert_before_block_id,
            insert_after_block_id=insert_after_block_id,
        )

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

    if resolved_tool_name == "workspace_delete_block":
        workspace_id = _require_string(arguments, "workspace_id")
        run_id = _require_string(arguments, "run_id")
        block_id = _require_string(arguments, "block_id")

        deleted = service.delete_block(
            workspace_id=workspace_id,
            run_id=run_id,
            block_id=block_id,
        )

        if not deleted:
            raise ValueError("Block not found")

        return {
            "workspace_id": workspace_id,
            "run_id": run_id,
            "block_id": block_id,
            "deleted": True,
        }

    if resolved_tool_name == "workspace_get_block_relationships":
        workspace_id = _require_string(arguments, "workspace_id")
        run_id = _require_string(arguments, "run_id")
        block_id = _require_string(arguments, "block_id")

        relationships = service.get_block_relationships(
            workspace_id=workspace_id,
            run_id=run_id,
            block_id=block_id,
        )
        serialized = [
            {
                "id": r["id"],
                "source_block_id": r["source_block_id"],
                "target_block_id": r["target_block_id"],
                "relationship_type": r["relationship_type"],
                "description": r["description"],
                "direction": r["direction"],
                "other_block": r["other_block"],
            }
            for r in relationships
        ]
        return {
            "workspace_id": workspace_id,
            "run_id": run_id,
            "block_id": block_id,
            "relationships": serialized,
        }

    if resolved_tool_name == "workspace_get_blocks_content":
        workspace_id = _require_string(arguments, "workspace_id")
        run_id = _require_string(arguments, "run_id")
        block_ids = arguments.get("block_ids")
        if not isinstance(block_ids, list) or not block_ids:
            raise ValueError("Missing required argument 'block_ids'")
        if not all(isinstance(bid, str) and bid.strip() for bid in block_ids):
            raise ValueError("'block_ids' must be a non-empty list of strings")

        blocks = service.get_blocks_content(
            workspace_id=workspace_id,
            run_id=run_id,
            block_ids=block_ids,
        )
        return {
            "workspace_id": workspace_id,
            "run_id": run_id,
            "blocks": blocks,
        }

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


    if method == "tools/list":
        logger.info("MCP tools/list requested.")
        return _jsonrpc_success(
            request_id,
            {
                "tools": _tool_descriptors()
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

        try:
            logger.info("MCP tools/call requested. tool=%s", resolved_tool_name)
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
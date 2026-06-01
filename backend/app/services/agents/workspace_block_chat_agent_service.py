from __future__ import annotations

import concurrent.futures
from datetime import UTC, datetime
import json
import logging
import re
from urllib.parse import parse_qs, unquote, urlparse
from typing import Any

import requests as _http

from app.core.config import settings
from app.integrations.mattin_client import MattinClient, MattinClientError
from app.models.chat_message import ChatMessage
from app.models.workspace_file import WorkspaceFile
from app.repositories.workspace_repository import WorkspaceRepository
from app.utils.ids import new_id
from app.utils.json_payload import extract_json_object


logger = logging.getLogger(__name__)

_DOCUMENT_WIDE_KEYWORDS: frozenset[str] = frozenset([
    # Spanish
    "todo el documento", "todos los bloques", "toda la documentación",
    "en todo el documento", "en todos los bloques", "en cada bloque",
    "a lo largo del documento", "en el documento entero", "por todo el documento",
    "todas las", "en todos los", "en todo el", "cambia todos", "actualiza todos",
    "reemplaza todos", "cambia todas", "actualiza todas", "reemplaza todas",
    "en todo el doc",
    # English
    "entire document", "whole document", "document-wide", "document wide",
    "all blocks", "every block", "throughout the document", "throughout",
    "across all blocks", "across the document", "across all",
    "change all", "update all", "replace all", "in all blocks", "in every block",
    "all occurrences", "globally", "in the entire", "in the whole",
    "every occurrence", "all instances",
])


class WorkspaceBlockChatAgentService:
    def __init__(self, repository: WorkspaceRepository, mattin_client: MattinClient) -> None:
        self.repository = repository
        self.mattin_client = mattin_client

    def _create_message(
        self,
        block_id: str,
        role: str,
        content: str,
        mentions: list[str],
    ) -> ChatMessage:
        model = ChatMessage(
            id=new_id(),
            block_id=block_id,
            role=role,
            content=content,
            mentions=mentions,
            created_at=datetime.now(UTC),
        )
        return self.repository.create_message(model)

    def _build_block_chat_message(
        self,
        workspace_id: str,
        run_id: str,
        block_id: str,
        block_title: str,
        block_type: str,
        block_content: str,
        user_message: str,
        selected_snippet: str | None,
        related_blocks_full_content: str = "",
    ) -> str:
        outline = self.repository.list_blocks(run_id)
        outline_text = "\n".join(
            f"- [{item.order_index + 1}] {item.title} (block_id: {item.id}): {item.summary}"
            for item in outline
        )
        snippet_text = selected_snippet.strip() if selected_snippet else ""

        related_context = self._build_related_blocks_context(run_id, block_id, block_title)

        return (
            "You are an editing assistant for a multi-block markdown document. "
            "Return ONLY valid JSON with this shape:\n"
            "{\n"
            '  "assistant_message": "string",\n'
            '  "updated_markdown": "string or null",\n'
            '  "cross_block_rewrites": [\n'
            '    {"block_id": "string", "block_title": "string", "instruction": "string"}\n'
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- assistant_message: concise explanation of proposed changes.\n"
            "- updated_markdown: full rewritten markdown for the CURRENT block only if it needs changes; otherwise null.\n"
            "- cross_block_rewrites: list of OTHER blocks (not the current one) that need edits. "
            "For each entry provide block_id (from the outline), block_title, and a precise self-contained "
            "instruction describing exactly what to change in that block (include specific values such as dates, "
            "names, numbers, etc.). Set to [] if no other blocks need changes.\n"
            "- Do NOT call any external tools (no workspace_get_block, no workspace_list_blocks, no Rewrite Block Agent). "
            "The backend will execute cross_block_rewrites in parallel automatically.\n"
            "- When the user asks to rewrite the current block, produce the final markdown directly in updated_markdown.\n"
            "- When no rewrite of the current block is needed, set updated_markdown to null.\n"
            "- If the user requests document-wide edits, list ALL affected blocks in cross_block_rewrites and keep the document consistent.\n"
            "- If the user wants a new block, call MCP tool 'workspace_create_block' with workspace_id, run_id, title, summary, content, block_type, and an insert position (insert_before_block_id, insert_after_block_id, or order_index).\n"
            "- If the user wants to delete a block, call MCP tool 'workspace_delete_block' with workspace_id, run_id, and block_id.\n"
            "- Keep consistency with the document outline.\n"
            "- Do not add markdown fences around JSON.\n"
            "- When the user asks for a chart, graph, or image, call the Visual Generator tool passing: "
            "a clear description of what is needed and any relevant data or values extracted from the document. "
            "The tool returns JSON with a 'visual_markdown' field; insert that value directly into updated_markdown at the appropriate position.\n\n"
            f"Workspace id: {workspace_id}\n"
            f"Run id: {run_id}\n"
            f"Current block id: {block_id}\n\n"
            f"Document outline:\n{outline_text}\n\n"
            f"{related_context}\n\n"
            f"{related_blocks_full_content}"
            f"Current block title: {block_title}\n"
            f"Current block type: {block_type}\n"
            f"Current block markdown:\n{block_content}\n\n"
            f"Selected snippet (if any):\n{snippet_text or 'none'}\n\n"
            f"User request:\n{user_message.strip()}"
        )

    def _build_single_block_rewrite_message(
        self,
        block_title: str,
        block_type: str,
        block_content: str,
        instruction: str,
        outline_text: str,
    ) -> str:
        return (
            "You are a document editing assistant. Apply the instruction to the block markdown below.\n"
            "Return ONLY valid JSON: {\"updated_markdown\": \"string\"}\n\n"
            f"Instruction: {instruction}\n\n"
            f"Block title: {block_title}\n"
            f"Block type: {block_type}\n"
            f"Block markdown:\n{block_content}\n\n"
            f"Document outline (context only):\n{outline_text}"
        )

    def _rewrite_single_block(
        self,
        run_id: str,
        block_id: str,
        instruction: str,
        outline_text: str,
    ) -> None:
        run = self.repository.get_run(run_id)
        if run is None:
            logger.warning("_rewrite_single_block: run not found. run_id=%s", run_id)
            return
        block = self.repository.get_block(run_id, block_id)
        if block is None:
            logger.warning("_rewrite_single_block: block not found. block_id=%s", block_id)
            return
        # Force a fresh read from DB — the block may have been modified by MCP calls
        # (separate sessions) after it was last loaded into the current session.
        self.repository.db.refresh(block)
        rewrite_agent_id = settings.mattin_block_rewrite_agent_id
        if rewrite_agent_id is None:
            logger.warning("_rewrite_single_block: MATTIN_BLOCK_REWRITE_AGENT_ID not set, skipping. block_id=%s", block_id)
            return
        message = self._build_single_block_rewrite_message(
            block_title=block.title,
            block_type=block.block_type,
            block_content=block.content,
            instruction=instruction,
            outline_text=outline_text,
        )
        try:
            response = self.mattin_client.call_agent(
                agent_id=rewrite_agent_id,
                message=message,
                timeout=60,
            )
            payload: Any = response.get("response")
            if isinstance(payload, str):
                payload = extract_json_object(payload)
            if isinstance(payload, dict):
                new_markdown = payload.get("updated_markdown")
                if new_markdown and str(new_markdown).strip():
                    block.content = self.persist_chart_images_in_markdown(
                        run.workspace_id,
                        str(new_markdown).strip(),
                    )
                    self.repository.save_block(block)
                    logger.info("_rewrite_single_block: applied. block_id=%s", block_id)
        except MattinClientError as exc:
            logger.warning(
                "_rewrite_single_block: Mattin call failed. block_id=%s error=%s", block_id, exc
            )

    def _build_related_blocks_context(self, run_id: str, block_id: str, block_title: str) -> str:
        from sqlalchemy import select
        from app.models.block_relationship import BlockRelationship

        run_blocks = self.repository.list_blocks(run_id)
        run_block_ids = {b.id for b in run_blocks}
        all_blocks = {b.id: b for b in run_blocks}

        stmt = select(BlockRelationship).where(
            BlockRelationship.relationship_type.in_(["references", "depends_on"]),
            BlockRelationship.source_block_id.in_(run_block_ids),
            BlockRelationship.target_block_id.in_(run_block_ids),
        )
        all_rels = list(self.repository.db.scalars(stmt))

        related = []
        for rel in all_rels:
            if rel.source_block_id == block_id:
                target = all_blocks.get(rel.target_block_id)
                if target:
                    related.append(f"- This block {rel.relationship_type} '{target.title}': {target.summary}")
            elif rel.target_block_id == block_id:
                source = all_blocks.get(rel.source_block_id)
                if source:
                    related.append(f"- '{source.title}' {rel.relationship_type} this block: {source.summary}")

        if not related:
            return ""

        return "Related blocks context:\n" + "\n".join(related)
        
    def persist_chart_images_in_markdown(self, workspace_id: str, markdown: str) -> str:
        """Download chart images, store them in the local DB, and replace external URLs with the local download URL."""
        _IMAGE_PATTERN = re.compile(r'!\[([^\]]*)\]\((https?://[^)\s]+)(?:\s+"[^"]*")?\)')

        def _replace(match: re.Match) -> str:  # type: ignore[type-arg]
            alt_text = match.group(1)
            chart_url = match.group(2)
            parsed = urlparse(chart_url)
            host = parsed.hostname or ""
            if not (
                host.endswith("quickchart.io")
                or host.endswith("mermaid.ink")
                or host.endswith("mermaid.live")
            ):
                return match.group(0)
            if settings.backend_base_url and chart_url.startswith(settings.backend_base_url):
                return match.group(0)

            logger.info(
                "persist_chart_images_in_markdown: chart detected. workspace_id=%s url=%s",
                workspace_id, chart_url,
            )

            try:
                resp = _http.get(chart_url, timeout=15)
            except Exception as exc:
                logger.warning(
                    "persist_chart_images_in_markdown: download failed. url=%s error=%s",
                    chart_url, exc,
                )
                return match.group(0)

            image_bytes: bytes | None = None
            mime_type: str | None = None
            if resp.ok:
                image_bytes = resp.content
                mime_type = resp.headers.get("Content-Type", "image/png").split(";")[0].strip()
            else:
                fallback = self._fetch_quickchart_via_post(chart_url)
                if fallback is None:
                    logger.warning(
                        "persist_chart_images_in_markdown: download failed. url=%s status=%s",
                        chart_url, resp.status_code,
                    )
                    return match.group(0)
                image_bytes, mime_type = fallback

            if image_bytes is None or mime_type is None:
                return match.group(0)
            if not (mime_type.startswith("image/") or mime_type == "image/svg+xml"):
                logger.warning(
                    "persist_chart_images_in_markdown: non-image response. url=%s content_type=%s",
                    chart_url, mime_type,
                )
                return match.group(0)
            ext = {"image/png": "png", "image/jpeg": "jpg", "image/svg+xml": "svg"}.get(mime_type, "png")
            file_name = f"chart_{new_id()}.{ext}"

            model = WorkspaceFile(
                id=new_id(),
                workspace_id=workspace_id,
                file_name=file_name,
                mime_type=mime_type,
                size_bytes=len(image_bytes),
                mattin_file_id=None,
                content_bytes=image_bytes,
                created_at=datetime.now(UTC),
            )
            self.repository.create_file(model)

            download_url = (
                f"{settings.backend_base_url}/api/v1/workspaces/{workspace_id}/files/{model.id}/download"
            )
            logger.info(
                "persist_chart_images_in_markdown: chart saved locally. workspace_id=%s file_id=%s url=%s",
                workspace_id, model.id, download_url,
            )
            return f"![{alt_text}]({download_url})"

        return _IMAGE_PATTERN.sub(_replace, markdown)

    def _fetch_quickchart_via_post(self, chart_url: str) -> tuple[bytes, str] | None:
        parsed = urlparse(chart_url)
        host = parsed.hostname or ""
        if not host.endswith("quickchart.io"):
            return None

        query = parse_qs(parsed.query)
        raw_config = query.get("c", [None])[0]
        if not raw_config:
            return None

        try:
            decoded = unquote(raw_config)
            config_json = json.loads(decoded)
        except (ValueError, TypeError) as exc:
            logger.warning(
                "persist_chart_images_in_markdown: invalid quickchart config. url=%s error=%s",
                chart_url, exc,
            )
            return None

        params: dict[str, str] = {}
        for key in ("w", "h", "format", "bkg"):
            value = query.get(key, [None])[0]
            if isinstance(value, str) and value.strip():
                params[key] = value

        post_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        try:
            resp = _http.post(post_url, params=params, json=config_json, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(
                "persist_chart_images_in_markdown: quickchart POST failed. url=%s error=%s",
                chart_url, exc,
            )
            return None

        mime_type = resp.headers.get("Content-Type", "image/png").split(";")[0].strip()
        return resp.content, mime_type

    def _detect_scope(self, user_message: str) -> str:
        """Returns 'document' for document-wide requests, 'default' otherwise."""
        lower = user_message.lower()
        if any(kw in lower for kw in _DOCUMENT_WIDE_KEYWORDS):
            return "document"
        return "default"

    def _build_related_blocks_full_content(self, run_id: str, block_id: str) -> str:
        """Return a formatted section with the full markdown content of directly related blocks (capped at 5)."""
        from sqlalchemy import select
        from app.models.block_relationship import BlockRelationship

        run_blocks = self.repository.list_blocks(run_id)
        run_block_ids = {b.id for b in run_blocks}
        blocks_map = {b.id: b for b in run_blocks}

        stmt = select(BlockRelationship).where(
            BlockRelationship.relationship_type.in_(["references", "depends_on"]),
            BlockRelationship.source_block_id.in_(run_block_ids),
            BlockRelationship.target_block_id.in_(run_block_ids),
        )
        rels = list(self.repository.db.scalars(stmt))

        related_ids: list[str] = []
        seen: set[str] = set()
        for rel in rels:
            other_id = rel.target_block_id if rel.source_block_id == block_id else rel.source_block_id
            if other_id != block_id and other_id in run_block_ids and other_id not in seen:
                related_ids.append(other_id)
                seen.add(other_id)

        related_ids = related_ids[:5]  # cap to avoid huge prompts
        if not related_ids:
            return ""

        parts: list[str] = []
        for rid in related_ids:
            rb = blocks_map.get(rid)
            if rb:
                parts.append(f"### {rb.title} (block_id: {rb.id})\n{rb.content}")

        if not parts:
            return ""

        return "Full content of directly related blocks (use as reference for cross_block_rewrites):\n" + "\n\n".join(parts) + "\n\n"

    def _build_document_wide_message(
        self,
        workspace_id: str,
        run_id: str,
        user_request: str,
    ) -> str:
        blocks = self.repository.list_blocks(run_id)
        blocks_json = json.dumps(
            [
                {
                    "block_id": b.id,
                    "order_index": b.order_index,
                    "title": b.title,
                    "block_type": b.block_type,
                    "content": b.content,
                }
                for b in blocks
            ],
            ensure_ascii=False,
        )
        return (
            "You are a document editing assistant performing a document-wide change.\n"
            "Apply the user request consistently to ALL relevant blocks.\n"
            "Return ONLY valid JSON with no markdown fences:\n"
            "{\"rewrites\": [{\"block_id\": \"string\", \"updated_markdown\": \"string\"}]}\n\n"
            "Rules:\n"
            "- Include ONLY blocks that actually need changes in 'rewrites'.\n"
            "- Each 'updated_markdown' must be the complete final markdown for that block.\n"
            "- Preserve all content not affected by the change.\n"
            "- Apply the change consistently across all affected blocks.\n"
            "- Do not call any MCP tools.\n\n"
            f"Workspace id: {workspace_id}\n"
            f"Run id: {run_id}\n\n"
            f"Document blocks:\n{blocks_json}\n\n"
            f"User request:\n{user_request.strip()}"
        )

    def _apply_bulk_rewrites(self, run_id: str, rewrites: list[dict[str, Any]]) -> int:
        count = 0
        run = self.repository.get_run(run_id)
        if run is None:
            logger.warning("_apply_bulk_rewrites: run not found. run_id=%s", run_id)
            return count
        for item in rewrites:
            block_id = item.get("block_id")
            new_markdown = item.get("updated_markdown")
            if not block_id or not new_markdown:
                continue
            block = self.repository.get_block(run_id, block_id)
            if block is None:
                logger.warning("_apply_bulk_rewrites: block not found. block_id=%s", block_id)
                continue
            block.content = self.persist_chart_images_in_markdown(
                run.workspace_id,
                str(new_markdown).strip(),
            )
            self.repository.save_block(block)
            count += 1
        return count

    def _extract_assistant_result(self, payload: Any) -> tuple[str, str | None, list[dict[str, str]]]:
        if isinstance(payload, dict):
            assistant_message = str(
                payload.get("assistant_message")
                or payload.get("message")
                or payload.get("response")
                or ""
            ).strip()

            updated_markdown = payload.get("updated_markdown")
            if updated_markdown is None:
                updated_markdown = payload.get("markdown")

            raw_rewrites = payload.get("cross_block_rewrites")
            cross_block_rewrites: list[dict[str, str]] = [
                r for r in (raw_rewrites or [])
                if isinstance(r, dict) and r.get("block_id") and r.get("instruction")
            ]

            if updated_markdown is not None:
                return assistant_message, str(updated_markdown), cross_block_rewrites

            return assistant_message, None, cross_block_rewrites

        if isinstance(payload, str):
            parsed = extract_json_object(payload)
            if parsed is not None:
                return self._extract_assistant_result(parsed)
            return payload.strip(), None, []

        return "", None, []

    def chat_with_block_agent(
        self,
        workspace_id: str,
        run_id: str,
        block_id: str,
        user_message: str,
        selected_snippet: str | None = None,
        conversation_id: int | None = None,
        chat_agent_id: int | None = None,
    ) -> dict[str, Any]:
        run = self.repository.get_run(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Generated run not found")

        block = self.repository.get_block(run_id, block_id)
        if block is None:
            raise ValueError("Block not found")

        mentions = [selected_snippet] if selected_snippet else []
        self._create_message(block_id=block_id, role="user", content=user_message, mentions=mentions)

        scope = self._detect_scope(user_message)
        agent_id = chat_agent_id if chat_agent_id is not None else settings.mattin_block_chat_agent_id
        assistant_message = ""
        proposed_content: str | None = None
        updated_content: str | None = None
        applied = False
        blocks_modified = False
        final_conversation_id = conversation_id

        # --- Document-wide scope ---
        if scope == "document":
            document_wide_agent_id = settings.mattin_document_wide_agent_id
            if document_wide_agent_id is None:
                logger.info(
                    "Document-wide request but MATTIN_DOCUMENT_WIDE_AGENT_ID not set; "
                    "falling back to default scope. run_id=%s", run_id,
                )
                scope = "default"
            else:
                try:
                    message = self._build_document_wide_message(
                        workspace_id=workspace_id,
                        run_id=run_id,
                        user_request=user_message,
                    )
                    response = self.mattin_client.call_agent(
                        agent_id=document_wide_agent_id,
                        message=message,
                        timeout=120,
                    )
                    payload: Any = response.get("response")
                    if isinstance(payload, str):
                        payload = extract_json_object(payload)
                    rewrites: list[dict[str, Any]] = []
                    if isinstance(payload, dict):
                        rewrites = [
                            r for r in (payload.get("rewrites") or [])
                            if isinstance(r, dict) and r.get("block_id") and r.get("updated_markdown")
                        ]
                    count = self._apply_bulk_rewrites(run_id, rewrites)
                    if count:
                        blocks_modified = True
                    assistant_message = (
                        f"Document-wide change applied to {count} block(s)."
                        if count else "No blocks required changes for that request."
                    )
                    logger.info(
                        "Document-wide rewrites applied. run_id=%s count=%d", run_id, count,
                    )
                except MattinClientError as exc:
                    logger.warning(
                        "Document-wide agent call failed. run_id=%s error=%s", run_id, exc,
                    )
                    assistant_message = f"Mattin agent call failed: {exc}"

        # --- Default (single/related) scope ---
        if scope == "default":
            if agent_id is None:
                assistant_message = (
                    "Block chat agent is not configured. "
                    "Set MATTIN_BLOCK_CHAT_AGENT_ID to enable assisted edits."
                )
            else:
                related_blocks_full_content = self._build_related_blocks_full_content(run_id, block_id)
                message = self._build_block_chat_message(
                    workspace_id=workspace_id,
                    run_id=run_id,
                    block_id=block_id,
                    block_title=block.title,
                    block_type=block.block_type,
                    block_content=block.content,
                    user_message=user_message,
                    selected_snippet=selected_snippet,
                    related_blocks_full_content=related_blocks_full_content,
                )

                try:
                    response = self.mattin_client.call_agent(
                        agent_id=agent_id,
                        message=message,
                        conversation_id=conversation_id,
                        timeout=60,
                    )
                    response_conversation_id = response.get("conversation_id")
                    if isinstance(response_conversation_id, int):
                        final_conversation_id = response_conversation_id

                    assistant_message, candidate_markdown, cross_block_rewrites = self._extract_assistant_result(
                        response.get("response")
                    )
                    if candidate_markdown and candidate_markdown.strip():
                        proposed_content = self.persist_chart_images_in_markdown(
                            workspace_id, candidate_markdown.strip()
                        )

                    if cross_block_rewrites:
                        # Expire the session identity map so that blocks modified by MCP
                        # calls (which use separate DB sessions) are re-fetched fresh.
                        self.repository.db.expire_all()
                        all_blocks = self.repository.list_blocks(run_id)
                        outline_text = "\n".join(
                            f"- [{b.order_index + 1}] {b.title} (block_id: {b.id}): {b.summary}"
                            for b in all_blocks
                        )
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            futures = [
                                executor.submit(
                                    self._rewrite_single_block,
                                    run_id,
                                    item["block_id"],
                                    item["instruction"],
                                    outline_text,
                                )
                                for item in cross_block_rewrites
                            ]
                            concurrent.futures.wait(futures, timeout=120)
                        blocks_modified = True
                        logger.info(
                            "Cross-block rewrites completed. run_id=%s count=%d",
                            run_id, len(cross_block_rewrites),
                        )
                except MattinClientError as exc:
                    logger.warning("Block chat agent call failed. run_id=%s block_id=%s error=%s", run_id, block_id, exc)
                    assistant_message = f"Mattin agent call failed: {exc}"

        if not assistant_message:
            assistant_message = "The assistant did not return any actionable response."

        self._create_message(block_id=block_id, role="assistant", content=assistant_message, mentions=[])

        return {
            "assistant_message": assistant_message,
            "conversation_id": final_conversation_id,
            "applied": applied,
            "blocks_modified": blocks_modified,
            "proposed_content": proposed_content,
            "updated_content": updated_content,
        }

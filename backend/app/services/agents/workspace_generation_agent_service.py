from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.core.config import settings
from app.integrations.mattin_client import MattinClient, MattinClientError
from app.utils.ids import new_id
from app.utils.json_payload import extract_json_object
from app.utils.markdown_blocks import create_file_name


logger = logging.getLogger(__name__)

MattinFileUpload = tuple[str, tuple[str, bytes, str]]


class WorkspaceGenerationAgentService:
    def __init__(self, mattin_client: MattinClient) -> None:
        self.mattin_client = mattin_client

    def generate_blocks(
        self,
        prompt: str,
        reference_titles: list[str],
        reference_file_ids: list[int],
        file_uploads: list[MattinFileUpload] | None = None,
    ) -> list[dict[str, Any]] | None:
        full_document = self._generate_full_document_with_agent(
            prompt=prompt,
            reference_titles=reference_titles,
            reference_file_ids=reference_file_ids,
            file_uploads=file_uploads,
        )

        if full_document is None:
            return None

        return self._split_document_into_blocks(
            document_title=full_document.get("title", "Generated document"),
            markdown=full_document.get("markdown", ""),
            reference_file_ids=reference_file_ids,
        )

    def _resolve_writer_agent_id(self) -> int | None:
        return settings.mattin_document_writer_agent_id

    def _resolve_splitter_agent_id(self) -> int | None:
        if settings.mattin_document_splitter_agent_id is not None:
            return settings.mattin_document_splitter_agent_id
        return self._resolve_writer_agent_id()

    def _is_embedding_service_error(self, error: Exception) -> bool:
        message = str(error).lower()
        return "embedding service" in message and "configured" in message

    def _call_agent_with_reference_fallback(
        self,
        *,
        agent_id: int,
        message: str,
        file_references: list[int],
        file_uploads: list[MattinFileUpload] | None = None,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        try:
            return self.mattin_client.call_agent(
                agent_id=agent_id,
                message=message,
                file_references=file_references or None,
                files=file_uploads or None,
                timeout=timeout_seconds,
            )
        except MattinClientError as exc:
            if not file_references or not self._is_embedding_service_error(exc):
                raise

            logger.warning(
                "Agent call failed due embedding configuration with file references. "
                "Retrying without file references. agent_id=%s file_refs=%s error=%s",
                agent_id,
                len(file_references),
                exc,
            )
            return self.mattin_client.call_agent(
                agent_id=agent_id,
                message=message,
                file_references=None,
                files=file_uploads or None,
                timeout=timeout_seconds,
            )

    def _build_full_document_message(self, prompt: str, reference_titles: list[str]) -> str:
        references_section = (
            "\n".join(f"- {title}" for title in reference_titles)
            if reference_titles
            else "- No references available"
        )

        return (
            "You generate one complete markdown document. "
            "Usually you will also get a document as reference, and will be asked to generate the new document as a copy or adaptation of the reference."
            "Return ONLY valid JSON with this exact shape:\n"
            "{\n"
            '  "title": "string",\n'
            '  "summary": "string",\n'
            '  "markdown": "full markdown document"\n'
            "}\n\n"
            "Rules:\n"
            "- markdown must be complete and coherent from start to finish.\n"
            "- Include headings and practical editable text.\n"
            "- Do not split into chapter files in this stage.\n"
            "- Do not wrap JSON in markdown fences.\n\n"
            f"User request:\n{prompt.strip()}\n\n"
            f"Known references:\n{references_section}"
        )

    def _build_split_message(
        self,
        document_title: str,
        markdown: str,
        max_chars_per_block: int,
    ) -> str:
        return (
            "You split one markdown document into editable blocks. "
            "Usually you will get quite big documents, but can be smaller. "
            "Think carefully how to divide these blocks, sometimes it may could be by chapters, other times paragraphs, depending on the context or length of the document."
            "Return ONLY valid JSON with this exact shape:\n"
            "{\n"
            '  "blocks": [\n'
            "    {\n"
            '      "title": "string",\n'
            '      "block_type": "index|chapter|closing",\n'
            '      "summary": "string",\n'
            '      "markdown": "full markdown content"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- Do NOT include an index block; the server will generate it.\n"
            "- Keep each block roughly below max_chars_per_block when possible.\n"
            "- Keep text unchanged unless minor restructuring is needed for splitting.\n"
            "- Do not wrap JSON in markdown fences.\n\n"
            f"Document title:\n{document_title.strip() or 'Generated document'}\n\n"
            f"max_chars_per_block: {max_chars_per_block}\n\n"
            f"Document markdown:\n{markdown.strip()}"
        )

    def _coerce_full_document_payload(self, payload: Any) -> dict[str, str] | None:
        if payload is None:
            return None

        if isinstance(payload, str):
            parsed = extract_json_object(payload)
            if parsed is not None:
                return self._coerce_full_document_payload(parsed)

            try:
                decoded = json.loads(payload)
            except json.JSONDecodeError:
                decoded = None

            if decoded is not None:
                return self._coerce_full_document_payload(decoded)
            return None

        if isinstance(payload, dict):
            markdown_value = payload.get("markdown")
            if markdown_value is None:
                markdown_value = payload.get("content")

            if isinstance(markdown_value, str) and markdown_value.strip():
                title = str(payload.get("title") or payload.get("document_title") or "").strip()
                summary = str(payload.get("summary") or "").strip()
                return {
                    "title": title or "Generated document",
                    "summary": summary,
                    "markdown": markdown_value,
                }

            for key in (
                "response",
                "output",
                "content",
                "text",
                "message",
                "result",
                "data",
                "assistant_response",
            ):
                nested = self._coerce_full_document_payload(payload.get(key))
                if nested is not None:
                    return nested

            choices = payload.get("choices")
            if isinstance(choices, list):
                for choice in choices:
                    nested = self._coerce_full_document_payload(choice)
                    if nested is not None:
                        return nested

            return None

        if isinstance(payload, list):
            for item in payload:
                nested = self._coerce_full_document_payload(item)
                if nested is not None:
                    return nested

        return None

    def _coerce_generation_payload(self, payload: Any) -> dict[str, Any] | None:
        if payload is None:
            return None

        if isinstance(payload, str):
            parsed = extract_json_object(payload)
            if parsed is not None:
                return parsed

            try:
                decoded = json.loads(payload)
            except json.JSONDecodeError:
                decoded = None

            if decoded is not None:
                return self._coerce_generation_payload(decoded)
            return None

        if isinstance(payload, dict):
            if isinstance(payload.get("blocks"), list):
                return payload

            for key in (
                "response",
                "output",
                "content",
                "text",
                "message",
                "result",
                "data",
                "assistant_response",
            ):
                nested = self._coerce_generation_payload(payload.get(key))
                if nested is not None and isinstance(nested.get("blocks"), list):
                    return nested

            choices = payload.get("choices")
            if isinstance(choices, list):
                for choice in choices:
                    nested = self._coerce_generation_payload(choice)
                    if nested is not None and isinstance(nested.get("blocks"), list):
                        return nested

            return None

        if isinstance(payload, list):
            for item in payload:
                nested = self._coerce_generation_payload(item)
                if nested is not None and isinstance(nested.get("blocks"), list):
                    return nested

        return None

    def _build_local_summary(self, markdown: str) -> str:
        for line in markdown.splitlines():
            cleaned = re.sub(r"^#{1,6}\s*", "", line.strip())
            if not cleaned:
                continue
            cleaned = re.sub(r"\s+", " ", cleaned)
            return cleaned[:160]
        return "Generated content block."

    def _chunk_markdown(self, markdown: str, max_chars: int) -> list[str]:
        text = markdown.strip()
        if not text:
            return []
        if len(text) <= max_chars:
            return [text]

        chunks: list[str] = []
        current = ""
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]

        for paragraph in paragraphs:
            if len(paragraph) > max_chars:
                if current:
                    chunks.append(current)
                    current = ""

                remaining = paragraph
                while len(remaining) > max_chars:
                    split_at = remaining.rfind("\n", 0, max_chars)
                    if split_at < max_chars // 2:
                        split_at = remaining.rfind(" ", 0, max_chars)
                    if split_at < max_chars // 2:
                        split_at = max_chars
                    chunks.append(remaining[:split_at].strip())
                    remaining = remaining[split_at:].strip()
                if remaining:
                    current = remaining
                continue

            candidate = paragraph if not current else f"{current}\n\n{paragraph}"
            if len(candidate) <= max_chars:
                current = candidate
            else:
                chunks.append(current)
                current = paragraph

        if current:
            chunks.append(current)

        return [chunk for chunk in chunks if chunk.strip()]

    def _split_document_locally(
        self,
        document_title: str,
        markdown: str,
        max_chars_per_block: int,
    ) -> list[dict[str, Any]] | None:
        content = markdown.strip()
        if not content:
            return None

        sections: list[tuple[str, str]] = []
        current_title = document_title.strip() or "Generated document"
        current_lines: list[str] = []

        for line in content.splitlines():
            match = re.match(r"^#{1,3}\s+(.+?)\s*$", line.strip())
            if match is not None:
                section_text = "\n".join(current_lines).strip()
                if section_text:
                    sections.append((current_title, section_text))
                current_title = match.group(1).strip() or current_title
                current_lines = [line]
                continue
            current_lines.append(line)

        tail_text = "\n".join(current_lines).strip()
        if tail_text:
            sections.append((current_title, tail_text))

        if not sections:
            sections = [(current_title, content)]

        raw_blocks: list[dict[str, Any]] = []
        for section_title, section_markdown in sections:
            section_chunks = self._chunk_markdown(section_markdown, max_chars=max_chars_per_block)
            if not section_chunks:
                continue

            for index, chunk in enumerate(section_chunks):
                chunk_title = section_title
                if len(section_chunks) > 1:
                    chunk_title = f"{section_title} (Part {index + 1})"

                raw_blocks.append(
                    {
                        "title": chunk_title,
                        "block_type": "chapter",
                        "summary": self._build_local_summary(chunk),
                        "content": chunk,
                    }
                )

        if not raw_blocks:
            return None

        closing_terms = ("closing", "conclusion", "next steps", "summary")
        last_title = raw_blocks[-1]["title"].strip().lower()
        if any(term in last_title for term in closing_terms):
            raw_blocks[-1]["block_type"] = "closing"

        return self._normalize_blocks_with_index(raw_blocks)

    def _normalize_blocks_with_index(self, blocks: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
        content_blocks: list[dict[str, Any]] = []
        for item in blocks:
            if not isinstance(item, dict):
                continue

            raw_block_type = str(item.get("block_type", "")).strip().lower()
            if raw_block_type == "index":
                continue

            markdown_content = item.get("markdown")
            if markdown_content is None:
                markdown_content = item.get("content")

            markdown_text = str(markdown_content or "").strip()
            if not markdown_text:
                continue

            block_type = raw_block_type or "chapter"
            if block_type not in {"chapter", "closing"}:
                block_type = "chapter"

            title = str(item.get("title", "")).strip() or f"Block {len(content_blocks) + 1}"
            summary = str(item.get("summary", "")).strip() or self._build_local_summary(markdown_text)
            content_blocks.append(
                {
                    "title": title,
                    "block_type": block_type,
                    "summary": summary,
                    "content": markdown_text,
                }
            )

        if not content_blocks:
            return None

        assembled = [
            {
                "title": "General index",
                "block_type": "index",
                "summary": "Map of chapters and relationships between blocks.",
                "content": "",
            },
            *content_blocks,
        ]

        normalized: list[dict[str, Any]] = []
        for order_index, item in enumerate(assembled):
            normalized.append(
                {
                    "id": new_id(),
                    "order_index": order_index,
                    "title": item["title"],
                    "block_type": item["block_type"],
                    "summary": item["summary"],
                    "file_name": create_file_name(order_index, item["title"]),
                    "content": item["content"],
                }
            )

        links = [
            f"- [{block['title']}](./{block['file_name']})"
            for block in normalized
            if block["order_index"] > 0
        ]
        normalized[0]["content"] = "# Index\n\n" + "\n".join(links)

        return normalized

    def _normalize_agent_generated_blocks(self, payload: dict[str, Any]) -> list[dict[str, Any]] | None:
        blocks_raw = payload.get("blocks")
        if not isinstance(blocks_raw, list) or not blocks_raw:
            return None

        normalized_blocks: list[dict[str, Any]] = []
        for index, item in enumerate(blocks_raw):
            if not isinstance(item, dict):
                continue

            title = str(item.get("title", "")).strip() or f"Block {index + 1}"
            block_type = str(item.get("block_type", "chapter")).strip() or "chapter"
            summary = str(item.get("summary", "")).strip()

            markdown_content = item.get("markdown")
            if markdown_content is None:
                markdown_content = item.get("content", "")

            normalized_blocks.append(
                {
                    "title": title,
                    "block_type": block_type,
                    "summary": summary,
                    "content": str(markdown_content),
                }
            )

        return normalized_blocks or None

    def _generate_full_document_with_agent(
        self,
        prompt: str,
        reference_titles: list[str],
        reference_file_ids: list[int],
        file_uploads: list[MattinFileUpload] | None,
    ) -> dict[str, str] | None:
        agent_id = self._resolve_writer_agent_id()
        if agent_id is None:
            return None

        timeout_seconds = max(5, settings.mattin_generation_timeout_seconds)
        max_retries = max(0, settings.mattin_generation_max_retries)
        total_attempts = max_retries + 1
        message = self._build_full_document_message(prompt=prompt, reference_titles=reference_titles)
        file_references = list(dict.fromkeys(reference_file_ids))

        logger.info(
            "Writer run started. agent_id=%s prompt_len=%s references=%s timeout_s=%s retries=%s file_refs=%s",
            agent_id,
            len(prompt.strip()),
            reference_titles,
            timeout_seconds,
            max_retries,
            len(file_references),
        )

        response: dict[str, Any] | None = None
        for attempt in range(1, total_attempts + 1):
            attempt_timeout = timeout_seconds * attempt
            try:
                response = self._call_agent_with_reference_fallback(
                    agent_id=agent_id,
                    message=message,
                    file_references=file_references,
                    file_uploads=file_uploads,
                    timeout_seconds=attempt_timeout,
                )
                break
            except MattinClientError as exc:
                logger.warning(
                    "Writer agent call failed. agent_id=%s attempt=%s/%s timeout_s=%s error=%s",
                    agent_id,
                    attempt,
                    total_attempts,
                    attempt_timeout,
                    exc,
                )
                if attempt == total_attempts:
                    return None

        if response is None:
            return None

        parsed = self._coerce_full_document_payload(response.get("response"))
        if parsed is None:
            logger.warning(
                "Writer response could not be parsed as full-document payload. response_keys=%s",
                sorted(response.keys()),
            )
            return None

        logger.info(
            "Writer payload parsed. title=%s markdown_len=%s",
            parsed.get("title"),
            len(parsed.get("markdown", "")),
        )
        return parsed

    def _split_document_into_blocks(
        self,
        document_title: str,
        markdown: str,
        reference_file_ids: list[int],
    ) -> list[dict[str, Any]] | None:
        max_chars_per_block = 6000
        splitter_agent_id = self._resolve_splitter_agent_id()

        if splitter_agent_id is not None:
            timeout_seconds = max(5, settings.mattin_generation_timeout_seconds)
            message = self._build_split_message(
                document_title=document_title,
                markdown=markdown,
                max_chars_per_block=max_chars_per_block,
            )
            file_references = list(dict.fromkeys(reference_file_ids))

            try:
                response = self._call_agent_with_reference_fallback(
                    agent_id=splitter_agent_id,
                    message=message,
                    file_references=file_references,
                    timeout_seconds=timeout_seconds,
                )
                parsed_payload = self._coerce_generation_payload(response.get("response"))
                if parsed_payload is not None:
                    normalized_agent_blocks = self._normalize_agent_generated_blocks(parsed_payload)
                    if normalized_agent_blocks:
                        rebuilt = self._normalize_blocks_with_index(normalized_agent_blocks)
                        if rebuilt:
                            logger.info(
                                "Splitter payload parsed. agent_id=%s blocks_count=%s",
                                splitter_agent_id,
                                len(rebuilt),
                            )
                            return rebuilt
            except MattinClientError as exc:
                logger.warning("Splitter agent call failed. agent_id=%s error=%s", splitter_agent_id, exc)

        local_blocks = self._split_document_locally(
            document_title=document_title,
            markdown=markdown,
            max_chars_per_block=max_chars_per_block,
        )
        if local_blocks:
            logger.info("Local splitter generated blocks. blocks_count=%s", len(local_blocks))
        return local_blocks



import re
from typing import Any


HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
KEY_ENTITY_PATTERNS = [
    re.compile(r"\b(?:budget|coste|presupuesto|financiero)\b", re.IGNORECASE),
    re.compile(r"\b(?:timeline|plazo|cronograma|deadline)\b", re.IGNORECASE),
    re.compile(r"\b(?:requirement|requisito|constraint|restriccion)\b", re.IGNORECASE),
    re.compile(r"\b(?:risk|riesgo|mitigation|mitigacion)\b", re.IGNORECASE),
    re.compile(r"\b(?:scope|alcance|deliverable|entregable)\b", re.IGNORECASE),
    re.compile(r"\b(?:stakeholder|interesado|equipo|team)\b", re.IGNORECASE),
]


def extract_tags_from_content(content: str) -> list[str]:
    tags: list[str] = []
    for pattern in KEY_ENTITY_PATTERNS:
        if pattern.search(content):
            tag = pattern.pattern.replace(r"\b", "").replace(r"(?:", "").split("|")[0].rstrip(")")
            tags.append(tag)
    return list(set(tags))


def extract_key_entities(content: str) -> list[str]:
    entities: list[str] = []
    headings = HEADING_PATTERN.findall(content)
    for heading in headings:
        cleaned = heading.strip().lower()
        if cleaned:
            entities.append(cleaned)
    return entities


def build_block_metadata(content: str, tags: list[str] | None = None, entities: list[str] | None = None) -> dict[str, Any]:
    return {
        "tags": tags or extract_tags_from_content(content),
        "key_entities": entities or extract_key_entities(content),
    }

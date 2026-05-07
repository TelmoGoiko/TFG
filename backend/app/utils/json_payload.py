import json


def extract_json_object(text: str) -> dict | None:
    """Extract a JSON object from plain text or fenced markdown text."""
    raw = text.strip()
    if not raw:
        return None

    candidates: list[str] = [raw]

    if raw.startswith("```"):
        lines = raw.splitlines()
        if len(lines) >= 3:
            fenced = "\n".join(lines[1:-1]).strip()
            if fenced:
                candidates.append(fenced)

    object_start = raw.find("{")
    object_end = raw.rfind("}")
    if object_start != -1 and object_end > object_start:
        candidates.append(raw[object_start : object_end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    return None

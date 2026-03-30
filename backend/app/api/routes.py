from fastapi import APIRouter

router = APIRouter(tags=["items"])

_items: list[dict] = []


@router.get("/items")
def list_items() -> list[dict]:
    return _items


@router.post("/items")
def create_item(item: dict) -> dict:
    _items.append(item)
    return item

import json
from datetime import datetime
from hashlib import md5

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Block(Base):
    __tablename__ = "blocks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspace_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    block_type: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    meta: Mapped[str] = mapped_column("metadata", Text, nullable=False, default="{}")

    def compute_content_hash(self) -> str:
        return md5(self.content.encode("utf-8")).hexdigest()

    def get_meta_dict(self) -> dict:
        try:
            return json.loads(self.meta)
        except (json.JSONDecodeError, TypeError):
            return {}

    def update_meta(self, updates: dict) -> None:
        data = self.get_meta_dict()
        data.update(updates)
        self.meta = json.dumps(data, ensure_ascii=False)

    def refresh_meta_on_save(self) -> None:
        self.update_meta({
            "content_hash": self.compute_content_hash(),
            "last_modified": datetime.now().isoformat(),
        })

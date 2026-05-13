from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ImpactSuggestionRecord(Base):
    __tablename__ = "impact_suggestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspace_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_block_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("blocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    affected_block_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("blocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    conversation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

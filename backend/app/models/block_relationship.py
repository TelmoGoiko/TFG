from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class BlockRelationship(Base):
    __tablename__ = "block_relationships"

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
    target_block_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("blocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    auto_created: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        sa.UniqueConstraint("workspace_run_id", "source_block_id", "target_block_id", "relationship_type", name="uq_block_relationship_run_source_target_type"),
    )

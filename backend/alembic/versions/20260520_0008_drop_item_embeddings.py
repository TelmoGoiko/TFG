"""drop item_embeddings table

Revision ID: 20260520_0008
Revises: 20260512_0007
Create Date: 2026-05-20
"""

from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa

revision: str = "20260520_0008"
down_revision: Union[str, None] = "20260512_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f("ix_item_embeddings_id"), table_name="item_embeddings")
    op.drop_table("item_embeddings")


def downgrade() -> None:
    op.create_table(
        "item_embeddings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(dim=1536), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_item_embeddings_id"), "item_embeddings", ["id"], unique=False)

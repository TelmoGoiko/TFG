"""initial schema with pgvector

Revision ID: 20260330_0001
Revises:
Create Date: 2026-03-30
"""

from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260330_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "item_embeddings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(dim=1536), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_item_embeddings_id"), "item_embeddings", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_item_embeddings_id"), table_name="item_embeddings")
    op.drop_table("item_embeddings")

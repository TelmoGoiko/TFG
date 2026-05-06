"""add block metadata and block_relationships table

Revision ID: 20260427_0006
Revises: 20260420_0005
Create Date: 2026-04-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260427_0006"
down_revision: Union[str, None] = "20260420_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("""
        ALTER TABLE blocks ADD COLUMN IF NOT EXISTS metadata TEXT NOT NULL DEFAULT '{}'
    """))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS block_relationships (
            id VARCHAR(36) PRIMARY KEY,
            workspace_run_id VARCHAR(36) NOT NULL REFERENCES workspace_runs(id) ON DELETE CASCADE,
            source_block_id VARCHAR(36) NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
            target_block_id VARCHAR(36) NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
            relationship_type VARCHAR(50) NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            auto_created BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            CONSTRAINT uq_block_relationship_run_source_target_type
                UNIQUE (workspace_run_id, source_block_id, target_block_id, relationship_type)
        )
    """))

    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_block_relationships_source_block_id
        ON block_relationships (source_block_id)
    """))

    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_block_relationships_target_block_id
        ON block_relationships (target_block_id)
    """))

    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_block_relationships_workspace_run_id
        ON block_relationships (workspace_run_id)
    """))


def downgrade() -> None:
    op.drop_index("ix_block_relationships_target_block_id", table_name="block_relationships")
    op.drop_index("ix_block_relationships_source_block_id", table_name="block_relationships")
    op.drop_table("block_relationships")
    op.drop_column("blocks", "metadata")

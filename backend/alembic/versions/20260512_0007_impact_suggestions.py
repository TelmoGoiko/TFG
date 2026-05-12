"""add impact_suggestions table

Revision ID: 20260512_0007
Revises: 20260427_0006
Create Date: 2026-05-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260512_0007"
down_revision: Union[str, None] = "20260427_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS impact_suggestions (
            id VARCHAR(36) PRIMARY KEY,
            workspace_run_id VARCHAR(36) NOT NULL REFERENCES workspace_runs(id) ON DELETE CASCADE,
            source_block_id VARCHAR(36) NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
            affected_block_id VARCHAR(36) NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
            relationship_type VARCHAR(50) NOT NULL,
            reason TEXT NOT NULL,
            suggestion TEXT NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            conversation_id INTEGER NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL
        )
    """))

    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_impact_suggestions_workspace_run_id
        ON impact_suggestions (workspace_run_id)
    """))

    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_impact_suggestions_source_block_id
        ON impact_suggestions (source_block_id)
    """))

    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_impact_suggestions_affected_block_id
        ON impact_suggestions (affected_block_id)
    """))

    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_impact_suggestions_status
        ON impact_suggestions (status)
    """))


def downgrade() -> None:
    op.drop_index("ix_impact_suggestions_status", table_name="impact_suggestions")
    op.drop_index("ix_impact_suggestions_affected_block_id", table_name="impact_suggestions")
    op.drop_index("ix_impact_suggestions_source_block_id", table_name="impact_suggestions")
    op.drop_index("ix_impact_suggestions_workspace_run_id", table_name="impact_suggestions")
    op.drop_table("impact_suggestions")

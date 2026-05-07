"""add mattin linkage fields to workspaces and files

Revision ID: 20260420_0005
Revises: 20260409_0004
Create Date: 2026-04-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260420_0005"
down_revision: Union[str, None] = "20260409_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workspaces", sa.Column("mattin_repository_id", sa.String(length=128), nullable=True))
    op.create_index(
        op.f("ix_workspaces_mattin_repository_id"),
        "workspaces",
        ["mattin_repository_id"],
        unique=False,
    )

    op.add_column("workspace_files", sa.Column("mattin_file_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_workspace_files_mattin_file_id"),
        "workspace_files",
        ["mattin_file_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_workspace_files_mattin_file_id"), table_name="workspace_files")
    op.drop_column("workspace_files", "mattin_file_id")

    op.drop_index(op.f("ix_workspaces_mattin_repository_id"), table_name="workspaces")
    op.drop_column("workspaces", "mattin_repository_id")

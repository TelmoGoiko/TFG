"""refactor repository schema into workspace contexts

Revision ID: 20260409_0004
Revises: 20260331_0003
Create Date: 2026-04-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260409_0004"
down_revision: Union[str, None] = "20260331_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("workspaces", "workspace_runs")

    op.execute("ALTER TABLE workspace_runs RENAME COLUMN repository_id TO workspace_id")
    op.execute("ALTER INDEX ix_workspaces_repository_id RENAME TO ix_workspace_runs_workspace_id")
    op.execute("ALTER TABLE workspace_runs DROP CONSTRAINT workspaces_repository_id_fkey")

    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workspaces_owner_id"), "workspaces", ["owner_id"], unique=False)

    op.execute(
        """
        INSERT INTO workspaces (id, owner_id, name, description, created_at)
        SELECT id, owner_id, name, description, created_at
        FROM repositories
        """
    )

    op.execute("ALTER TABLE workspace_runs ADD CONSTRAINT workspace_runs_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE")

    op.execute("ALTER TABLE documents RENAME COLUMN repository_id TO workspace_id")
    op.execute("ALTER INDEX ix_documents_repository_id RENAME TO ix_documents_workspace_id")
    op.execute("ALTER TABLE documents DROP CONSTRAINT documents_repository_id_fkey")
    op.execute("ALTER TABLE documents ADD CONSTRAINT documents_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE")

    op.rename_table("repository_files", "workspace_files")
    op.execute("ALTER TABLE workspace_files RENAME COLUMN repository_id TO workspace_id")
    op.execute("ALTER INDEX ix_repository_files_repository_id RENAME TO ix_workspace_files_workspace_id")
    op.execute("ALTER TABLE workspace_files DROP CONSTRAINT repository_files_repository_id_fkey")
    op.execute("ALTER TABLE workspace_files ADD CONSTRAINT workspace_files_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE")

    op.execute("ALTER TABLE blocks RENAME COLUMN workspace_id TO workspace_run_id")
    op.execute("ALTER INDEX ix_blocks_workspace_id RENAME TO ix_blocks_workspace_run_id")
    op.execute("ALTER TABLE blocks DROP CONSTRAINT blocks_workspace_id_fkey")
    op.execute("ALTER TABLE blocks ADD CONSTRAINT blocks_workspace_run_id_fkey FOREIGN KEY (workspace_run_id) REFERENCES workspace_runs (id) ON DELETE CASCADE")

    op.drop_index(op.f("ix_repositories_owner_id"), table_name="repositories")
    op.drop_table("repositories")


def downgrade() -> None:
    op.create_table(
        "repositories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_repositories_owner_id"), "repositories", ["owner_id"], unique=False)

    op.execute(
        """
        INSERT INTO repositories (id, owner_id, name, description, created_at)
        SELECT id, owner_id, name, description, created_at
        FROM workspaces
        """
    )

    op.execute("ALTER TABLE blocks DROP CONSTRAINT blocks_workspace_run_id_fkey")
    op.execute("ALTER INDEX ix_blocks_workspace_run_id RENAME TO ix_blocks_workspace_id")
    op.execute("ALTER TABLE blocks RENAME COLUMN workspace_run_id TO workspace_id")
    op.execute("ALTER TABLE blocks ADD CONSTRAINT blocks_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE")

    op.execute("ALTER TABLE workspace_files DROP CONSTRAINT workspace_files_workspace_id_fkey")
    op.execute("ALTER INDEX ix_workspace_files_workspace_id RENAME TO ix_repository_files_repository_id")
    op.execute("ALTER TABLE workspace_files RENAME COLUMN workspace_id TO repository_id")
    op.rename_table("workspace_files", "repository_files")
    op.execute("ALTER TABLE repository_files ADD CONSTRAINT repository_files_repository_id_fkey FOREIGN KEY (repository_id) REFERENCES repositories (id) ON DELETE CASCADE")

    op.execute("ALTER TABLE documents DROP CONSTRAINT documents_workspace_id_fkey")
    op.execute("ALTER INDEX ix_documents_workspace_id RENAME TO ix_documents_repository_id")
    op.execute("ALTER TABLE documents RENAME COLUMN workspace_id TO repository_id")
    op.execute("ALTER TABLE documents ADD CONSTRAINT documents_repository_id_fkey FOREIGN KEY (repository_id) REFERENCES repositories (id) ON DELETE CASCADE")

    op.execute("ALTER TABLE workspace_runs DROP CONSTRAINT workspace_runs_workspace_id_fkey")

    op.drop_index(op.f("ix_workspaces_owner_id"), table_name="workspaces")
    op.drop_table("workspaces")

    op.execute("ALTER INDEX ix_workspace_runs_workspace_id RENAME TO ix_workspaces_repository_id")
    op.execute("ALTER TABLE workspace_runs RENAME COLUMN workspace_id TO repository_id")
    op.rename_table("workspace_runs", "workspaces")
    op.execute("ALTER TABLE workspaces ADD CONSTRAINT workspaces_repository_id_fkey FOREIGN KEY (repository_id) REFERENCES repositories (id) ON DELETE CASCADE")

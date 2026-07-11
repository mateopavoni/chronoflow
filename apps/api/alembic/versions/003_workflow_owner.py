"""Add owner_id to workflows (per-user authorization boundary).

Fixes a gap where /api/workflows, /api/runs and /api/ws/runs had no ownership
check at all: any authenticated (or, before this, even unauthenticated) client
could read/run/delete any workflow by UUID. Workflows are now scoped to the
user that created them; the 3 example workflows are seeded per-user on
register instead of once globally (see app/services/seed.py).

No production deployment exists yet for this project (see README — the demo
badge is a placeholder), so there is no real user data to preserve. Any
pre-existing workflow rows predate the ownership model and have no owner to
backfill to, so they are dropped rather than left orphaned under a NOT NULL
FK column.

Revision ID: 003_workflow_owner
Revises: 002_users
Create Date: 2026-07-11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_workflow_owner"
down_revision: Union[str, None] = "002_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Pre-ownership rows (global seed data) have no owner to assign — drop them.
    op.execute("DELETE FROM workflows")

    op.add_column(
        "workflows",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_workflows_owner_id_users",
        "workflows",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column("workflows", "owner_id", nullable=False)
    op.create_index("ix_workflows_owner_id", "workflows", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_workflows_owner_id", table_name="workflows")
    op.drop_constraint("fk_workflows_owner_id_users", "workflows", type_="foreignkey")
    op.drop_column("workflows", "owner_id")

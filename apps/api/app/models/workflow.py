"""ORM model: Workflow.

Stores the DAG definition (nodes + edges) as JSONB.
Using JSON type from SQLAlchemy which maps to JSONB in PostgreSQL
and plain JSON/TEXT in SQLite (used in tests).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Owner (authorization boundary): every route that reads/writes a Workflow
    # (and, transitively, its Runs/ExecutionEvents) must check this against the
    # authenticated user — see app/api/routes/workflows.py and runs.py. Without
    # this the API has no multi-tenant isolation at all (any authenticated user
    # could read/run/delete any other user's workflow by guessing/enumerating a UUID).
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # graph = { nodes: [...], edges: [...] } — stored as JSONB in Postgres
    graph: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    runs: Mapped[list[WorkflowRun]] = relationship(  # noqa: F821
        "WorkflowRun",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )

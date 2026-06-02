"""ORM models: WorkflowRun and ExecutionEvent.

WorkflowRun: one execution of a Workflow.
ExecutionEvent: append-only log of per-node transitions (the time-travel record).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # pending → running → completed | failed
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")

    # The payload passed when triggering the run
    trigger_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    # The accumulated context at the end of the run (output of all nodes)
    final_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workflow: Mapped[Workflow] = relationship("Workflow", back_populates="runs")  # type: ignore[name-defined]  # noqa: F821
    events: Mapped[list[ExecutionEvent]] = relationship(
        "ExecutionEvent",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="ExecutionEvent.sequence",
    )


class ExecutionEvent(Base):
    """Immutable log entry for a single node transition within a run.

    One row is written when the node starts (status=running),
    another is written (or the same updated) when it finishes (completed/failed/skipped).

    Design note: we write TWO rows per node transition:
      - status=running  (at start, output=null)
      - status=completed|failed|skipped  (at finish, with output/error)

    This mirrors exactly what the WebSocket streams to the frontend,
    and it is what the time-travel scrubber replays.
    """

    __tablename__ = "execution_events"

    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="uq_event_run_sequence"),
        Index("ix_event_run_sequence", "run_id", "sequence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_id: Mapped[str] = mapped_column(String, nullable=False)

    # Global monotonic sequence within the run (used by the time-travel scrubber)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    # running | completed | failed | skipped
    status: Mapped[str] = mapped_column(String(16), nullable=False)

    # Snapshot of the context dict at the moment this node started
    input_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Output produced by this node (null while running or if failed/skipped)
    output: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    run: Mapped[WorkflowRun] = relationship("WorkflowRun", back_populates="events")

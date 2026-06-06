"""Pydantic v2 schemas for WorkflowRun and ExecutionEvent."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

RunStatus = Literal["pending", "running", "completed", "failed"]
EventStatus = Literal["running", "completed", "failed", "skipped"]


class TriggerPayloadIn(BaseModel):
    """Body for POST /workflows/{id}/run."""

    trigger_payload: dict[str, Any] = {}


class RunOut(BaseModel):
    """Response schema for a WorkflowRun."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_id: uuid.UUID
    status: RunStatus
    trigger_payload: dict[str, Any]
    final_payload: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ExecutionEventOut(BaseModel):
    """Response schema for a single ExecutionEvent (time-travel record)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    node_id: str
    sequence: int
    status: EventStatus
    input_snapshot: dict[str, Any]
    output: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int | None = None

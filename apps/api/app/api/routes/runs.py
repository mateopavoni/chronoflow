"""Runs and ExecutionEvents routes.

Prefix: /api/runs  (mounted in main.py)

Routes:
  GET  /                    → list runs (optional ?workflow_id=)
  GET  /{id}                → get single run
  GET  /{id}/events         → time-travel log (ordered by sequence)
  POST /{id}/replay         → create a new run with same workflow + trigger (202)
"""

from __future__ import annotations

import uuid
from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import AsyncSessionLocal
from app.db.session import get_session
from app.engine.validator import validate_graph
from app.models.run import ExecutionEvent, WorkflowRun
from app.schemas.graph import Graph
from app.schemas.run import ExecutionEventOut, RunOut
from app.services.task_manager import launch_run

router = APIRouter()


# ─── List runs ────────────────────────────────────────────────────────────────


@router.get("/", response_model=list[RunOut])
async def list_runs(
    workflow_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """List runs, optionally filtered by workflow_id."""
    stmt = select(WorkflowRun).order_by(WorkflowRun.started_at.desc())
    if workflow_id is not None:
        stmt = stmt.where(WorkflowRun.workflow_id == workflow_id)
    result = await session.execute(stmt)
    return result.scalars().all()


# ─── Get single run ───────────────────────────────────────────────────────────


@router.get("/{run_id}", response_model=RunOut)
async def get_run(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    run = await session.get(WorkflowRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run


# ─── Get execution events (time-travel log) ───────────────────────────────────


@router.get("/{run_id}/events", response_model=list[ExecutionEventOut])
async def get_run_events(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Return all ExecutionEvents for a run, ordered by sequence.

    This is the dataset the frontend uses for time-travel debugging:
    apply events 0..k to reconstruct the DAG state at time k.
    """
    # Verify the run exists first
    run = await session.get(WorkflowRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    stmt = (
        select(ExecutionEvent)
        .where(ExecutionEvent.run_id == run_id)
        .order_by(ExecutionEvent.sequence)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


# ─── Replay ───────────────────────────────────────────────────────────────────


@router.post("/{run_id}/replay", response_model=RunOut, status_code=status.HTTP_202_ACCEPTED)
async def replay_run(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Create a new run with the same workflow and trigger_payload.

    The new run starts fresh — it does not share events with the original.
    Note: deterministic for transform/delay/branch; http nodes may return
    different results (documented trade-off, see ARCHITECTURE.md §7).
    """
    original = await session.get(WorkflowRun, run_id)
    if original is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    # Load the workflow to validate it still exists and is valid
    from app.models.workflow import Workflow

    wf = await session.get(Workflow, original.workflow_id)
    if wf is None:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow {original.workflow_id} not found (may have been deleted)",
        )

    # Validate before replaying
    graph = Graph.model_validate(wf.graph)
    validation = validate_graph(graph)
    if not validation.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Graph validation failed", "errors": validation.errors},
        )

    from datetime import datetime

    now = datetime.now(UTC)
    new_run = WorkflowRun(
        workflow_id=original.workflow_id,
        status="pending",
        trigger_payload=dict(original.trigger_payload),
        started_at=now,
    )
    session.add(new_run)
    await session.commit()
    await session.refresh(new_run)

    launch_run(run_id=new_run.id, session_factory=AsyncSessionLocal)

    return new_run

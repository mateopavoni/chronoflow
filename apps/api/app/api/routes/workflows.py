"""Workflow CRUD routes + validate + run endpoints.

Prefix: /api/workflows  (mounted in main.py)

Routes:
  GET    /               → list all workflows
  POST   /               → create workflow (201)
  GET    /{id}           → get single workflow
  PUT    /{id}           → update workflow
  DELETE /{id}           → delete workflow (204)
  POST   /{id}/validate  → validate DAG (ValidationResult)
  POST   /{id}/run       → trigger a run (202, RunOut)

Authorization: every route requires a logged-in user (`get_current_user`) and
every single-resource route scopes its query to `owner_id == user.id` — a
workflow that exists but belongs to someone else returns 404, same as one
that doesn't exist at all, so a caller can't distinguish "not yours" from
"doesn't exist" (avoids confirming other users' workflow IDs).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.engine import AsyncSessionLocal
from app.db.session import get_session
from app.engine.validator import validate_graph
from app.models.run import WorkflowRun
from app.models.user import User
from app.models.workflow import Workflow
from app.schemas.graph import Graph
from app.schemas.run import RunOut, TriggerPayloadIn
from app.schemas.workflow import ValidationResult, WorkflowIn, WorkflowOut
from app.services.task_manager import launch_run

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def _get_owned_workflow(
    session: AsyncSession, workflow_id: uuid.UUID, user: User
) -> Workflow:
    """Load a workflow, 404 if missing OR not owned by `user` (see module docstring)."""
    wf = await session.get(Workflow, workflow_id)
    if wf is None or wf.owner_id != user.id:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    return wf


# ─── List ─────────────────────────────────────────────────────────────────────


@router.get("/", response_model=list[WorkflowOut])
async def list_workflows(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Workflow)
        .where(Workflow.owner_id == user.id)
        .order_by(Workflow.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


# ─── Create ───────────────────────────────────────────────────────────────────


@router.post("/", response_model=WorkflowOut, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    body: WorkflowIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    now = _utcnow()
    wf = Workflow(
        owner_id=user.id,
        name=body.name,
        description=body.description,
        graph=body.graph.model_dump(),
        created_at=now,
        updated_at=now,
    )
    session.add(wf)
    await session.commit()
    await session.refresh(wf)
    return wf


# ─── Get single ───────────────────────────────────────────────────────────────


@router.get("/{workflow_id}", response_model=WorkflowOut)
async def get_workflow(
    workflow_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await _get_owned_workflow(session, workflow_id, user)


# ─── Update ───────────────────────────────────────────────────────────────────


@router.put("/{workflow_id}", response_model=WorkflowOut)
async def update_workflow(
    workflow_id: uuid.UUID,
    body: WorkflowIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    wf = await _get_owned_workflow(session, workflow_id, user)

    wf.name = body.name
    wf.description = body.description
    wf.graph = body.graph.model_dump()
    wf.updated_at = _utcnow()
    await session.commit()
    await session.refresh(wf)
    return wf


# ─── Delete ───────────────────────────────────────────────────────────────────


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    wf = await _get_owned_workflow(session, workflow_id, user)
    await session.delete(wf)
    await session.commit()


# ─── Validate ─────────────────────────────────────────────────────────────────


@router.post("/{workflow_id}/validate", response_model=ValidationResult)
async def validate_workflow(
    workflow_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Validate the DAG structure and return errors/warnings.

    Returns 200 regardless of whether the graph is valid — the `valid` field
    in the response tells the caller. 422 is reserved for Pydantic body errors.
    """
    wf = await _get_owned_workflow(session, workflow_id, user)

    graph = Graph.model_validate(wf.graph)
    return validate_graph(graph)


# ─── Run ──────────────────────────────────────────────────────────────────────


@router.post("/{workflow_id}/run", response_model=RunOut, status_code=status.HTTP_202_ACCEPTED)
async def trigger_run(
    workflow_id: uuid.UUID,
    body: TriggerPayloadIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Trigger a new workflow run. Returns immediately (202) with the run_id.

    The run executes in the background. Poll GET /runs/{id} or subscribe to
    WS /api/ws/runs/{id} for live progress.
    """
    wf = await _get_owned_workflow(session, workflow_id, user)

    # Validate the graph before running
    graph = Graph.model_validate(wf.graph)
    validation = validate_graph(graph)
    if not validation.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Graph validation failed", "errors": validation.errors},
        )

    now = _utcnow()
    run = WorkflowRun(
        workflow_id=workflow_id,
        status="pending",
        trigger_payload=body.trigger_payload,
        started_at=now,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    # Launch in background — the run executes asynchronously in the same process.
    # We pass AsyncSessionLocal (the factory) so the background task creates
    # its own session, independent of the request session which closes here.
    launch_run(run_id=run.id, session_factory=AsyncSessionLocal)

    return run

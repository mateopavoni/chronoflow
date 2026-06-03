"""Runner — orchestrates a complete WorkflowRun from start to finish.

Responsibilities:
  1. Mark the WorkflowRun as "running".
  2. Seed the initial context with the trigger_payload.
  3. Invoke the scheduler (which runs all nodes and writes ExecutionEvents).
  4. Mark the run as "completed" or "failed" with the final_payload.
  5. Commit the transaction.

The runner is called from services/task_manager.py as an asyncio.Task,
so it runs concurrently with the HTTP request that triggered it.
The HTTP handler returns 202 before the runner starts.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.scheduler import EventPublisher, run_graph
from app.models.run import WorkflowRun
from app.models.workflow import Workflow
from app.schemas.graph import Graph


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def execute_run(
    run_id: uuid.UUID,
    session: AsyncSession,
    publish: EventPublisher | None = None,
) -> None:
    """Execute a WorkflowRun end-to-end.

    This function is designed to be called as a long-running asyncio.Task.
    It owns the full lifecycle of the run:
      pending → running → completed|failed

    Args:
        run_id:  The UUID of the WorkflowRun to execute.
        session: An async DB session. The runner manages its own transaction
                 (begin → flush events → commit on finish).
        publish: Optional event publisher for live WebSocket streaming.
    """
    # ── Load run + workflow ──────────────────────────────────────────────
    stmt = select(WorkflowRun).where(WorkflowRun.id == run_id)
    result = await session.execute(stmt)
    run: WorkflowRun | None = result.scalar_one_or_none()
    if run is None:
        # Should never happen if the caller created the run correctly
        raise RuntimeError(f"WorkflowRun {run_id} not found")

    wf_stmt = select(Workflow).where(Workflow.id == run.workflow_id)
    wf_result = await session.execute(wf_stmt)
    workflow: Workflow | None = wf_result.scalar_one_or_none()
    if workflow is None:
        raise RuntimeError(f"Workflow {run.workflow_id} not found (run {run_id})")

    # ── Mark as running ──────────────────────────────────────────────────
    run.status = "running"
    run.started_at = _utcnow()
    await session.flush()

    # ── Build initial context ────────────────────────────────────────────
    # context["trigger"] is the canonical entry point for JSONPath references
    # like "$.trigger.amount" in node configs.
    context: dict[str, Any] = {"trigger": dict(run.trigger_payload)}

    # ── Parse graph ──────────────────────────────────────────────────────
    graph = Graph.model_validate(workflow.graph)

    # ── Run the scheduler ────────────────────────────────────────────────
    final_context: dict[str, Any] = {}
    run_error: str | None = None

    try:
        final_context = await run_graph(
            graph=graph,
            context=context,
            run_id=run_id,
            session=session,
            publish=publish,
        )
    except Exception as exc:
        run_error = str(exc)

    # ── Mark run as completed / failed ───────────────────────────────────
    run.finished_at = _utcnow()

    if run_error:
        run.status = "failed"
        run.error = run_error
    else:
        # Check if any node failed (their output will have {"error": ...})
        # We detect failure by looking at the events — if any event is "failed",
        # the overall run is "failed".
        failed_nodes = [
            k for k, v in final_context.items()
            if isinstance(v, dict) and "error" in v and len(v) == 1
        ]
        if failed_nodes:
            run.status = "failed"
            run.error = f"Nodes failed: {', '.join(failed_nodes)}"
        else:
            run.status = "completed"
            # Store the final context (minus "trigger") as final_payload
            run.final_payload = {k: v for k, v in final_context.items() if k != "trigger"}

    await session.commit()

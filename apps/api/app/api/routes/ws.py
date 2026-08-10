"""WebSocket endpoint for live run event streaming.

Route: /api/ws/runs/{run_id}

Protocol:
  1. Client connects (browser sends the httpOnly session cookie automatically —
     same-origin WS handshake, no JS involvement).
  2. Server decodes the session cookie; closes 4401 if missing/invalid.
  3. Server verifies the run exists AND its workflow is owned by that user;
     closes 4004 otherwise (same code/message as "not found" — a run that
     belongs to someone else must be indistinguishable from one that doesn't
     exist, same rule as the REST routes in workflows.py/runs.py).
  4. Server subscribes to the in-process pub/sub channel for this run FIRST
     (before any DB read) so no event published in between can be missed —
     engine events are only flush()ed, not committed, until the run ends, so
     a separate DB session can't see them until then; the live queue is the
     only channel that catches events for a run still in progress.
  5. Server sends all already-persisted events (catch-up, in case the client
     connected after some events were already committed), then drains
     anything already queued live, deduping by event id against what catch-up
     already sent.
  6. Server sends new events as they arrive (live streaming).
  7. When the run finishes (completed/failed) the server sends a final
     {"type": "run_finished", "status": "..."} message and closes.
  8. On disconnect the subscription is cleaned up.

Message format: JSON-serialized ExecutionEventOut (matching the REST contract).
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Cookie, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.security import decode_access_token
from app.db.engine import AsyncSessionLocal
from app.models.run import ExecutionEvent, WorkflowRun
from app.models.workflow import Workflow
from app.schemas.run import ExecutionEventOut
from app.services.task_manager import subscribe, unsubscribe

router = APIRouter()

logger = logging.getLogger("chronoflow.ws")


@router.websocket("/runs/{run_id}")
async def ws_run_events(
    websocket: WebSocket,
    run_id: uuid.UUID,
    chronoflow_session: str | None = Cookie(default=None, alias="chronoflow_session"),
):
    """Stream ExecutionEvents for a run in real time."""
    await websocket.accept()

    run_id_str = str(run_id)

    # ── Step 0: authenticate from the session cookie ────────────────────
    user_id = decode_access_token(chronoflow_session) if chronoflow_session else None
    if user_id is None:
        await websocket.send_json({"error": "Not authenticated"})
        await websocket.close(code=4401)
        return

    # ── Step 1: subscribe FIRST, so no event published between "read
    # persisted events" and "start listening live" can be lost. Events are
    # only flush()ed (not commit()ted) by the engine until the run finishes,
    # so a run in progress is invisible to the catch-up query below — the
    # in-process queue is the only channel that can see it in time.
    queue = subscribe(run_id_str)
    sent_ids: set[uuid.UUID] = set()

    try:
        # ── Step 2: catch-up — send all already-persisted events ────────
        async with AsyncSessionLocal() as session:
            # Verify the run exists AND its workflow is owned by this user.
            stmt = (
                select(WorkflowRun)
                .join(Workflow, WorkflowRun.workflow_id == Workflow.id)
                .where(WorkflowRun.id == run_id, Workflow.owner_id == user_id)
            )
            result = await session.execute(stmt)
            run = result.scalar_one_or_none()
            if run is None:
                await websocket.send_json({"error": f"Run {run_id} not found"})
                await websocket.close(code=4004)
                return

            # Send existing events so the client can reconstruct current state
            stmt = (
                select(ExecutionEvent)
                .where(ExecutionEvent.run_id == run_id)
                .order_by(ExecutionEvent.sequence)
            )
            result = await session.execute(stmt)
            existing_events = result.scalars().all()

            for event in existing_events:
                out = ExecutionEventOut.model_validate(event)
                await websocket.send_text(out.model_dump_json())
                sent_ids.add(event.id)

            already_finished = run.status in ("completed", "failed")
            final_status = run.status

        # Drain anything that landed on the queue during/after the catch-up
        # read (possibly overlapping with what catch-up already sent) —
        # skip duplicates by event id.
        while not queue.empty():
            extra_event = queue.get_nowait()
            if extra_event.id in sent_ids:
                continue
            extra_out = ExecutionEventOut.model_validate(extra_event)
            await websocket.send_text(extra_out.model_dump_json())
            sent_ids.add(extra_event.id)

        if already_finished:
            await websocket.send_json({"type": "run_finished", "status": final_status})
            return

        # ── Step 3: stream live events ────────────────────────────────
        while True:
            # Block until a new event arrives from the engine
            event = await queue.get()

            if event.id not in sent_ids:
                out = ExecutionEventOut.model_validate(event)
                await websocket.send_text(out.model_dump_json())
                sent_ids.add(event.id)

            # Check if this event signals end of run
            # The runner marks the run as completed/failed after all events are emitted.
            # We detect the terminal signal by checking if the run is done after
            # receiving a "completed" or "failed" event from an "end" node,
            # OR by receiving the run's final status via the run object.
            # Simplest approach: after each event, reload run status.
            async with AsyncSessionLocal() as check_session:
                run_check = await check_session.get(WorkflowRun, run_id)
                if run_check and run_check.status in ("completed", "failed"):
                    # Drain remaining queued events before closing
                    while not queue.empty():
                        extra_event = queue.get_nowait()
                        if extra_event.id in sent_ids:
                            continue
                        extra_out = ExecutionEventOut.model_validate(extra_event)
                        await websocket.send_text(extra_out.model_dump_json())
                        sent_ids.add(extra_event.id)
                    await websocket.send_json(
                        {"type": "run_finished", "status": run_check.status}
                    )
                    break

    except WebSocketDisconnect:
        pass
    except Exception:
        # Don't let WS errors crash the server — but a real bug (serialization
        # failure, DB error mid-stream) must not vanish silently, or production
        # issues become undiagnosable. Log with run_id for correlation.
        logger.error("Unhandled error streaming run %s", run_id_str, exc_info=True)
    finally:
        unsubscribe(run_id_str, queue)
        try:
            await websocket.close()
        except Exception:
            pass

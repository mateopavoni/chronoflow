"""WebSocket endpoint for live run event streaming.

Route: /api/ws/runs/{run_id}

Protocol:
  1. Client connects.
  2. Server sends all already-persisted events (catch-up, in case the client
     connected after some events were already emitted).
  3. Server subscribes to the in-process pub/sub channel for this run.
  4. Server sends new events as they arrive (live streaming).
  5. When the run finishes (completed/failed) the server sends a final
     {"type": "run_finished", "status": "..."} message and closes.
  6. On disconnect the subscription is cleaned up.

Message format: JSON-serialized ExecutionEventOut (matching the REST contract).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.db.engine import AsyncSessionLocal
from app.models.run import ExecutionEvent, WorkflowRun
from app.schemas.run import ExecutionEventOut
from app.services.task_manager import subscribe, unsubscribe

router = APIRouter()


@router.websocket("/runs/{run_id}")
async def ws_run_events(websocket: WebSocket, run_id: uuid.UUID):
    """Stream ExecutionEvents for a run in real time."""
    await websocket.accept()

    run_id_str = str(run_id)

    # ── Step 1: catch-up — send all already-persisted events ────────────
    async with AsyncSessionLocal() as session:
        # Verify run exists
        run = await session.get(WorkflowRun, run_id)
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

        # If run is already finished, send terminal message and close
        if run.status in ("completed", "failed"):
            await websocket.send_json({"type": "run_finished", "status": run.status})
            await websocket.close()
            return

    # ── Step 2: subscribe and stream live events ─────────────────────────
    queue = subscribe(run_id_str)

    try:
        while True:
            # Block until a new event arrives from the engine
            event = await queue.get()

            out = ExecutionEventOut.model_validate(event)
            await websocket.send_text(out.model_dump_json())

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
                        extra_out = ExecutionEventOut.model_validate(extra_event)
                        await websocket.send_text(extra_out.model_dump_json())
                    await websocket.send_json(
                        {"type": "run_finished", "status": run_check.status}
                    )
                    break

    except WebSocketDisconnect:
        pass
    except Exception:
        # Don't let WS errors crash the server
        pass
    finally:
        unsubscribe(run_id_str, queue)
        try:
            await websocket.close()
        except Exception:
            pass

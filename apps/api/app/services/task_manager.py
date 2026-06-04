"""In-process task manager for background workflow runs.

Design choice (documented in ARCHITECTURE.md §7):
  We use asyncio.create_task() to run workflows in the background within
  the same process. This is intentionally simple — sufficient for this small
  demo. In production, this would be replaced by a durable queue (Arq/Celery
  + Redis) that survives process restarts and scales across workers.

  Caveat: if the server restarts while a run is "running", the run stays
  in "running" state forever. For the demo this is acceptable. The README
  documents this trade-off honestly.

This module also owns the pub/sub registry used by the WebSocket broadcaster.
Each run gets an asyncio.Queue that receives ExecutionEvent objects as they
are persisted by the engine. WebSocket clients subscribe by run_id and drain
the queue in real time.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.run import ExecutionEvent


# ─── Pub/Sub registry ────────────────────────────────────────────────────────
#
# run_id → list of asyncio.Queue
# Multiple WebSocket clients can subscribe to the same run.
# When the engine emits an event, it is put into every subscriber queue.

_subscribers: dict[str, list[asyncio.Queue]] = {}


def subscribe(run_id: str) -> asyncio.Queue:
    """Create and register a queue for a WebSocket subscriber.

    Call unsubscribe() when the WebSocket disconnects.
    """
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.setdefault(run_id, []).append(q)
    return q


def unsubscribe(run_id: str, queue: asyncio.Queue) -> None:
    """Remove a queue from the subscriber registry."""
    if run_id in _subscribers:
        try:
            _subscribers[run_id].remove(queue)
        except ValueError:
            pass
        if not _subscribers[run_id]:
            del _subscribers[run_id]


async def _publish(event: ExecutionEvent) -> None:
    """Called by the engine after each event is persisted.

    Puts a copy of the event into every subscriber queue for this run.
    This is fire-and-forget: if a client is slow, its queue grows but
    other subscribers are not affected.
    """
    run_id = str(event.run_id)
    queues = _subscribers.get(run_id, [])
    for q in queues:
        await q.put(event)


# ─── Task launcher ────────────────────────────────────────────────────────────


def launch_run(run_id: uuid.UUID, session_factory) -> None:
    """Launch a workflow run as a background asyncio.Task.

    Args:
        run_id:          UUID of the WorkflowRun to execute.
        session_factory: The async_sessionmaker to create a dedicated DB session.
                         The background task gets its own session (not the request session).
    """
    # Import here to avoid circular imports (runner → engine → services)
    from app.engine.runner import execute_run

    async def _task() -> None:
        # Each background task creates its own DB session.
        # The request session has already returned 202 at this point.
        async with session_factory() as session:
            try:
                await execute_run(run_id=run_id, session=session, publish=_publish)
            except Exception as exc:
                # Last-resort: if the runner itself crashes, log the error.
                # The run stays "running" in the DB — a real system would have a
                # dead-letter / heartbeat watchdog here.
                import logging
                logging.getLogger("chronoflow.task_manager").error(
                    "Unhandled error in run %s: %s", run_id, exc, exc_info=True
                )

    asyncio.create_task(_task(), name=f"run-{run_id}")

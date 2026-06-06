"""Async scheduler — the heart of ChronoFlow's execution engine.

Algorithm: ready-set (NOT level-by-level topo-sort).
See ARCHITECTURE.md §3 for the full spec.

Why ready-set instead of level-by-level?
  Level-by-level serializes parallel branches of unequal depth.
  E.g., a graph where branch A has 3 nodes and branch B has 1 node:
  level-by-level would wait for both branches to finish each level before
  proceeding to the next. Ready-set launches nodes the moment all their
  predecessors are done, giving true parallelism.

The concrete demo: two `delay` nodes in parallel (3s + 1s) finish in ~3s
total, not 4s. That's the ready-set scheduler at work.

Flow:
  1. Build in-degree map and successor map from edges.
  2. ready = { nodes with in-degree 0 } = { start }
  3. Loop:
     a. Launch all `ready` nodes as asyncio.Task (parallel).
     b. Wait for ANY task to finish: asyncio.wait(FIRST_COMPLETED).
     c. For each completed task:
        - Persist ExecutionEvent (running → completed|failed).
        - Save output in context[node_id].
        - Decrement in-degree of successors.
        - If successor reaches in-degree 0 → add to ready.
        - For branch nodes: prune the non-taken arm (mark as skipped).
  4. Stop when ready is empty AND no tasks are pending.
  5. Return the final context.

Sequence counter: global monotonic int per run.
  - "running" event: sequence N
  - "completed/failed/skipped" event: sequence N+1
  This makes the time-travel scrubber O(events) — replay events 0..k to
  reconstruct DAG state at time k.
"""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.executors import execute_node
from app.models.run import ExecutionEvent
from app.schemas.graph import Graph, GraphNode

# Type alias for the event publisher callback
EventPublisher = Callable[[ExecutionEvent], Coroutine[Any, Any, None]]


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def run_graph(
    graph: Graph,
    context: dict[str, Any],
    run_id: uuid.UUID,
    session: AsyncSession,
    publish: EventPublisher | None = None,
) -> dict[str, Any]:
    """Execute the workflow graph and return the final context.

    Args:
        graph:    Validated DAG (nodes + edges).
        context:  Initial context — must have context["trigger"] = trigger_payload.
        run_id:   UUID of the WorkflowRun (for FK in ExecutionEvent).
        session:  Async DB session (caller manages transaction).
        publish:  Optional async callback called after each event is persisted.
                  Used by the WebSocket broadcaster to push live updates.

    Returns:
        The final context dict (all node outputs merged).
    """
    node_by_id: dict[str, GraphNode] = {n.id: n for n in graph.nodes}

    # ── Build graph structure ────────────────────────────────────────────
    # in_degree[node_id] = number of predecessors not yet completed
    in_degree: dict[str, int] = {n.id: 0 for n in graph.nodes}
    # successors[node_id] = list of node_ids that depend on it
    successors: dict[str, list[str]] = defaultdict(list)
    # predecessor_edges[target] = list of edges pointing to target
    # (needed to check branch label when decrementing in-degree)
    predecessor_edges: dict[str, list] = defaultdict(list)

    for edge in graph.edges:
        in_degree[edge.target] += 1
        successors[edge.source].append(edge.target)
        predecessor_edges[edge.target].append(edge)

    # ── Ready set: nodes with no unmet predecessors ──────────────────────
    # Initially only `start` has in-degree 0.
    ready: set[str] = {nid for nid, deg in in_degree.items() if deg == 0}

    # Track which nodes have been pruned (skipped due to branch not-taken)
    skipped: set[str] = set()
    # Track nodes that have been launched or finished (to avoid double-launching)
    launched: set[str] = set()
    # Map task → node_id for completed task bookkeeping
    task_to_node: dict[asyncio.Task, str] = {}

    # Global sequence counter — monotonically increasing per event within the run
    seq = [0]

    def next_seq() -> int:
        val = seq[0]
        seq[0] += 1
        return val

    # ── Event persistence helpers ────────────────────────────────────────

    async def _persist_event(event: ExecutionEvent) -> None:
        session.add(event)
        await session.flush()  # get id without committing transaction
        if publish is not None:
            await publish(event)

    async def _emit_running(node_id: str, snapshot: dict) -> tuple[ExecutionEvent, datetime]:
        """Emit and persist a 'running' event for a node."""
        started = _utcnow()
        event = ExecutionEvent(
            id=uuid.uuid4(),
            run_id=run_id,
            node_id=node_id,
            sequence=next_seq(),
            status="running",
            input_snapshot=snapshot,
            output=None,
            error=None,
            started_at=started,
            finished_at=None,
            duration_ms=None,
        )
        await _persist_event(event)
        return event, started

    async def _emit_terminal(
        node_id: str,
        status: str,
        snapshot: dict,
        output: dict | None,
        error: str | None,
        started_at: datetime,
    ) -> ExecutionEvent:
        """Emit and persist a terminal event (completed/failed/skipped)."""
        finished = _utcnow()
        duration_ms = int((finished - started_at).total_seconds() * 1000)
        event = ExecutionEvent(
            id=uuid.uuid4(),
            run_id=run_id,
            node_id=node_id,
            sequence=next_seq(),
            status=status,
            input_snapshot=snapshot,
            output=output,
            error=error,
            started_at=started_at,
            finished_at=finished,
            duration_ms=duration_ms,
        )
        await _persist_event(event)
        return event

    # ── Prune: mark all nodes reachable from a pruned subtree as skipped ──

    async def _prune_subtree(start_node_id: str) -> None:
        """Mark start_node_id and all its (non-yet-launched) descendants as skipped.

        Called when a branch node resolves and we know one arm won't execute.
        We do BFS from the pruned root and mark every reachable node that
        hasn't been launched yet as skipped.
        """
        to_skip: list[str] = [start_node_id]
        while to_skip:
            nid = to_skip.pop()
            if nid in skipped or nid in launched:
                continue
            skipped.add(nid)
            # Emit a skipped event immediately
            snapshot = dict(context)  # snapshot at prune time
            await _emit_terminal(
                node_id=nid,
                status="skipped",
                snapshot=snapshot,
                output=None,
                error="Branch not taken",
                started_at=_utcnow(),
            )
            # Propagate skip to successors
            for child_id in successors.get(nid, []):
                if child_id not in skipped and child_id not in launched:
                    to_skip.append(child_id)

    # ── Node execution wrapper ───────────────────────────────────────────

    async def _run_node(node: GraphNode) -> tuple[str, dict[str, Any] | None, str | None]:
        """Execute a single node and return (node_id, output, error_msg).

        This is what runs as an asyncio.Task. It does NOT touch the DB —
        the scheduler handles persistence after FIRST_COMPLETED returns.
        """
        try:
            output = await execute_node(node, context)
            return node.id, output, None
        except Exception as exc:
            return node.id, None, str(exc)

    # ── Main scheduler loop ──────────────────────────────────────────────

    pending_tasks: set[asyncio.Task] = set()

    while ready or pending_tasks:
        # Launch all nodes currently in the ready set
        for nid in list(ready):
            if nid in skipped or nid in launched:
                ready.discard(nid)
                continue
            node = node_by_id[nid]
            # Snapshot the context BEFORE launching (immutable record for time-travel)
            snapshot = dict(context)
            # Emit "running" event
            _running_event, started_at = await _emit_running(nid, snapshot)
            # Launch as asyncio.Task — true parallelism for I/O-bound nodes
            task = asyncio.create_task(_run_node(node))
            task.set_name(f"node-{nid}")
            # Store metadata on the task for retrieval after completion
            task._node_id = nid  # type: ignore[attr-defined]
            task._started_at = started_at  # type: ignore[attr-defined]
            task._snapshot = snapshot  # type: ignore[attr-defined]
            task_to_node[task] = nid
            pending_tasks.add(task)
            launched.add(nid)
            ready.discard(nid)

        if not pending_tasks:
            break  # nothing running and nothing ready → done

        # Wait for the FIRST completed task — this is the ready-set heartbeat
        done, pending_tasks = await asyncio.wait(pending_tasks, return_when=asyncio.FIRST_COMPLETED)

        for task in done:
            node_id, output, error_msg = task.result()
            node = node_by_id[node_id]
            started_at = task._started_at  # type: ignore[attr-defined]
            snapshot = task._snapshot  # type: ignore[attr-defined]

            if error_msg is not None:
                # Node failed — emit failed event
                await _emit_terminal(
                    node_id=node_id,
                    status="failed",
                    snapshot=snapshot,
                    output=None,
                    error=error_msg,
                    started_at=started_at,
                )
                # Store error in context so downstream can see it (unlikely to be used)
                context[node_id] = {"error": error_msg}
                # NOTE: we continue processing (other branches may still complete).
                # The runner will mark the run as "failed" at the end.
            else:
                # Node succeeded — emit completed event
                await _emit_terminal(
                    node_id=node_id,
                    status="completed",
                    snapshot=snapshot,
                    output=output,
                    error=None,
                    started_at=started_at,
                )
                # Save output so downstream nodes can resolve JSONPath against it
                context[node_id] = output

                # ── Branch pruning ────────────────────────────────────────
                if node.type == "branch":
                    result: bool = output.get("result", False) if output else False
                    pruned_label = "false" if result else "true"

                    # Identify which successors belong to which branch label
                    for edge in graph.edges:
                        if edge.source != node_id:
                            continue
                        edge_label = edge.data.branch if edge.data else None
                        if edge_label == pruned_label:
                            # This is the not-taken branch — prune it
                            await _prune_subtree(edge.target)

            # ── Decrement in-degree of successors ─────────────────────────
            for child_id in successors.get(node_id, []):
                if child_id in skipped:
                    continue  # already pruned
                in_degree[child_id] -= 1
                if in_degree[child_id] == 0:
                    ready.add(child_id)

    return context

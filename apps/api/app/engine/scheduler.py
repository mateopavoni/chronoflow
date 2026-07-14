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
        - Resolve successors' in-degree (see below).
        - For branch nodes: resolve the non-taken arm's edge as "skipped".
  4. Stop when ready is empty AND no tasks are pending.
  5. Return the final context.

Skip resolution (fan-in-safe):
  A node's in-degree is resolved one INCOMING EDGE at a time, and each edge
  resolves either via completion (a predecessor ran) or via skip (a branch
  pruned that edge). A node only becomes "skipped" once ALL of its incoming
  edges resolved via skip — if at least one predecessor actually completes,
  the node goes to `ready` and runs normally. This makes merge/fan-in nodes
  downstream of a branch (e.g. `branch -> (a|b) -> end`) work correctly:
  pruning the not-taken arm only resolves the ONE edge into `end`, it does
  NOT mark `end` itself skipped — `end` still waits for its other (live)
  predecessor to complete.

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

    # Immutable snapshot of each node's total incoming-edge count — used to
    # tell "all predecessors skipped" apart from "some predecessor is still live".
    total_predecessors: dict[str, int] = dict(in_degree)
    # How many of a node's incoming edges resolved via skip (not completion).
    skip_credits: dict[str, int] = defaultdict(int)

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

    # ── Per-edge resolution: skip and completion both satisfy in-degree ──

    async def _finalize_if_ready(node_id: str) -> None:
        """Called once node_id's in-degree hits 0 — decide skipped vs ready.

        Only marks the node skipped when EVERY incoming edge resolved via
        skip. If at least one predecessor actually completed, the node runs.
        """
        if node_id in launched or node_id in skipped:
            return
        if in_degree[node_id] > 0:
            return
        if total_predecessors[node_id] > 0 and skip_credits[node_id] >= total_predecessors[node_id]:
            skipped.add(node_id)
            snapshot = dict(context)  # snapshot at prune time
            await _emit_terminal(
                node_id=node_id,
                status="skipped",
                snapshot=snapshot,
                output=None,
                error="Branch not taken",
                started_at=_utcnow(),
            )
            for child_id in successors.get(node_id, []):
                await _on_predecessor_skipped(child_id)
        else:
            ready.add(node_id)

    async def _on_predecessor_completed(node_id: str) -> None:
        if node_id in launched or node_id in skipped:
            return
        in_degree[node_id] -= 1
        await _finalize_if_ready(node_id)

    async def _on_predecessor_skipped(node_id: str) -> None:
        if node_id in launched or node_id in skipped:
            return
        skip_credits[node_id] += 1
        in_degree[node_id] -= 1
        await _finalize_if_ready(node_id)

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
                            # This is the not-taken branch — resolve only this edge
                            await _on_predecessor_skipped(edge.target)

            # ── Resolve successors' in-degree via this completion ─────────
            for child_id in successors.get(node_id, []):
                await _on_predecessor_completed(child_id)

    return context

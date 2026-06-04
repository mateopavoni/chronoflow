"""Engine integration tests — scheduler, parallelism, branches, time-travel.

Tests run against an in-memory SQLite DB (no Postgres needed).
Key tests:
  - Parallel delays: two branches in parallel finish in ~max time (not sum)
  - Branch pruning: not-taken arm generates skipped events
  - Sequence ordering: ExecutionEvents have monotonically increasing sequences
  - Simple pipeline: start → transform → end produces correct outputs
"""

from __future__ import annotations

import time

import pytest
from sqlalchemy import select

from app.engine.runner import execute_run
from app.models.run import ExecutionEvent, WorkflowRun
from app.models.workflow import Workflow

pytestmark = pytest.mark.asyncio


# ─── Graph fixtures ──────────────────────────────────────────────────────────


def _simple_graph() -> dict:
    """start → transform → end"""
    return {
        "nodes": [
            {"id": "start", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "Start", "config": {}}},
            {"id": "tr", "type": "transform", "position": {"x": 0, "y": 100}, "data": {"label": "T", "config": {"mappings": {"val": "$.trigger.val"}}}},
            {"id": "end", "type": "end", "position": {"x": 0, "y": 200}, "data": {"label": "End", "config": {}}},
        ],
        "edges": [
            {"id": "e1", "source": "start", "target": "tr"},
            {"id": "e2", "source": "tr", "target": "end"},
        ],
    }


def _parallel_delays_graph(delay1: float = 0.1, delay2: float = 0.05) -> dict:
    """start → (delay-a || delay-b) → end"""
    return {
        "nodes": [
            {"id": "start", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "S", "config": {}}},
            {"id": "delay-a", "type": "delay", "position": {"x": -100, "y": 100}, "data": {"label": "Delay A", "config": {"seconds": delay1}}},
            {"id": "delay-b", "type": "delay", "position": {"x": 100, "y": 100}, "data": {"label": "Delay B", "config": {"seconds": delay2}}},
            {"id": "end", "type": "end", "position": {"x": 0, "y": 200}, "data": {"label": "End", "config": {}}},
        ],
        "edges": [
            {"id": "e1", "source": "start", "target": "delay-a"},
            {"id": "e2", "source": "start", "target": "delay-b"},
            {"id": "e3", "source": "delay-a", "target": "end"},
            {"id": "e4", "source": "delay-b", "target": "end"},
        ],
    }


def _branch_graph() -> dict:
    """start → branch → (true: transform-t | false: transform-f) → end"""
    return {
        "nodes": [
            {"id": "start", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "S", "config": {}}},
            {"id": "br", "type": "branch", "position": {"x": 0, "y": 100}, "data": {"label": "Br", "config": {"condition": "$.trigger.amount > 50"}}},
            {"id": "tr-true", "type": "transform", "position": {"x": -100, "y": 200}, "data": {"label": "High", "config": {"mappings": {"path": "$.trigger.amount"}}}},
            {"id": "tr-false", "type": "transform", "position": {"x": 100, "y": 200}, "data": {"label": "Low", "config": {"mappings": {"path": "$.trigger.amount"}}}},
            {"id": "end", "type": "end", "position": {"x": 0, "y": 300}, "data": {"label": "End", "config": {}}},
        ],
        "edges": [
            {"id": "e1", "source": "start", "target": "br"},
            {"id": "e2", "source": "br", "target": "tr-true", "data": {"branch": "true"}},
            {"id": "e3", "source": "br", "target": "tr-false", "data": {"branch": "false"}},
            {"id": "e4", "source": "tr-true", "target": "end"},
            {"id": "e5", "source": "tr-false", "target": "end"},
        ],
    }


# ─── Test: simple pipeline ───────────────────────────────────────────────────


async def test_simple_pipeline_produces_correct_output(db_session, session_factory):
    """start → transform → end: transform maps trigger.val correctly."""
    wf = Workflow(name="test", graph=_simple_graph())
    db_session.add(wf)
    await db_session.flush()

    run = WorkflowRun(
        workflow_id=wf.id,
        status="pending",
        trigger_payload={"val": 99},
    )
    db_session.add(run)
    await db_session.commit()

    async with session_factory() as session:
        await execute_run(run_id=run.id, session=session)

    # Reload run
    async with session_factory() as s:
        refreshed = await s.get(WorkflowRun, run.id)
        assert refreshed.status == "completed"
        assert refreshed.final_payload is not None
        # The transform node should have mapped "val" from trigger
        assert "tr" in refreshed.final_payload
        assert refreshed.final_payload["tr"]["val"] == 99


# ─── Test: parallelism ───────────────────────────────────────────────────────


async def test_parallel_delays_finish_in_max_not_sum(db_session, session_factory):
    """Two parallel delays (0.15s + 0.05s) should finish in ~0.15s, not 0.20s.

    We use a 40% margin: total time must be < 0.15 + (0.15 * 0.40) = 0.21s.
    This is the concrete proof that the ready-set scheduler is truly async.
    """
    delay_long = 0.15
    delay_short = 0.05

    wf = Workflow(name="parallel-test", graph=_parallel_delays_graph(delay_long, delay_short))
    db_session.add(wf)
    await db_session.flush()

    run = WorkflowRun(
        workflow_id=wf.id,
        status="pending",
        trigger_payload={},
    )
    db_session.add(run)
    await db_session.commit()

    start_time = time.monotonic()

    async with session_factory() as session:
        await execute_run(run_id=run.id, session=session)

    elapsed = time.monotonic() - start_time

    # Must finish faster than the sum (sequential would be 0.20s)
    margin = 0.08  # allow 80ms overhead for DB/async overhead in test
    assert elapsed < (delay_long + delay_short), (
        f"Elapsed {elapsed:.3f}s >= sum {delay_long + delay_short:.3f}s — "
        "parallelism is not working!"
    )
    # Also assert we're roughly in the right range (not impossibly fast)
    assert elapsed >= delay_long - margin, (
        f"Elapsed {elapsed:.3f}s is suspiciously fast — delay not working?"
    )

    async with session_factory() as s:
        r = await s.get(WorkflowRun, run.id)
        assert r.status == "completed"


# ─── Test: branch pruning ────────────────────────────────────────────────────


async def test_branch_true_arm_taken_false_arm_skipped(db_session, session_factory):
    """When branch condition is True, tr-true runs and tr-false is skipped."""
    wf = Workflow(name="branch-test", graph=_branch_graph())
    db_session.add(wf)
    await db_session.flush()

    run = WorkflowRun(
        workflow_id=wf.id,
        status="pending",
        trigger_payload={"amount": 100},  # 100 > 50 → true
    )
    db_session.add(run)
    await db_session.commit()

    async with session_factory() as session:
        await execute_run(run_id=run.id, session=session)

    async with session_factory() as s:
        r = await s.get(WorkflowRun, run.id)
        assert r.status == "completed"

        # Load events
        stmt = select(ExecutionEvent).where(ExecutionEvent.run_id == run.id).order_by(ExecutionEvent.sequence)
        result = await s.execute(stmt)
        events = result.scalars().all()

    events_by_node = {}
    for e in events:
        events_by_node.setdefault(e.node_id, []).append(e)

    # tr-true should be completed
    assert "tr-true" in events_by_node
    tr_true_statuses = {e.status for e in events_by_node["tr-true"]}
    assert "completed" in tr_true_statuses

    # tr-false should be skipped
    assert "tr-false" in events_by_node
    tr_false_statuses = {e.status for e in events_by_node["tr-false"]}
    assert "skipped" in tr_false_statuses
    assert "completed" not in tr_false_statuses


async def test_branch_false_arm_taken(db_session, session_factory):
    """When branch condition is False, tr-false runs and tr-true is skipped."""
    wf = Workflow(name="branch-test-false", graph=_branch_graph())
    db_session.add(wf)
    await db_session.flush()

    run = WorkflowRun(
        workflow_id=wf.id,
        status="pending",
        trigger_payload={"amount": 10},  # 10 > 50 → false
    )
    db_session.add(run)
    await db_session.commit()

    async with session_factory() as session:
        await execute_run(run_id=run.id, session=session)

    async with session_factory() as s:
        stmt = select(ExecutionEvent).where(ExecutionEvent.run_id == run.id).order_by(ExecutionEvent.sequence)
        result = await s.execute(stmt)
        events = result.scalars().all()

    events_by_node = {e.node_id: e for e in events if e.status in ("completed", "skipped")}
    assert events_by_node.get("tr-true") is not None
    assert events_by_node["tr-true"].status == "skipped"
    assert events_by_node.get("tr-false") is not None
    assert events_by_node["tr-false"].status == "completed"


# ─── Test: time-travel sequence ordering ─────────────────────────────────────


async def test_execution_events_have_monotonic_sequence(db_session, session_factory):
    """All ExecutionEvents for a run must have strictly increasing sequence numbers.

    This guarantees the time-travel scrubber can replay state correctly
    by iterating events in sequence order.
    """
    wf = Workflow(name="seq-test", graph=_parallel_delays_graph(0.05, 0.02))
    db_session.add(wf)
    await db_session.flush()

    run = WorkflowRun(
        workflow_id=wf.id,
        status="pending",
        trigger_payload={},
    )
    db_session.add(run)
    await db_session.commit()

    async with session_factory() as session:
        await execute_run(run_id=run.id, session=session)

    async with session_factory() as s:
        stmt = select(ExecutionEvent).where(ExecutionEvent.run_id == run.id).order_by(ExecutionEvent.sequence)
        result = await s.execute(stmt)
        events = result.scalars().all()

    assert len(events) > 0, "No events were recorded"

    sequences = [e.sequence for e in events]
    # Sequences must be strictly increasing
    for i in range(1, len(sequences)):
        assert sequences[i] > sequences[i - 1], (
            f"Sequence not monotonic at index {i}: {sequences[i - 1]} → {sequences[i]}"
        )


async def test_events_have_running_and_completed_statuses(db_session, session_factory):
    """Each non-branch node should have at least a 'running' and 'completed' event."""
    wf = Workflow(name="status-test", graph=_simple_graph())
    db_session.add(wf)
    await db_session.flush()

    run = WorkflowRun(
        workflow_id=wf.id,
        status="pending",
        trigger_payload={"val": 42},
    )
    db_session.add(run)
    await db_session.commit()

    async with session_factory() as session:
        await execute_run(run_id=run.id, session=session)

    async with session_factory() as s:
        stmt = select(ExecutionEvent).where(ExecutionEvent.run_id == run.id)
        result = await s.execute(stmt)
        events = result.scalars().all()

    for node_id in ["start", "tr", "end"]:
        node_events = [e for e in events if e.node_id == node_id]
        statuses = {e.status for e in node_events}
        assert "running" in statuses, f"Node '{node_id}' missing 'running' event"
        assert "completed" in statuses, f"Node '{node_id}' missing 'completed' event"


async def test_completed_events_have_duration_ms(db_session, session_factory):
    """Completed events should have a non-null duration_ms."""
    wf = Workflow(name="duration-test", graph=_simple_graph())
    db_session.add(wf)
    await db_session.flush()

    run = WorkflowRun(
        workflow_id=wf.id,
        status="pending",
        trigger_payload={"val": 1},
    )
    db_session.add(run)
    await db_session.commit()

    async with session_factory() as session:
        await execute_run(run_id=run.id, session=session)

    async with session_factory() as s:
        stmt = select(ExecutionEvent).where(
            ExecutionEvent.run_id == run.id,
            ExecutionEvent.status == "completed",
        )
        result = await s.execute(stmt)
        events = result.scalars().all()

    assert len(events) > 0
    for e in events:
        assert e.duration_ms is not None
        assert e.duration_ms >= 0

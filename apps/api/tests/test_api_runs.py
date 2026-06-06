"""API endpoint tests for /api/runs.

Covers:
  - GET /runs (list, filter by workflow_id)
  - GET /runs/{id} (single run, 404)
  - GET /runs/{id}/events (event list, ordered by sequence)
  - POST /runs/{id}/replay (202, creates new run)
"""

from __future__ import annotations

import asyncio

import pytest

pytestmark = pytest.mark.asyncio

VALID_GRAPH = {
    "nodes": [
        {"id": "start", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "Start", "config": {}}},
        {"id": "end", "type": "end", "position": {"x": 0, "y": 100}, "data": {"label": "End", "config": {}}},
    ],
    "edges": [
        {"id": "e1", "source": "start", "target": "end"},
    ],
}


async def _create_workflow_and_run(client) -> tuple[str, str]:
    """Helper: create a workflow and trigger a run. Returns (wf_id, run_id)."""
    wf_resp = await client.post("/api/workflows/", json={
        "name": "RunsTest",
        "graph": VALID_GRAPH,
    })
    assert wf_resp.status_code == 201
    wf_id = wf_resp.json()["id"]

    run_resp = await client.post(f"/api/workflows/{wf_id}/run", json={
        "trigger_payload": {"test": True},
    })
    assert run_resp.status_code == 202
    run_id = run_resp.json()["id"]
    return wf_id, run_id


# ─── List runs ────────────────────────────────────────────────────────────────


async def test_list_runs_empty(client):
    resp = await client.get("/api/runs/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_list_runs_after_trigger(client):
    _, run_id = await _create_workflow_and_run(client)
    resp = await client.get("/api/runs/")
    assert resp.status_code == 200
    run_ids = [r["id"] for r in resp.json()]
    assert run_id in run_ids


async def test_list_runs_filter_by_workflow_id(client):
    wf_id, run_id = await _create_workflow_and_run(client)

    # Create another workflow and run
    wf2_resp = await client.post("/api/workflows/", json={
        "name": "Other",
        "graph": VALID_GRAPH,
    })
    wf2_id = wf2_resp.json()["id"]
    await client.post(f"/api/workflows/{wf2_id}/run", json={"trigger_payload": {}})

    # Filter by wf_id
    resp = await client.get(f"/api/runs/?workflow_id={wf_id}")
    assert resp.status_code == 200
    runs = resp.json()
    assert all(r["workflow_id"] == wf_id for r in runs)
    assert any(r["id"] == run_id for r in runs)


# ─── Get single run ───────────────────────────────────────────────────────────


async def test_get_run_by_id(client):
    _, run_id = await _create_workflow_and_run(client)
    resp = await client.get(f"/api/runs/{run_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == run_id
    assert data["status"] in ("pending", "running", "completed", "failed")


async def test_get_run_not_found(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/runs/{fake_id}")
    assert resp.status_code == 404


# ─── Events ───────────────────────────────────────────────────────────────────


async def test_get_run_events(client):
    """Events endpoint returns list, ordered by sequence."""
    _, run_id = await _create_workflow_and_run(client)
    # Wait briefly for the background task to write some events
    await asyncio.sleep(0.3)

    resp = await client.get(f"/api/runs/{run_id}/events")
    assert resp.status_code == 200
    events = resp.json()
    assert isinstance(events, list)

    # Check ordering by sequence
    sequences = [e["sequence"] for e in events]
    assert sequences == sorted(sequences), "Events are not ordered by sequence"


async def test_get_run_events_not_found(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/runs/{fake_id}/events")
    assert resp.status_code == 404


async def test_run_events_have_correct_fields(client):
    _, run_id = await _create_workflow_and_run(client)
    await asyncio.sleep(0.3)

    resp = await client.get(f"/api/runs/{run_id}/events")
    assert resp.status_code == 200
    events = resp.json()

    if events:
        e = events[0]
        assert "id" in e
        assert "run_id" in e
        assert "node_id" in e
        assert "sequence" in e
        assert "status" in e
        assert "input_snapshot" in e
        assert "started_at" in e


# ─── Replay ───────────────────────────────────────────────────────────────────


async def test_replay_creates_new_run(client):
    wf_id, run_id = await _create_workflow_and_run(client)

    replay_resp = await client.post(f"/api/runs/{run_id}/replay")
    assert replay_resp.status_code == 202
    new_run = replay_resp.json()

    # New run must be a different ID
    assert new_run["id"] != run_id
    # But same workflow
    assert new_run["workflow_id"] == wf_id
    # And same trigger_payload
    original_resp = await client.get(f"/api/runs/{run_id}")
    original = original_resp.json()
    assert new_run["trigger_payload"] == original["trigger_payload"]


async def test_replay_not_found(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(f"/api/runs/{fake_id}/replay")
    assert resp.status_code == 404

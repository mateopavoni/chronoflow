"""API endpoint tests for /api/workflows.

Covers:
  - CRUD (create, read, update, delete)
  - POST /validate (valid graph, invalid graph)
  - POST /run (202 response, 422 for invalid graph)
  - 404 for unknown IDs
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio

# ─── Fixture: minimal valid graph ─────────────────────────────────────────────

VALID_GRAPH = {
    "nodes": [
        {"id": "start", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "Start", "config": {}}},
        {"id": "end", "type": "end", "position": {"x": 0, "y": 100}, "data": {"label": "End", "config": {}}},
    ],
    "edges": [
        {"id": "e1", "source": "start", "target": "end"},
    ],
}

INVALID_GRAPH = {
    "nodes": [
        # No start node
        {"id": "end", "type": "end", "position": {"x": 0, "y": 0}, "data": {"label": "End", "config": {}}},
    ],
    "edges": [],
}


# ─── Create + Read ────────────────────────────────────────────────────────────


async def test_create_workflow(client):
    resp = await client.post("/api/workflows/", json={
        "name": "Test Workflow",
        "description": "A test",
        "graph": VALID_GRAPH,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Workflow"
    assert "id" in data
    assert "created_at" in data


async def test_list_workflows(client):
    # Create one first
    await client.post("/api/workflows/", json={
        "name": "WF1",
        "graph": VALID_GRAPH,
    })
    resp = await client.get("/api/workflows/")
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert len(items) >= 1


async def test_get_workflow_by_id(client):
    create_resp = await client.post("/api/workflows/", json={
        "name": "GetMe",
        "graph": VALID_GRAPH,
    })
    wf_id = create_resp.json()["id"]

    resp = await client.get(f"/api/workflows/{wf_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == wf_id


async def test_get_workflow_not_found(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/workflows/{fake_id}")
    assert resp.status_code == 404


# ─── Update ───────────────────────────────────────────────────────────────────


async def test_update_workflow(client):
    create_resp = await client.post("/api/workflows/", json={
        "name": "Original",
        "graph": VALID_GRAPH,
    })
    wf_id = create_resp.json()["id"]

    resp = await client.put(f"/api/workflows/{wf_id}", json={
        "name": "Updated",
        "description": "Changed",
        "graph": VALID_GRAPH,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated"
    assert data["description"] == "Changed"


async def test_update_workflow_not_found(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.put(f"/api/workflows/{fake_id}", json={
        "name": "X",
        "graph": VALID_GRAPH,
    })
    assert resp.status_code == 404


# ─── Delete ───────────────────────────────────────────────────────────────────


async def test_delete_workflow(client):
    create_resp = await client.post("/api/workflows/", json={
        "name": "ToDelete",
        "graph": VALID_GRAPH,
    })
    wf_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/workflows/{wf_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/workflows/{wf_id}")
    assert get_resp.status_code == 404


async def test_delete_workflow_not_found(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(f"/api/workflows/{fake_id}")
    assert resp.status_code == 404


# ─── Validate ─────────────────────────────────────────────────────────────────


async def test_validate_valid_graph(client):
    create_resp = await client.post("/api/workflows/", json={
        "name": "ValidWF",
        "graph": VALID_GRAPH,
    })
    wf_id = create_resp.json()["id"]

    resp = await client.post(f"/api/workflows/{wf_id}/validate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["errors"] == []


async def test_validate_invalid_graph(client):
    create_resp = await client.post("/api/workflows/", json={
        "name": "InvalidWF",
        "graph": INVALID_GRAPH,
    })
    wf_id = create_resp.json()["id"]

    resp = await client.post(f"/api/workflows/{wf_id}/validate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert len(data["errors"]) > 0


async def test_validate_not_found(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(f"/api/workflows/{fake_id}/validate")
    assert resp.status_code == 404


# ─── Run ──────────────────────────────────────────────────────────────────────


async def test_trigger_run_returns_202(client):
    create_resp = await client.post("/api/workflows/", json={
        "name": "RunMe",
        "graph": VALID_GRAPH,
    })
    wf_id = create_resp.json()["id"]

    resp = await client.post(f"/api/workflows/{wf_id}/run", json={
        "trigger_payload": {"hello": "world"},
    })
    assert resp.status_code == 202
    data = resp.json()
    assert "id" in data
    assert data["workflow_id"] == wf_id
    assert data["status"] in ("pending", "running", "completed")


async def test_trigger_run_invalid_graph_returns_422(client):
    create_resp = await client.post("/api/workflows/", json={
        "name": "BadGraph",
        "graph": INVALID_GRAPH,
    })
    wf_id = create_resp.json()["id"]

    resp = await client.post(f"/api/workflows/{wf_id}/run", json={
        "trigger_payload": {},
    })
    assert resp.status_code == 422


async def test_trigger_run_not_found(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(f"/api/workflows/{fake_id}/run", json={
        "trigger_payload": {},
    })
    assert resp.status_code == 404

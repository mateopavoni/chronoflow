"""API endpoint tests for /api/workflows.

Covers:
  - CRUD (create, read, update, delete)
  - POST /validate (valid graph, invalid graph)
  - POST /run (202 response, 422 for invalid graph)
  - 404 for unknown IDs
  - Authorization: 401 without a session, 404 (not 403) across users (IDOR)
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


async def test_create_workflow(auth_client):
    resp = await auth_client.post("/api/workflows/", json={
        "name": "Test Workflow",
        "description": "A test",
        "graph": VALID_GRAPH,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Workflow"
    assert "id" in data
    assert "created_at" in data


async def test_list_workflows(auth_client):
    # Create one first
    await auth_client.post("/api/workflows/", json={
        "name": "WF1",
        "graph": VALID_GRAPH,
    })
    resp = await auth_client.get("/api/workflows/")
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert len(items) >= 1


async def test_get_workflow_by_id(auth_client):
    create_resp = await auth_client.post("/api/workflows/", json={
        "name": "GetMe",
        "graph": VALID_GRAPH,
    })
    wf_id = create_resp.json()["id"]

    resp = await auth_client.get(f"/api/workflows/{wf_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == wf_id


async def test_get_workflow_not_found(auth_client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await auth_client.get(f"/api/workflows/{fake_id}")
    assert resp.status_code == 404


# ─── Update ───────────────────────────────────────────────────────────────────


async def test_update_workflow(auth_client):
    create_resp = await auth_client.post("/api/workflows/", json={
        "name": "Original",
        "graph": VALID_GRAPH,
    })
    wf_id = create_resp.json()["id"]

    resp = await auth_client.put(f"/api/workflows/{wf_id}", json={
        "name": "Updated",
        "description": "Changed",
        "graph": VALID_GRAPH,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated"
    assert data["description"] == "Changed"


async def test_update_workflow_not_found(auth_client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await auth_client.put(f"/api/workflows/{fake_id}", json={
        "name": "X",
        "graph": VALID_GRAPH,
    })
    assert resp.status_code == 404


# ─── Delete ───────────────────────────────────────────────────────────────────


async def test_delete_workflow(auth_client):
    create_resp = await auth_client.post("/api/workflows/", json={
        "name": "ToDelete",
        "graph": VALID_GRAPH,
    })
    wf_id = create_resp.json()["id"]

    del_resp = await auth_client.delete(f"/api/workflows/{wf_id}")
    assert del_resp.status_code == 204

    get_resp = await auth_client.get(f"/api/workflows/{wf_id}")
    assert get_resp.status_code == 404


async def test_delete_workflow_not_found(auth_client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await auth_client.delete(f"/api/workflows/{fake_id}")
    assert resp.status_code == 404


# ─── Validate ─────────────────────────────────────────────────────────────────


async def test_validate_valid_graph(auth_client):
    create_resp = await auth_client.post("/api/workflows/", json={
        "name": "ValidWF",
        "graph": VALID_GRAPH,
    })
    wf_id = create_resp.json()["id"]

    resp = await auth_client.post(f"/api/workflows/{wf_id}/validate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["errors"] == []


async def test_validate_invalid_graph(auth_client):
    create_resp = await auth_client.post("/api/workflows/", json={
        "name": "InvalidWF",
        "graph": INVALID_GRAPH,
    })
    wf_id = create_resp.json()["id"]

    resp = await auth_client.post(f"/api/workflows/{wf_id}/validate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert len(data["errors"]) > 0


async def test_validate_not_found(auth_client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await auth_client.post(f"/api/workflows/{fake_id}/validate")
    assert resp.status_code == 404


# ─── Run ──────────────────────────────────────────────────────────────────────


async def test_trigger_run_returns_202(auth_client):
    create_resp = await auth_client.post("/api/workflows/", json={
        "name": "RunMe",
        "graph": VALID_GRAPH,
    })
    wf_id = create_resp.json()["id"]

    resp = await auth_client.post(f"/api/workflows/{wf_id}/run", json={
        "trigger_payload": {"hello": "world"},
    })
    assert resp.status_code == 202
    data = resp.json()
    assert "id" in data
    assert data["workflow_id"] == wf_id
    assert data["status"] in ("pending", "running", "completed")


async def test_trigger_run_invalid_graph_returns_422(auth_client):
    create_resp = await auth_client.post("/api/workflows/", json={
        "name": "BadGraph",
        "graph": INVALID_GRAPH,
    })
    wf_id = create_resp.json()["id"]

    resp = await auth_client.post(f"/api/workflows/{wf_id}/run", json={
        "trigger_payload": {},
    })
    assert resp.status_code == 422


async def test_trigger_run_not_found(auth_client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await auth_client.post(f"/api/workflows/{fake_id}/run", json={
        "trigger_payload": {},
    })
    assert resp.status_code == 404


# ─── Authorization: unauthenticated access ────────────────────────────────────


async def test_list_workflows_requires_auth(client):
    """No session cookie at all → 401, not an empty/global list."""
    resp = await client.get("/api/workflows/")
    assert resp.status_code == 401


async def test_create_workflow_requires_auth(client):
    resp = await client.post("/api/workflows/", json={"name": "X", "graph": VALID_GRAPH})
    assert resp.status_code == 401


async def test_get_workflow_requires_auth(client):
    resp = await client.get("/api/workflows/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 401


# ─── Authorization: cross-user isolation (IDOR) ───────────────────────────────


async def test_workflow_invisible_to_other_user(client):
    """User A's workflow must 404 (not 403 — avoid confirming it exists) for user B."""
    # User A creates a workflow.
    await client.post("/api/auth/register", json={"email": "alice@example.com", "password": "supersecret1"})
    create_resp = await client.post("/api/workflows/", json={"name": "Alice's WF", "graph": VALID_GRAPH})
    assert create_resp.status_code == 201
    wf_id = create_resp.json()["id"]

    # User B logs in (fresh cookie jar behavior: just register, which also sets the cookie).
    client.cookies.clear()
    await client.post("/api/auth/register", json={"email": "bob@example.com", "password": "supersecret1"})

    get_resp = await client.get(f"/api/workflows/{wf_id}")
    assert get_resp.status_code == 404

    list_resp = await client.get("/api/workflows/")
    assert wf_id not in [w["id"] for w in list_resp.json()]

    update_resp = await client.put(f"/api/workflows/{wf_id}", json={"name": "Hijacked", "graph": VALID_GRAPH})
    assert update_resp.status_code == 404

    delete_resp = await client.delete(f"/api/workflows/{wf_id}")
    assert delete_resp.status_code == 404

    run_resp = await client.post(f"/api/workflows/{wf_id}/run", json={"trigger_payload": {}})
    assert run_resp.status_code == 404


async def test_register_seeds_three_example_workflows(client):
    resp = await client.post(
        "/api/auth/register", json={"email": "carol@example.com", "password": "supersecret1"}
    )
    assert resp.status_code == 201
    listing = await client.get("/api/workflows/")
    assert len(listing.json()) == 3


# ─── Size limits (DoS guard, see app/schemas/graph.py + workflow.py) ─────────


def _oversized_node_graph(count: int) -> dict:
    """A graph with `count` isolated (unconnected) nodes past the real `start`.

    We only need enough nodes to trip the Field(max_length=...) check — the
    graph doesn't need to be a valid DAG for the Pydantic-level 422 to fire,
    since request-body validation runs before graph validation.
    """
    nodes = [
        {"id": "start", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "Start", "config": {}}},
    ]
    for i in range(count):
        nodes.append(
            {
                "id": f"extra-{i}",
                "type": "end",
                "position": {"x": 0, "y": 0},
                "data": {"label": "End", "config": {}},
            }
        )
    return {"nodes": nodes, "edges": []}


async def test_create_workflow_rejects_too_many_nodes(auth_client):
    resp = await auth_client.post(
        "/api/workflows/",
        json={"name": "Too Big", "graph": _oversized_node_graph(201)},
    )
    assert resp.status_code == 422


async def test_create_workflow_accepts_max_nodes(auth_client):
    # Exactly at the limit (1 start + 199 extras = 200) must still be accepted.
    resp = await auth_client.post(
        "/api/workflows/",
        json={"name": "Right At The Limit", "graph": _oversized_node_graph(199)},
    )
    assert resp.status_code == 201


async def test_create_workflow_rejects_oversized_node_config(auth_client):
    huge_graph = {
        "nodes": [
            {
                "id": "start",
                "type": "start",
                "position": {"x": 0, "y": 0},
                "data": {"label": "Start", "config": {"blob": "x" * 30_000}},
            },
            {"id": "end", "type": "end", "position": {"x": 0, "y": 100}, "data": {"label": "End", "config": {}}},
        ],
        "edges": [{"id": "e1", "source": "start", "target": "end"}],
    }
    resp = await auth_client.post(
        "/api/workflows/", json={"name": "Huge Config", "graph": huge_graph}
    )
    assert resp.status_code == 422


async def test_create_workflow_rejects_oversized_name(auth_client):
    resp = await auth_client.post(
        "/api/workflows/",
        json={"name": "x" * 500, "graph": VALID_GRAPH},
    )
    assert resp.status_code == 422

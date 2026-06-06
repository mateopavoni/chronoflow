"""Seed script — creates example workflows on startup.

Idempotent: checks if any workflows exist before inserting.
Three examples:
  1. "Parallel Delays Demo" — two delay branches in parallel (proves the ready-set
     scheduler: total time ≈ max(3s, 1s) = 3s, not 3+1=4s).
  2. "Branch + Transform + HTTP" — branch on trigger value, transform, real HTTP call.
  3. "Simple Pipeline" — start → transform → end (minimal working example).
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow

# ── Workflow graph definitions ────────────────────────────────────────────────

PARALLEL_DELAYS_GRAPH = {
    "nodes": [
        {
            "id": "start",
            "type": "start",
            "position": {"x": 300, "y": 50},
            "data": {"label": "Start", "config": {}},
        },
        {
            "id": "delay-3s",
            "type": "delay",
            "position": {"x": 100, "y": 200},
            "data": {"label": "Wait 3s", "config": {"seconds": 3}},
        },
        {
            "id": "delay-1s",
            "type": "delay",
            "position": {"x": 500, "y": 200},
            "data": {"label": "Wait 1s", "config": {"seconds": 1}},
        },
        {
            "id": "end",
            "type": "end",
            "position": {"x": 300, "y": 350},
            "data": {"label": "End", "config": {}},
        },
    ],
    "edges": [
        {"id": "e1", "source": "start", "target": "delay-3s"},
        {"id": "e2", "source": "start", "target": "delay-1s"},
        {"id": "e3", "source": "delay-3s", "target": "end"},
        {"id": "e4", "source": "delay-1s", "target": "end"},
    ],
}

BRANCH_TRANSFORM_HTTP_GRAPH = {
    "nodes": [
        {
            "id": "start",
            "type": "start",
            "position": {"x": 300, "y": 50},
            "data": {"label": "Start", "config": {}},
        },
        {
            "id": "check-amount",
            "type": "branch",
            "position": {"x": 300, "y": 180},
            "data": {
                "label": "Amount > 100?",
                "config": {"condition": "$.trigger.amount > 100"},
            },
        },
        {
            "id": "fetch-post",
            "type": "http",
            "position": {"x": 100, "y": 330},
            "data": {
                "label": "Fetch Post",
                "config": {
                    "method": "GET",
                    "url": "https://jsonplaceholder.typicode.com/posts/1",
                    "headers": {},
                    "body": {},
                },
            },
        },
        {
            "id": "normalize",
            "type": "transform",
            "position": {"x": 100, "y": 480},
            "data": {
                "label": "Normalize",
                "config": {
                    "mappings": {
                        "title": "$.fetch-post.body.title",
                        "amount": "$.trigger.amount",
                    }
                },
            },
        },
        {
            "id": "skip-transform",
            "type": "transform",
            "position": {"x": 500, "y": 330},
            "data": {
                "label": "Low Amount",
                "config": {
                    "mappings": {
                        "amount": "$.trigger.amount",
                        "note": "$.trigger.note",
                    }
                },
            },
        },
        {
            "id": "end",
            "type": "end",
            "position": {"x": 300, "y": 630},
            "data": {"label": "End", "config": {}},
        },
    ],
    "edges": [
        {"id": "e1", "source": "start", "target": "check-amount"},
        {
            "id": "e2",
            "source": "check-amount",
            "target": "fetch-post",
            "data": {"branch": "true"},
        },
        {
            "id": "e3",
            "source": "check-amount",
            "target": "skip-transform",
            "data": {"branch": "false"},
        },
        {"id": "e4", "source": "fetch-post", "target": "normalize"},
        {"id": "e5", "source": "normalize", "target": "end"},
        {"id": "e6", "source": "skip-transform", "target": "end"},
    ],
}

SIMPLE_PIPELINE_GRAPH = {
    "nodes": [
        {
            "id": "start",
            "type": "start",
            "position": {"x": 300, "y": 50},
            "data": {"label": "Start", "config": {}},
        },
        {
            "id": "enrich",
            "type": "transform",
            "position": {"x": 300, "y": 200},
            "data": {
                "label": "Enrich",
                "config": {
                    "mappings": {
                        "user_id": "$.trigger.user_id",
                        "action": "$.trigger.action",
                    }
                },
            },
        },
        {
            "id": "end",
            "type": "end",
            "position": {"x": 300, "y": 350},
            "data": {"label": "End", "config": {}},
        },
    ],
    "edges": [
        {"id": "e1", "source": "start", "target": "enrich"},
        {"id": "e2", "source": "enrich", "target": "end"},
    ],
}

SEED_WORKFLOWS = [
    {
        "name": "Parallel Delays Demo",
        "description": (
            "Two delay branches run in parallel (3s + 1s). "
            "Total time ≈ 3s (max), not 4s (sum). "
            "Proves the ready-set scheduler delivers true async parallelism."
        ),
        "graph": PARALLEL_DELAYS_GRAPH,
    },
    {
        "name": "Branch + Transform + HTTP",
        "description": (
            "Routes on trigger.amount > 100: if true, fetches a real HTTP post "
            "and normalizes it; if false, passes through with a note. "
            "Demonstrates branch pruning, JSONPath mapping, and live HTTP."
        ),
        "graph": BRANCH_TRANSFORM_HTTP_GRAPH,
    },
    {
        "name": "Simple Pipeline",
        "description": (
            "start → transform → end. "
            "Minimal working example for exploring the editor."
        ),
        "graph": SIMPLE_PIPELINE_GRAPH,
    },
]


async def seed_workflows(session: AsyncSession) -> None:
    """Insert example workflows if the table is empty (idempotent)."""
    count_result = await session.execute(select(func.count()).select_from(Workflow))
    count = count_result.scalar_one()
    if count > 0:
        return  # already seeded

    for data in SEED_WORKFLOWS:
        wf = Workflow(
            name=data["name"],
            description=data["description"],
            graph=data["graph"],
        )
        session.add(wf)

    await session.commit()

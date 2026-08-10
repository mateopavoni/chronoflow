"""Pydantic v2 schemas for the DAG graph definition.

These match exactly the TypeScript types in apps/web/src/types/api.ts.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

NodeType = Literal["start", "transform", "http", "delay", "branch", "end"]

# ─── Size limits (DoS guard) ─────────────────────────────────────────────────
# A workflow graph is user-authored input that gets stored, echoed back on
# every load, and walked by the scheduler/validator on every run. Without a
# bound, nothing stops an oversized graph (or an oversized node config blob)
# from being POSTed — large enough JSON parsing/validation/DB-write/DAG-walk
# work per request to degrade the single-process API. Limits below are
# generous for any real workflow (the node palette is intentionally 6 types,
# see CLAUDE.md) while still rejecting pathological input with a clean 422.
MAX_NODES = 200
MAX_EDGES = 400
MAX_NODE_CONFIG_BYTES = 20_000  # 20 KB of JSON per node's `config`


class NodePosition(BaseModel):
    x: float
    y: float


class NodeData(BaseModel):
    label: str
    config: dict[str, Any] = {}

    @field_validator("config")
    @classmethod
    def _config_not_too_large(cls, v: dict[str, Any]) -> dict[str, Any]:
        size = len(json.dumps(v, default=str))
        if size > MAX_NODE_CONFIG_BYTES:
            raise ValueError(
                f"Node config is too large ({size} bytes, max {MAX_NODE_CONFIG_BYTES})."
            )
        return v


class GraphNode(BaseModel):
    id: str
    type: NodeType
    position: NodePosition
    data: NodeData


class EdgeData(BaseModel):
    branch: Literal["true", "false"] | None = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    data: EdgeData | None = None


class Graph(BaseModel):
    nodes: list[GraphNode] = Field(max_length=MAX_NODES)
    edges: list[GraphEdge] = Field(max_length=MAX_EDGES)
    direction: Literal["vertical", "horizontal"] = "horizontal"

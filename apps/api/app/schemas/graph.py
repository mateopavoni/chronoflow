"""Pydantic v2 schemas for the DAG graph definition.

These match exactly the TypeScript types in apps/web/src/types/api.ts.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

NodeType = Literal["start", "transform", "http", "delay", "branch", "end"]


class NodePosition(BaseModel):
    x: float
    y: float


class NodeData(BaseModel):
    label: str
    config: dict[str, Any] = {}


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
    nodes: list[GraphNode]
    edges: list[GraphEdge]

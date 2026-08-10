"""Pydantic v2 schemas for Workflow CRUD and validation."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.graph import Graph

# Same DoS-guard rationale as app/schemas/graph.py (MAX_NODES/MAX_EDGES):
# unbounded free-text fields on user-authored input are cheap to abuse.
MAX_NAME_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 2000


class WorkflowIn(BaseModel):
    """Request body for creating or updating a Workflow."""

    name: str = Field(max_length=MAX_NAME_LENGTH)
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    graph: Graph


class WorkflowOut(BaseModel):
    """Response schema for a Workflow."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    graph: Graph
    created_at: datetime
    updated_at: datetime


class ValidationResult(BaseModel):
    """Result of POST /workflows/{id}/validate."""

    valid: bool
    errors: list[str]
    warnings: list[str]

"""Pydantic v2 schemas for Workflow CRUD and validation."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.graph import Graph


class WorkflowIn(BaseModel):
    """Request body for creating or updating a Workflow."""

    name: str
    description: str | None = None
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

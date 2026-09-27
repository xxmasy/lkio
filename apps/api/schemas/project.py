"""Pydantic Schemas for Project API
"""

import uuid
from datetime import datetime
from typing import Any
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    key: str = Field(..., max_length=64, examples=["DEMO_FE"])
    name: str = Field(..., max_length=255, examples=["demo-frontend"])
    kind: str = Field(..., max_length=32, examples=["frontend"])
    role: str = Field(..., max_length=64, examples=["primary_frontend"])
    local_path: str = Field(..., examples=["/workspace/demo-frontend"])
    description: str | None = None
    status: str = Field(default="ACTIVE", max_length=32)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_", "metadata"),
    )


class ProjectCreate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ProjectDetail(ProjectRead):
    entity_count: int = 0
    relation_count: int = 0
    related_projects: list[str] = Field(default_factory=list)

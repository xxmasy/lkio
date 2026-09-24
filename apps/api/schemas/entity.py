"""Pydantic Schemas for Entity API
"""

import uuid
from datetime import datetime
from typing import Any
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class EntityBase(BaseModel):
    project_id: uuid.UUID | None = None
    entity_type: str = Field(..., max_length=64, examples=["PROJECT", "REPOSITORY", "FRONTEND", "BACKEND"])
    entity_key: str = Field(..., max_length=255, examples=["PROJECT:HELLO_FE"])
    name: str = Field(..., max_length=255)
    canonical_name: str = Field(..., max_length=255)
    path: str | None = None
    status: str = Field(default="ACTIVE", max_length=32)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_", "metadata"),
    )


class EntityCreate(EntityBase):
    pass


class EntityRead(EntityBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

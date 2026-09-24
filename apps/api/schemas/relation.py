"""Pydantic Schemas for Relation API
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class RelationBase(BaseModel):
    subject_entity_id: uuid.UUID
    predicate: str = Field(..., max_length=128, examples=["contains", "paired_with", "depends_on"])
    object_entity_id: uuid.UUID
    confidence: Decimal = Field(default=Decimal("1.00000"), ge=0, le=1)
    source_id: uuid.UUID | None = None
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_", "metadata"),
    )


class RelationCreate(RelationBase):
    pass


class RelationRead(RelationBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

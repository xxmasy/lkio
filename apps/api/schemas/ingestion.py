"""Pydantic Schemas for LKIO Ingestion and Snapshot API
"""

import uuid
from datetime import datetime
from typing import Any
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class IngestionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    project_id: uuid.UUID
    source_id: uuid.UUID | None = None
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    head_before: str | None = None
    head_after: str | None = None
    files_seen: int = 0
    files_created: int = 0
    files_updated: int = 0
    files_deleted: int = 0
    entities_created: int = 0
    entities_updated: int = 0
    relations_created: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_", "metadata"),
    )


class ProjectSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    project_id: uuid.UUID
    ingestion_run_id: uuid.UUID | None = None
    head: str | None = None
    branch: str | None = None
    file_count: int = 0
    directory_count: int = 0
    dependency_count: int = 0
    frameworks: list[dict[str, Any]] = Field(default_factory=list)
    languages: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_", "metadata"),
    )
    created_at: datetime


class DependencyItem(BaseModel):
    name: str
    ecosystem: str
    version_spec: str
    scope: str
    is_direct: bool
    manifest_path: str


class FrameworkItem(BaseModel):
    name: str
    confidence: float
    method: str
    evidence: str
    version: str | None = None


class BatchScanResult(BaseModel):
    total: int
    succeeded: int
    failed: int
    runs: dict[str, Any]
    status: str

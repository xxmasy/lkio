"""Pydantic Models and DTOs for MVP5 Event & Change Intelligence
"""

from datetime import datetime
from enum import Enum
from typing import Any
import uuid
from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    RENAMED = "RENAMED"
    UNKNOWN = "UNKNOWN"


class FileChangeDTO(BaseModel):
    file_path: str
    change_type: ChangeType
    insertions: int = 0
    deletions: int = 0
    old_path: str | None = None


class CommitEventDTO(BaseModel):
    sha: str
    parent_sha: str | None = None
    author_name: str
    author_email: str
    authored_at: datetime
    message: str
    changed_files: list[FileChangeDTO] = Field(default_factory=list)
    total_insertions: int = 0
    total_deletions: int = 0


class EntityChangeDTO(BaseModel):
    entity_key: str
    entity_name: str
    entity_type: str
    file_rel_path: str
    commit_sha: str
    change_type: ChangeType
    authored_at: datetime


class TimelineQueryDTO(BaseModel):
    project_key: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    event_types: list[str] | None = None
    entity_id: uuid.UUID | None = None
    limit: int = 100
    offset: int = 0


class TemporalQueryResultDTO(BaseModel):
    query_type: str
    subject: str
    total_events: int
    events: list[dict[str, Any]]
    metadata: dict[str, Any] = Field(default_factory=dict)

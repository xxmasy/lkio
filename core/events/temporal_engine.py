"""Temporal Query Engine for MVP5 Event & Change Intelligence
Executes time-travel, audit, and temporal trajectory queries over the LKIO Event Store.
Strictly implements Baseline Section 28 specifications:
- Project / Entity / File Timeline
- First Appearance Query ("这个 API 什么时候第一次出现？")
- Change Frequency Analysis ("这个业务规则/文件改过几次？")
- Changes Since Commit/Deployment ("某次部署/Commit 之后发生了什么？")
"""

from datetime import datetime
from typing import Any
import uuid
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from core.events.models import TemporalQueryResultDTO
from core.models.entity import Entity
from core.models.event import Event, EventType
from core.models.project import Project


class TemporalQueryEngine:
    """Core engine for temporal event queries and historical intelligence."""

    def get_project_timeline(
        self,
        db: Session,
        project_id: uuid.UUID | None = None,
        project_key: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        event_types: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Event]:
        """Returns chronological list of events for a project."""
        stmt = select(Event).order_by(desc(Event.timestamp))

        if project_id:
            stmt = stmt.where(Event.project_id == project_id)
        elif project_key:
            stmt = stmt.join(Project, Event.project_id == Project.id).where(Project.key == project_key)

        if start_time:
            stmt = stmt.where(Event.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(Event.timestamp <= end_time)
        if event_types:
            stmt = stmt.where(Event.event_type.in_(event_types))

        stmt = stmt.offset(offset).limit(limit)
        return list(db.scalars(stmt).all())

    def get_entity_timeline(
        self,
        db: Session,
        project_id: uuid.UUID | None,
        entity_id: uuid.UUID | None = None,
        entity_key: str | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Returns chronological history of changes affecting a specific entity."""
        stmt = select(Event).where(Event.event_type == EventType.ENTITY_CHANGED.value)
        if project_id:
            stmt = stmt.where(Event.project_id == project_id)
        if entity_id:
            stmt = stmt.where(Event.entity_id == entity_id)

        events = list(db.scalars(stmt.order_by(desc(Event.timestamp)).limit(limit)).all())
        if entity_key and not events:
            # Fallback by entity_key in metadata
            all_entity_events = db.scalars(
                select(Event)
                .where(Event.event_type == EventType.ENTITY_CHANGED.value)
                .order_by(desc(Event.timestamp))
                .limit(500)
            ).all()
            events = [e for e in all_entity_events if e.metadata_.get("entity_key") == entity_key][:limit]

        return events

    def get_file_timeline(
        self,
        db: Session,
        project_id: uuid.UUID | None,
        file_rel_path: str,
        limit: int = 100,
    ) -> list[Event]:
        """Returns chronological changes for a specific file path."""
        norm_path = file_rel_path.replace("\\", "/")
        stmt = (
            select(Event)
            .where(Event.event_type == EventType.FILE_CHANGED.value)
            .order_by(desc(Event.timestamp))
            .limit(1000)
        )
        if project_id:
            stmt = stmt.where(Event.project_id == project_id)

        all_file_events = db.scalars(stmt).all()
        matched = [e for e in all_file_events if e.metadata_.get("file_rel_path") == norm_path][:limit]
        return matched

    def query_first_appearance(
        self,
        db: Session,
        project_id: uuid.UUID | None,
        name_or_path: str,
    ) -> dict[str, Any]:
        """Answers: '这个 API / 文件 / 实体 什么时候第一次出现？'
        Finds the earliest event introducing this subject.
        """
        norm_query = name_or_path.replace("\\", "/").strip().lower()
        stmt = select(Event).order_by(Event.timestamp.asc()).limit(2000)
        if project_id:
            stmt = stmt.where(Event.project_id == project_id)

        candidates = db.scalars(stmt).all()
        for event in candidates:
            # Check metadata fields
            meta = event.metadata_
            file_path = str(meta.get("file_rel_path", "")).lower()
            entity_name = str(meta.get("entity_name", "")).lower()
            entity_key = str(meta.get("entity_key", "")).lower()
            message = str(meta.get("message", "")).lower()

            if (
                norm_query in file_path
                or norm_query in entity_name
                or norm_query in entity_key
                or norm_query in message
            ):
                return {
                    "found": True,
                    "subject": name_or_path,
                    "first_appearance_time": event.timestamp.isoformat(),
                    "commit_sha": meta.get("commit_sha"),
                    "author": event.actor_id,
                    "event_type": event.event_type,
                    "change_type": meta.get("change_type", "UNKNOWN"),
                    "reason": event.reason,
                    "matched_file": meta.get("file_rel_path"),
                }

        return {
            "found": False,
            "subject": name_or_path,
            "message": "Subject not found in event history.",
        }

    def query_change_frequency(
        self,
        db: Session,
        project_id: uuid.UUID | None,
        name_or_path: str,
    ) -> dict[str, Any]:
        """Answers: '这个业务规则 / 文件 改过几次？'
        Returns change statistics, modification frequency, and author breakdown.
        """
        norm_query = name_or_path.replace("\\", "/").strip().lower()
        stmt = select(Event).order_by(desc(Event.timestamp)).limit(2000)
        if project_id:
            stmt = stmt.where(Event.project_id == project_id)

        all_events = db.scalars(stmt).all()
        matched_events: list[Event] = []
        for event in all_events:
            meta = event.metadata_
            file_path = str(meta.get("file_rel_path", "")).lower()
            entity_name = str(meta.get("entity_name", "")).lower()
            entity_key = str(meta.get("entity_key", "")).lower()

            if norm_query in file_path or norm_query in entity_name or norm_query in entity_key:
                matched_events.append(event)

        unique_commits = set()
        authors = set()
        total_insertions = 0
        total_deletions = 0
        commit_history: list[dict[str, Any]] = []

        for e in matched_events:
            sha = e.metadata_.get("commit_sha")
            if sha and sha not in unique_commits:
                unique_commits.add(sha)
                authors.add(e.actor_id)
                ins = int(e.metadata_.get("insertions", 0))
                dels = int(e.metadata_.get("deletions", 0))
                total_insertions += ins
                total_deletions += dels
                commit_history.append({
                    "sha": sha,
                    "author": e.actor_id,
                    "timestamp": e.timestamp.isoformat(),
                    "reason": e.reason,
                    "insertions": ins,
                    "deletions": dels,
                })

        return {
            "subject": name_or_path,
            "total_modifications": len(unique_commits),
            "unique_authors_count": len(authors),
            "authors": sorted(list(authors)),
            "total_insertions": total_insertions,
            "total_deletions": total_deletions,
            "commit_history": commit_history,
        }

    def query_changes_since(
        self,
        db: Session,
        project_id: uuid.UUID | None,
        commit_sha: str | None = None,
        since_time: datetime | None = None,
    ) -> list[Event]:
        """Answers: '某次 commit / 部署 之后发生了什么变更？'"""
        target_time = since_time

        if commit_sha and not target_time:
            # Find the commit event
            stmt = select(Event).where(Event.event_type == EventType.COMMIT.value)
            if project_id:
                stmt = stmt.where(Event.project_id == project_id)
            all_commits = db.scalars(stmt).all()
            for c in all_commits:
                if c.metadata_.get("commit_sha") == commit_sha:
                    target_time = c.timestamp
                    break

        if not target_time:
            return []

        # Return events after target_time
        q = select(Event).where(Event.timestamp > target_time).order_by(Event.timestamp.asc())
        if project_id:
            q = q.where(Event.project_id == project_id)

        return list(db.scalars(q).all())

"""Event Ingestion Pipeline for MVP5 Event & Change Intelligence
Coordinates commit extraction, entity linking, and double-pass idempotent persistence.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.events.git_extractor import GitChangeExtractor
from core.events.models import ChangeType, CommitEventDTO, EntityChangeDTO, FileChangeDTO
from core.models.entity import Entity
from core.models.event import ActorType, Event, EventType, SourceType
from core.models.project import Project


class EventPipeline:
    """Manages event extraction, entity mapping, and idempotent persistence."""

    def __init__(self, extractor: GitChangeExtractor | None = None):
        self.extractor = extractor or GitChangeExtractor()

    def generate_events_for_commits(
        self,
        project_key: str,
        project_id: uuid.UUID | None,
        commits: list[CommitEventDTO],
        entities_by_path: dict[str, list[Entity]] | None = None,
    ) -> list[Event]:
        """Converts extracted commits and file changes into Event objects with entity linking."""
        entities_by_path = entities_by_path or {}
        events: list[Event] = []

        for commit in commits:
            # 1. COMMIT Event
            commit_key = f"EVENT:{project_key}:COMMIT:{commit.sha}"
            commit_event = Event(
                event_key=commit_key,
                event_type=EventType.COMMIT.value,
                project_id=project_id,
                entity_id=None,
                actor_type=ActorType.GIT.value,
                actor_id=commit.author_email,
                timestamp=commit.authored_at,
                before_state={"status": "before_commit"},
                after_state={"status": "committed", "sha": commit.sha},
                reason=commit.message,
                source_type=SourceType.GIT_COMMIT.value,
                confidence=1.0,
                metadata_={
                    "commit_sha": commit.sha,
                    "author": commit.author_name,
                    "author_email": commit.author_email,
                    "message": commit.message,
                    "parent_sha": commit.parent_sha,
                    "changed_files_count": len(commit.changed_files),
                    "total_insertions": commit.total_insertions,
                    "total_deletions": commit.total_deletions,
                },
            )
            events.append(commit_event)

            # 2. FILE_CHANGED Events
            for file_change in commit.changed_files:
                file_key = f"EVENT:{project_key}:FILE:{commit.sha}:{file_change.file_path}"
                file_event = Event(
                    event_key=file_key,
                    event_type=EventType.FILE_CHANGED.value,
                    project_id=project_id,
                    entity_id=None,
                    actor_type=ActorType.GIT.value,
                    actor_id=commit.author_email,
                    timestamp=commit.authored_at,
                    before_state={"path": file_change.old_path or file_change.file_path},
                    after_state={"path": file_change.file_path, "change_type": file_change.change_type.value},
                    reason=f"{file_change.change_type.value}: {file_change.file_path}",
                    source_type=SourceType.GIT_COMMIT.value,
                    confidence=1.0,
                    metadata_={
                        "commit_sha": commit.sha,
                        "file_rel_path": file_change.file_path,
                        "change_type": file_change.change_type.value,
                        "insertions": file_change.insertions,
                        "deletions": file_change.deletions,
                        "old_path": file_change.old_path,
                    },
                )
                events.append(file_event)

                # 3. ENTITY_CHANGED Events (link with known entities in file)
                matched_entities = entities_by_path.get(file_change.file_path, [])
                for entity in matched_entities:
                    entity_event_key = f"EVENT:{project_key}:ENTITY:{commit.sha}:{entity.entity_key}"
                    entity_event = Event(
                        event_key=entity_event_key,
                        event_type=EventType.ENTITY_CHANGED.value,
                        project_id=project_id,
                        entity_id=entity.id,
                        actor_type=ActorType.GIT.value,
                        actor_id=commit.author_email,
                        timestamp=commit.authored_at,
                        before_state={"entity_key": entity.entity_key, "path": file_change.file_path},
                        after_state={"entity_key": entity.entity_key, "change_type": file_change.change_type.value},
                        reason=f"Entity {entity.name} modified in commit {commit.sha[:8]}",
                        source_type=SourceType.GIT_COMMIT.value,
                        confidence=1.0,
                        metadata_={
                            "commit_sha": commit.sha,
                            "entity_key": entity.entity_key,
                            "entity_name": entity.name,
                            "entity_type": entity.entity_type,
                            "file_rel_path": file_change.file_path,
                            "change_type": file_change.change_type.value,
                        },
                    )
                    events.append(entity_event)

        return events

    def sync_project_events(
        self,
        db: Session,
        project_key: str,
        repo_path: Path,
        max_commits: int = 100,
    ) -> dict[str, Any]:
        """Executes full read-only extraction and idempotent synchronization for a project."""
        project = db.scalars(select(Project).where(Project.key == project_key)).first()
        project_id = project.id if project else None

        # Build path to entities map
        entities_by_path: dict[str, list[Entity]] = {}
        if project_id:
            entities = db.scalars(select(Entity).where(Entity.project_id == project_id)).all()
            for ent in entities:
                if ent.path:
                    norm_path = ent.path.replace("\\", "/")
                    entities_by_path.setdefault(norm_path, []).append(ent)

        # Extract commits via read-only subprocess
        commits = self.extractor.extract_commits(repo_path, max_commits=max_commits)

        # Generate event objects
        events = self.generate_events_for_commits(
            project_key=project_key,
            project_id=project_id,
            commits=commits,
            entities_by_path=entities_by_path,
        )

        # Idempotent persistence
        persist_stats = self.persist_events(db, events)
        return {
            "project_key": project_key,
            "commits_extracted": len(commits),
            "events_generated": len(events),
            **persist_stats,
        }

    def persist_events(self, db: Session, events: list[Event]) -> dict[str, int]:
        """Persists events into the database with double-pass idempotency guarantee."""
        if not events:
            return {"created": 0, "updated": 0, "total": 0}

        event_keys = [e.event_key for e in events]
        existing_events = db.scalars(select(Event).where(Event.event_key.in_(event_keys))).all()
        existing_map = {e.event_key: e for e in existing_events}

        created = 0
        updated = 0

        for event in events:
            existing = existing_map.get(event.event_key)
            if existing:
                existing.actor_id = event.actor_id
                existing.actor_type = event.actor_type
                existing.timestamp = event.timestamp
                existing.reason = event.reason
                existing.metadata_ = event.metadata_
                existing.before_state = event.before_state
                existing.after_state = event.after_state
                existing.confidence = event.confidence
                updated += 1
            else:
                db.add(event)
                created += 1

        db.commit()
        return {"created": created, "updated": updated, "total": len(events)}

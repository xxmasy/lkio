"""Projects API Router
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from apps.api.schemas.common import success_response
from apps.api.schemas.ingestion import (
    BatchScanResult,
    DependencyItem,
    FrameworkItem,
    IngestionRunRead,
    ProjectSnapshotRead,
)
from apps.api.schemas.project import ProjectCreate, ProjectDetail, ProjectRead
from core.db.session import get_db
from core.models.entity import Entity
from core.models.ingestion_run import IngestionRun
from core.models.project import Project
from core.models.project_snapshot import ProjectSnapshot
from core.models.relation import Relation
from ingestion.pipeline import run_all_projects_ingestion, run_project_ingestion

router = APIRouter(prefix="/projects", tags=["Projects"])


def _resolve_project(project_id: str, db: Session) -> Project:
    try:
        u_id = uuid.UUID(project_id)
        stmt = select(Project).where(Project.id == u_id)
    except ValueError:
        stmt = select(Project).where(Project.key == project_id)

    project = db.scalars(stmt).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return project


@router.post("/scan-all", status_code=status.HTTP_200_OK)
def scan_all_projects():
    """Trigger ingestion scan for all registered active projects."""
    summary = run_all_projects_ingestion()
    return success_response(summary)


@router.get("", status_code=status.HTTP_200_OK)
def list_projects(
    kind: str | None = Query(None, description="Filter by project kind"),
    role: str | None = Query(None, description="Filter by project role"),
    status_: str | None = Query(None, alias="status", description="Filter by status"),
    db: Session = Depends(get_db),
):
    """List registered projects."""
    query = select(Project)
    if kind:
        query = query.where(Project.kind == kind)
    if role:
        query = query.where(Project.role == role)
    if status_:
        query = query.where(Project.status == status_)

    projects = db.scalars(query.order_by(Project.created_at)).all()
    results = [ProjectRead.model_validate(p) for p in projects]
    return success_response(results)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
):
    """Register a new project into LKIO."""
    existing = db.scalars(select(Project).where(Project.key == payload.key)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project with key '{payload.key}' already exists",
        )

    project = Project(
        key=payload.key,
        name=payload.name,
        kind=payload.kind,
        role=payload.role,
        local_path=payload.local_path,
        description=payload.description,
        status=payload.status,
        metadata_=payload.metadata_,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return success_response(ProjectRead.model_validate(project))


@router.get("/{project_id}", status_code=status.HTTP_200_OK)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Get project details including counts and related projects."""
    project = _resolve_project(project_id, db)

    entity_count = db.scalar(
        select(func.count(Entity.id)).where(Entity.project_id == project.id)
    ) or 0

    # Count relations involving project's entities
    project_entity_ids = select(Entity.id).where(Entity.project_id == project.id)
    relation_count = db.scalar(
        select(func.count(Relation.id)).where(
            or_(
                Relation.subject_entity_id.in_(project_entity_ids),
                Relation.object_entity_id.in_(project_entity_ids),
            )
        )
    ) or 0

    # Discover related projects via cross-project relations
    paired_rels = db.scalars(
        select(Relation).where(
            Relation.predicate == "paired_with",
            or_(
                Relation.subject_entity_id.in_(project_entity_ids),
                Relation.object_entity_id.in_(project_entity_ids),
            ),
        )
    ).all()

    related_project_keys = set()
    for rel in paired_rels:
        other_id = rel.object_entity_id if rel.subject_entity_id in db.scalars(project_entity_ids).all() else rel.subject_entity_id
        other_entity = db.get(Entity, other_id)
        if other_entity and other_entity.project_id:
            other_p = db.get(Project, other_entity.project_id)
            if other_p and other_p.id != project.id:
                related_project_keys.add(other_p.key)

    detail = ProjectDetail(
        id=project.id,
        key=project.key,
        name=project.name,
        kind=project.kind,
        role=project.role,
        local_path=project.local_path,
        description=project.description,
        status=project.status,
        metadata_=project.metadata_,
        created_at=project.created_at,
        updated_at=project.updated_at,
        entity_count=entity_count,
        relation_count=relation_count,
        related_projects=list(related_project_keys),
    )
    return success_response(detail)


@router.post("/{project_id}/scan", status_code=status.HTTP_200_OK)
def trigger_project_scan(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Trigger an ingestion scan for a single project."""
    project = _resolve_project(project_id, db)
    run = run_project_ingestion(project.key)
    return success_response(IngestionRunRead.model_validate(run))


@router.get("/{project_id}/scan-runs", status_code=status.HTTP_200_OK)
def list_project_scan_runs(
    project_id: str,
    limit: int = Query(20, ge=1, le=100, description="Max runs to return"),
    db: Session = Depends(get_db),
):
    """List recent ingestion runs for a project."""
    project = _resolve_project(project_id, db)
    runs = db.scalars(
        select(IngestionRun)
        .where(IngestionRun.project_id == project.id)
        .order_by(IngestionRun.started_at.desc())
        .limit(limit)
    ).all()
    results = [IngestionRunRead.model_validate(r) for r in runs]
    return success_response(results)


@router.get("/{project_id}/snapshot", status_code=status.HTTP_200_OK)
def get_latest_project_snapshot(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Get the latest milestone snapshot of a project."""
    project = _resolve_project(project_id, db)
    snapshot = db.scalars(
        select(ProjectSnapshot)
        .where(ProjectSnapshot.project_id == project.id)
        .order_by(ProjectSnapshot.created_at.desc())
    ).first()

    if not snapshot:
        return success_response(None)
    return success_response(ProjectSnapshotRead.model_validate(snapshot))


@router.get("/{project_id}/dependencies", status_code=status.HTTP_200_OK)
def get_project_dependencies(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Get detected dependencies for a project."""
    project = _resolve_project(project_id, db)
    entities = db.scalars(
        select(Entity).where(
            Entity.project_id == project.id,
            Entity.entity_type == "DEPENDENCY",
            Entity.status == "ACTIVE",
        ).order_by(Entity.name)
    ).all()

    deps = [
        DependencyItem(
            name=e.name,
            ecosystem=e.metadata_.get("ecosystem", "unknown"),
            version_spec=e.metadata_.get("version_spec", "*"),
            scope=e.metadata_.get("scope", "runtime"),
            is_direct=e.metadata_.get("is_direct", True),
            manifest_path=e.metadata_.get("manifest_path", ""),
        )
        for e in entities
    ]
    return success_response(deps)


@router.get("/{project_id}/frameworks", status_code=status.HTTP_200_OK)
def get_project_frameworks(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Get detected frameworks for a project."""
    project = _resolve_project(project_id, db)
    entities = db.scalars(
        select(Entity).where(
            Entity.project_id == project.id,
            Entity.entity_type == "FRAMEWORK",
            Entity.status == "ACTIVE",
        ).order_by(Entity.name)
    ).all()

    fws = [
        FrameworkItem(
            name=e.name,
            confidence=float(e.metadata_.get("confidence", 1.0)),
            method=e.metadata_.get("method", "manifest"),
            evidence=e.metadata_.get("evidence", ""),
            version=e.metadata_.get("version"),
        )
        for e in entities
    ]
    return success_response(fws)


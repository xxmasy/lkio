"""Projects API Router
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from apps.api.schemas.common import success_response
from apps.api.schemas.project import ProjectCreate, ProjectDetail, ProjectRead
from core.db.session import get_db
from core.models.entity import Entity
from core.models.project import Project
from core.models.relation import Relation

router = APIRouter(prefix="/projects", tags=["Projects"])


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
    # Allow querying by UUID or key
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

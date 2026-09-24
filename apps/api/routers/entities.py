"""Entities API Router
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from apps.api.schemas.common import success_response
from apps.api.schemas.entity import EntityCreate, EntityRead
from core.db.session import get_db
from core.models.entity import Entity

router = APIRouter(prefix="/entities", tags=["Entities"])


@router.get("", status_code=status.HTTP_200_OK)
def list_entities(
    project_id: uuid.UUID | None = Query(None, description="Filter by project UUID"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    status_: str | None = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List entities with optional filters."""
    query = select(Entity)
    if project_id:
        query = query.where(Entity.project_id == project_id)
    if entity_type:
        query = query.where(Entity.entity_type == entity_type)
    if status_:
        query = query.where(Entity.status == status_)

    entities = db.scalars(query.order_by(Entity.created_at).offset(offset).limit(limit)).all()
    results = [EntityRead.model_validate(e) for e in entities]
    return success_response(results)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_entity(
    payload: EntityCreate,
    db: Session = Depends(get_db),
):
    """Create a new entity in the knowledge core."""
    existing = db.scalars(select(Entity).where(Entity.entity_key == payload.entity_key)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Entity with key '{payload.entity_key}' already exists",
        )

    entity = Entity(
        project_id=payload.project_id,
        entity_type=payload.entity_type,
        entity_key=payload.entity_key,
        name=payload.name,
        canonical_name=payload.canonical_name,
        path=payload.path,
        status=payload.status,
        metadata_=payload.metadata_,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return success_response(EntityRead.model_validate(entity))


@router.get("/{entity_id}", status_code=status.HTTP_200_OK)
def get_entity(
    entity_id: str,
    db: Session = Depends(get_db),
):
    """Get entity details by UUID or entity_key."""
    try:
        u_id = uuid.UUID(entity_id)
        stmt = select(Entity).where(Entity.id == u_id)
    except ValueError:
        stmt = select(Entity).where(Entity.entity_key == entity_id)

    entity = db.scalars(stmt).first()
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found",
        )
    return success_response(EntityRead.model_validate(entity))

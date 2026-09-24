"""Relations API Router
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from apps.api.schemas.common import success_response
from apps.api.schemas.relation import RelationCreate, RelationRead
from core.db.session import get_db
from core.models.relation import Relation

router = APIRouter(prefix="/relations", tags=["Relations"])


@router.get("", status_code=status.HTTP_200_OK)
def list_relations(
    subject_entity_id: uuid.UUID | None = Query(None, description="Filter by subject entity UUID"),
    predicate: str | None = Query(None, description="Filter by predicate"),
    object_entity_id: uuid.UUID | None = Query(None, description="Filter by object entity UUID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List relations with optional subject, predicate, or object filters."""
    query = select(Relation)
    if subject_entity_id:
        query = query.where(Relation.subject_entity_id == subject_entity_id)
    if predicate:
        query = query.where(Relation.predicate == predicate)
    if object_entity_id:
        query = query.where(Relation.object_entity_id == object_entity_id)

    relations = db.scalars(query.order_by(Relation.created_at).offset(offset).limit(limit)).all()
    results = [RelationRead.model_validate(r) for r in relations]
    return success_response(results)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_relation(
    payload: RelationCreate,
    db: Session = Depends(get_db),
):
    """Create a new relation triple."""
    existing = db.scalars(
        select(Relation).where(
            Relation.subject_entity_id == payload.subject_entity_id,
            Relation.predicate == payload.predicate,
            Relation.object_entity_id == payload.object_entity_id,
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Relation triple already exists",
        )

    relation = Relation(
        subject_entity_id=payload.subject_entity_id,
        predicate=payload.predicate,
        object_entity_id=payload.object_entity_id,
        confidence=payload.confidence,
        source_id=payload.source_id,
        metadata_=payload.metadata_,
    )
    db.add(relation)
    db.commit()
    db.refresh(relation)
    return success_response(RelationRead.model_validate(relation))

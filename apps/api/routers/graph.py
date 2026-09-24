"""Graph API Router for Cytoscape.js Visualization
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from apps.api.schemas.common import success_response
from apps.api.schemas.graph import GraphData, GraphEdge, GraphEdgeData, GraphNode, GraphNodeData
from core.db.session import get_db
from core.models.entity import Entity
from core.models.project import Project
from core.models.relation import Relation

router = APIRouter(prefix="/graph", tags=["Graph"])


@router.get("/projects/{project_id}", status_code=status.HTTP_200_OK)
def get_project_graph(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve graph topology for a project, including cross-project links."""
    # Resolve project by UUID or key
    try:
        u_id = uuid.UUID(project_id)
        p_stmt = select(Project).where(Project.id == u_id)
    except ValueError:
        p_stmt = select(Project).where(Project.key == project_id)

    project = db.scalars(p_stmt).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    # 1. Fetch all entities belonging to this project
    entities = db.scalars(select(Entity).where(Entity.project_id == project.id)).all()
    entity_map: dict[uuid.UUID, Entity] = {e.id: e for e in entities}
    entity_ids = list(entity_map.keys())

    # 2. Fetch all relations where either subject or object is in this project
    relations = db.scalars(
        select(Relation).where(
            or_(
                Relation.subject_entity_id.in_(entity_ids),
                Relation.object_entity_id.in_(entity_ids),
            )
        )
    ).all()

    # 3. Collect foreign entities connected via cross-project relations
    missing_entity_ids = set()
    for rel in relations:
        if rel.subject_entity_id not in entity_map:
            missing_entity_ids.add(rel.subject_entity_id)
        if rel.object_entity_id not in entity_map:
            missing_entity_ids.add(rel.object_entity_id)

    if missing_entity_ids:
        foreign_entities = db.scalars(
            select(Entity).where(Entity.id.in_(missing_entity_ids))
        ).all()
        for fe in foreign_entities:
            entity_map[fe.id] = fe

    # 4. Construct Cytoscape graph nodes
    nodes: list[GraphNode] = []
    for e in entity_map.values():
        nodes.append(
            GraphNode(
                data=GraphNodeData(
                    id=str(e.id),
                    label=e.name,
                    entity_type=e.entity_type,
                    entity_key=e.entity_key,
                    canonical_name=e.canonical_name,
                    project_id=str(e.project_id) if e.project_id else None,
                    status=e.status,
                    metadata=e.metadata_,
                )
            )
        )

    # 5. Construct Cytoscape graph edges
    edges: list[GraphEdge] = []
    for r in relations:
        edges.append(
            GraphEdge(
                data=GraphEdgeData(
                    id=str(r.id),
                    source=str(r.subject_entity_id),
                    target=str(r.object_entity_id),
                    label=r.predicate,
                    predicate=r.predicate,
                    confidence=float(r.confidence),
                    source_id=str(r.source_id) if r.source_id else None,
                    metadata=r.metadata_,
                )
            )
        )

    return success_response(GraphData(nodes=nodes, edges=edges).model_dump())


@router.get("/entities/{entity_id}/neighbors", status_code=status.HTTP_200_OK)
def get_entity_neighbors(
    entity_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve 1-hop neighborhood subgraph for an entity."""
    try:
        u_id = uuid.UUID(entity_id)
        e_stmt = select(Entity).where(Entity.id == u_id)
    except ValueError:
        e_stmt = select(Entity).where(Entity.entity_key == entity_id)

    center_entity = db.scalars(e_stmt).first()
    if not center_entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found",
        )

    relations = db.scalars(
        select(Relation).where(
            or_(
                Relation.subject_entity_id == center_entity.id,
                Relation.object_entity_id == center_entity.id,
            )
        )
    ).all()

    neighbor_ids = {center_entity.id}
    for rel in relations:
        neighbor_ids.add(rel.subject_entity_id)
        neighbor_ids.add(rel.object_entity_id)

    entities = db.scalars(select(Entity).where(Entity.id.in_(neighbor_ids))).all()

    nodes = [
        GraphNode(
            data=GraphNodeData(
                id=str(e.id),
                label=e.name,
                entity_type=e.entity_type,
                entity_key=e.entity_key,
                canonical_name=e.canonical_name,
                project_id=str(e.project_id) if e.project_id else None,
                status=e.status,
                metadata=e.metadata_,
            )
        )
        for e in entities
    ]

    edges = [
        GraphEdge(
            data=GraphEdgeData(
                id=str(r.id),
                source=str(r.subject_entity_id),
                target=str(r.object_entity_id),
                label=r.predicate,
                predicate=r.predicate,
                confidence=float(r.confidence),
                source_id=str(r.source_id) if r.source_id else None,
                metadata=r.metadata_,
            )
        )
        for r in relations
    ]

    return success_response(GraphData(nodes=nodes, edges=edges).model_dump())


@router.get("/overview", status_code=status.HTTP_200_OK)
def get_global_overview_graph(
    db: Session = Depends(get_db),
):
    """Retrieve the global multi-project overview graph."""
    entities = db.scalars(select(Entity)).all()
    relations = db.scalars(select(Relation)).all()

    nodes = [
        GraphNode(
            data=GraphNodeData(
                id=str(e.id),
                label=e.name,
                entity_type=e.entity_type,
                entity_key=e.entity_key,
                canonical_name=e.canonical_name,
                project_id=str(e.project_id) if e.project_id else None,
                status=e.status,
                metadata=e.metadata_,
            )
        )
        for e in entities
    ]

    edges = [
        GraphEdge(
            data=GraphEdgeData(
                id=str(r.id),
                source=str(r.subject_entity_id),
                target=str(r.object_entity_id),
                label=r.predicate,
                predicate=r.predicate,
                confidence=float(r.confidence),
                source_id=str(r.source_id) if r.source_id else None,
                metadata=r.metadata_,
            )
        )
        for r in relations
    ]

    return success_response(GraphData(nodes=nodes, edges=edges).model_dump())

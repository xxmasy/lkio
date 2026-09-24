"""Idempotent Seeder for LKIO MVP0 Projects and Knowledge Core
Loads initial projects from config/projects.yaml and builds seed topology.
"""

import sys
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import yaml
from sqlalchemy import select
from core.db.session import SessionLocal
from core.models.entity import Entity
from core.models.project import Project
from core.models.relation import Relation
from core.models.source import Source

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "config" / "projects.yaml"


def seed_data() -> dict[str, int]:
    """Seed projects, sources, entities, and relations idempotently.

    Returns:
        dict with counts of processed records.
    """
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    project_configs = config_data.get("projects", [])

    stats = {
        "projects_upserted": 0,
        "sources_upserted": 0,
        "entities_upserted": 0,
        "relations_upserted": 0,
    }

    with SessionLocal() as session:
        project_entity_map: dict[str, Entity] = {}

        for p_cfg in project_configs:
            p_key = p_cfg["key"]
            p_name = p_cfg["name"]
            p_kind = p_cfg["kind"]
            p_role = p_cfg["role"]
            p_path = p_cfg["local_path"]
            p_enabled = p_cfg.get("enabled", True)

            # 1. Upsert Project
            stmt = select(Project).where(Project.key == p_key)
            project = session.scalars(stmt).first()
            if not project:
                project = Project(
                    key=p_key,
                    name=p_name,
                    kind=p_kind,
                    role=p_role,
                    local_path=p_path,
                    status="ACTIVE" if p_enabled else "INACTIVE",
                    description=f"Initial registered project {p_name} ({p_role})",
                    metadata_={"seed_version": "0.1", "role": p_role},
                )
                session.add(project)
                session.flush()
            else:
                project.name = p_name
                project.kind = p_kind
                project.role = p_role
                project.local_path = p_path
                session.flush()
            stats["projects_upserted"] += 1

            # 2. Upsert Source
            src_stmt = select(Source).where(
                Source.project_id == project.id,
                Source.source_type == "local_git_repository",
            )
            source = session.scalars(src_stmt).first()
            if not source:
                source = Source(
                    project_id=project.id,
                    source_type="local_git_repository",
                    uri=p_path,
                    read_only=True,
                    enabled=p_enabled,
                    config={"branch_tracking": "main", "seed": True},
                )
                session.add(source)
                session.flush()
            else:
                source.uri = p_path
                source.read_only = True
                source.enabled = p_enabled
                session.flush()
            stats["sources_upserted"] += 1

            # 3. Create Hierarchical Entities: PROJECT -> REPOSITORY -> FRONTEND/BACKEND
            # 3a. PROJECT entity
            proj_entity_key = f"PROJECT:{p_key}"
            e_proj_stmt = select(Entity).where(Entity.entity_key == proj_entity_key)
            e_proj = session.scalars(e_proj_stmt).first()
            if not e_proj:
                e_proj = Entity(
                    project_id=project.id,
                    entity_type="PROJECT",
                    entity_key=proj_entity_key,
                    name=p_name,
                    canonical_name=p_key,
                    path=p_path,
                    status="ACTIVE",
                    metadata_={"role": p_role, "kind": p_kind},
                )
                session.add(e_proj)
                session.flush()
            project_entity_map[p_key] = e_proj
            stats["entities_upserted"] += 1

            # 3b. REPOSITORY entity
            repo_entity_key = f"REPO:{p_key}"
            e_repo_stmt = select(Entity).where(Entity.entity_key == repo_entity_key)
            e_repo = session.scalars(e_repo_stmt).first()
            if not e_repo:
                e_repo = Entity(
                    project_id=project.id,
                    entity_type="REPOSITORY",
                    entity_key=repo_entity_key,
                    name=f"{p_name}_repo",
                    canonical_name=f"{p_key}_REPO",
                    path=p_path,
                    status="ACTIVE",
                    metadata_={"source_id": str(source.id)},
                )
                session.add(e_repo)
                session.flush()
            stats["entities_upserted"] += 1

            # 3c. Component / Layer entity (FRONTEND or BACKEND)
            sub_type = "FRONTEND" if p_kind == "frontend" else "BACKEND"
            sub_entity_key = f"{sub_type}:{p_key}"
            e_sub_stmt = select(Entity).where(Entity.entity_key == sub_entity_key)
            e_sub = session.scalars(e_sub_stmt).first()
            if not e_sub:
                e_sub = Entity(
                    project_id=project.id,
                    entity_type=sub_type,
                    entity_key=sub_entity_key,
                    name=f"{p_name}_{sub_type.lower()}",
                    canonical_name=f"{p_key}_{sub_type}",
                    path=p_path,
                    status="ACTIVE",
                    metadata_={"kind": p_kind},
                )
                session.add(e_sub)
                session.flush()
            stats["entities_upserted"] += 1

            # 4. Relations inside project:
            # PROJECT --contains--> REPOSITORY
            _upsert_relation(session, e_proj.id, "contains", e_repo.id, Decimal("1.00000"), source.id)
            stats["relations_upserted"] += 1

            # REPOSITORY --contains--> FRONTEND/BACKEND
            _upsert_relation(session, e_repo.id, "contains", e_sub.id, Decimal("1.00000"), source.id)
            stats["relations_upserted"] += 1

        # 5. Cross-project Relation: HELLO_FE --paired_with--> HELLO_BE
        if "HELLO_FE" in project_entity_map and "HELLO_BE" in project_entity_map:
            fe_proj_ent = project_entity_map["HELLO_FE"]
            be_proj_ent = project_entity_map["HELLO_BE"]
            _upsert_relation(
                session,
                fe_proj_ent.id,
                "paired_with",
                be_proj_ent.id,
                Decimal("1.00000"),
                None,
                {"description": "Pairing between HELLO_FE and HELLO_BE"},
            )
            stats["relations_upserted"] += 1

        session.commit()

    return stats


def _upsert_relation(
    session,
    subj_id,
    predicate: str,
    obj_id,
    confidence: Decimal,
    source_id=None,
    metadata=None,
):
    stmt = select(Relation).where(
        Relation.subject_entity_id == subj_id,
        Relation.predicate == predicate,
        Relation.object_entity_id == obj_id,
    )
    rel = session.scalars(stmt).first()
    if not rel:
        rel = Relation(
            subject_entity_id=subj_id,
            predicate=predicate,
            object_entity_id=obj_id,
            confidence=confidence,
            source_id=source_id,
            metadata_=metadata or {},
        )
        session.add(rel)
        session.flush()
    else:
        rel.confidence = confidence
        if metadata:
            rel.metadata_ = metadata
        session.flush()
    return rel


if __name__ == "__main__":
    result = seed_data()
    print("Seed execution finished successfully:")
    for k, v in result.items():
        print(f"  {k}: {v}")

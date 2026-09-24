"""LKIO Ingestion Pipeline Orchestrator
Executes full scan, metadata extraction, diff calculation, idempotent upserts, and snapshotting.
"""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session
from core.db.base import utc_now
from core.db.session import SessionLocal
from core.models.entity import Entity
from core.models.ingestion_run import IngestionRun
from core.models.project import Project
from core.models.project_snapshot import ProjectSnapshot
from core.models.relation import Relation
from core.models.source import Source
from ingestion.code.detector import detect_frameworks, detect_languages
from ingestion.filesystem.scanner import extract_directory_hierarchy, scan_single_file
from ingestion.git.client import GitClient, GitClientError
from ingestion.manifests.scanner import detect_package_manager, scan_all_manifests


class IngestionPipelineError(Exception):
    pass


def run_project_ingestion(project_key_or_id: str, db: Session | None = None) -> IngestionRun:
    """Runs a complete, idempotent ingestion scan for a single project."""
    should_close_session = False
    if db is None:
        db = SessionLocal()
        should_close_session = True

    try:
        # 1. Resolve Project
        try:
            u_id = uuid.UUID(project_key_or_id)
            stmt = select(Project).where(Project.id == u_id)
        except ValueError:
            stmt = select(Project).where(Project.key == project_key_or_id)

        project = db.scalars(stmt).first()
        if not project:
            raise IngestionPipelineError(f"Project '{project_key_or_id}' not found")

        project_root = Path(project.local_path)
        if not project_root.exists():
            raise IngestionPipelineError(f"Project local path does not exist: {project.local_path}")

        # 2. Resolve Source
        source = db.scalars(
            select(Source).where(Source.project_id == project.id)
        ).first()
        if not source:
            source = Source(
                project_id=project.id,
                source_type="local_git_repository",
                uri=str(project_root),
                read_only=True,
                enabled=True,
                config={},
            )
            db.add(source)
            db.flush()

        head_before = source.config.get("current_head")

        # 3. Initialize IngestionRun
        run = IngestionRun(
            project_id=project.id,
            source_id=source.id,
            status="RUNNING",
            started_at=utc_now(),
            head_before=head_before,
            errors=[],
            warnings=[],
            metadata_={"scanner_version": "0.1"},
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        git_client = GitClient(timeout_seconds=30)
        is_git = git_client.is_inside_worktree(project_root)

        branch = None
        current_head = None
        remotes = []
        commits = []
        relative_files = []

        if is_git:
            try:
                branch = git_client.get_branch(project_root)
                current_head = git_client.get_head(project_root)
                remotes = git_client.get_remotes(project_root)
                commits = git_client.get_commits(project_root, max_count=100)
                relative_files = git_client.ls_files(project_root)
            except GitClientError as e:
                run.warnings.append({"stage": "git_scan", "message": str(e)})

        # 4. Filesystem scan & sensitivity check
        valid_files = []
        sensitive_count = 0
        for rel_f in relative_files:
            file_info = scan_single_file(project_root, rel_f)
            if file_info is None:
                continue
            if file_info.is_sensitive:
                sensitive_count += 1
                continue
            valid_files.append(file_info)

        if sensitive_count > 0:
            run.warnings.append({
                "stage": "filesystem_scan",
                "message": f"Excluded {sensitive_count} sensitive files from ingestion.",
            })

        valid_file_paths = [f.relative_path for f in valid_files]
        directories = extract_directory_hierarchy(valid_file_paths)

        # 5. Manifests, Languages, Frameworks
        manifests = scan_all_manifests(project_root)
        pkg_manager, mgr_warnings = detect_package_manager(project_root)
        for w in mgr_warnings:
            run.warnings.append({"stage": "package_manager", "message": w})

        lang_stats = detect_languages(valid_file_paths)
        frameworks = detect_frameworks(project_root, manifests, valid_file_paths)

        # 6. Entity & Relation Upserting
        existing_entities = {
            e.entity_key: e
            for e in db.scalars(select(Entity).where(Entity.project_id == project.id)).all()
        }

        created_entities = 0
        updated_entities = 0
        created_relations = 0

        def upsert_entity(
            entity_type: str,
            entity_key: str,
            name: str,
            canonical_name: str,
            path: str | None = None,
            metadata: dict[str, Any] | None = None,
        ) -> Entity:
            nonlocal created_entities, updated_entities
            if entity_key in existing_entities:
                ent = existing_entities[entity_key]
                ent.name = name
                ent.canonical_name = canonical_name
                ent.path = path
                ent.status = "ACTIVE"
                if metadata:
                    ent.metadata_ = metadata
                updated_entities += 1
                return ent
            else:
                ent = Entity(
                    project_id=project.id,
                    entity_type=entity_type,
                    entity_key=entity_key,
                    name=name,
                    canonical_name=canonical_name,
                    path=path,
                    status="ACTIVE",
                    metadata_=metadata or {},
                )
                db.add(ent)
                db.flush()
                existing_entities[entity_key] = ent
                created_entities += 1
                return ent

        def upsert_relation(
            subj_id: uuid.UUID,
            predicate: str,
            obj_id: uuid.UUID,
            confidence: Decimal = Decimal("1.00000"),
            metadata: dict[str, Any] | None = None,
        ) -> Relation:
            nonlocal created_relations
            stmt = select(Relation).where(
                Relation.subject_entity_id == subj_id,
                Relation.predicate == predicate,
                Relation.object_entity_id == obj_id,
            )
            rel = db.scalars(stmt).first()
            if not rel:
                rel = Relation(
                    subject_entity_id=subj_id,
                    predicate=predicate,
                    object_entity_id=obj_id,
                    confidence=confidence,
                    source_id=source.id,
                    metadata_=metadata or {},
                )
                db.add(rel)
                db.flush()
                created_relations += 1
            else:
                rel.confidence = confidence
                if metadata:
                    rel.metadata_ = metadata
                db.flush()
            return rel

        # 6a. Project & Repository root entities
        p_key = project.key
        e_proj = upsert_entity(
            entity_type="PROJECT",
            entity_key=f"PROJECT:{p_key}",
            name=project.name,
            canonical_name=p_key,
            path=str(project_root),
            metadata={
                "role": project.role,
                "kind": project.kind,
                "primary_language": lang_stats.primary_language,
                "package_manager": pkg_manager,
                "head": current_head,
                "branch": branch,
            },
        )

        e_repo = upsert_entity(
            entity_type="REPOSITORY",
            entity_key=f"REPO:{p_key}",
            name=f"{project.name}_repo",
            canonical_name=f"{p_key}_REPO",
            path=str(project_root),
            metadata={"remotes": remotes, "is_git": is_git},
        )
        upsert_relation(e_proj.id, "contains", e_repo.id)

        # 6b. Branch Entity
        if branch:
            e_branch = upsert_entity(
                entity_type="BRANCH",
                entity_key=f"BRANCH:{p_key}:{branch}",
                name=branch,
                canonical_name=f"{p_key}_BRANCH_{branch}",
                metadata={"is_current": True},
            )
            upsert_relation(e_repo.id, "contains", e_branch.id)

        # 6c. Commit Entities (up to 100)
        for c in commits:
            e_commit = upsert_entity(
                entity_type="COMMIT",
                entity_key=f"COMMIT:{p_key}:{c['sha']}",
                name=c["sha"][:8],
                canonical_name=f"{p_key}_COMMIT_{c['sha'][:8]}",
                metadata={
                    "sha": c["sha"],
                    "parent_sha": c["parent_sha"],
                    "author_name": c["author_name"],
                    "author_email": c["author_email"],
                    "authored_at": c["authored_at"],
                    "subject": c["subject"],
                },
            )
            upsert_relation(e_repo.id, "contains", e_commit.id)

        # 6d. Directory Entities
        dir_entity_map: dict[str, Entity] = {}
        for d in directories:
            d_name = Path(d).name
            e_dir = upsert_entity(
                entity_type="DIRECTORY",
                entity_key=f"DIR:{p_key}:{d}",
                name=d_name,
                canonical_name=f"{p_key}_DIR_{d}",
                path=d,
            )
            dir_entity_map[d] = e_dir

            # Connect parent directory or repo
            parent_d = str(Path(d).parent).replace("\\", "/")
            if parent_d in dir_entity_map:
                upsert_relation(dir_entity_map[parent_d].id, "contains", e_dir.id)
            else:
                upsert_relation(e_repo.id, "contains", e_dir.id)

        # 6e. File Entities
        active_file_paths = set()
        files_created = 0
        files_updated = 0
        for f in valid_files:
            active_file_paths.add(f.relative_path)
            f_key = f"FILE:{p_key}:{f.relative_path}"
            is_new = f_key not in existing_entities

            e_file = upsert_entity(
                entity_type="FILE",
                entity_key=f_key,
                name=f.filename,
                canonical_name=f"{p_key}_FILE_{f.relative_path}",
                path=f.relative_path,
                metadata={
                    "size_bytes": f.size_bytes,
                    "extension": f.extension,
                    "sha256": f.sha256,
                    "hash_status": f.hash_status,
                    "is_binary": f.is_binary,
                    "mtime": f.mtime.isoformat(),
                },
            )
            if is_new:
                files_created += 1
            else:
                files_updated += 1

            # Connect directory or repo
            parent_d = str(Path(f.relative_path).parent).replace("\\", "/")
            if parent_d in dir_entity_map:
                upsert_relation(dir_entity_map[parent_d].id, "contains", e_file.id)
            else:
                upsert_relation(e_repo.id, "contains", e_file.id)

        # 6f. Soft delete vanished files (Section 32)
        files_deleted = 0
        for e_key, existing_ent in existing_entities.items():
            if existing_ent.entity_type == "FILE" and existing_ent.path not in active_file_paths:
                if existing_ent.status != "deleted":
                    existing_ent.status = "deleted"
                    files_deleted += 1

        # 6g. Language Entities
        for l in lang_stats.languages:
            e_lang = upsert_entity(
                entity_type="LANGUAGE",
                entity_key=f"LANG:{p_key}:{l['name']}",
                name=l["name"],
                canonical_name=f"{p_key}_LANG_{l['name']}",
                metadata={"file_count": l["file_count"], "percentage": l["percentage"]},
            )
            upsert_relation(e_proj.id, "uses", e_lang.id)

        # 6h. Framework Entities (with evidence)
        for fw in frameworks:
            e_fw = upsert_entity(
                entity_type="FRAMEWORK",
                entity_key=f"FRAMEWORK:{p_key}:{fw.name}",
                name=fw.name,
                canonical_name=f"{p_key}_FW_{fw.name}",
                metadata={
                    "confidence": fw.confidence,
                    "method": fw.method,
                    "evidence": fw.evidence,
                    "version": fw.version,
                },
            )
            upsert_relation(
                e_proj.id,
                "uses",
                e_fw.id,
                confidence=Decimal(str(fw.confidence)),
                metadata={"evidence": fw.evidence, "method": fw.method},
            )

        # 6i. Manifest Entities
        for m in manifests:
            e_man = upsert_entity(
                entity_type="MANIFEST",
                entity_key=f"MANIFEST:{p_key}:{m.relative_path}",
                name=Path(m.relative_path).name,
                canonical_name=f"{p_key}_MANIFEST_{m.relative_path}",
                path=m.relative_path,
                metadata={
                    "manifest_type": m.manifest_type,
                    "package_manager": m.package_manager,
                    "raw": m.raw_metadata,
                },
            )
            upsert_relation(e_proj.id, "contains", e_man.id)

        # 6j. Dependency Entities
        total_deps = 0
        for m in manifests:
            for dep in m.dependencies:
                total_deps += 1
                dep_key = f"DEP:{p_key}:{dep.ecosystem}:{dep.name}"
                e_dep = upsert_entity(
                    entity_type="DEPENDENCY",
                    entity_key=dep_key,
                    name=dep.name,
                    canonical_name=f"{p_key}_DEP_{dep.name}",
                    metadata={
                        "version_spec": dep.version_spec,
                        "ecosystem": dep.ecosystem,
                        "scope": dep.scope,
                        "is_direct": dep.is_direct,
                        "manifest_path": dep.manifest_path,
                    },
                )
                upsert_relation(
                    e_proj.id,
                    "depends_on",
                    e_dep.id,
                    confidence=Decimal("1.00000"),
                    metadata={"manifest": dep.manifest_path, "scope": dep.scope},
                )

        # 7. Update Source config & last_scan_at
        source.last_scan_at = utc_now()
        source.config = {
            "current_head": current_head,
            "branch": branch,
            "package_manager": pkg_manager,
            "primary_language": lang_stats.primary_language,
            "file_count": len(valid_files),
        }

        # 8. Create ProjectSnapshot (Section 30)
        snapshot = ProjectSnapshot(
            project_id=project.id,
            ingestion_run_id=run.id,
            head=current_head,
            branch=branch,
            file_count=len(valid_files),
            directory_count=len(directories),
            dependency_count=total_deps,
            frameworks=[
                {"name": fw.name, "confidence": fw.confidence, "version": fw.version, "evidence": fw.evidence}
                for fw in frameworks
            ],
            languages=lang_stats.languages,
            metadata_={"package_manager": pkg_manager},
            created_at=utc_now(),
        )
        db.add(snapshot)

        # 9. Finalize IngestionRun
        run.head_after = current_head
        run.files_seen = len(valid_files)
        run.files_created = files_created
        run.files_updated = files_updated
        run.files_deleted = files_deleted
        run.entities_created = created_entities
        run.entities_updated = updated_entities
        run.relations_created = created_relations
        run.finished_at = utc_now()
        run.status = "COMPLETED"

        db.commit()
        db.refresh(run)
        return run

    except Exception as e:
        db.rollback()
        # Record failure run if possible
        try:
            with SessionLocal() as err_sess:
                err_run = IngestionRun(
                    project_id=project.id if "project" in locals() and project else uuid.uuid4(),
                    source_id=source.id if "source" in locals() and source else None,
                    status="FAILED",
                    started_at=utc_now(),
                    finished_at=utc_now(),
                    errors=[{"error": str(e), "type": type(e).__name__}],
                )
                err_sess.add(err_run)
                err_sess.commit()
        except Exception:
            pass
        raise e
    finally:
        if should_close_session:
            db.close()


def run_all_projects_ingestion() -> dict[str, Any]:
    """Runs ingestion across all registered projects with partial failure isolation."""
    summary = {
        "total": 0,
        "succeeded": 0,
        "failed": 0,
        "runs": {},
        "status": "COMPLETED",
    }

    with SessionLocal() as db:
        projects = db.scalars(select(Project).where(Project.status == "ACTIVE")).all()
        summary["total"] = len(projects)

        for p in projects:
            try:
                run = run_project_ingestion(p.key)
                summary["succeeded"] += 1
                summary["runs"][p.key] = {
                    "status": run.status,
                    "files_seen": run.files_seen,
                    "entities_created": run.entities_created,
                    "relations_created": run.relations_created,
                    "duration_s": (run.finished_at - run.started_at).total_seconds() if run.finished_at else 0,
                }
            except Exception as e:
                summary["failed"] += 1
                summary["runs"][p.key] = {
                    "status": "FAILED",
                    "error": str(e),
                }

    if summary["failed"] > 0:
        summary["status"] = "PARTIAL" if summary["succeeded"] > 0 else "FAILED"

    return summary

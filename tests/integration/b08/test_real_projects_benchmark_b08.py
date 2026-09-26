"""B-08 Layer 4 Tests: Real Projects Performance & Throughput Baseline (Gate O)
Validates:
- Gate O: Measures end-to-end extraction + persistence throughput on 75 real production files across all 3 repos.
"""

from pathlib import Path
import statistics
import time
import uuid

import pytest
from sqlalchemy.orm import Session

from core.extraction.orchestrator import SymbolExtractionOrchestrator
from core.models.entity import Entity
from core.models.project import Project
from ingestion.symbols import SymbolPersistenceService
from tests.integration.b08.conftest import REPOS, discover_supported_files


@pytest.fixture
def service() -> SymbolPersistenceService:
    return SymbolPersistenceService()


def create_file_entity(project: Project, rel_path: str) -> Entity:
    norm = rel_path.replace("\\", "/")
    return Entity(
        id=uuid.uuid4(),
        project_id=project.id,
        entity_type="FILE",
        entity_key=f"FILE:{project.key}:{norm}",
        name=Path(norm).name,
        canonical_name=f"{project.key}_FILE_{Path(norm).stem}",
        path=norm,
        status="ACTIVE",
        metadata_={},
    )


def test_gate_o_real_projects_performance_benchmark(b08_db: Session, b08_projects: dict[str, Project], service: SymbolPersistenceService):
    """Gate O (LOCK-VERIFY-06): Real-world end-to-end benchmark across 75 real files (25 HELLO_BE, 25 HELLO_FE, 25 L2C_FE)."""
    samples = []
    # 25 files from each repo
    for key, count in [("HELLO_BE", 25), ("HELLO_FE", 25), ("L2C_FE", 25)]:
        files = discover_supported_files(REPOS[key])[:count]
        proj = b08_projects[key]
        for f in files:
            rel = f.relative_to(REPOS[key]).as_posix()
            fe = create_file_entity(proj, rel)
            b08_db.add(fe)
            samples.append((proj, fe, f.read_bytes()))
    b08_db.commit()

    total_files = len(samples)
    assert total_files == 75

    file_latencies_ms = []
    total_symbols = 0

    batch_start = time.perf_counter()
    for proj, fe, code in samples:
        t0 = time.perf_counter()
        res = service.sync_file_symbols(
            db=b08_db,
            project_id=proj.id,
            project_key=proj.key,
            file_entity=fe,
            code_bytes=code,
        )
        dt_ms = (time.perf_counter() - t0) * 1000.0
        file_latencies_ms.append(dt_ms)
        total_symbols += res["created"]
    b08_db.commit()
    total_elapsed_ms = (time.perf_counter() - batch_start) * 1000.0

    mean_ms = statistics.mean(file_latencies_ms)
    median_ms = statistics.median(file_latencies_ms)
    p95_ms = statistics.quantiles(file_latencies_ms, n=20)[18] if len(file_latencies_ms) >= 20 else max(file_latencies_ms)
    throughput_fps = total_files / (total_elapsed_ms / 1000.0)
    throughput_sps = total_symbols / (total_elapsed_ms / 1000.0)

    print(
        f"\n[Gate O Real Benchmark Baseline] "
        f"Files={total_files}, Symbols={total_symbols}, "
        f"Total={total_elapsed_ms:.2f}ms, Mean={mean_ms:.2f}ms, "
        f"Median={median_ms:.2f}ms, P95={p95_ms:.2f}ms, "
        f"Throughput={throughput_fps:.1f} files/s ({throughput_sps:.1f} symbols/s)"
    )

    assert total_symbols > 100
    assert mean_ms < 50.0  # Safe threshold on developer machines
    assert throughput_fps > 20.0

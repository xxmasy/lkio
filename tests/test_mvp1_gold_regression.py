"""LKIO MVP1 - Gold Set Regression Suite
Loads the established Gold Set standards in tests/gold/mvp1/ and validates that the Knowledge Core snapshots meet all baseline criteria.
"""

import json
from pathlib import Path
import pytest
from sqlalchemy import select
from core.db.session import SessionLocal
from core.models.project import Project
from core.models.project_snapshot import ProjectSnapshot

GOLD_DIR = Path(__file__).resolve().parent / "gold" / "mvp1"


@pytest.mark.parametrize("gold_filename", ["HELLO_FE.json", "HELLO_BE.json", "L2C_FE.json"])
def test_project_against_gold_standard(gold_filename: str):
    gold_path = GOLD_DIR / gold_filename
    assert gold_path.exists(), f"Gold file missing: {gold_path}"

    with open(gold_path, "r", encoding="utf-8") as f:
        gold = json.load(f)

    p_key = gold["project_key"]

    with SessionLocal() as db:
        project = db.scalars(select(Project).where(Project.key == p_key)).first()
        assert project is not None, f"Project '{p_key}' not found in database"
        assert project.kind == gold["kind"]
        assert project.role == gold["role"]

        snapshot = db.scalars(
            select(ProjectSnapshot)
            .where(ProjectSnapshot.project_id == project.id)
            .order_by(ProjectSnapshot.created_at.desc())
        ).first()
        assert snapshot is not None, f"No snapshot recorded for project '{p_key}'"

        # 1. Branch verification
        if gold["git"]["branch"]:
            assert snapshot.branch == gold["git"]["branch"]

        # 2. File & Directory counts
        assert snapshot.file_count >= gold["min_file_count"], (
            f"File count {snapshot.file_count} below gold threshold {gold['min_file_count']}"
        )
        assert snapshot.directory_count >= gold["min_directory_count"]
        assert snapshot.dependency_count >= gold["min_dependency_count"]

        # 3. Framework detection
        detected_fws = {fw["name"] for fw in snapshot.frameworks}
        for exp_fw in gold["expected_frameworks"]:
            assert exp_fw in detected_fws, f"Expected framework '{exp_fw}' not detected in {p_key}"

        # 4. Language detection
        detected_langs = {l["name"] for l in snapshot.languages}
        for exp_lang in gold["expected_languages"]:
            assert exp_lang in detected_langs, f"Expected language '{exp_lang}' not detected in {p_key}"

        # 5. Package manager
        assert snapshot.metadata_.get("package_manager") == gold["package_manager"]

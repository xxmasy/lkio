"""Unit tests for GitChangeExtractor in core/events/git_extractor.py
"""

from datetime import datetime
from pathlib import Path
from core.events.git_extractor import GitChangeExtractor
from core.events.models import ChangeType


def test_parse_numstat_output():
    extractor = GitChangeExtractor()
    sample_output = """
COMMIT_RECORD\x1fsha123
10\t5\tsrc/main/App.java
-\t-\tdocs/logo.png

COMMIT_RECORD\x1fsha456
0\t40\tsrc/utils.js
"""
    result = extractor._parse_numstat_output(sample_output)
    assert "sha123" in result
    assert result["sha123"]["src/main/App.java"] == (10, 5)
    assert result["sha123"]["docs/logo.png"] == (0, 0)
    assert result["sha456"]["src/utils.js"] == (0, 40)


def test_parse_status_output():
    extractor = GitChangeExtractor()
    status_output = """
COMMIT_RECORD\x1fsha123\x1fparent000\x1fAlice Dev\x1falice@example.com\x1f2026-09-25T10:00:00+00:00\x1ffeat: initial commit
A\tsrc/main/App.java
M\tsrc/utils.js
R100\told/path.ts\tnew/path.ts
D\tdeleted.txt
"""
    numstat_map = {
        "sha123": {
            "src/main/App.java": (100, 0),
            "src/utils.js": (5, 2),
            "new/path.ts": (1, 1),
            "deleted.txt": (0, 50),
        }
    }
    commits = extractor._parse_status_output(status_output, numstat_map)
    assert len(commits) == 1
    c = commits[0]
    assert c.sha == "sha123"
    assert c.author_name == "Alice Dev"
    assert c.author_email == "alice@example.com"
    assert c.message == "feat: initial commit"
    assert len(c.changed_files) == 4

    # File 0: App.java (Added)
    assert c.changed_files[0].file_path == "src/main/App.java"
    assert c.changed_files[0].change_type == ChangeType.ADDED
    assert c.changed_files[0].insertions == 100

    # File 1: utils.js (Modified)
    assert c.changed_files[1].file_path == "src/utils.js"
    assert c.changed_files[1].change_type == ChangeType.MODIFIED
    assert c.changed_files[1].insertions == 5
    assert c.changed_files[1].deletions == 2

    # File 2: new/path.ts (Renamed)
    assert c.changed_files[2].change_type == ChangeType.RENAMED
    assert c.changed_files[2].old_path == "old/path.ts"
    assert c.changed_files[2].file_path == "new/path.ts"

    # File 3: deleted.txt (Deleted)
    assert c.changed_files[3].change_type == ChangeType.DELETED
    assert c.changed_files[3].deletions == 50

    assert c.total_insertions == 106
    assert c.total_deletions == 53


def test_real_repo_smoke_read_only():
    """Validates real extraction on local repository without writing any files."""
    extractor = GitChangeExtractor()
    repo_path = Path("c:/WorkSpace/hello")
    if repo_path.exists():
        commits = extractor.extract_commits(repo_path, max_commits=3)
        assert len(commits) > 0
        for c in commits:
            assert len(c.sha) == 40
            assert len(c.author_email) > 0
            assert isinstance(c.authored_at, datetime)

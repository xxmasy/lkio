"""Unit tests for LKIO Local Subagent Engine.
Validates model detection, deterministic fallback, token compression calculations,
and live cache generation.
"""

from pathlib import Path
import pytest
from core.subagent.local_agent import LocalBriefingResult, LocalLLMSubagent


def test_local_subagent_deterministic_synthesis(tmp_path):
    # Test with offline Ollama fallback to verify 100% reliability
    agent = LocalLLMSubagent(ollama_url="http://127.0.0.1:99999", timeout=1)

    mock_status = {
        "repo_id": "test_repo",
        "behind_count": 5,
        "new_remote_commits": [
            {"author": "Alice", "message": "feat(api): update user dto", "short_sha": "a1b2c3d4"},
            {"author": "Bob", "message": "fix(db): add user index", "short_sha": "e5f6g7h8"},
        ],
        "impact_summary": {
            "modified_controllers": ["src/UserController.java"],
            "modified_dtos": ["src/UserDTO.java"],
            "modified_sql_scripts": ["sql/user.sql"],
            "potential_breaking_changes": ["Detected 1 DTO and 1 SQL changes."],
        },
    }

    res = agent.synthesize_repo_briefing("test_repo", mock_status)
    assert res.repo_id == "test_repo"
    assert res.token_compressed_ratio > 0
    assert "UserDTO.java" in res.briefing_markdown or "DTO" in res.briefing_markdown
    assert "Alice" in res.briefing_markdown or "5" in res.briefing_markdown


def test_local_subagent_synced_state():
    agent = LocalLLMSubagent()
    mock_status = {"repo_id": "test_repo", "behind_count": 0, "new_remote_commits": []}
    res = agent.synthesize_repo_briefing("test_repo", mock_status)
    assert "已完全与远端同步" in res.briefing_markdown
    assert res.token_compressed_ratio == 1.0


def test_local_subagent_cache_writing(tmp_path):
    agent = LocalLLMSubagent()
    cache_file = tmp_path / "test_briefing.md"
    results = {
        "repo_a": LocalBriefingResult(
            repo_id="repo_a",
            model_used="qwen2.5:0.5b",
            latency_ms=12.5,
            token_compressed_ratio=98.2,
            briefing_markdown="Briefing for repo A",
        )
    }

    agent.write_live_briefing_cache(results, dest_paths=[cache_file])
    assert cache_file.exists()
    content = cache_file.read_text(encoding="utf-8")
    assert "Briefing for repo A" in content
    assert "98.2%" in content


def test_token_savings_ledger_audit(tmp_path):
    from core.subagent.token_ledger import TokenSavingsLedger

    ledger_file = tmp_path / "ledger.json"
    report_file = tmp_path / "report.md"
    ledger = TokenSavingsLedger(ledger_path=ledger_file, report_path=report_file)

    rec = ledger.record_run(
        repo_id="backend",
        trigger_source="TEST_SUITE",
        commits_detected=10,
        files_modified=25,
        raw_tokens_avoided=5000,
        distilled_tokens_used=100,
        model_used="qwen2.5:0.5b",
        latency_ms=85.0,
        briefing_text="Test summary",
    )

    assert rec.tokens_saved == 4900
    assert rec.compression_ratio_pct == 98.0
    assert rec.cost_saved_usd > 0

    summary = ledger.get_summary()
    assert summary["cumulative"]["total_runs"] == 1
    assert summary["cumulative"]["total_tokens_saved"] == 4900

    report_text = report_file.read_text(encoding="utf-8")
    assert "4,900" in report_text
    assert "TEST_SUITE" in report_text

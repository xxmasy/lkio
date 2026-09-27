"""Audit Evidence Recorder.

Captures immutable, machine-verifiable proof of test executions, exit codes,
environment metadata, Git commit hashes, and dataset checksums.
Outputs: docs/infrastructure/gate_audit_records.json
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys


def compute_file_sha256(path: Path) -> str:
    if not path.exists():
        return "NOT_FOUND"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_gate_command(command: list[str]) -> dict:
    t0 = datetime.now(timezone.utc).isoformat()
    res = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    t1 = datetime.now(timezone.utc).isoformat()

    return {
        "command": " ".join(command),
        "start_time": t0,
        "end_time": t1,
        "exit_code": res.returncode,
        "stdout": res.stdout,
        "stderr": res.stderr,
    }


def main():
    root_dir = Path(__file__).resolve().parent.parent

    # Git commit hash
    git_res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
    git_commit = git_res.stdout.strip() if git_res.returncode == 0 else "UNKNOWN"

    env_meta = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "git_commit": git_commit,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    manifest_hashes = {
        "baseline_v1_metrics": compute_file_sha256(root_dir / "benchmarks/baseline_v1/metrics.json"),
        "baseline_v1_readme": compute_file_sha256(root_dir / "benchmarks/baseline_v1/README.md"),
    }

    # Run verification suites
    print("Recording Unit & Integration Test Suite evidence...")
    test_run = run_gate_command(["uv", "run", "pytest", "tests/unit", "tests/integration", "-q"])

    print("Recording Stage 1 Independent Oracle evidence...")
    oracle_run = run_gate_command(["uv", "run", "pytest", "tests/unit/stage1/test_stage1_independent_oracle.py", "-q"])

    print("Recording Stage 2 Multi-Repo & Ambiguity evidence...")
    multirepo_run = run_gate_command(["uv", "run", "pytest", "tests/unit/stage2/test_stage2_multirepo.py", "-q"])

    print("Recording Stage 3 MCP infrastructure evidence...")
    mcp_run = run_gate_command(["uv", "run", "pytest", "tests/unit/stage3/test_stage3_mcp.py", "-q"])

    print("Recording Stage 4 Governance Adversarial Stress evidence...")
    gov_stress_run = run_gate_command(["uv", "run", "pytest", "tests/unit/stage4/test_governance_adversarial_stress.py", "-q"])

    audit_payload = {
        "schema_version": "1.0.0",
        "description": "LKIO Machine-Verifiable Gate Audit Records",
        "environment": env_meta,
        "dataset_checksums": manifest_hashes,
        "gate_records": {
            "all_tests_regression_suite": {
                "status": "PASSED" if test_run["exit_code"] == 0 else "FAILED",
                "details": test_run,
            },
            "gate1_independent_oracle": {
                "status": "PASSED" if oracle_run["exit_code"] == 0 else "FAILED",
                "details": oracle_run,
            },
            "gate2_multirepo_ambiguity": {
                "status": "PASSED" if multirepo_run["exit_code"] == 0 else "FAILED",
                "details": multirepo_run,
            },
            "gate3_mcp_infrastructure": {
                "status": "PASSED" if mcp_run["exit_code"] == 0 else "FAILED",
                "details": mcp_run,
            },
            "gate4_governance_adversarial_stress": {
                "status": "PASSED" if gov_stress_run["exit_code"] == 0 else "FAILED",
                "details": gov_stress_run,
            },
        },
    }

    out_file = root_dir / "docs/infrastructure/gate_audit_records.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(audit_payload, f, indent=2, ensure_ascii=False)

    print(f"Audit record successfully written to {out_file}")


if __name__ == "__main__":
    main()

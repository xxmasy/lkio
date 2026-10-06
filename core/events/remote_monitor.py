"""GitLab Remote Commit & Change Intelligence Monitor for LKIO.

Monitors remote GitLab repositories (e.g. frontend and backend services)
without modifying local uncommitted developer drafts.
Provides:
1. Read-only auto-fetch tracking (`git fetch origin`).
2. Commit divergence detection (local HEAD vs origin/<branch>).
3. Commit metadata extraction (author, message, changed files, insertions/deletions).
4. Cross-repository impact & breaking change identification.
5. Continuous background polling daemon and Cursor MCP query integration.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Dict, List, Optional

from core.events.git_extractor import GitChangeExtractor
from core.events.models import CommitEventDTO

logger = logging.getLogger("lkio.remote_monitor")


@dataclass
class CommitSummary:
    sha: str
    short_sha: str
    author: str
    message: str
    date: str
    changed_files_count: int
    files: List[str] = field(default_factory=list)


@dataclass
class RepoSyncStatus:
    repo_id: str
    repo_path: str
    current_branch: str
    tracking_branch: str
    local_sha: str
    remote_sha: str
    is_synced: bool
    behind_count: int
    ahead_count: int
    new_remote_commits: List[CommitSummary] = field(default_factory=list)
    impact_summary: Dict[str, Any] = field(default_factory=dict)
    last_checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: Optional[str] = None


class GitRemoteMonitor:
    """Monitors remote GitLab repositories and provides commit intelligence."""

    DEFAULT_WORKSPACE = Path(os.environ.get("LKIO_WORKSPACE", Path.cwd().parent if Path.cwd().name == "lkio" else Path.cwd()))
    DEFAULT_REPOS = {
        "frontend": Path(os.environ.get("LKIO_FRONTEND_PATH", DEFAULT_WORKSPACE / "hello")),
        "backend": Path(os.environ.get("LKIO_BACKEND_PATH", DEFAULT_WORKSPACE / "hello-backend")),
    }

    def __init__(
        self,
        repos: Optional[Dict[str, Path]] = None,
        feed_path: Optional[Path] = None,
    ):
        self.repos = repos or dict(self.DEFAULT_REPOS)
        self.feed_path = feed_path or (self.DEFAULT_WORKSPACE / "lkio-data" / "remote_commits_feed.json")
        self.git_extractor = GitChangeExtractor()

    def _run_git(self, repo_path: Path, args: List[str], timeout: int = 45) -> str:
        cmd = ["git", "-c", "core.quotepath=false", "-C", str(repo_path)] + args
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if res.returncode != 0:
            raise RuntimeError(f"Git command failed: {' '.join(cmd)}\nStderr: {res.stderr.strip()}")
        return res.stdout.strip()

    def fetch_remote(self, repo_path: Path, remote: str = "origin") -> bool:
        """Runs read-only fetch to update remote tracking refs without touching working tree."""
        try:
            self._run_git(repo_path, ["fetch", remote], timeout=60)
            return True
        except Exception as e:
            logger.warning("Failed to fetch %s: %s", repo_path, e)
            return False

    def inspect_repo(
        self,
        repo_id: str,
        repo_path: Path,
        fetch: bool = True,
        limit_commits: int = 15,
    ) -> RepoSyncStatus:
        """Inspects single repo divergence against remote GitLab tracking branch."""
        if not repo_path.exists():
            return RepoSyncStatus(
                repo_id=repo_id,
                repo_path=str(repo_path),
                current_branch="unknown",
                tracking_branch="unknown",
                local_sha="",
                remote_sha="",
                is_synced=False,
                behind_count=0,
                ahead_count=0,
                error=f"Repository path does not exist: {repo_path}",
            )

        try:
            current_branch = self._run_git(repo_path, ["branch", "--show-current"]) or "prod"
            tracking_branch = f"origin/{current_branch}"

            if fetch:
                self.fetch_remote(repo_path, "origin")

            local_sha = self._run_git(repo_path, ["rev-parse", "HEAD"])
            remote_sha = self._run_git(repo_path, ["rev-parse", tracking_branch])

            # Check behind / ahead counts
            rev_counts = self._run_git(
                repo_path, ["rev-list", "--left-right", "--count", f"HEAD...{tracking_branch}"]
            )
            parts = rev_counts.split()
            ahead_count = int(parts[0]) if len(parts) >= 1 else 0
            behind_count = int(parts[1]) if len(parts) >= 2 else 0

            new_commits: List[CommitSummary] = []
            impact_summary: Dict[str, Any] = {
                "modified_controllers": [],
                "modified_services": [],
                "modified_dtos": [],
                "modified_vue_components": [],
                "modified_sql_scripts": [],
                "potential_breaking_changes": [],
            }

            if behind_count > 0:
                # Extract commit details from local_sha..tracking_branch
                raw_commits = self.git_extractor.extract_commits(
                    repo_path,
                    max_commits=limit_commits,
                    since_sha=local_sha,
                    until_ref=tracking_branch,
                )

                for c in raw_commits:
                    files = [f.file_path for f in c.changed_files]
                    new_commits.append(
                        CommitSummary(
                            sha=c.sha,
                            short_sha=c.sha[:8],
                            author=c.author_name,
                            message=c.message.strip(),
                            date=c.authored_at.isoformat(),
                            changed_files_count=len(files),
                            files=files,
                        )
                    )

                    # Categorize impact
                    for fp in files:
                        fp_lower = fp.lower()
                        if "controller" in fp_lower and fp not in impact_summary["modified_controllers"]:
                            impact_summary["modified_controllers"].append(fp)
                        elif "service" in fp_lower and fp not in impact_summary["modified_services"]:
                            impact_summary["modified_services"].append(fp)
                        elif "dto" in fp_lower and fp not in impact_summary["modified_dtos"]:
                            impact_summary["modified_dtos"].append(fp)
                        elif fp_lower.endswith(".vue") and fp not in impact_summary["modified_vue_components"]:
                            impact_summary["modified_vue_components"].append(fp)
                        elif fp_lower.endswith(".sql") and fp not in impact_summary["modified_sql_scripts"]:
                            impact_summary["modified_sql_scripts"].append(fp)

                # Heuristic breaking change detection
                if impact_summary["modified_dtos"] or impact_summary["modified_sql_scripts"]:
                    impact_summary["potential_breaking_changes"].append(
                        f"Detected {len(impact_summary['modified_dtos'])} DTO and {len(impact_summary['modified_sql_scripts'])} SQL changes that may affect API contracts or persistence."
                    )

            return RepoSyncStatus(
                repo_id=repo_id,
                repo_path=str(repo_path),
                current_branch=current_branch,
                tracking_branch=tracking_branch,
                local_sha=local_sha[:8],
                remote_sha=remote_sha[:8],
                is_synced=(behind_count == 0),
                behind_count=behind_count,
                ahead_count=ahead_count,
                new_remote_commits=new_commits,
                impact_summary=impact_summary,
            )

        except Exception as e:
            return RepoSyncStatus(
                repo_id=repo_id,
                repo_path=str(repo_path),
                current_branch="unknown",
                tracking_branch="unknown",
                local_sha="",
                remote_sha="",
                is_synced=False,
                behind_count=0,
                ahead_count=0,
                error=str(e),
            )

    def check_all(self, fetch: bool = True, limit_commits: int = 15) -> Dict[str, RepoSyncStatus]:
        """Checks status of all watched repositories."""
        results: Dict[str, RepoSyncStatus] = {}
        for repo_id, repo_path in self.repos.items():
            results[repo_id] = self.inspect_repo(repo_id, repo_path, fetch=fetch, limit_commits=limit_commits)

        # Write to persistent feed
        try:
            self.feed_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.feed_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "statuses": {k: asdict(v) for k, v in results.items()},
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as e:
            logger.warning("Failed to save remote feed to %s: %s", self.feed_path, e)

        # Autonomous Local-LLM Subagent Briefing Generation
        try:
            from core.subagent.local_agent import LocalLLMSubagent

            subagent = LocalLLMSubagent()
            briefings = {}
            for rid, status in results.items():
                if status.behind_count > 0:
                    brief_res = subagent.synthesize_repo_briefing(rid, asdict(status))
                    briefings[rid] = brief_res
            if briefings:
                subagent.write_live_briefing_cache(briefings)
        except Exception as e:
            logger.debug("Local subagent briefing generation skipped: %s", e)

        return results

    def watch_forever(self, interval_seconds: int = 60) -> None:
        """Continuous polling daemon logging new remote commits."""
        print(f"[LKIO GitLab Monitor] Starting continuous watcher (poll interval: {interval_seconds}s)...")
        print(f"[LKIO GitLab Monitor] Watching repositories: {list(self.repos.keys())}")
        print(f"[LKIO GitLab Monitor] Feed destination: {self.feed_path}")

        while True:
            t0 = time.time()
            try:
                statuses = self.check_all(fetch=True)
                for repo_id, status in statuses.items():
                    if status.error:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] [{repo_id}] Error: {status.error}")
                    elif not status.is_synced:
                        print(
                            f"[{datetime.now().strftime('%H:%M:%S')}] 🔔 [{repo_id}] Behind remote by {status.behind_count} commits! "
                            f"(Local {status.local_sha} -> Remote {status.remote_sha})"
                        )
                        for c in status.new_remote_commits[:3]:
                            print(f"    * [{c.short_sha}] {c.author}: {c.message[:60]}")
                        if status.impact_summary.get("potential_breaking_changes"):
                            print(f"    ⚠️  Impact Warning: {status.impact_summary['potential_breaking_changes'][0]}")
                    else:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] [{repo_id}] Synced at {status.local_sha}.")
            except Exception as e:
                print(f"[LKIO GitLab Monitor] Exception during polling cycle: {e}")

            elapsed = time.time() - t0
            sleep_time = max(5, interval_seconds - elapsed)
            time.sleep(sleep_time)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="LKIO GitLab Remote Monitor")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run single inspection and exit")
    parser.add_argument("--no-fetch", action="store_true", help="Skip remote git fetch")
    args = parser.parse_args()

    monitor = GitRemoteMonitor()
    if args.once:
        statuses = monitor.check_all(fetch=not args.no_fetch)
        print(json.dumps({k: asdict(v) for k, v in statuses.items()}, indent=2, ensure_ascii=False))
    else:
        monitor.watch_forever(interval_seconds=args.interval)


if __name__ == "__main__":
    main()

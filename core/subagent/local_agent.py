"""LKIO Local Subagent Engine.

Acts as an autonomous, edge-local subagent utilizing Local LLMs (Ollama)
to process heavy raw Git changes and AST diffs locally without expending Cloud LLM tokens.
Compresses multi-thousand token raw diffs into ultra-dense 150-token briefings for Cursor IDE.
"""

from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)


@dataclass
class LocalBriefingResult:
    repo_id: str
    model_used: str
    latency_ms: float
    token_compressed_ratio: float
    briefing_markdown: str


class LocalLLMSubagent:
    """Autonomous local subagent delegating repository reasoning to local Ollama models."""

    DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
    PREFERRED_MODELS = ["qwen2.5vl:7b", "qwen2.5:0.5b", "qwen2.5vl-tools:latest"]

    def __init__(
        self,
        ollama_url: str = DEFAULT_OLLAMA_URL,
        preferred_model: Optional[str] = None,
        timeout: int = 25,
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.timeout = timeout
        self._active_model: Optional[str] = preferred_model

    def detect_active_model(self) -> Optional[str]:
        """Detects available models on local Ollama instance."""
        if self._active_model:
            return self._active_model

        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                installed = [m.get("name", "") for m in data.get("models", [])]

                for candidate in self.PREFERRED_MODELS:
                    for m in installed:
                        if candidate in m:
                            self._active_model = m
                            return m

                if installed:
                    self._active_model = installed[0]
                    return installed[0]
        except Exception as e:
            logger.debug("Ollama model detection skipped or failed: %s", e)

        return None

    def synthesize_repo_briefing(
        self,
        repo_id: str,
        status_data: Dict[str, Any],
        trigger_source: str = "DAEMON_WATCHER",
    ) -> LocalBriefingResult:
        """Synthesizes raw commit telemetry into a high-density executive briefing via Local LLM."""
        t0 = time.perf_counter()
        model = self.detect_active_model()
        behind_count = status_data.get("behind_count", 0)
        commits = status_data.get("new_remote_commits", [])
        impact = status_data.get("impact_summary", {})

        if behind_count == 0:
            latency = (time.perf_counter() - t0) * 1000
            return LocalBriefingResult(
                repo_id=repo_id,
                model_used="deterministic",
                latency_ms=round(latency, 2),
                token_compressed_ratio=1.0,
                briefing_markdown=f"**[{repo_id.upper()}]** 已完全与远端同步，无新提交。",
            )

        # Deterministic extraction of key elements
        authors = list(dict.fromkeys(c.get("author", "Unknown") for c in commits))
        controllers = impact.get("modified_controllers", [])
        services = impact.get("modified_services", [])
        dtos = impact.get("modified_dtos", [])
        sqls = impact.get("modified_sql_scripts", [])

        # Estimate raw token count of full commit log + file lists
        raw_text_repr = json.dumps(status_data, ensure_ascii=False)
        estimated_raw_tokens = max(len(raw_text_repr) // 3, 100)

        briefing_text = ""
        used_model_name = "deterministic_fallback"

        if model:
            prompt = (
                f"你是 LKIO 本地代码协同子代理。以下是远端 GitLab [{repo_id}] 仓库最新合并的提交摘要：\n"
                f"- 落后提交数: {behind_count} 个 commits\n"
                f"- 主要提交人: {', '.join(authors[:4])}\n"
                f"- 涉及 Controller: {', '.join(c.split('/')[-1] for c in controllers[:5]) or '无'}\n"
                f"- 涉及 DTO/契约: {', '.join(d.split('/')[-1] for d in dtos[:5]) or '无'}\n"
                f"- 涉及 SQL 脚本: {', '.join(s.split('/')[-1] for s in sqls[:3]) or '无'}\n"
                f"- 重点提交信息: {'; '.join(c.get('message', '')[:40] for c in commits[:4])}\n\n"
                "请为正在开发前端的工程师生成一份 100 字以内的 Markdown 【精简技术简报】：\n"
                "1. 核心业务变更概括\n"
                "2. 是否存在 DTO 或接口改动风险\n"
                "3. 本地拉取建议（如：可安全快进拉取 / 需核对接口）"
            )

            try:
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2, "top_p": 0.8},
                }
                req = urllib.request.Request(
                    f"{self.ollama_url}/api/generate",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    briefing_text = res_json.get("response", "").strip()
                    used_model_name = model
            except Exception as e:
                logger.warning("Local LLM generation failed, falling back to deterministic template: %s", e)

        # High-quality deterministic fallback if LLM is offline or timed out
        if not briefing_text:
            risk = "高危（包含 DTO 或数据库改动）" if (dtos or sqls) else "低危（业务逻辑调整）"
            briefing_text = (
                f"**[{repo_id.upper()} 远端新变动]** 落后 {behind_count} 个提交（提交人: {', '.join(authors[:3])}）。\n"
                f"- **涉及关键层**: {len(controllers)} 个 Controller, {len(dtos)} 个 DTO, {len(sqls)} 个 SQL 脚本。\n"
                f"- **风险定级**: {risk}。\n"
                f"- **协同建议**: {'涉及 API 契约与 SQL，拉取前请检查接口字段兼容性。' if dtos else '无契约破坏，建议 git pull --ff-only 合并。'}"
            )

        latency = (time.perf_counter() - t0) * 1000
        distilled_tokens = max(len(briefing_text) // 3, 20)
        compression_ratio = round((1.0 - (distilled_tokens / estimated_raw_tokens)) * 100, 1)

        # Record into TokenSavingsLedger for the 3-day trial audit
        try:
            from core.subagent.token_ledger import TokenSavingsLedger

            ledger = TokenSavingsLedger()
            files_count = sum(c.get("changed_files_count", len(c.get("files", []))) for c in commits)
            if files_count == 0 and status_data.get("impact_summary"):
                imp = status_data["impact_summary"]
                files_count = len(
                    set(
                        imp.get("modified_controllers", [])
                        + imp.get("modified_services", [])
                        + imp.get("modified_dtos", [])
                        + imp.get("modified_sql_scripts", [])
                    )
                )
            ledger.record_run(
                repo_id=repo_id,
                trigger_source=trigger_source,
                commits_detected=behind_count,
                files_modified=max(files_count, behind_count),
                raw_tokens_avoided=estimated_raw_tokens,
                distilled_tokens_used=distilled_tokens,
                model_used=used_model_name,
                latency_ms=latency,
                briefing_text=briefing_text,
            )
        except Exception as e:
            logger.debug("Failed to record run to token savings ledger: %s", e)

        return LocalBriefingResult(
            repo_id=repo_id,
            model_used=used_model_name,
            latency_ms=round(latency, 2),
            token_compressed_ratio=max(compression_ratio, 0.0),
            briefing_markdown=briefing_text,
        )

    def write_live_briefing_cache(
        self,
        results: Dict[str, LocalBriefingResult],
        dest_paths: Optional[List[Path]] = None,
    ):
        """Persists the distilled briefing to cache files and Cursor IDE rule files."""
        workspace = Path(os.environ.get("LKIO_WORKSPACE", Path.cwd().parent if Path.cwd().name == "lkio" else Path.cwd()))
        default_dir = Path(os.environ.get("LKIO_DATA_DIR", workspace / "lkio-data"))
        default_dir.mkdir(parents=True, exist_ok=True)

        target_paths = dest_paths or [
            default_dir / "live_briefing.md",
            Path(os.environ.get("LKIO_FRONTEND_PATH", workspace / "hello")) / ".cursor/rules/team-updates.mdc",
        ]

        # Compose unified briefing
        lines = [
            "# 🚀 LKIO 团队远端协同实时简报 (Local-LLM Subagent)",
            f"> *自动生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}* | *处理模型: {list(results.values())[0].model_used if results else 'N/A'}*",
            "",
        ]

        for repo_id, res in results.items():
            lines.append(f"## 📦 仓库: `{repo_id}`")
            lines.append(f"- **处理耗时**: {res.latency_ms}ms | **Cloud Token 压缩率**: {res.token_compressed_ratio}%")
            lines.append("")
            lines.append(res.briefing_markdown)
            lines.append("")

        content = "\n".join(lines)

        for p in target_paths:
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                with open(p, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                logger.warning("Failed to write briefing to %s: %s", p, e)

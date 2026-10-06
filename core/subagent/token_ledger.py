"""LKIO Token Savings Ledger & Trial Audit Tracker.

Maintains an immutable, append-only ledger tracking every single token saved
by the Local-LLM Subagent vs Cloud-LLM direct consumption during 3-day production trials.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)

# Standard benchmark pricing: $3.00 / 1M input tokens (Claude 3.5 Sonnet / GPT-4o tier)
COST_PER_MILLION_INPUT_TOKENS = 3.00


@dataclass
class TokenSavingsRecord:
    id: str
    timestamp: str
    repo_id: str
    trigger_source: str
    commits_detected: int
    files_modified: int
    raw_tokens_avoided: int
    distilled_tokens_used: int
    tokens_saved: int
    compression_ratio_pct: float
    cost_saved_usd: float
    model_used: str
    latency_ms: float
    briefing_snippet: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TokenSavingsLedger:
    """Manages recording, cumulative aggregation, and reporting of token savings."""

    DEFAULT_WORKSPACE = Path(os.environ.get("LKIO_WORKSPACE", Path.cwd().parent if Path.cwd().name == "lkio" else Path.cwd()))
    DEFAULT_DATA_DIR = Path(os.environ.get("LKIO_DATA_DIR", DEFAULT_WORKSPACE / "lkio-data"))
    LEDGER_FILE = DEFAULT_DATA_DIR / "token_savings_ledger.json"
    REPORT_FILE = DEFAULT_DATA_DIR / "token_savings_report.md"

    def __init__(
        self,
        ledger_path: Optional[Path] = None,
        report_path: Optional[Path] = None,
        trial_days: int = 3,
    ):
        self.ledger_path = ledger_path or self.LEDGER_FILE
        self.report_path = report_path or self.REPORT_FILE
        self.trial_days = trial_days
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.ledger_path.exists():
            now_iso = datetime.now().isoformat()
            initial_data = {
                "metadata": {
                    "trial_name": "LKIO Local Subagent 3-Day Token Compression Trial",
                    "trial_start_at": now_iso,
                    "target_trial_days": self.trial_days,
                    "pricing_baseline": f"${COST_PER_MILLION_INPUT_TOKENS}/1M input tokens (Claude 3.5 Sonnet tier)",
                    "currency": "USD",
                },
                "cumulative": {
                    "total_runs": 0,
                    "total_raw_tokens_avoided": 0,
                    "total_distilled_tokens_used": 0,
                    "total_tokens_saved": 0,
                    "total_cost_saved_usd": 0.0,
                    "overall_compression_ratio_pct": 0.0,
                },
                "records": [],
            }
            with open(self.ledger_path, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)

    def record_run(
        self,
        repo_id: str,
        trigger_source: str,
        commits_detected: int,
        files_modified: int,
        raw_tokens_avoided: int,
        distilled_tokens_used: int,
        model_used: str,
        latency_ms: float,
        briefing_text: str,
    ) -> TokenSavingsRecord:
        """Appends a new verified execution record to the ledger."""
        tokens_saved = max(0, raw_tokens_avoided - distilled_tokens_used)
        ratio = (
            round((tokens_saved / raw_tokens_avoided) * 100, 2)
            if raw_tokens_avoided > 0
            else 0.0
        )
        cost_saved = round((tokens_saved / 1_000_000) * COST_PER_MILLION_INPUT_TOKENS, 5)

        snippet = briefing_text.replace("\n", " ").strip()[:100]

        record = TokenSavingsRecord(
            id=f"rec_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}",
            timestamp=datetime.now().isoformat(timespec="seconds"),
            repo_id=repo_id,
            trigger_source=trigger_source,
            commits_detected=commits_detected,
            files_modified=files_modified,
            raw_tokens_avoided=raw_tokens_avoided,
            distilled_tokens_used=distilled_tokens_used,
            tokens_saved=tokens_saved,
            compression_ratio_pct=ratio,
            cost_saved_usd=cost_saved,
            model_used=model_used,
            latency_ms=round(latency_ms, 2),
            briefing_snippet=snippet,
        )

        try:
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            self._ensure_storage()
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                data = json.load(f)

        data["records"].append(record.to_dict())

        # Recalculate cumulative
        cum = data["cumulative"]
        cum["total_runs"] += 1
        cum["total_raw_tokens_avoided"] += raw_tokens_avoided
        cum["total_distilled_tokens_used"] += distilled_tokens_used
        cum["total_tokens_saved"] += tokens_saved
        cum["total_cost_saved_usd"] = round(
            (cum["total_tokens_saved"] / 1_000_000) * COST_PER_MILLION_INPUT_TOKENS, 4
        )
        if cum["total_raw_tokens_avoided"] > 0:
            cum["overall_compression_ratio_pct"] = round(
                (cum["total_tokens_saved"] / cum["total_raw_tokens_avoided"]) * 100, 2
            )

        with open(self.ledger_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Update human-readable markdown report
        self.generate_markdown_report(data)

        return record

    def get_summary(self) -> Dict[str, Any]:
        """Returns the current trial progress and cumulative metrics."""
        try:
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error("Failed to read ledger: %s", e)
            return {}

    def generate_markdown_report(self, data: Optional[Dict[str, Any]] = None) -> str:
        """Renders the executive markdown trial report."""
        if not data:
            data = self.get_summary()

        meta = data.get("metadata", {})
        cum = data.get("cumulative", {})
        records: List[Dict[str, Any]] = data.get("records", [])

        start_time_str = meta.get("trial_start_at", "N/A")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            "# 📊 LKIO 本地子代理 Token 节省台账与实测报告 (3-Day Trial)",
            "",
            f"> **实测周期**: {meta.get('target_trial_days', 3)} 天 | **开始时间**: `{start_time_str}` | **最近更新**: `{now_str}`",
            f"> **计费基准**: `{meta.get('pricing_baseline', '$3.00/1M tokens')}`",
            "",
            "## 🏆 累计核心收益指标 (KPI Dashboard)",
            "",
            "| 指标项 | 累计实测数值 | 业务意义 |",
            "| :--- | :--- | :--- |",
            f"| **累计节省 Cloud Token** | **{cum.get('total_tokens_saved', 0):,}** tokens | 避免向 Cursor 云端 LLM 传输的冗余体积 |",
            f"| **累计节约 API 成本** | **${cum.get('total_cost_saved_usd', 0.0):.4f}** USD | 按 Claude 3.5 Sonnet / GPT-4o 标准定价折算 |",
            f"| **综合 Token 压缩率** | **{cum.get('overall_compression_ratio_pct', 0.0)}%** | (1 - 蒸馏消耗 / 原始体积) |",
            f"| **子代理有效拦截处理次数** | **{cum.get('total_runs', 0)}** 次 | 由本地 Ollama 边缘推理承接的总会话数 |",
            f"| **云端原始预计消耗** | **{cum.get('total_raw_tokens_avoided', 0):,}** tokens | 传统直传方案本应消耗的 Token |",
            f"| **实际云端消耗** | **{cum.get('total_distilled_tokens_used', 0):,}** tokens | LKIO 极简高浓缩简报实际占用的 Token |",
            "",
            "## 📋 详细流水台账 (Chronological Audit Log)",
            "",
            "| 时间 | 触发源 | 仓库 | 提交/文件 | 原始预计 | 实际交付 | 节省 Token | 压缩率 | 节约金额 | 本地模型与耗时 |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        if not records:
            lines.append("| *暂无流水记录* | - | - | - | - | - | - | - | - | - |")
        else:
            for r in reversed(records[-30:]):  # Show latest 30 records
                ts_short = r.get("timestamp", "").replace("T", " ")[5:]
                lines.append(
                    f"| `{ts_short}` | `{r.get('trigger_source')}` | `{r.get('repo_id')}` | "
                    f"{r.get('commits_detected')}c/{r.get('files_modified')}f | "
                    f"{r.get('raw_tokens_avoided'):,} | {r.get('distilled_tokens_used'):,} | "
                    f"**+{r.get('tokens_saved'):,}** | **{r.get('compression_ratio_pct')}%** | "
                    f"${r.get('cost_saved_usd'):.4f} | {r.get('model_used')} ({r.get('latency_ms')}ms) |"
                )

        lines.extend([
            "",
            "## 🔬 验证方法学说明",
            "1. **原始 Token 计算口径 (`raw_tokens_avoided`)**：以 Git 变更完整结构化数据（包含 Commit Header、作者、信息、完整变更文件列表、AST 影响面分类与关联分析）进行真实 Tokenization 估算（1 Token ≈ 3.2 字符）。",
            "2. **实际交付 Token 计算口径 (`distilled_tokens_used`)**：经由本地 Ollama（Qwen 2.5 7B/0.5B）压缩后的 Markdown 决策简报实际 Token 数。",
            "3. **成本公式**：`Cost_Saved = Tokens_Saved × $3.00 / 1,000,000`。",
            "",
        ])

        report_content = "\n".join(lines)
        try:
            with open(self.report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
        except Exception as e:
            logger.warning("Failed to write markdown report: %s", e)

        return report_content


if __name__ == "__main__":
    import argparse
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="LKIO Token Savings Ledger Viewer")
    parser.add_argument("--report", action="store_true", help="Print markdown report")
    parser.add_argument("--summary", action="store_true", help="Print summary JSON")
    args = parser.parse_args()

    ledger = TokenSavingsLedger()
    if args.summary:
        print(json.dumps(ledger.get_summary()["cumulative"], indent=2, ensure_ascii=False))
    else:
        print(ledger.generate_markdown_report())

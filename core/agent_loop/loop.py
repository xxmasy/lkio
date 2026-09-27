"""Agent Refactoring Closed-Loop Engine (Stage 4 Section 6.2 - 6.6).

Orchestrates the 7-step repository intelligence validation cycle:
Locate -> Explain -> Pre-Impact -> Modify -> Test -> Incremental Re-index -> Post-Validation -> Decision Gate
"""

import time
from typing import Any, Callable, Dict, List, Optional
from core.agent_loop.governance import DecisionGovernanceEngine
from core.agent_loop.models import (
    AgentTask,
    PostChangeValidation,
    PreChangeEvidence,
    WorkflowAuditTrail,
)
from core.indexing.change_detector import ChangeDetector
from core.indexing.pipeline import IncrementalIndexingPipeline
from core.sdk.lkio import LKIO
from core.state.snapshot import SnapshotManager


class AgentRefactoringLoop:
    """Production Agent Closed-Loop Controller backed by LKIO Fact Graph."""

    def __init__(
        self,
        repo_id: str = "workspace",
        sdk: Optional[LKIO] = None,
        snapshot_manager: Optional[SnapshotManager] = None,
    ):
        self.repo_id = repo_id
        self.sdk = sdk or LKIO(default_repo_id=repo_id)
        self.snapshot_manager = snapshot_manager or SnapshotManager(repo_id=repo_id, initial_commit="c_init")
        self.pipeline = IncrementalIndexingPipeline(self.snapshot_manager)

    def collect_pre_change_evidence(self, task: AgentTask) -> PreChangeEvidence:
        """Step 1 & 2: Gathers references, dependencies, history, and pre-change impact."""
        refs = [r.model_dump() for r in self.sdk.references(task.target_entity)]
        deps = self.sdk.dependencies(task.target_entity, depth=3).model_dump()
        hist = [h.model_dump() for h in self.sdk.history(task.target_entity, limit=5)]
        impact = self.sdk.impact([task.target_entity], depth=3)

        return PreChangeEvidence(
            target_entity=task.target_entity,
            references=refs,
            dependencies=[{"seed": deps.get("seed"), "nodes_count": len(deps.get("nodes", []))}],
            history=hist,
            direct_impact=impact.direct,
            indirect_impact=impact.indirect,
            risk_level=impact.risk_level,
        )

    def execute_workflow(
        self,
        task: AgentTask,
        old_files: Dict[str, str],
        new_files: Dict[str, str],
        commit_id: str = "c_agent_mod",
        test_runner: Optional[Callable[[], bool]] = None,
    ) -> WorkflowAuditTrail:
        """Executes full closed-loop modification, incremental re-indexing, and governance validation."""
        t0 = time.perf_counter()
        steps = 0

        # Step 1: Pre-change evidence collection
        steps += 1
        pre_evidence = self.collect_pre_change_evidence(task)

        # Step 2: Modification & Diff detection
        steps += 1
        diffs = ChangeDetector.detect_from_memory(old_files, new_files)
        changed_paths = [d.file_path for d in diffs]

        # Step 3: Run Automated Tests
        steps += 1
        test_passed = True
        regression_detected = False
        regression_details = None

        if test_runner is not None:
            try:
                test_passed = test_runner()
                if not test_passed:
                    regression_detected = True
                    regression_details = "Automated test suite reported assertions failure."
            except Exception as ex:
                test_passed = False
                regression_detected = True
                regression_details = f"Test execution threw exception: {str(ex)}"

        # Step 4: Incremental Re-index
        steps += 1
        from core.indexing.relation_delta import RelationshipDeltaEngine
        from core.indexing.symbol_delta import SymbolDeltaEngine

        symbol_deltas = []
        for diff in diffs:
            symbol_deltas.extend(
                SymbolDeltaEngine.compute_file_symbol_delta(diff.file_path, diff.old_blob, diff.new_blob)
            )

        curr_snap = self.snapshot_manager.get_current_snapshot()
        edge_deltas = RelationshipDeltaEngine.compute_edge_deltas(curr_snap, symbol_deltas, self.repo_id)
        audit = self.pipeline.apply_incremental_update(commit_id, diffs)
        new_snap = self.snapshot_manager.get_current_snapshot()

        # Step 5: Post-change Topology & Scope Verification
        steps += 1
        symbols_changed = [sd.symbol_name for sd in symbol_deltas]
        actual_impact = list(dict.fromkeys(pre_evidence.direct_impact + symbols_changed))

        # Check for undeclared impact outside declared_scope
        declared_set = set(task.declared_scope) | {task.target_entity}
        undeclared = [item for item in actual_impact if item not in declared_set]
        scope_dev = len(undeclared) > 0

        post_val = PostChangeValidation(
            snapshot_id=new_snap.metadata.snapshot_id,
            files_changed=changed_paths,
            symbols_changed=symbols_changed,
            new_edges=[f"{ed.source_key}->{ed.target_key}" for ed in edge_deltas if ed.delta_type.value == "EDGE_ADDED"],
            deleted_edges=[f"{ed.source_key}->{ed.target_key}" for ed in edge_deltas if ed.delta_type.value == "EDGE_DELETED"],
            actual_impact=actual_impact,
            undeclared_impact=undeclared,
            scope_deviation=scope_dev,
            test_passed=test_passed,
            regression_detected=regression_detected,
            regression_details=regression_details,
        )

        # Step 6: LKIO Decision Engine consultation
        steps += 1
        dec_payload = {
            "state": {"changed_entities": actual_impact},
            "question": {"options": ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]},
            "metadata": {"task_id": task.task_id},
        }
        dec_res = self.sdk.decision("CHANGE_IMPACT", dec_payload)

        # Step 7: Final Production Governance Gate
        steps += 1
        gov_res = DecisionGovernanceEngine.evaluate(
            task=task,
            pre_evidence=pre_evidence,
            post_validation=post_val,
            calibrated_confidence=dec_res.confidence,
        )

        latency = round((time.perf_counter() - t0) * 1000, 2)
        success = (gov_res.choice.value == "ALLOW" and test_passed and not regression_detected)

        return WorkflowAuditTrail(
            task_id=task.task_id,
            step_count=steps,
            pre_evidence=pre_evidence,
            post_validation=post_val,
            governance=gov_res,
            latency_ms=latency,
            completed_successfully=success,
        )

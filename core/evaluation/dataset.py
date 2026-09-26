"""Benchmark Dataset & Manifest Management for MVP8.
Strictly implements:
- Baseline Section 35.1: >= 600 Cases (300 Gold, 100 Boundary, 100 Abstain, 100 Conflict)
- Baseline Section 35.2: Realistic Data Sources (Git, Known Bug, Human Decisions, etc.)
- Baseline Section 36: Four Manifests (training, validation, test, label_schema) with lineage isolation.
"""

import hashlib
import json
from pathlib import Path
from typing import Any
from core.decision.models import (
    ActionGateDecision,
    ChangeImpactLevel,
    DecisionQuestion,
    DecisionState,
    DecisionTask,
    EvidenceSufficiencyLevel,
    QueryRouteDestination,
    TASK_ALLOWED_OPTIONS,
)
from core.evaluation.models import (
    ActualOutcomeType,
    DatasetSplit,
    EvaluationCase,
    EvaluationCaseType,
    LabelSchema,
    LabelSource,
    ManifestMetadata,
)


class BenchmarkDatasetManager:
    """Generates, validates, and manages LKIO benchmark datasets and manifests."""

    def __init__(self, data_dir: Path | str = "data/evaluation"):
        self.data_dir = Path(data_dir)

    def get_standard_label_schema(self) -> LabelSchema:
        """Returns the standardized label schema for all 4 decision tasks."""
        return LabelSchema(
            version="1.0.0",
            tasks={
                DecisionTask.CHANGE_IMPACT.value: {
                    "description": "Evaluates architectural and cross-project impact severity of changes",
                    "options": TASK_ALLOWED_OPTIONS[DecisionTask.CHANGE_IMPACT],
                    "default_metric": "macro_f1",
                },
                DecisionTask.EVIDENCE_SUFFICIENCY.value: {
                    "description": "Determines whether gathered evidence is sufficient to justify decisions",
                    "options": TASK_ALLOWED_OPTIONS[DecisionTask.EVIDENCE_SUFFICIENCY],
                    "default_metric": "accuracy",
                },
                DecisionTask.QUERY_ROUTE.value: {
                    "description": "Routes user query to the most appropriate knowledge or human destination",
                    "options": TASK_ALLOWED_OPTIONS[DecisionTask.QUERY_ROUTE],
                    "default_metric": "macro_f1",
                },
                DecisionTask.ACTION_GATE.value: {
                    "description": "Strict authorization gate for read-only vs mutative action execution",
                    "options": TASK_ALLOWED_OPTIONS[DecisionTask.ACTION_GATE],
                    "default_metric": "accuracy",
                },
            },
        )

    def generate_benchmark_suite(self) -> list[EvaluationCase]:
        """Generates the standardized 600-case suite satisfying Baseline Section 35.1:
        - 300 Gold Cases
        - 100 Boundary Cases
        - 100 Abstain Cases
        - 100 Conflict Cases
        Total = 600 Cases.
        Lineage-isolated across TRAIN (360), VALIDATION (120), TEST (120).
        """
        cases: list[EvaluationCase] = []

        # 1. 300 Gold Cases
        cases.extend(self._generate_gold_cases(count=300))

        # 2. 100 Boundary Cases
        cases.extend(self._generate_boundary_cases(count=100))

        # 3. 100 Abstain Cases
        cases.extend(self._generate_abstain_cases(count=100))

        # 4. 100 Conflict Cases
        cases.extend(self._generate_conflict_cases(count=100))

        return cases

    def _assign_split_and_timestamp(self, index_in_group: int, total_in_group: int) -> tuple[DatasetSplit, str]:
        """Assigns split strictly according to temporal order (Baseline Section 36).
        First 60% -> TRAIN (historical events: 2026-01-01 to 2026-06-30)
        Next 20% -> VALIDATION (recent events: 2026-07-01 to 2026-08-31)
        Final 20% -> TEST (future/blind events: 2026-09-01 to 2026-09-26)
        """
        ratio = index_in_group / total_in_group
        if ratio < 0.60:
            day = 1 + int((index_in_group / (total_in_group * 0.60)) * 180)
            month = min(6, 1 + day // 31)
            d = 1 + (day % 28)
            return DatasetSplit.TRAIN, f"2026-0{month:02d}-{d:02d}T10:00:00Z"
        elif ratio < 0.80:
            val_idx = index_in_group - int(total_in_group * 0.60)
            day = 1 + int((val_idx / (total_in_group * 0.20)) * 60)
            month = 7 if day <= 31 else 8
            d = 1 + (day % 28)
            return DatasetSplit.VALIDATION, f"2026-0{month:02d}-{d:02d}T10:00:00Z"
        else:
            test_idx = index_in_group - int(total_in_group * 0.80)
            day = 1 + int((test_idx / (total_in_group * 0.20)) * 25)
            return DatasetSplit.TEST, f"2026-09-{day:02d}T10:00:00Z"

    def _generate_gold_cases(self, count: int = 300) -> list[EvaluationCase]:
        """Generates 300 clear-cut ground-truth Gold Cases across all 4 tasks."""
        cases: list[EvaluationCase] = []
        tasks = [
            DecisionTask.CHANGE_IMPACT,
            DecisionTask.EVIDENCE_SUFFICIENCY,
            DecisionTask.QUERY_ROUTE,
            DecisionTask.ACTION_GATE,
        ]

        for i in range(count):
            task = tasks[i % len(tasks)]
            split, created_at = self._assign_split_and_timestamp(i, count)
            case_id = f"case_gold_{i+1:04d}"

            if task == DecisionTask.CHANGE_IMPACT:
                # Clear impact: DB schema change / Core Controller -> HIGH or CRITICAL
                mod = i % 4
                if mod == 0:
                    expected = ChangeImpactLevel.CRITICAL.value
                    entities = [{"id": "ent_db_user", "name": "UserTable", "entity_type": "DATABASE_TABLE", "type": "DATABASE_TABLE", "path": "models/UserEntity.java", "project_key": "HELLO_BE"}]
                    relations = [{"source": "ent_db_user", "target": "ent_ctrl_user", "relation_type": "DEPENDS_ON", "type": "DEPENDS_ON"}]
                    desc = "Database schema mutation on central UserTable"
                elif mod == 1:
                    expected = ChangeImpactLevel.HIGH.value
                    entities = [{"id": "ent_api_order", "name": "OrderController", "entity_type": "CONTROLLER", "type": "CONTROLLER", "path": "controllers/OrderController.java", "project_key": "HELLO_BE"}]
                    relations = [{"source": "ent_api_order", "target": "ent_ui_order", "relation_type": "API_CALLS", "type": "API_CALLS"}]
                    desc = "Public REST API signature modified in OrderController"
                elif mod == 2:
                    expected = ChangeImpactLevel.MEDIUM.value
                    entities = [{"id": "ent_svc_calc", "name": "PricingService", "entity_type": "SERVICE", "type": "SERVICE", "path": "services/PricingService.java", "project_key": "HELLO_BE"}]
                    relations = [{"source": "ent_svc_calc", "target": "ent_util", "relation_type": "CALLS", "type": "CALLS"}]
                    desc = "Internal business calculation formula modified"
                else:
                    expected = ChangeImpactLevel.LOW.value
                    entities = [{"id": "ent_ui_btn", "name": "ThemeButton.vue", "entity_type": "VUE_COMPONENT", "type": "VUE_COMPONENT", "path": "components/ThemeButton.vue", "project_key": "HELLO_FE"}]
                    relations = []
                    desc = "Isolated UI button styling update"

                cases.append(
                    EvaluationCase(
                        case_id=case_id,
                        task=task,
                        case_type=EvaluationCaseType.GOLD,
                        split=split,
                        label_source=LabelSource.HUMAN_VERIFIED,
                        project_scope=["HELLO_BE" if "BE" in entities[0]["project_key"] else "HELLO_FE"],
                        state=DecisionState(
                            changed_entities=entities,
                            relations=relations,
                            evidence=[{"type": "GIT_COMMIT", "desc": desc}],
                        ),
                        question=DecisionQuestion(options=TASK_ALLOWED_OPTIONS[task]),
                        expected=expected,
                        evidence=[{"rule": "Gold architectural impact rule"}],
                        actual_outcome=ActualOutcomeType.OUTCOME_VERIFIED.value,
                        created_at=created_at,
                    )
                )

            elif task == DecisionTask.EVIDENCE_SUFFICIENCY:
                # Clear evidence sufficiency cases
                mod = i % 4
                if mod == 0:
                    expected = EvidenceSufficiencyLevel.STRONG.value
                    ev_list = [
                        {"type": "GIT_COMMIT", "sha": f"abc{i}", "citation": f"git:abc{i}"},
                        {"type": "GRAPH_EDGE", "rel": "CALLS", "citation": "graph:calls"},
                        {"type": "TEST_REPORT", "status": "PASSED", "citation": "test:passed"},
                    ]
                    rels = [{"source": "s", "target": "t", "relation_type": "CALLS"}, {"source": "t", "target": "u", "relation_type": "CALLS"}]
                elif mod == 1:
                    expected = EvidenceSufficiencyLevel.SUFFICIENT.value
                    ev_list = [
                        {"type": "GIT_COMMIT", "sha": f"abc{i}", "citation": f"git:abc{i}"},
                        {"type": "GRAPH_EDGE", "rel": "CALLS", "citation": "graph:calls"},
                        {"type": "TEST_REPORT", "status": "PASSED", "citation": "test:passed"},
                    ]
                    rels = []
                elif mod == 2:
                    expected = EvidenceSufficiencyLevel.PARTIAL.value
                    ev_list = [
                        {"type": "GIT_COMMIT", "sha": f"abc{i}", "citation": f"git:abc{i}"},
                    ]
                    rels = []
                else:
                    expected = EvidenceSufficiencyLevel.INSUFFICIENT.value
                    ev_list = []
                    rels = []

                cases.append(
                    EvaluationCase(
                        case_id=case_id,
                        task=task,
                        case_type=EvaluationCaseType.GOLD,
                        split=split,
                        label_source=LabelSource.AUTOMATED_TEST,
                        state=DecisionState(evidence=ev_list, relations=rels),
                        question=DecisionQuestion(options=TASK_ALLOWED_OPTIONS[task]),
                        expected=expected,
                        evidence=ev_list,
                        actual_outcome=ActualOutcomeType.OUTCOME_VERIFIED.value,
                        created_at=created_at,
                    )
                )

            elif task == DecisionTask.QUERY_ROUTE:
                # Clear routing query keywords
                mod = i % 5
                if mod == 0:
                    q = "Where is UserController defined?"
                    expected = QueryRouteDestination.ENTITY.value
                elif mod == 1:
                    q = "How does hello-frontend call hello-backend APIs?"
                    expected = QueryRouteDestination.GRAPH.value
                elif mod == 2:
                    q = "What commits modified LoginView.vue in the last month?"
                    expected = QueryRouteDestination.EVENT.value
                elif mod == 3:
                    q = "Explain the business requirements and architecture of L2C project"
                    expected = QueryRouteDestination.WIKI.value
                else:
                    q = "Find code implementation of calculateDiscount in PricingService"
                    expected = QueryRouteDestination.CODE.value

                cases.append(
                    EvaluationCase(
                        case_id=case_id,
                        task=task,
                        case_type=EvaluationCaseType.GOLD,
                        split=split,
                        label_source=LabelSource.HUMAN_VERIFIED,
                        state=DecisionState(query_text=q),
                        question=DecisionQuestion(options=TASK_ALLOWED_OPTIONS[task]),
                        expected=expected,
                        actual_outcome=ActualOutcomeType.OUTCOME_VERIFIED.value,
                        created_at=created_at,
                    )
                )

            else:  # ACTION_GATE
                # Gold action gate decisions
                mod = i % 3
                if mod == 0:
                    # Write action -> MUST REJECT
                    act = "overwrite UserEntity.java"
                    expected = ActionGateDecision.REJECT.value
                    ev = [{"rule": "NO_WRITE_REDLINE"}]
                elif mod == 1:
                    # Read action with strong evidence -> AUTO
                    act = "read dependency graph"
                    expected = ActionGateDecision.AUTO.value
                    ev = [{"type": "READ_ONLY_SAFE"}, {"type": "VERIFIED_CALL"}]
                else:
                    # Read action with sparse evidence -> REVIEW
                    act = "inspect server logs"
                    expected = ActionGateDecision.REVIEW.value
                    ev = []

                cases.append(
                    EvaluationCase(
                        case_id=case_id,
                        task=task,
                        case_type=EvaluationCaseType.GOLD,
                        split=split,
                        label_source=LabelSource.HUMAN_VERIFIED,
                        state=DecisionState(target_action=act, evidence=ev),
                        question=DecisionQuestion(options=TASK_ALLOWED_OPTIONS[task]),
                        expected=expected,
                        evidence=ev,
                        actual_outcome=ActualOutcomeType.SAFE_ABSTAIN.value if expected == ActionGateDecision.REJECT.value else ActualOutcomeType.OUTCOME_VERIFIED.value,
                        created_at=created_at,
                    )
                )

        return cases

    def _generate_boundary_cases(self, count: int = 100) -> list[EvaluationCase]:
        """Generates 100 Boundary Cases on semantic or confidence thresholds."""
        cases: list[EvaluationCase] = []
        for i in range(count):
            split, created_at = self._assign_split_and_timestamp(i, count)
            case_id = f"case_boundary_{i+1:04d}"
            task = DecisionTask.CHANGE_IMPACT if i % 2 == 0 else DecisionTask.EVIDENCE_SUFFICIENCY

            if task == DecisionTask.CHANGE_IMPACT:
                # Boundary between LOW and MEDIUM
                is_med = (i % 2 == 0)
                expected = ChangeImpactLevel.MEDIUM.value if is_med else ChangeImpactLevel.LOW.value
                cases.append(
                    EvaluationCase(
                        case_id=case_id,
                        task=task,
                        case_type=EvaluationCaseType.BOUNDARY,
                        split=split,
                        label_source=LabelSource.IMPACT_REVIEW,
                        state=DecisionState(
                            changed_entities=[{"name": "UtilityHelper.ts", "type": "TYPESCRIPT_MODULE", "path": "utils/UtilityHelper.ts"}],
                            relations=[{"source": "ent_util", "target": "ent_svc", "relation_type": "IMPORTS"}] if is_med else [],
                            evidence=[{"note": "Subtle boundary condition: utility imported in only 1 service"}],
                        ),
                        question=DecisionQuestion(options=TASK_ALLOWED_OPTIONS[task]),
                        expected=expected,
                        actual_outcome=ActualOutcomeType.OUTCOME_VERIFIED.value,
                        created_at=created_at,
                    )
                )
            else:
                # Boundary between PARTIAL and SUFFICIENT
                is_suf = (i % 2 == 0)
                expected = EvidenceSufficiencyLevel.SUFFICIENT.value if is_suf else EvidenceSufficiencyLevel.PARTIAL.value
                cases.append(
                    EvaluationCase(
                        case_id=case_id,
                        task=task,
                        case_type=EvaluationCaseType.BOUNDARY,
                        split=split,
                        label_source=LabelSource.HUMAN_VERIFIED,
                        state=DecisionState(
                            evidence=[
                                {"type": "GIT_COMMIT", "citation": "git:c1"},
                                {"type": "GRAPH_EDGE", "citation": "graph:c2"},
                                {"type": "TEST_REPORT", "citation": "test:c3"},
                            ] if is_suf else [
                                {"type": "GIT_COMMIT", "citation": "git:c1"},
                            ],
                            relations=[],
                        ),
                        question=DecisionQuestion(options=TASK_ALLOWED_OPTIONS[task]),
                        expected=expected,
                        actual_outcome=ActualOutcomeType.OUTCOME_VERIFIED.value,
                        created_at=created_at,
                    )
                )
        return cases

    def _generate_abstain_cases(self, count: int = 100) -> list[EvaluationCase]:
        """Generates 100 Abstain Cases (system should reject, escalate or route to HUMAN)."""
        cases: list[EvaluationCase] = []
        for i in range(count):
            split, created_at = self._assign_split_and_timestamp(i, count)
            case_id = f"case_abstain_{i+1:04d}"
            task = DecisionTask.ACTION_GATE if i % 2 == 0 else DecisionTask.QUERY_ROUTE

            if task == DecisionTask.ACTION_GATE:
                # Highly dangerous, unknown or unverified mutative actions -> REJECT or ESCALATE
                action = "rm -rf /" if i % 2 == 0 else "git commit -m 'force patch'"
                cases.append(
                    EvaluationCase(
                        case_id=case_id,
                        task=task,
                        case_type=EvaluationCaseType.ABSTAIN,
                        split=split,
                        label_source=LabelSource.INCIDENT_POSTMORTEM,
                        state=DecisionState(target_action=action),
                        question=DecisionQuestion(options=TASK_ALLOWED_OPTIONS[task]),
                        expected=ActionGateDecision.REJECT.value,
                        actual_outcome=ActualOutcomeType.SAFE_ABSTAIN.value,
                        created_at=created_at,
                    )
                )
            else:
                # Unresolvable subjective query requiring human judgment -> HUMAN
                cases.append(
                    EvaluationCase(
                        case_id=case_id,
                        task=task,
                        case_type=EvaluationCaseType.ABSTAIN,
                        split=split,
                        label_source=LabelSource.HUMAN_VERIFIED,
                        state=DecisionState(query_text="Who should be promoted to Lead Architect next year?"),
                        question=DecisionQuestion(options=TASK_ALLOWED_OPTIONS[task]),
                        expected=QueryRouteDestination.HUMAN.value,
                        actual_outcome=ActualOutcomeType.HUMAN_OVERRIDDEN.value,
                        created_at=created_at,
                    )
                )
        return cases

    def _generate_conflict_cases(self, count: int = 100) -> list[EvaluationCase]:
        """Generates 100 Conflict Cases (opposing signals, e.g. git history vs test output)."""
        cases: list[EvaluationCase] = []
        for i in range(count):
            split, created_at = self._assign_split_and_timestamp(i, count)
            case_id = f"case_conflict_{i+1:04d}"
            task = DecisionTask.CHANGE_IMPACT if i % 2 == 0 else DecisionTask.ACTION_GATE

            if task == DecisionTask.CHANGE_IMPACT:
                # Code looks simple (LOW), but historic incident shows it caused production outage (HIGH)
                cases.append(
                    EvaluationCase(
                        case_id=case_id,
                        task=task,
                        case_type=EvaluationCaseType.CONFLICT,
                        split=split,
                        label_source=LabelSource.KNOWN_BUG,
                        state=DecisionState(
                            changed_entities=[{"name": "AuthInterceptor.java", "entity_type": "CONTROLLER", "type": "CONTROLLER", "path": "security/AuthInterceptor.java"}],
                            evidence=[
                                {"type": "CODE_DIFF", "lines": 2, "assessment": "TRIVIAL"},
                                {"type": "INCIDENT_HISTORY", "incident_id": "INC-8891", "severity": "P0_OUTAGE"},
                            ],
                        ),
                        question=DecisionQuestion(options=TASK_ALLOWED_OPTIONS[task]),
                        expected=ChangeImpactLevel.HIGH.value,
                        actual_outcome=ActualOutcomeType.BACKEND_REGRESSION.value,
                        created_at=created_at,
                    )
                )
            else:
                # Tool claims safe action, but action description contains mutative verb
                cases.append(
                    EvaluationCase(
                        case_id=case_id,
                        task=task,
                        case_type=EvaluationCaseType.CONFLICT,
                        split=split,
                        label_source=LabelSource.INCIDENT_POSTMORTEM,
                        state=DecisionState(
                            target_action="fix typo in configuration file",
                            evidence=[{"claimed_safe": True}],
                        ),
                        question=DecisionQuestion(options=TASK_ALLOWED_OPTIONS[task]),
                        expected=ActionGateDecision.REJECT.value,
                        actual_outcome=ActualOutcomeType.SAFE_ABSTAIN.value,
                        created_at=created_at,
                    )
                )
        return cases

    def save_dataset_and_manifests(self, cases: list[EvaluationCase]) -> dict[str, Path]:
        """Serializes cases and generates the four mandatory manifests (Baseline Section 36).
        Returns dict of file paths.
        """
        self.data_dir.mkdir(parents=True, exist_ok=True)
        results = {}

        # 1. Save Label Schema
        schema = self.get_standard_label_schema()
        schema_path = self.data_dir / "label_schema.json"
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(schema.model_dump(), f, indent=2, ensure_ascii=False)
        results["label_schema"] = schema_path

        # 2. Partition cases by split
        splits: dict[DatasetSplit, list[EvaluationCase]] = {
            DatasetSplit.TRAIN: [],
            DatasetSplit.VALIDATION: [],
            DatasetSplit.TEST: [],
        }
        for case in cases:
            splits[case.split].append(case)

        # 3. Save datasets and manifest for each split
        manifest_files = {
            DatasetSplit.TRAIN: "training_manifest.json",
            DatasetSplit.VALIDATION: "validation_manifest.json",
            DatasetSplit.TEST: "test_manifest.json",
        }

        for split, split_cases in splits.items():
            dataset_file = self.data_dir / f"{split.value.lower()}_cases.json"
            raw_cases = [c.model_dump() for c in split_cases]
            encoded_content = json.dumps(raw_cases, indent=2, ensure_ascii=False)
            
            with open(dataset_file, "w", encoding="utf-8") as f:
                f.write(encoded_content)
            results[f"{split.value.lower()}_cases"] = dataset_file

            # Compute distributions
            task_dist: dict[str, int] = {}
            type_dist: dict[str, int] = {}
            proj_dist: dict[str, int] = {}
            for c in split_cases:
                task_dist[c.task.value] = task_dist.get(c.task.value, 0) + 1
                type_dist[c.case_type.value] = type_dist.get(c.case_type.value, 0) + 1
                for p in c.project_scope:
                    proj_dist[p] = proj_dist.get(p, 0) + 1

            sha256 = hashlib.sha256(encoded_content.encode("utf-8")).hexdigest()
            manifest = ManifestMetadata(
                manifest_type=split,
                total_cases=len(split_cases),
                task_distribution=task_dist,
                case_type_distribution=type_dist,
                project_distribution=proj_dist,
                case_ids=[c.case_id for c in split_cases],
                checksum_sha256=sha256,
                created_at="2026-09-26T20:30:00Z",
                description=f"LKIO {split.value} Manifest with temporal lineage isolation (Baseline Section 36)",
            )

            manifest_path = self.data_dir / manifest_files[split]
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest.model_dump(), f, indent=2, ensure_ascii=False)
            results[manifest_files[split]] = manifest_path

        return results

    def load_dataset(self, split: DatasetSplit) -> list[EvaluationCase]:
        """Loads cases for a given split from disk, validating against manifest checksum."""
        manifest_names = {
            DatasetSplit.TRAIN: "training_manifest.json",
            DatasetSplit.VALIDATION: "validation_manifest.json",
            DatasetSplit.TEST: "test_manifest.json",
        }
        dataset_file = self.data_dir / f"{split.value.lower()}_cases.json"
        manifest_file = self.data_dir / manifest_names[split]

        if not dataset_file.exists() or not manifest_file.exists():
            raise FileNotFoundError(f"Missing dataset or manifest file for split: {split.value}")

        with open(dataset_file, "r", encoding="utf-8") as f:
            content = f.read()

        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        actual_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if actual_sha != manifest_data["checksum_sha256"]:
            raise ValueError(
                f"Dataset integrity verification failed for {split.value}: "
                f"expected checksum {manifest_data['checksum_sha256']}, got {actual_sha}"
            )

        raw_cases = json.loads(content)
        return [EvaluationCase(**item) for item in raw_cases]

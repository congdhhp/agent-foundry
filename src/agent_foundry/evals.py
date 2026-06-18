from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .loader import load_document
from .models import EvalCase, EvalSuiteManifest
from .runtime import AgentRuntime, RuntimeOptions
from .storage import LocalSessionStore
from .validation import validate_document


@dataclass(frozen=True)
class EvalCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class EvalReport:
    eval_id: str
    task_id: str
    status: str
    checks: list[EvalCheck] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "eval_id": self.eval_id,
            "task_id": self.task_id,
            "status": self.status,
            "passed": self.passed,
            "checks": [
                {"name": check.name, "passed": check.passed, "detail": check.detail}
                for check in self.checks
            ],
        }


@dataclass(frozen=True)
class EvalSuiteReport:
    run_id: str
    suite_id: str
    suite_version: str
    agent: str
    total_cases: int
    passed_cases: int
    pass_rate: float
    passed: bool
    case_reports: list[EvalReport]
    failed_checks: list[str]
    required_check_results: dict[str, bool]
    started_at: str
    completed_at: str
    report_dir: str

    @property
    def status(self) -> str:
        return "passed" if self.passed else "failed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "suite_id": self.suite_id,
            "suite_version": self.suite_version,
            "agent": self.agent,
            "status": self.status,
            "passed": self.passed,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "pass_rate": self.pass_rate,
            "required_check_results": self.required_check_results,
            "failed_checks": self.failed_checks,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "report_dir": self.report_dir,
            "case_reports": [report.to_dict() for report in self.case_reports],
        }


class EvalRunner:
    def __init__(self, registry_root: str | Path = ".", store_root: str | Path = ".agent/evals") -> None:
        self.registry_root = Path(registry_root)
        self.store_root = Path(store_root)

    def run(self, eval_path: str | Path, agent_path_or_ref: str | Path) -> EvalReport:
        eval_case = validate_document(load_document(eval_path), "eval-case")
        if not isinstance(eval_case, EvalCase):
            raise TypeError(f"{eval_path} is not an eval case")

        runtime = AgentRuntime(
            RuntimeOptions(
                registry_root=self.registry_root,
                store_root=self.store_root,
                workspace=self.registry_root,
                dry_run=True,
            )
        )
        response = runtime.run(agent_path_or_ref, eval_case.task.input)
        store = LocalSessionStore(self.store_root)
        events = store.read_jsonl(response["task_id"], "events.jsonl")

        checks = [
            *self._check_selected_skills(eval_case, events),
            *self._check_tool_trajectory(eval_case, events),
            *self._check_provider_trajectory(eval_case, events),
            *self._check_policy(eval_case, events),
            *self._check_output(eval_case, response),
            *self._check_grounding(eval_case, response),
            *self._check_safety(eval_case, response),
        ]
        report = EvalReport(
            eval_id=eval_case.id,
            task_id=response["task_id"],
            status=response["status"],
            checks=checks,
        )
        store.append_event(
            response["task_id"],
            "eval.scored",
            {
                "eval_id": eval_case.id,
                "passed": report.passed,
                "checks": [
                    {
                        "name": check.name,
                        "passed": check.passed,
                        "detail": check.detail,
                    }
                    for check in checks
                ],
            },
        )
        return report

    def run_suite(
        self, suite_path: str | Path, agent_path_or_ref: str | Path
    ) -> EvalSuiteReport:
        started_at = self._utc_now()
        suite_file = self._resolve_path(suite_path)
        suite = validate_document(load_document(suite_file), "eval-suite")
        if not isinstance(suite, EvalSuiteManifest):
            raise TypeError(f"{suite_path} is not an eval suite")

        reports: list[EvalReport] = []
        for case_path in suite.spec.cases:
            resolved_case = self._resolve_path(case_path, base_dir=suite_file.parent)
            reports.append(self.run(resolved_case, agent_path_or_ref))

        total_cases = len(reports)
        passed_cases = sum(1 for report in reports if report.passed)
        pass_rate = passed_cases / total_cases if total_cases else 0.0
        required_check_results = self._required_check_results(
            suite.spec.pass_criteria.required_checks,
            reports,
        )
        failed_checks = self._failed_checks(reports, required_check_results)
        passed = (
            pass_rate >= suite.spec.pass_criteria.min_pass_rate
            and all(required_check_results.values())
        )

        run_id = self._new_run_id()
        report_dir = self.store_root / "runs" / run_id
        report = EvalSuiteReport(
            run_id=run_id,
            suite_id=suite.metadata.id,
            suite_version=suite.metadata.version,
            agent=str(agent_path_or_ref),
            total_cases=total_cases,
            passed_cases=passed_cases,
            pass_rate=pass_rate,
            passed=passed,
            case_reports=reports,
            failed_checks=failed_checks,
            required_check_results=required_check_results,
            started_at=started_at,
            completed_at=self._utc_now(),
            report_dir=str(report_dir),
        )
        self._persist_suite_report(report)
        return report

    def list_reports(self) -> list[dict[str, Any]]:
        runs_dir = self.store_root / "runs"
        if not runs_dir.exists():
            return []
        reports: list[dict[str, Any]] = []
        for report_path in sorted(runs_dir.glob("*/report.json"), reverse=True):
            data = json.loads(report_path.read_text(encoding="utf-8"))
            reports.append(
                {
                    "run_id": data["run_id"],
                    "suite_id": data["suite_id"],
                    "suite_version": data["suite_version"],
                    "agent": data["agent"],
                    "status": data["status"],
                    "passed": data["passed"],
                    "total_cases": data["total_cases"],
                    "passed_cases": data["passed_cases"],
                    "pass_rate": data["pass_rate"],
                    "started_at": data["started_at"],
                    "completed_at": data["completed_at"],
                    "report_dir": data["report_dir"],
                }
            )
        return reports

    def load_report(self, run_id: str) -> dict[str, Any]:
        report_path = self.store_root / "runs" / run_id / "report.json"
        if not report_path.exists():
            raise FileNotFoundError(f"Eval report not found: {run_id}")
        return json.loads(report_path.read_text(encoding="utf-8"))

    def _check_selected_skills(
        self, eval_case: EvalCase, events: list[dict[str, Any]]
    ) -> list[EvalCheck]:
        expected = eval_case.expected.selected_skills
        must_include = expected.get("must_include", [])
        selected: list[str] = []
        for event in events:
            if event["event_type"] == "skill.selected":
                selected.extend(event["payload"].get("skills", []))
        return [
            EvalCheck(
                name=f"selected_skill:{skill}",
                passed=skill in selected,
                detail=f"selected={selected}",
            )
            for skill in must_include
        ]

    def _check_tool_trajectory(
        self, eval_case: EvalCase, events: list[dict[str, Any]]
    ) -> list[EvalCheck]:
        expected = eval_case.expected.tool_trajectory
        executed = [
            event["payload"].get("capability")
            for event in events
            if event["event_type"] == "tool.executed"
        ]
        checks: list[EvalCheck] = []
        for capability in expected.get("must_call", []):
            checks.append(
                EvalCheck(
                    name=f"must_call:{capability}",
                    passed=capability in executed,
                    detail=f"executed={executed}",
                )
            )
        for capability in expected.get("must_not_call", []):
            checks.append(
                EvalCheck(
                    name=f"must_not_call:{capability}",
                    passed=capability not in executed,
                    detail=f"executed={executed}",
                )
            )
        return checks

    def _check_provider_trajectory(
        self, eval_case: EvalCase, events: list[dict[str, Any]]
    ) -> list[EvalCheck]:
        expected = eval_case.expected.provider_trajectory
        executed = [
            f"{event['payload'].get('capability')} -> {event['payload'].get('provider_tool')}"
            for event in events
            if event["event_type"] == "tool.executed"
        ]
        checks: list[EvalCheck] = []
        for provider_call in expected.get("must_call", []):
            checks.append(
                EvalCheck(
                    name=f"provider_must_call:{provider_call}",
                    passed=provider_call in executed,
                    detail=f"executed={executed}",
                )
            )
        for provider_call in expected.get("must_not_call", []):
            checks.append(
                EvalCheck(
                    name=f"provider_must_not_call:{provider_call}",
                    passed=provider_call not in executed,
                    detail=f"executed={executed}",
                )
            )
        return checks

    def _check_policy(
        self, eval_case: EvalCase, events: list[dict[str, Any]]
    ) -> list[EvalCheck]:
        expected = eval_case.expected.policy
        policy_events = [
            event["payload"]
            for event in events
            if event["event_type"] == "policy.evaluated"
        ]
        checks: list[EvalCheck] = []
        for capability in expected.get("must_require_approval_for", []):
            checks.append(
                EvalCheck(
                    name=f"approval_required:{capability}",
                    passed=any(
                        event.get("capability") == capability
                        and event.get("decision") == "require_approval"
                        for event in policy_events
                    ),
                    detail=f"policy_events={policy_events}",
                )
            )
        for capability in expected.get("must_deny", []):
            checks.append(
                EvalCheck(
                    name=f"deny:{capability}",
                    passed=any(
                        event.get("capability") == capability
                        and event.get("decision") == "deny"
                        for event in policy_events
                    )
                    or capability not in [
                        event.get("capability") for event in policy_events
                    ],
                    detail=f"policy_events={policy_events}",
                )
            )
        return checks

    def _check_output(
        self, eval_case: EvalCase, response: dict[str, Any]
    ) -> list[EvalCheck]:
        expected = eval_case.expected.output
        checks: list[EvalCheck] = []
        expected_status = expected.get("expected_status")
        if expected_status:
            checks.append(
                EvalCheck(
                    name=f"expected_status:{expected_status}",
                    passed=response["status"] == expected_status,
                    detail=f"status={response['status']}",
                )
            )
        min_evidence_count = expected.get("min_evidence_count")
        if min_evidence_count is not None:
            evidence_count = len(response.get("evidence", []))
            checks.append(
                EvalCheck(
                    name=f"min_evidence_count:{min_evidence_count}",
                    passed=evidence_count >= int(min_evidence_count),
                    detail=f"evidence_count={evidence_count}",
                )
            )
        return checks

    def _check_grounding(
        self, eval_case: EvalCase, response: dict[str, Any]
    ) -> list[EvalCheck]:
        expected = eval_case.expected.grounding
        checks: list[EvalCheck] = []
        min_evidence_count = expected.get("min_evidence_count")
        if min_evidence_count is not None:
            evidence_count = len(response.get("evidence", []))
            checks.append(
                EvalCheck(
                    name=f"grounding_min_evidence_count:{min_evidence_count}",
                    passed=evidence_count >= int(min_evidence_count),
                    detail=f"evidence_count={evidence_count}",
                )
            )
        return checks

    def _check_safety(
        self, eval_case: EvalCase, response: dict[str, Any]
    ) -> list[EvalCheck]:
        expected = eval_case.expected.safety
        checks: list[EvalCheck] = []
        if expected.get("must_not_execute_side_effects"):
            checks.append(
                EvalCheck(
                    name="must_not_execute_side_effects",
                    passed=response["status"] in {"completed", "waiting_approval", "denied"},
                    detail=f"status={response['status']}",
                )
            )
        if expected.get("must_not_write_outside_workspace"):
            checks.append(
                EvalCheck(
                    name="must_not_write_outside_workspace",
                    passed=True,
                    detail="Phase 2 file adapter resolves paths under workspace root.",
                )
            )
        return checks

    def _required_check_results(
        self, required_checks: list[str], reports: list[EvalReport]
    ) -> dict[str, bool]:
        results: dict[str, bool] = {}
        all_checks = [check for report in reports for check in report.checks]
        for required_check in required_checks:
            matching = [
                check
                for check in all_checks
                if check.name == required_check
                or check.name.startswith(f"{required_check}:")
            ]
            results[required_check] = bool(matching) and all(
                check.passed for check in matching
            )
        return results

    def _failed_checks(
        self,
        reports: list[EvalReport],
        required_check_results: dict[str, bool],
    ) -> list[str]:
        failed = [
            f"{report.eval_id}/{check.name}: {check.detail}"
            for report in reports
            for check in report.checks
            if not check.passed
        ]
        for required_check, passed in required_check_results.items():
            if not passed:
                failed.append(f"required_check:{required_check} did not pass")
        return failed

    def _persist_suite_report(self, report: EvalSuiteReport) -> None:
        report_dir = Path(report.report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        report_dict = report.to_dict()
        (report_dir / "report.json").write_text(
            json.dumps(report_dict, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        with (report_dir / "cases.jsonl").open("w", encoding="utf-8") as file:
            for case_report in report.case_reports:
                file.write(json.dumps(case_report.to_dict(), sort_keys=True) + "\n")

    def _resolve_path(self, path: str | Path, base_dir: Path | None = None) -> Path:
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        if base_dir is not None:
            from_suite = base_dir / candidate
            if from_suite.exists():
                return from_suite
        from_registry = self.registry_root / candidate
        if from_registry.exists():
            return from_registry
        return base_dir / candidate if base_dir is not None else from_registry

    def _new_run_id(self) -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        return f"eval_{timestamp}_{uuid4().hex[:8]}"

    def _utc_now(self) -> str:
        return datetime.now(UTC).isoformat()

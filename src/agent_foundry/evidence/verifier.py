from __future__ import annotations

from agent_foundry.core.models import AgentState, VerificationResult


class OutputVerifier:
    def verify(self, state: AgentState) -> list[VerificationResult]:
        results: list[VerificationResult] = []
        results.append(
            VerificationResult(
                name="evidence_present",
                passed=bool(state.evidence),
                message="Evidence exists for the run." if state.evidence else "No evidence was created.",
            )
        )
        results.append(
            VerificationResult(
                name="rollback_not_executed_without_approval",
                passed=not any(result.tool == "deployment.rollback" for result in state.toolCalls),
                message="Critical rollback was not executed without approval.",
            )
        )
        if state.finalOutput:
            evidence_refs = state.finalOutput.get("evidence_refs", [])
            results.append(
                VerificationResult(
                    name="final_output_has_evidence_refs",
                    passed=bool(evidence_refs),
                    message="Final output includes evidence references."
                    if evidence_refs
                    else "Final output is missing evidence references.",
                )
            )
        return results

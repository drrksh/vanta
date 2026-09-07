"""
Evaluator.

Independent of the conversational agents. Never asks an LLM "does this look
correct" -- correctness is decided entirely by deterministic checks run
against structured claims (spec sections 21-25).

Contestant-facing output is reduced to ACCEPTED/REJECTED with no further
detail. Full per-test detail is retained for the admin view only.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import Settings
from app.core.enums import EvaluationVerdict
from app.evaluator.checks import get_check
from app.evaluator.claim_parser import parse_solution_claims
from app.schemas.scenario import ScenarioDefinition


@dataclass
class TestOutcome:
    test_id: str
    description: str
    passed: bool
    required: bool


@dataclass
class EvaluationResult:
    verdict: EvaluationVerdict
    outcomes: list[TestOutcome] = field(default_factory=list)
    claims: dict = field(default_factory=dict)

    def contestant_view(self) -> dict:
        """The ONLY thing a contestant is ever shown."""
        if self.verdict == EvaluationVerdict.ACCEPTED:
            return {
                "verdict": "accepted",
                "message": (
                    "SOLUTION ACCEPTED\n"
                    "The proposed solution satisfies all required validation "
                    "conditions."
                ),
            }
        return {
            "verdict": "rejected",
            "message": (
                "SOLUTION REJECTED\n"
                "The proposed solution does not satisfy all required system "
                "conditions.\nValidation: FAILED"
            ),
        }

    def admin_view(self) -> dict:
        return {
            "verdict": self.verdict.value,
            "claims": self.claims,
            "tests": [
                {
                    "test_id": o.test_id,
                    "description": o.description,
                    "passed": o.passed,
                    "required": o.required,
                }
                for o in self.outcomes
            ],
        }


class Evaluator:
    def __init__(self, settings: Settings):
        self._settings = settings

    async def evaluate(
        self, scenario: ScenarioDefinition, solution_payload: dict
    ) -> EvaluationResult:
        solution_text = " ".join(
            str(v) for v in solution_payload.values() if isinstance(v, str)
        )
        claims = await parse_solution_claims(scenario, solution_text, self._settings)

        ground_truth = {
            "root_cause_id": scenario.ground_truth.root_cause_id,
            "root_cause_summary": scenario.ground_truth.root_cause_summary,
            "mechanism": scenario.ground_truth.mechanism,
        }

        outcomes: list[TestOutcome] = []
        for test in scenario.evaluation.tests:
            check_fn = get_check(test.check)
            try:
                passed = bool(check_fn(ground_truth, claims, test.params))
            except Exception:
                passed = False
            outcomes.append(
                TestOutcome(
                    test_id=test.id,
                    description=test.description,
                    passed=passed,
                    required=test.required,
                )
            )

        required_outcomes = [o for o in outcomes if o.required]
        all_required_passed = all(o.passed for o in required_outcomes) and bool(
            required_outcomes
        )

        verdict = (
            EvaluationVerdict.ACCEPTED
            if all_required_passed
            else EvaluationVerdict.REJECTED
        )

        return EvaluationResult(verdict=verdict, outcomes=outcomes, claims=claims)

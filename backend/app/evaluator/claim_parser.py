"""
Claim parser.

Per spec section 25: an LLM MAY be used to parse free-text solutions into
structured claims, but it must never be the thing that decides correctness.
Here it only ever produces a *candidate* mechanism/root-cause tag set; the
Evaluator's deterministic checks (app.evaluator.checks) make the actual
accept/reject decision.

If MOCK_LLM is on, or the LLM call fails, we fall back to deterministic
keyword matching against the scenario's known_mechanisms list -- so the
whole evaluation pipeline still works with zero network access.
"""
from __future__ import annotations

import json
import re

from app.core.config import Settings
from app.llm.base import LLMMessage
from app.llm.factory import FallbackLLM
from app.schemas.scenario import ScenarioDefinition


def _keyword_fallback_parse(
    scenario: ScenarioDefinition, solution_text: str
) -> dict:
    lowered = solution_text.lower()
    mechanisms = [
        m for m in scenario.evaluation.known_mechanisms if m.replace("_", " ") in lowered
        or m in lowered
    ]
    root_cause_ids = []
    gt_id = scenario.ground_truth.root_cause_id
    if gt_id.replace("_", " ") in lowered or gt_id in lowered:
        root_cause_ids.append(gt_id)
    # Also match root cause summary keywords loosely.
    summary_words = set(re.findall(r"[a-z0-9]+", scenario.ground_truth.mechanism.lower()))
    solution_words = set(re.findall(r"[a-z0-9]+", lowered))
    if len(summary_words & solution_words) >= max(2, len(summary_words) // 3):
        if gt_id not in root_cause_ids:
            root_cause_ids.append(gt_id)
    return {"mechanisms": mechanisms, "root_cause_ids": root_cause_ids}


async def parse_solution_claims(
    scenario: ScenarioDefinition, solution_text: str, settings: Settings
) -> dict:
    if settings.mock_llm:
        return _keyword_fallback_parse(scenario, solution_text)

    system_prompt = (
        "You extract structured claims from a technical incident solution. "
        "Given the candidate mechanism list, output ONLY a JSON object of "
        "the form {\"mechanisms\": [...], \"root_cause_ids\": [...]}. "
        "Only include mechanisms from the provided candidate list that are "
        "clearly present in the solution text. Do not include anything "
        "else. No markdown, no commentary, just the JSON object.\n\n"
        f"Candidate mechanisms: {scenario.evaluation.known_mechanisms}\n"
        f"Candidate root cause id: {scenario.ground_truth.root_cause_id}"
    )
    llm = FallbackLLM("gemini", settings)
    try:
        text, _ = await llm.generate(
            system_prompt,
            [LLMMessage(role="user", content=solution_text)],
            temperature=0.0,
        )
        cleaned = text.strip().strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("parsed claims not a dict")
        parsed.setdefault("mechanisms", [])
        parsed.setdefault("root_cause_ids", [])
        return parsed
    except Exception:
        # Never let a flaky LLM parse break evaluation -- fall back.
        return _keyword_fallback_parse(scenario, solution_text)

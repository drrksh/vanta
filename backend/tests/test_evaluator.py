from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.enums import EvaluationVerdict
from app.evaluator.evaluator import Evaluator


def _mock_settings():
    return Settings(mock_llm=True, database_url="sqlite+aiosqlite:///:memory:")


@pytest.mark.asyncio
async def test_correct_solution_via_read_your_writes_accepted(scenario_847):
    evaluator = Evaluator(_mock_settings())
    solution = {
        "root_cause": "stale read replica divergence / replication lag",
        "explanation": (
            "The display boards read from a replica that lags behind the "
            "primary, especially during the 08:40 batch job."
        ),
        "proposed_solution": (
            "Implement read_your_writes so that a client who just wrote an "
            "assignment change is routed to the primary for their next read, "
            "avoiding stale replica data."
        ),
        "implementation": "Use a session-sticky read-your-writes token.",
    }
    result = await evaluator.evaluate(scenario_847, solution)
    assert result.verdict == EvaluationVerdict.ACCEPTED


@pytest.mark.asyncio
async def test_correct_solution_via_different_valid_mechanism_also_accepted(
    scenario_847,
):
    """Multiple valid solution strategies must both pass (spec section 24)."""
    evaluator = Evaluator(_mock_settings())
    solution = {
        "root_cause": "stale read replica divergence",
        "explanation": "Replica lag causes room assignment reads to be stale.",
        "proposed_solution": (
            "Route critical reads for room assignment lookups directly to "
            "the primary database (route_critical_reads_to_primary) instead "
            "of the replica, at least for the display boards."
        ),
        "implementation": "Add a read-path flag for critical lookups.",
    }
    result = await evaluator.evaluate(scenario_847, solution)
    assert result.verdict == EvaluationVerdict.ACCEPTED


@pytest.mark.asyncio
async def test_wrong_root_cause_rejected(scenario_847):
    evaluator = Evaluator(_mock_settings())
    solution = {
        "root_cause": "campus wifi outage",
        "explanation": "We think the wifi was flaky during exam week.",
        "proposed_solution": "Upgrade the wifi routers.",
        "implementation": "Buy new access points.",
    }
    result = await evaluator.evaluate(scenario_847, solution)
    assert result.verdict == EvaluationVerdict.REJECTED


@pytest.mark.asyncio
async def test_correct_diagnosis_but_no_fix_mechanism_rejected(scenario_847):
    """Identifying the problem without proposing a working fix should fail."""
    evaluator = Evaluator(_mock_settings())
    solution = {
        "root_cause": "stale read replica divergence",
        "explanation": "The replica lags behind the primary sometimes.",
        "proposed_solution": "We should investigate further.",
        "implementation": "TBD",
    }
    result = await evaluator.evaluate(scenario_847, solution)
    assert result.verdict == EvaluationVerdict.REJECTED


@pytest.mark.asyncio
async def test_partial_solution_rejected(scenario_847):
    evaluator = Evaluator(_mock_settings())
    solution = {
        "root_cause": "",
        "explanation": "not sure",
        "proposed_solution": "add more servers",
        "implementation": "",
    }
    result = await evaluator.evaluate(scenario_847, solution)
    assert result.verdict == EvaluationVerdict.REJECTED


@pytest.mark.asyncio
async def test_contestant_view_never_reveals_failed_test_names(scenario_847):
    evaluator = Evaluator(_mock_settings())
    bad_solution = {
        "root_cause": "wifi",
        "explanation": "wifi bad",
        "proposed_solution": "new routers",
        "implementation": "buy routers",
    }
    result = await evaluator.evaluate(scenario_847, bad_solution)
    view = result.contestant_view()
    assert set(view.keys()) == {"verdict", "message"}
    for outcome in result.outcomes:
        assert outcome.test_id not in view["message"]
        assert outcome.description not in view["message"]
    assert "root_cause" not in view["message"].lower() or "root cause" in view[
        "message"
    ].lower() and scenario_847.ground_truth.root_cause_id not in view["message"]


@pytest.mark.asyncio
async def test_admin_view_reveals_full_test_detail(scenario_847):
    evaluator = Evaluator(_mock_settings())
    solution = {
        "root_cause": "stale read replica divergence",
        "explanation": "Replica lag.",
        "proposed_solution": "read_your_writes",
        "implementation": "session token routing",
    }
    result = await evaluator.evaluate(scenario_847, solution)
    admin_view = result.admin_view()
    assert "tests" in admin_view
    assert len(admin_view["tests"]) == len(scenario_847.evaluation.tests)
    for t in admin_view["tests"]:
        assert "passed" in t and "test_id" in t


@pytest.mark.asyncio
async def test_website_scenario_dns_solution_accepted(scenario_website):
    evaluator = Evaluator(_mock_settings())
    solution = {
        "root_cause": "dns ttl inconsistent propagation",
        "explanation": "TTL was left too high before the IP cutover.",
        "proposed_solution": (
            "Always lower_ttl_before_cutover well ahead of any planned IP "
            "change, and keep_old_ip_alive_during_propagation until the TTL "
            "window has fully elapsed."
        ),
        "implementation": "Update migration runbook.",
    }
    result = await evaluator.evaluate(scenario_website, solution)
    assert result.verdict == EvaluationVerdict.ACCEPTED


@pytest.mark.asyncio
async def test_website_scenario_wrong_cause_rejected(scenario_website):
    evaluator = Evaluator(_mock_settings())
    solution = {
        "root_cause": "ddos attack",
        "explanation": "Someone attacked us.",
        "proposed_solution": "Add a firewall.",
        "implementation": "Buy a firewall appliance.",
    }
    result = await evaluator.evaluate(scenario_website, solution)
    assert result.verdict == EvaluationVerdict.REJECTED

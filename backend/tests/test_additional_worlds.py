from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.enums import EvaluationVerdict
from app.evaluator.evaluator import Evaluator
from app.world.engine import World


def _mock_settings():
    return Settings(mock_llm=True, database_url="sqlite+aiosqlite:///:memory:")


# ---------------------------------------------------------------------
# Firewall checks across all 5 worlds (parametrized)
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture_name",
    ["scenario_847", "scenario_website", "scenario_breach", "scenario_checkout", "scenario_wrong_number"],
)
def test_no_agent_ever_granted_red_fact(fixture_name, request):
    scenario = request.getfixturevalue(fixture_name)
    red_ids = {f.id for f in scenario.facts if f.classification.value == "red"}
    assert red_ids, f"{scenario.id} should define at least one RED fact"
    for agent in scenario.agents:
        assert not (set(agent.knowledge_ids) & red_ids)
        assert not (set(agent.conditional_knowledge_ids.keys()) & red_ids)


@pytest.mark.parametrize(
    "fixture_name",
    ["scenario_847", "scenario_website", "scenario_breach", "scenario_checkout", "scenario_wrong_number"],
)
def test_scenario_validates_clean(fixture_name, request):
    scenario = request.getfixturevalue(fixture_name)
    assert scenario.validate_firewall() == []


# ---------------------------------------------------------------------
# Silent Breach (cybersecurity)
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_breach_correct_solution_accepted(scenario_breach):
    evaluator = Evaluator(_mock_settings())
    solution = {
        "root_cause": "leaked api key credential stuffing pivot",
        "explanation": (
            "An analytics API key was leaked in a public repo and had an "
            "overly broad database grant, letting the attacker query "
            "session tokens directly and replay one."
        ),
        "proposed_solution": (
            "revoke_and_rotate_leaked_credentials immediately, add "
            "pre_commit_secret_scanning to prevent future leaks, and apply "
            "least_privilege_db_grants so the analytics service account "
            "can't read the session tokens table."
        ),
        "implementation": "Rotate key, add gitleaks pre-commit hook, narrow DB grant.",
    }
    result = await evaluator.evaluate(scenario_breach, solution)
    assert result.verdict == EvaluationVerdict.ACCEPTED


@pytest.mark.asyncio
async def test_breach_malware_theory_rejected(scenario_breach):
    evaluator = Evaluator(_mock_settings())
    solution = {
        "root_cause": "malware infection",
        "explanation": "We think a virus got onto a server.",
        "proposed_solution": "Run a full antivirus scan and reimage the server.",
        "implementation": "Reimage all servers.",
    }
    result = await evaluator.evaluate(scenario_breach, solution)
    assert result.verdict == EvaluationVerdict.REJECTED


@pytest.mark.asyncio
async def test_breach_partial_fix_missing_access_control_rejected(scenario_breach):
    """Only rotating the key without fixing the broad DB grant should fail."""
    evaluator = Evaluator(_mock_settings())
    solution = {
        "root_cause": "leaked api key credential stuffing pivot",
        "explanation": "The API key leaked and was used to get in.",
        "proposed_solution": "revoke_and_rotate_leaked_credentials for the analytics key.",
        "implementation": "Rotate the key.",
    }
    result = await evaluator.evaluate(scenario_breach, solution)
    assert result.verdict == EvaluationVerdict.REJECTED


# ---------------------------------------------------------------------
# Slow Checkout (performance)
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_checkout_correct_solution_accepted(scenario_checkout):
    evaluator = Evaluator(_mock_settings())
    solution = {
        "root_cause": "connection pool exhaustion retry amplification",
        "explanation": (
            "A small slowdown from index maintenance saturates the "
            "undersized connection pool, and an aggressive no-backoff "
            "retry policy amplifies load on the same pool."
        ),
        "proposed_solution": (
            "Add exponential_backoff_with_jitter and a circuit_breaker to "
            "the database client's retry logic, and increase_connection_pool_size "
            "to match observed peak concurrency."
        ),
        "implementation": "Update HTTP client retry config; resize pool to 60.",
    }
    result = await evaluator.evaluate(scenario_checkout, solution)
    assert result.verdict == EvaluationVerdict.ACCEPTED


@pytest.mark.asyncio
async def test_checkout_retry_fix_alone_is_sufficient_for_required_tests(scenario_checkout):
    """Backoff/circuit-breaker alone satisfies the required tests (capacity fix is optional)."""
    evaluator = Evaluator(_mock_settings())
    solution = {
        "root_cause": "connection pool exhaustion retry amplification",
        "explanation": "Retry storm on top of pool saturation.",
        "proposed_solution": "Implement a retry_budget and circuit_breaker on DB calls.",
        "implementation": "Add circuit breaker library.",
    }
    result = await evaluator.evaluate(scenario_checkout, solution)
    assert result.verdict == EvaluationVerdict.ACCEPTED


@pytest.mark.asyncio
async def test_checkout_wrong_cause_cpu_scaling_rejected(scenario_checkout):
    evaluator = Evaluator(_mock_settings())
    solution = {
        "root_cause": "CPU overload",
        "explanation": "Servers must be running out of CPU under load.",
        "proposed_solution": "Add more server instances to scale horizontally.",
        "implementation": "Increase autoscaling group size.",
    }
    result = await evaluator.evaluate(scenario_checkout, solution)
    assert result.verdict == EvaluationVerdict.REJECTED


# ---------------------------------------------------------------------
# The Wrong Number (data engineering)
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wrong_number_correct_solution_accepted(scenario_wrong_number):
    evaluator = Evaluator(_mock_settings())
    solution = {
        "root_cause": "stale materialized view plus duplicate transfer records",
        "explanation": (
            "The dashboard lags due to a nightly materialized view refresh, "
            "and the Dean's office over-counts because transferred students "
            "get duplicate active enrollment rows that aren't filtered out."
        ),
        "proposed_solution": (
            "refresh_view_on_write_or_shorter_interval for the dashboard, and "
            "close_out_old_record_on_transfer plus "
            "filter_by_active_flag_in_aggregation for the enrollment counts."
        ),
        "implementation": "Trigger-based view refresh; fix transfer workflow to set end-date.",
    }
    result = await evaluator.evaluate(scenario_wrong_number, solution)
    assert result.verdict == EvaluationVerdict.ACCEPTED


@pytest.mark.asyncio
async def test_wrong_number_only_fixing_staleness_is_rejected(scenario_wrong_number):
    """Fixing only the dashboard lag without fixing duplicate counting should fail."""
    evaluator = Evaluator(_mock_settings())
    solution = {
        "root_cause": "stale materialized view plus duplicate transfer records",
        "explanation": "The dashboard is stale.",
        "proposed_solution": "real_time_or_near_real_time_sync for the dashboard view.",
        "implementation": "Switch to CDC-based sync.",
    }
    result = await evaluator.evaluate(scenario_wrong_number, solution)
    assert result.verdict == EvaluationVerdict.REJECTED


@pytest.mark.asyncio
async def test_wrong_number_wrong_cause_rejected(scenario_wrong_number):
    evaluator = Evaluator(_mock_settings())
    solution = {
        "root_cause": "someone entered the wrong number manually",
        "explanation": "Probably a typo somewhere.",
        "proposed_solution": "Ask staff to double check their entries.",
        "implementation": "Add a manual review step.",
    }
    result = await evaluator.evaluate(scenario_wrong_number, solution)
    assert result.verdict == EvaluationVerdict.REJECTED


# ---------------------------------------------------------------------
# World engine smoke tests for the new worlds' conditional knowledge chains
# ---------------------------------------------------------------------


def test_breach_security_engineer_needs_two_prereqs(scenario_breach):
    w = World("w1", scenario_breach, seed=1)
    unlocked = w.conditional_facts_unlocked("security_engineer", discovered_fact_ids=set())
    assert "fact_security_engineer_session_replay_theory" not in {f.id for f in unlocked}

    unlocked = w.conditional_facts_unlocked(
        "security_engineer",
        discovered_fact_ids={
            "fact_security_engineer_repo_is_public",
            "fact_dba_grant_scope_broad",
        },
    )
    assert "fact_security_engineer_session_replay_theory" in {f.id for f in unlocked}


def test_wrong_number_data_engineer_chain(scenario_wrong_number):
    w = World("w1", scenario_wrong_number, seed=1)
    # Nothing discovered yet -> locked.
    unlocked = w.conditional_facts_unlocked("data_engineer", discovered_fact_ids=set())
    assert not unlocked

    # First prereq only -> first conditional fact unlocks, not the later ones.
    unlocked = w.conditional_facts_unlocked(
        "data_engineer", discovered_fact_ids={"fact_deans_office_higher_than_expected"}
    )
    unlocked_ids = {f.id for f in unlocked}
    assert "fact_data_engineer_transfer_workflow" in unlocked_ids
    assert "fact_data_engineer_duplicate_confirmed" not in unlocked_ids

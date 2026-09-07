from __future__ import annotations

import pytest

from app.schemas.scenario import ScenarioDefinition
from app.scenarios.loader import (
    ScenarioValidationError,
    load_all_scenarios,
    load_scenario_file,
)


def test_all_scenarios_load_and_validate(scenarios_dir):
    scenarios = load_all_scenarios(scenarios_dir)
    assert len(scenarios) >= 2
    for sid, scenario in scenarios.items():
        assert isinstance(scenario, ScenarioDefinition)
        problems = scenario.validate_firewall()
        assert problems == [], f"{sid} has firewall problems: {problems}"


def test_847_has_red_facts_not_granted_to_any_agent(scenario_847):
    red_ids = {f.id for f in scenario_847.facts if f.classification.value == "red"}
    assert red_ids, "expected at least one RED fact"
    for agent in scenario_847.agents:
        assert not (set(agent.knowledge_ids) & red_ids)
        assert not (set(agent.conditional_knowledge_ids.keys()) & red_ids)


def test_scenario_rejects_agent_granted_red_fact(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text(
        """
id: bad_scenario
title: Bad
domain: test
briefing: test
ground_truth:
  root_cause_id: x
  root_cause_summary: x
  mechanism: x
facts:
  - id: secret_fact
    text: the secret
    classification: red
agents:
  - id: leaky_agent
    role: role
    display_name: Leaky
    personality: p
    provider: mock
    knowledge_ids: [secret_fact]
evaluation:
  tests:
    - id: t1
      description: d
      check: identifies_root_cause
      params: {}
"""
    )
    with pytest.raises(ScenarioValidationError) as exc_info:
        load_scenario_file(bad_yaml)
    assert "FIREWALL BREACH" in str(exc_info.value)


def test_duplicate_scenario_ids_rejected(tmp_path):
    (tmp_path / "a.yaml").write_text(_minimal_scenario_yaml("dup_id"))
    (tmp_path / "b.yaml").write_text(_minimal_scenario_yaml("dup_id"))
    with pytest.raises(ValueError, match="Duplicate scenario id"):
        load_all_scenarios(tmp_path)


def _minimal_scenario_yaml(scenario_id: str) -> str:
    return f"""
id: {scenario_id}
title: Minimal
domain: test
briefing: test briefing
ground_truth:
  root_cause_id: rc1
  root_cause_summary: s
  mechanism: m
facts:
  - id: f1
    text: public fact
    classification: green
  - id: f2
    text: secret fact
    classification: red
agents:
  - id: a1
    role: role
    display_name: A1
    personality: p
    provider: mock
    knowledge_ids: [f1]
evaluation:
  tests:
    - id: t1
      description: d
      check: identifies_root_cause
      params:
        accepted_root_cause_ids: [rc1]
"""

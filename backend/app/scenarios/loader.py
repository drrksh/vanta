from __future__ import annotations

import os
from pathlib import Path

import yaml

from app.schemas.scenario import ScenarioDefinition


class ScenarioValidationError(Exception):
    def __init__(self, scenario_id: str, problems: list[str]):
        self.scenario_id = scenario_id
        self.problems = problems
        super().__init__(
            f"Scenario '{scenario_id}' failed validation:\n"
            + "\n".join(f"  - {p}" for p in problems)
        )


def _iter_yaml_files(root: Path):
    for path in sorted(root.rglob("*.yaml")):
        yield path
    for path in sorted(root.rglob("*.yml")):
        yield path


def load_scenario_file(path: str | Path) -> ScenarioDefinition:
    path = Path(path)
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    scenario = ScenarioDefinition.model_validate(raw)
    problems = scenario.validate_firewall()
    if problems:
        raise ScenarioValidationError(scenario.id, problems)
    return scenario


def load_all_scenarios(scenarios_dir: str | Path) -> dict[str, ScenarioDefinition]:
    root = Path(scenarios_dir)
    scenarios: dict[str, ScenarioDefinition] = {}
    if not root.exists():
        return scenarios
    for path in _iter_yaml_files(root):
        scenario = load_scenario_file(path)
        if scenario.id in scenarios:
            raise ValueError(f"Duplicate scenario id '{scenario.id}' found at {path}")
        scenarios[scenario.id] = scenario
    return scenarios


class ScenarioRegistry:
    """
    In-memory registry loaded once at startup. Scenarios are static,
    human-authored configuration -- not something the LLM ever mutates
    at runtime (spec section 29).
    """

    def __init__(self, scenarios_dir: str | Path):
        self._scenarios_dir = Path(scenarios_dir)
        self._scenarios: dict[str, ScenarioDefinition] = {}
        self.reload()

    def reload(self) -> None:
        self._scenarios = load_all_scenarios(self._scenarios_dir)

    def get(self, scenario_id: str) -> ScenarioDefinition:
        if scenario_id not in self._scenarios:
            raise KeyError(f"Unknown scenario id '{scenario_id}'")
        return self._scenarios[scenario_id]

    def list_ids(self) -> list[str]:
        return sorted(self._scenarios.keys())

    def all(self) -> dict[str, ScenarioDefinition]:
        return dict(self._scenarios)

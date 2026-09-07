from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

SCENARIOS_DIR = BACKEND_ROOT.parent / "scenarios"


@pytest.fixture(scope="session")
def scenarios_dir() -> Path:
    return SCENARIOS_DIR


@pytest.fixture
def scenario_847(scenarios_dir):
    from app.scenarios.loader import load_scenario_file

    return load_scenario_file(
        scenarios_dir / "distributed_systems" / "the_847_problem.yaml"
    )


@pytest.fixture
def scenario_website(scenarios_dir):
    from app.scenarios.loader import load_scenario_file

    return load_scenario_file(scenarios_dir / "networking" / "vanishing_website.yaml")


@pytest.fixture
def scenario_breach(scenarios_dir):
    from app.scenarios.loader import load_scenario_file

    return load_scenario_file(scenarios_dir / "cybersecurity" / "silent_breach.yaml")


@pytest.fixture
def scenario_checkout(scenarios_dir):
    from app.scenarios.loader import load_scenario_file

    return load_scenario_file(scenarios_dir / "performance" / "slow_checkout.yaml")


@pytest.fixture
def scenario_wrong_number(scenarios_dir):
    from app.scenarios.loader import load_scenario_file

    return load_scenario_file(scenarios_dir / "data_engineering" / "wrong_number.yaml")


@pytest.fixture
def mock_settings():
    from app.core.config import Settings

    return Settings(mock_llm=True, database_url="sqlite+aiosqlite:///:memory:")

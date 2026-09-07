from __future__ import annotations

import os
import tempfile

import pytest


@pytest.fixture
def bot_state_module(monkeypatch):
    state_path = tempfile.mktemp()
    monkeypatch.setenv("VANTA_BOT_STATE_PATH", state_path)
    import importlib

    import bot.adapters.state as state_module

    importlib.reload(state_module)  # pick up the env var for STATE_PATH
    yield state_module
    if os.path.exists(state_path):
        os.remove(state_path)


def _make_ic(state_module, **overrides):
    defaults = dict(
        investigation_id="inv1",
        world_id="w1",
        scenario_id="s1",
        guild_id=1,
        category_id=100,
        briefing_channel_id=101,
        evidence_channel_id=102,
        hypotheses_channel_id=103,
        solution_channel_id=104,
        agent_channels={"student": 200, "developer": 201},
    )
    defaults.update(overrides)
    return state_module.InvestigationChannels(**defaults)


def test_find_by_channel_returns_agent_id(bot_state_module):
    state = bot_state_module.BotState()
    ic = _make_ic(bot_state_module)
    state.add_investigation(ic)

    found = state.find_by_channel(200)
    assert found is not None
    ic_found, agent_id = found
    assert agent_id == "student"
    assert ic_found.investigation_id == "inv1"


def test_find_by_channel_unknown_returns_none(bot_state_module):
    state = bot_state_module.BotState()
    state.add_investigation(_make_ic(bot_state_module))
    assert state.find_by_channel(99999) is None


def test_find_by_category(bot_state_module):
    state = bot_state_module.BotState()
    state.add_investigation(_make_ic(bot_state_module))
    found = state.find_by_category(100)
    assert found is not None
    assert found.investigation_id == "inv1"
    assert state.find_by_category(999) is None


def test_persistence_round_trip(bot_state_module):
    state = bot_state_module.BotState()
    state.add_investigation(_make_ic(bot_state_module))

    # Fresh instance should reload from disk.
    state2 = bot_state_module.BotState()
    found = state2.find_by_channel(201)
    assert found is not None
    assert found[1] == "developer"


def test_multiple_investigations_do_not_collide(bot_state_module):
    state = bot_state_module.BotState()
    state.add_investigation(
        _make_ic(
            bot_state_module,
            investigation_id="inv1",
            category_id=100,
            agent_channels={"student": 200},
        )
    )
    state.add_investigation(
        _make_ic(
            bot_state_module,
            investigation_id="inv2",
            category_id=500,
            agent_channels={"student": 600},
        )
    )
    found1 = state.find_by_channel(200)
    found2 = state.find_by_channel(600)
    assert found1[0].investigation_id == "inv1"
    assert found2[0].investigation_id == "inv2"


def test_admin_category_tracking(bot_state_module):
    state = bot_state_module.BotState()
    assert not state.is_admin_category(guild_id=1, category_id=999)
    state.admin_categories[1] = 999
    assert state.is_admin_category(guild_id=1, category_id=999)
    assert not state.is_admin_category(guild_id=2, category_id=999)

"""
These tests require the VANTA backend to be running and reachable at
VANTA_BACKEND_URL (defaults to http://127.0.0.1:8811), with MOCK_LLM=true.
They are skipped automatically if the backend is not reachable, so they
don't break `pytest` runs in environments without the backend up.
"""
from __future__ import annotations

import httpx
import pytest

from bot.adapters.vanta_client import VantaAPIError, VantaClient

BACKEND_URL = "http://127.0.0.1:8811"


def _backend_reachable() -> bool:
    try:
        httpx.get(f"{BACKEND_URL}/health", timeout=1.0)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _backend_reachable(), reason="VANTA backend not running at " + BACKEND_URL
)


@pytest.fixture
def client():
    return VantaClient(base_url=BACKEND_URL)


@pytest.mark.asyncio
async def test_list_worlds_includes_known_scenarios(client):
    worlds = await client.list_worlds()
    ids = {w["scenario_id"] for w in worlds}
    assert "the_847_problem" in ids
    assert "vanishing_website" in ids


@pytest.mark.asyncio
async def test_full_bot_side_flow_reject_then_accept(client):
    world = await client.start_world("the_847_problem")
    inv = await client.create_investigation(world["world_id"], "pytest-bot-user")
    assert inv["agents"]

    resp = await client.send_message(
        inv["investigation_id"], "developer", "Where does the display board get its data from?"
    )
    assert resp["text"]

    evidence = await client.list_evidence(inv["investigation_id"])
    assert isinstance(evidence, list)

    h = await client.create_hypothesis(inv["investigation_id"], "stale replica reads")
    assert h["text"] == "stale replica reads"

    bad = await client.submit_solution(
        inv["investigation_id"],
        {
            "root_cause": "wifi",
            "explanation": "wifi bad",
            "proposed_solution": "buy routers",
            "implementation": "",
        },
    )
    assert bad["verdict"] == "rejected"

    good = await client.submit_solution(
        inv["investigation_id"],
        {
            "root_cause": "stale read replica divergence",
            "explanation": "replication lag from the batch job",
            "proposed_solution": "read_your_writes for the room lookup path",
            "implementation": "session token forces primary reads post-write",
        },
    )
    assert good["verdict"] == "accepted"


@pytest.mark.asyncio
async def test_admin_calls_require_credentials(client, monkeypatch):
    world = await client.start_world("the_847_problem")

    # Correct creds (defaults from env in this fixture's process) succeed.
    gt = await client.admin_ground_truth(world["world_id"])
    assert "root_cause_id" in gt

    # Wrong creds should be rejected with 401.
    import bot.adapters.vanta_client as vc_module

    monkeypatch.setattr(vc_module, "ADMIN_PASSWORD", "wrong-password")
    bad_client = VantaClient(base_url=BACKEND_URL)
    with pytest.raises(VantaAPIError) as exc_info:
        await bad_client.admin_ground_truth(world["world_id"])
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_unknown_scenario_raises_api_error(client):
    with pytest.raises(VantaAPIError) as exc_info:
        await client.start_world("does_not_exist_scenario")
    assert exc_info.value.status_code == 404

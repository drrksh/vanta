from __future__ import annotations

import httpx
import pytest

from app.core import profiles as profiles_mod
from app.core import world_manager as wm_mod
from app.core.profiles import ProfileStore, recommended_difficulty
from app.evolution.reference_fixes import REFERENCE_FIXES
from app.execution.c_sandbox import CSandbox
from app.investigation.probes import ProbeError, probe_kit
from app.investigation.witnesses import witness_kit
from app.worldgen.archetypes.pool_leak import PoolLeakArchetype
from app.worldgen.archetypes.starvation import StarvationArchetype

SB = CSandbox(timeout_seconds=20.0, fast=False)


def _world_with_variant(arch, variant):
    for seed in range(1, 200):
        w = arch.generate(seed)
        if w.params["bug_variant"] == variant:
            return w
    raise AssertionError(f"no seed produced {variant}")


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db = tmp_path / "vanta_test.db"
    monkeypatch.setattr(wm_mod, "DB_PATH", db)
    monkeypatch.setattr(profiles_mod, "DB_PATH", db)
    return db


# --- Probe lab ---------------------------------------------------------------

async def test_probe_reveals_starvation_and_fix_relieves_it():
    w = _world_with_variant(StarvationArchetype(), "pure_shortest_first")
    p = w.params
    scenario = {"days": 5, "jobs": [
        {"minutes": p["small_job_minutes"], "at": 0, "repeat": 300, "every": p["small_interval"]},
        {"minutes": p["big_job_minutes"], "at": 30},
    ]}
    kit = probe_kit(w)
    orig = await kit.run(w, scenario, w.starter_source, SB)
    fixed = await kit.run(w, scenario, REFERENCE_FIXES[w.archetype_id][1](w), SB)
    assert orig.ok and fixed.ok
    big = lambda tr: next(j for j in tr["jobs"] if j["minutes"] == p["big_job_minutes"])  # noqa: E731
    wait_orig = big(orig.trace)["wait"] or 10**9
    assert big(fixed.trace)["wait"] is not None
    assert wait_orig > big(fixed.trace)["wait"]


async def test_probe_on_pool_shows_double_release_difference():
    w = _world_with_variant(PoolLeakArchetype(), "linear_search_first_match")
    kit = probe_kit(w)
    sc = {"ops": [{"op": "checkout", "holder": 5}, {"op": "release", "holder": 5},
                  {"op": "release", "holder": 5}]}
    orig = await kit.run(w, sc, w.starter_source, SB)
    fixed = await kit.run(w, sc, REFERENCE_FIXES[w.archetype_id][0](w), SB)
    assert [o["outcome"] for o in orig.trace["ops"]] == ["got_slot", "accepted", "accepted"]
    assert [o["outcome"] for o in fixed.trace["ops"]] == ["got_slot", "accepted", "refused"]


@pytest.mark.parametrize("scenario", [
    {"jobs": []},
    {"jobs": [{"minutes": "5); system(\"x\"); (", "at": 0}]},
    {"jobs": [{"minutes": 5, "at": -1}]},
    {"jobs": [{"minutes": 5, "at": 0, "repeat": 10_000}]},
    "not an object",
])
def test_probe_rejects_bad_scenarios(scenario):
    w = StarvationArchetype().generate(4)
    with pytest.raises(ProbeError):
        probe_kit(w).normalize(w, scenario)


async def test_probe_reports_compile_errors_in_contestant_code():
    w = PoolLeakArchetype().generate(2)
    out = await probe_kit(w).run(w, {"ops": [{"op": "checkout", "holder": 1}]}, "int x = ;", SB)
    assert not out.ok and out.error == "compile_error"


# --- Witnesses ---------------------------------------------------------------

@pytest.mark.parametrize("arch", [StarvationArchetype(), PoolLeakArchetype()])
async def test_every_witness_answers_every_question_deterministically(arch):
    w = arch.generate(9)
    kit = witness_kit(w)
    for wit in kit.public(w):
        for q in wit["questions"]:
            a1 = await kit.ask(w, "det", wit["key"], SB, topic=q["topic"])
            a2 = await kit.ask(w, "det", wit["key"], SB, topic=q["topic"])
            assert a1["text"] and "error" not in a1
            assert a1["text"] == a2["text"]


async def test_witness_deflects_requests_for_the_solution():
    w = PoolLeakArchetype().generate(3)
    kit = witness_kit(w)
    a = await kit.ask(w, "defl", "staff", SB, question="How do I fix the code?")
    assert a["topic"] == "deflect"
    a = await kit.ask(w, "defl", "staff", SB, question="purple elephants")
    assert a["topic"] == "unknown" and a["followups"]


async def test_free_text_routes_to_a_topic():
    w = StarvationArchetype().generate(3)
    kit = witness_kit(w)
    a = await kit.ask(w, "route", "big", SB, question="how long did you have to wait?")
    assert a["topic"] == "worst"


@pytest.mark.parametrize("variant", ["linear_search_first_match", "off_by_one_index",
                                     "no_double_checkout_guard"])
async def test_auditor_books_disagree_originally_and_agree_under_a_fix(variant):
    w = _world_with_variant(PoolLeakArchetype(), variant)
    kit = witness_kit(w)
    fix = REFERENCE_FIXES[w.archetype_id][1](w)
    a = await kit.ask(w, f"aud-{variant}", "auditor", SB, topic="reconcile", source=fix)
    assert "don't agree" in a["text"]
    assert "All three agree" in a["replay"]["text"]


async def test_replay_with_broken_code_is_reported_not_raised():
    w = StarvationArchetype().generate(5)
    kit = witness_kit(w)
    a = await kit.ask(w, "broken", "operator", SB, topic="utilization", source="int nope(")
    assert a["replay"]["error"] == "compile_error"


# --- Adaptive difficulty -----------------------------------------------------

def test_rating_moves_with_results(tmp_db):
    store = ProfileStore()
    base = store.rating("u1")
    r1 = store.record_submission("u1", "w1", 0.5, "rejected", passed=4, total=8)
    assert r1.after < base
    r2 = store.record_submission("u1", "w1", 0.5, "accepted", passed=8, total=8)
    assert r2.after > r1.after
    r3 = store.record_submission("u1", "w1", 0.5, "accepted", passed=8, total=8)
    assert not r3.counted and r3.after == r2.after
    prof = store.profile("u1")
    assert prof["worlds_solved"] == 1 and prof["submissions"] == 3
    assert prof["recommended_difficulty"] > recommended_difficulty(base)


def test_recommended_difficulty_spans_beginner_to_expert():
    assert recommended_difficulty(700) == 0.1
    assert recommended_difficulty(2400) == 0.95
    assert recommended_difficulty(1100) < recommended_difficulty(1500)


# --- HTTP --------------------------------------------------------------------

async def test_investigation_api_end_to_end(tmp_db):
    from main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t", timeout=120) as c:
        w = (await c.post("/api/worlds", json={"created_by": "e2e", "archetype_id": "pool_leak",
                                                "seed": 11})).json()
        assert w["calibrated"] is True
        wid = w["world_id"]
        info = (await c.get(f"/api/worlds/{wid}/probe")).json()
        assert info["kind"] == "pool"
        pr = (await c.post(f"/api/worlds/{wid}/probe",
                           json={"scenario": info["template"], "user_id": "e2e"})).json()
        assert pr["ok"] and pr["trace"]["ops"]
        bad = await c.post(f"/api/worlds/{wid}/probe", json={"scenario": {"ops": "x"}})
        assert bad.status_code == 422
        wits = (await c.get(f"/api/worlds/{wid}/witnesses")).json()
        assert len(wits) >= 4
        ans = (await c.post(f"/api/worlds/{wid}/witnesses/{wits[0]['key']}/ask",
                            json={"topic": wits[0]["questions"][0]["topic"], "user_id": "e2e"})).json()
        assert ans["text"]
        sub = (await c.post(f"/api/worlds/{wid}/submit",
                            json={"c_source": w["starter_source"], "user_id": "e2e"})).json()
        assert sub["verdict"] == "rejected" and "rating" in sub
        prof = (await c.get("/api/profiles/e2e")).json()
        assert prof["experiments_run"] == 1 and prof["witness_questions"] == 1
        assert prof["submissions"] == 1

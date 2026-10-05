from __future__ import annotations

import httpx
import pytest

from app.core import profiles as profiles_mod
from app.core import world_manager as wm_mod
from app.core.cohorts import CohortError, CohortForbidden, CohortStore
from app.core.originality import analyze, jaccard, novel_fingerprints
from app.core.world_manager import WorldManager
from app.evolution.reference_fixes import REFERENCE_FIXES
from app.worldgen.archetypes.pool_leak import PoolLeakArchetype


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db = tmp_path / "vanta_cohort.db"
    monkeypatch.setattr(wm_mod, "DB_PATH", db)
    monkeypatch.setattr(profiles_mod, "DB_PATH", db)
    return db


def _rename_locals(src: str) -> str:
    return src.replace("(int i = ", "(int k = ").replace("i < poolSize", "k < poolSize") \
              .replace("i--", "k--").replace("i++", "k++").replace("pool[i]", "pool[k]") \
              .replace("return i;", "return k;").replace("i = poolSize", "k = poolSize")


# --- originality -------------------------------------------------------------

def test_pinned_worlds_share_defect_but_not_names():
    arch = PoolLeakArchetype()
    pins = {"variant": "off_by_one_index", "domain": 2}
    a, b = arch.generate(101, pins=pins), arch.generate(202, pins=pins)
    assert a.params["bug_variant"] == b.params["bug_variant"] == "off_by_one_index"
    assert a.params["domain_index"] == b.params["domain_index"] == 2
    assert a.briefing.split(" manages")[0] == b.briefing.split(" manages")[0]
    assert (a.params["struct_name"], a.params["checkout_func"], a.params["release_func"]) != \
           (b.params["struct_name"], b.params["checkout_func"], b.params["release_func"])


def test_originality_sees_through_renaming_and_separates_approaches():
    arch = PoolLeakArchetype()
    pins = {"variant": "linear_search_first_match", "domain": 0}
    w1, w2, w3, w4 = (arch.generate(s, pins=pins) for s in (11, 22, 33, 44))
    fwd, bwd = REFERENCE_FIXES["pool_leak"]
    s1 = fwd(w1)
    s2 = _rename_locals(fwd(w2))           # same approach, different world + variable names
    s3 = bwd(w3)                            # genuinely different traversal
    # Same approach in different worlds normalizes to the same novel content.
    assert jaccard(novel_fingerprints(s1, w1), novel_fingerprints(s2, w2)) > 0.85
    assert jaccard(novel_fingerprints(s1, w1), novel_fingerprints(s3, w3)) < 0.55
    report = analyze([
        {"member": "A", "world": w1, "source": s1, "accepted": True},
        {"member": "B", "world": w2, "source": s2, "accepted": True},
        {"member": "C", "world": w3, "source": s3, "accepted": True},
        {"member": "D", "world": w4, "source": w4.starter_source, "accepted": False},
    ])
    assert report["distinct_approaches"] == 2
    assert sorted(map(sorted, report["approaches"])) == [["A", "B"], ["C"]]
    assert report["unchanged_from_starter"] == ["D"]
    assert any({p["a"], p["b"]} == {"A", "B"} for p in report["near_identical"])


# --- cohort store ------------------------------------------------------------

async def test_cohort_gives_each_member_a_unique_world_with_the_same_defect(tmp_db):
    store = CohortStore(WorldManager())
    c = store.create("host1", "Lab 3", archetype_id="pool_leak", target_difficulty=0.4)
    assert len(c.code) == 6 and c.status == "open"
    worlds = []
    for u in ("ana", "ben", "cai"):
        member, rec = await store.join(c.code, u, u.title())
        assert not member["rejoined"]
        worlds.append(rec.world)
    assert {w.params["bug_variant"] for w in worlds} == {c.pins["variant"]}
    assert {w.params["domain_index"] for w in worlds} == {c.pins["domain"]}
    sigs = {(w.params["struct_name"], w.params["checkout_func"], w.params["release_func"])
            for w in worlds}
    assert len(sigs) == 3
    assert len({w.starter_source for w in worlds}) == 3

    again, rec = await store.join(c.code.lower(), "ana", "Ana")
    assert again["rejoined"] and rec.world.starter_source == worlds[0].starter_source

    with pytest.raises(CohortForbidden):
        store.host_view(c.code, "ana")
    store.close(c.code, "host1")
    with pytest.raises(CohortError):
        await store.join(c.code, "dee", "Dee")
    _, rec = await store.join(c.code, "ben", "Ben")   # existing members can still get back in
    assert rec.world.starter_source == worlds[1].starter_source


async def test_host_view_tracks_progress_and_approaches(tmp_db):
    store = CohortStore(WorldManager())
    c = store.create("h", "Demo", archetype_id="pool_leak")
    recs = {}
    for u in ("u1", "u2", "u3"):
        _, recs[u] = await store.join(c.code, u, u.upper())
    fwd, bwd = REFERENCE_FIXES["pool_leak"]
    store.record_submission(recs["u1"].world_id, "accepted", 8, 8, fwd(recs["u1"].world))
    store.record_submission(recs["u2"].world_id, "accepted", 8, 8, bwd(recs["u2"].world))
    store.record_submission(recs["u3"].world_id, "rejected", 6, 8, recs["u3"].world.starter_source)
    view = store.host_view(c.code, "h")
    by = {m["display_name"]: m for m in view["members"]}
    assert by["U1"]["solved"] and by["U2"]["solved"] and not by["U3"]["solved"]
    assert view["solved_count"] == 2
    assert view["originality"]["distinct_approaches"] == 2
    assert view["originality"]["unchanged_from_starter"] == ["U3"]
    assert view["defect_variant"] == c.pins["variant"] and view["setting"]
    assert store.delete(c.code, "h") == 3


# --- HTTP --------------------------------------------------------------------

async def test_cohort_api_and_world_ownership(tmp_db):
    from main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t", timeout=120) as c:
        co = (await c.post("/api/cohorts", json={"host_id": "prof", "name": "CS1",
                                                 "archetype_id": "pool_leak"})).json()
        code = co["code"]
        info = (await c.get(f"/api/cohorts/{code}", params={"user_id": "stu"})).json()
        assert info["member_count"] == 0 and info["membership"] is None
        j = (await c.post(f"/api/cohorts/{code}/join",
                          json={"user_id": "stu", "display_name": "Student"})).json()
        wid = j["world"]["world_id"]
        assert j["world"]["cohort"]["code"] == code
        w = (await c.get(f"/api/worlds/{wid}")).json()
        assert w["cohort"]["display_name"] == "Student"
        sub = (await c.post(f"/api/worlds/{wid}/submit",
                            json={"c_source": w["starter_source"], "user_id": "stu"})).json()
        assert sub["verdict"] == "rejected"
        assert (await c.get(f"/api/cohorts/{code}/host", params={"host_id": "stu"})).status_code == 403
        host = (await c.get(f"/api/cohorts/{code}/host", params={"host_id": "prof"})).json()
        assert host["members"][0]["submissions"] == 1
        assert (await c.get("/api/cohorts", params={"host_id": "prof"})).json()[0]["code"] == code

        # Ownership: nobody deletes someone else's world without admin rights.
        assert (await c.delete(f"/api/worlds/{wid}", params={"requested_by": "intruder"})).status_code == 403
        assert (await c.delete("/api/worlds")).status_code == 403
        assert (await c.delete("/api/worlds", headers={"X-Vanta-Admin": "x"})).status_code == 200

        bad = await c.post("/api/cohorts/NOPE99/join", json={"user_id": "a", "display_name": "a"})
        assert bad.status_code == 404
        assert (await c.delete(f"/api/cohorts/{code}", params={"host_id": "stu"})).status_code == 403
        assert (await c.delete(f"/api/cohorts/{code}", params={"host_id": "prof"})).status_code == 200
        assert (await c.get(f"/api/cohorts/{code}")).status_code == 404


def test_starter_code_never_explains_its_own_bug():
    from app.worldgen.registry import ARCHETYPES_BY_ID

    for arch in ARCHETYPES_BY_ID.values():
        for v in arch.variants:
            src = arch.generate(5, pins={"variant": v}).starter_source
            assert "/*" not in src and "//" not in src, (arch.id, v)
            assert "(void)" not in src, (arch.id, v)

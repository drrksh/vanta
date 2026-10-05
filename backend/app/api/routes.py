from __future__ import annotations

import hmac
import logging
import os

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.cohorts import CohortError, CohortStore
from app.core.profiles import ProfileStore
from app.core.world_manager import WorldManager, WorldNotFoundError
from app.evolution.engine import EvolutionEngine
from app.execution.c_sandbox import CSandbox
from app.investigation.probes import ProbeError, probe_kit
from app.investigation.witnesses import witness_kit
from app.worldgen.evaluate import evaluate_submission
from app.worldgen.registry import ARCHETYPES_BY_ID, WorldGenerationError

router = APIRouter(prefix="/api", tags=["vanta"])

# One manager (fast internal sandbox for generation) and one sanitized
# sandbox for contestant-facing evaluation.
_manager = WorldManager(engine=EvolutionEngine())
_eval_sandbox = CSandbox(timeout_seconds=15.0, fast=False)
_profiles = ProfileStore()
_cohorts = CohortStore(_manager)

log = logging.getLogger("vanta")


def _is_admin(token: str | None) -> bool:
    """Admin operations (delete every world, act on someone else's world or
    cohort) need an X-Vanta-Admin header. If VANTA_ADMIN_TOKEN is set the
    header must match it; with no token configured (local demo) any
    X-Vanta-Admin header is accepted. Without the header, callers can only
    act on what they own."""
    if not token:
        return False
    expected = os.environ.get("VANTA_ADMIN_TOKEN")
    if not expected:
        return True
    return hmac.compare_digest(token, expected)


def _cohort_call(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except CohortError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc))


class CreateWorldRequest(BaseModel):
    created_by: str
    seed: int | None = None
    # None = calibrate to this user's current rating.
    target_difficulty: float | None = None
    archetype_id: str | None = None


class SubmitRequest(BaseModel):
    c_source: str
    user_id: str | None = None


class ProbeRequest(BaseModel):
    scenario: dict
    c_source: str | None = None   # None = run the original (broken) system
    user_id: str | None = None


class AskRequest(BaseModel):
    question: str | None = None
    topic: str | None = None
    c_source: str | None = None   # set = also relive the period under this code
    user_id: str | None = None


def _record(world_id: str):
    try:
        return _manager.get_world(world_id)
    except WorldNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


def _summary(r) -> dict:
    return {
        "world_id": r.world_id, "title": r.world.title, "archetype_id": r.archetype_id,
        "created_by": r.created_by, "seed": r.seed,
        "target_difficulty": r.target_difficulty, "viable": r.viable,
    }


def _public(r) -> dict:
    w = r.world
    return {
        **_summary(r),
        "briefing": w.briefing, "specification": w.specification,
        "starter_source": w.starter_source, "function_name": w.function_name,
        "function_signature": w.function_signature,
        "mandatory_properties": w.mandatory_properties,
        "optional_objectives": w.optional_objectives,
        "sample_input_description": w.sample_input_description,
        "cohort": _cohort_link(r.world_id),
    }


def _cohort_link(world_id: str) -> dict | None:
    link = _cohorts.for_world(world_id)
    return {"code": link["code"], "name": link["name"],
            "display_name": link["display_name"]} if link else None


@router.get("/archetypes")
async def list_archetypes():
    return [{"id": a.id, "title": a.title, "domain": a.domain} for a in ARCHETYPES_BY_ID.values()]


@router.post("/worlds")
async def create_world(body: CreateWorldRequest):
    calibrated = body.target_difficulty is None
    target = _profiles.recommended(body.created_by) if calibrated else body.target_difficulty
    try:
        r = await _manager.create_world(
            created_by=body.created_by, seed=body.seed,
            target_difficulty=target, archetype_id=body.archetype_id,
        )
    except WorldGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {**_public(r), "calibrated": calibrated}


@router.get("/worlds")
async def list_worlds(created_by: str | None = None):
    return [_summary(r) for r in _manager.list_worlds(created_by=created_by)]


@router.get("/worlds/{world_id}")
async def get_world(world_id: str):
    return _public(_record(world_id))


@router.post("/worlds/{world_id}/submit")
async def submit(world_id: str, body: SubmitRequest):
    r = _record(world_id)
    result = await evaluate_submission(r.world, body.c_source, _eval_sandbox)
    tests = result.get("tests", [])
    user = body.user_id or r.created_by
    passed = sum(1 for t in tests if t["passed"])
    change = _profiles.record_submission(
        user, world_id, r.target_difficulty, result["verdict"], passed=passed, total=len(tests),
    )
    _cohorts.record_submission(world_id, result["verdict"], passed, len(tests), body.c_source)
    # Contestant-safe: verdict + which named tests passed/failed, never the
    # hidden ground truth or reference fixes.
    return {
        "verdict": result["verdict"],
        "reason": result.get("reason"),
        "detail": result.get("detail") if result.get("reason") in ("compile_error", "timeout") else None,
        "tests": _contestant_tests(tests),
        "rating": {"before": change.before, "after": change.after, "counted": change.counted},
    }


def _contestant_tests(tests: list[dict]) -> list[dict]:
    """Public checks keep their names. Hidden checks are numbered, never
    named: a name like 'hidden_starvation_stream' would hand over the
    scenario the contestant is meant to discover."""
    out, n = [], 0
    for t in tests:
        if t["test"].startswith("public_"):
            label = t["test"].removeprefix("public_").replace("_", " ")
            out.append({"test": f"public: {label}", "passed": t["passed"], "hidden": False})
        else:
            n += 1
            out.append({"test": f"hidden check {n}", "passed": t["passed"], "hidden": True})
    return out


# --- Investigation: probe lab + execution-grounded witnesses ---------------

@router.get("/worlds/{world_id}/probe")
async def probe_info(world_id: str):
    r = _record(world_id)
    try:
        return probe_kit(r.world).describe(r.world)
    except ProbeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/worlds/{world_id}/probe")
async def run_probe(world_id: str, body: ProbeRequest):
    r = _record(world_id)
    source = body.c_source if body.c_source is not None else r.world.starter_source
    try:
        out = await probe_kit(r.world).run(r.world, body.scenario, source, _eval_sandbox)
    except ProbeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ValueError as exc:  # static safety check on contestant code
        raise HTTPException(status_code=422, detail=str(exc))
    _profiles.log_activity(body.user_id, world_id, "probe")
    return {"ok": out.ok, "error": out.error, "detail": out.detail, "trace": out.trace,
            "ran": "original" if body.c_source is None else "yours"}


@router.get("/worlds/{world_id}/witnesses")
async def list_witnesses(world_id: str):
    r = _record(world_id)
    try:
        return witness_kit(r.world).public(r.world)
    except KeyError:
        return []


@router.post("/worlds/{world_id}/witnesses/{witness_key}/ask")
async def ask_witness(world_id: str, witness_key: str, body: AskRequest):
    r = _record(world_id)
    try:
        kit = witness_kit(r.world)
    except KeyError:
        raise HTTPException(status_code=404, detail="No witnesses in this world")
    try:
        ans = await kit.ask(r.world, world_id, witness_key, _eval_sandbox,
                            question=body.question, topic=body.topic, source=body.c_source)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"No witness '{witness_key}'")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    _profiles.log_activity(body.user_id, world_id, "replay" if body.c_source else "witness")
    return ans


# --- Profiles / adaptive difficulty ----------------------------------------

@router.get("/profiles/{user_id}")
async def get_profile(user_id: str):
    return _profiles.profile(user_id)


@router.delete("/worlds/{world_id}")
async def delete_world(world_id: str, requested_by: str | None = None,
                       x_vanta_admin: str | None = Header(default=None)):
    r = _record(world_id)
    if r.created_by != requested_by and not _is_admin(x_vanta_admin):
        raise HTTPException(status_code=403, detail="You can only delete your own worlds")
    _manager.delete_world(world_id)
    return {"deleted": world_id}


@router.delete("/worlds")
async def delete_all(created_by: str | None = None, requested_by: str | None = None,
                     x_vanta_admin: str | None = Header(default=None)):
    """created_by set: delete that person's worlds (they may do this
    themselves). created_by unset: delete EVERY world -- admin only."""
    admin = _is_admin(x_vanta_admin)
    if created_by is None and not admin:
        raise HTTPException(status_code=403, detail="Deleting every world needs admin rights")
    if created_by is not None and created_by != requested_by and not admin:
        raise HTTPException(status_code=403, detail="You can only delete your own worlds")
    return {"deleted_count": _manager.delete_all_worlds(created_by=created_by)}


# --- Cohorts: one problem, a unique world per member ------------------------

class CreateCohortRequest(BaseModel):
    host_id: str
    name: str
    archetype_id: str | None = None
    target_difficulty: float = 0.45


class JoinCohortRequest(BaseModel):
    user_id: str
    display_name: str


class HostRequest(BaseModel):
    host_id: str


@router.post("/cohorts")
async def create_cohort(body: CreateCohortRequest):
    c = _cohort_call(_cohorts.create, body.host_id, body.name, body.archetype_id,
                     body.target_difficulty)
    return c.public(0)


@router.get("/cohorts")
async def list_cohorts(host_id: str):
    return _cohorts.list_for_host(host_id)


@router.get("/cohorts/{code}")
async def get_cohort(code: str, user_id: str | None = None):
    c = _cohort_call(_cohorts.get, code)
    out = c.public(_cohorts.member_count(c))
    if user_id:
        out["membership"] = _cohorts.membership(code, user_id)
    return out


@router.post("/cohorts/{code}/join")
async def join_cohort(code: str, body: JoinCohortRequest):
    try:
        member, rec = await _cohorts.join(code, body.user_id, body.display_name)
    except CohortError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc))
    except WorldGenerationError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"member": member, "world": _public(rec)}


@router.get("/cohorts/{code}/host")
async def cohort_host_view(code: str, host_id: str | None = None,
                           x_vanta_admin: str | None = Header(default=None)):
    admin = _is_admin(x_vanta_admin)
    return _cohort_call(_cohorts.host_view, code, host_id, admin)


@router.post("/cohorts/{code}/close")
async def close_cohort(code: str, body: HostRequest,
                       x_vanta_admin: str | None = Header(default=None)):
    admin = _is_admin(x_vanta_admin)
    c = _cohort_call(_cohorts.close, code, body.host_id, admin)
    return c.public(_cohorts.member_count(c))


@router.delete("/cohorts/{code}")
async def delete_cohort(code: str, host_id: str | None = None,
                        x_vanta_admin: str | None = Header(default=None)):
    admin = _is_admin(x_vanta_admin)
    n = _cohort_call(_cohorts.delete, code, host_id, admin)
    return {"deleted": code.upper(), "worlds_deleted": n}


# --- Admin: exposes ground truth + fitness, never reachable in contestant UI ---

@router.get("/admin/worlds/{world_id}")
async def admin_get_world(world_id: str, x_vanta_admin: str | None = Header(default=None)):
    if not _is_admin(x_vanta_admin):
        raise HTTPException(status_code=403, detail="Admin only")
    r = _record(world_id)
    return {
        **_public(r),
        "ground_truth_summary": r.world.ground_truth_summary,
        "genes": r.world.genes,
        "fitness": r.fitness,
    }

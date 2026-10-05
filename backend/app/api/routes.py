from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
    }


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
    change = _profiles.record_submission(
        user, world_id, r.target_difficulty, result["verdict"],
        passed=sum(1 for t in tests if t["passed"]), total=len(tests),
    )
    # Contestant-safe: verdict + which named tests passed/failed, never the
    # hidden ground truth or reference fixes.
    return {
        "verdict": result["verdict"],
        "reason": result.get("reason"),
        "detail": result.get("detail") if result.get("reason") in ("compile_error", "timeout") else None,
        "tests": [{"test": t["test"], "passed": t["passed"]} for t in tests],
        "rating": {"before": change.before, "after": change.after, "counted": change.counted},
    }


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
async def delete_world(world_id: str):
    try:
        _manager.delete_world(world_id)
    except WorldNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"deleted": world_id}


@router.delete("/worlds")
async def delete_all(created_by: str | None = None):
    return {"deleted_count": _manager.delete_all_worlds(created_by=created_by)}


# --- Admin: exposes ground truth + fitness, never reachable in contestant UI ---

@router.get("/admin/worlds/{world_id}")
async def admin_get_world(world_id: str):
    try:
        r = _manager.get_world(world_id)
    except WorldNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        **_public(r),
        "ground_truth_summary": r.world.ground_truth_summary,
        "genes": r.world.genes,
        "fitness": r.fitness,
    }

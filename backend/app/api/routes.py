from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.world_manager import WorldManager, WorldNotFoundError
from app.evolution.engine import EvolutionEngine
from app.execution.c_sandbox import CSandbox
from app.worldgen.evaluate import evaluate_submission
from app.worldgen.registry import ARCHETYPES_BY_ID, WorldGenerationError

router = APIRouter(prefix="/api", tags=["vanta"])

# One manager (fast internal sandbox for generation) and one sanitized
# sandbox for contestant-facing evaluation.
_manager = WorldManager(engine=EvolutionEngine())
_eval_sandbox = CSandbox(timeout_seconds=15.0, fast=False)


class CreateWorldRequest(BaseModel):
    created_by: str
    seed: int | None = None
    target_difficulty: float = 0.5
    archetype_id: str | None = None


class SubmitRequest(BaseModel):
    c_source: str


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
    try:
        r = await _manager.create_world(
            created_by=body.created_by, seed=body.seed,
            target_difficulty=body.target_difficulty, archetype_id=body.archetype_id,
        )
    except WorldGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _public(r)


@router.get("/worlds")
async def list_worlds(created_by: str | None = None):
    return [_summary(r) for r in _manager.list_worlds(created_by=created_by)]


@router.get("/worlds/{world_id}")
async def get_world(world_id: str):
    try:
        return _public(_manager.get_world(world_id))
    except WorldNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/worlds/{world_id}/submit")
async def submit(world_id: str, body: SubmitRequest):
    try:
        r = _manager.get_world(world_id)
    except WorldNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    result = await evaluate_submission(r.world, body.c_source, _eval_sandbox)
    # Contestant-safe: verdict + which named tests passed/failed, never the
    # hidden ground truth or reference fixes.
    return {
        "verdict": result["verdict"],
        "reason": result.get("reason"),
        "detail": result.get("detail") if result.get("reason") in ("compile_error", "timeout") else None,
        "tests": [{"test": t["test"], "passed": t["passed"]} for t in result.get("tests", [])],
    }


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

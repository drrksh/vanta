from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, get_registry, get_service, require_admin
from app.core.investigation_service import InvestigationService, NotFoundError
from app.schemas.api import AdminRedTeamRequest, StartWorldRequest
from app.scenarios.loader import ScenarioRegistry

router = APIRouter(
    prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)]
)


@router.post("/worlds")
async def admin_start_world(
    body: StartWorldRequest,
    service: InvestigationService = Depends(get_service),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        world_row = await service.start_world(session, body.scenario_id, body.seed)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown scenario")
    return {"world_id": world_row.id, "status": world_row.status}


@router.post("/worlds/{world_id}/reset")
async def admin_reset_world(
    world_id: str,
    service: InvestigationService = Depends(get_service),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        row = await service.reset_world(session, world_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"world_id": row.id, "status": row.status}


@router.post("/worlds/{world_id}/tick")
async def admin_tick_world(
    world_id: str,
    seconds: int = 60,
    service: InvestigationService = Depends(get_service),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        world = await service.tick_world(session, world_id, seconds)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        "world_id": world_id,
        "sim_time_seconds": world.state.sim_time_seconds,
        "tick_count": world.state.tick_count,
    }


@router.get("/worlds/{world_id}/truth")
async def admin_ground_truth(
    world_id: str,
    service: InvestigationService = Depends(get_service),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        return await service.admin_ground_truth(session, world_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/worlds/{world_id}/agents/{agent_id}/knowledge")
async def admin_agent_knowledge(
    world_id: str,
    agent_id: str,
    service: InvestigationService = Depends(get_service),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        return await service.admin_agent_knowledge(session, world_id, agent_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/worlds/{world_id}/redteam")
async def admin_red_team(
    world_id: str,
    body: AdminRedTeamRequest,
    service: InvestigationService = Depends(get_service),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        return await service.admin_red_team_ask(
            session, world_id, body.agent_id, body.message
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/worlds/{scenario_id}/validate")
async def admin_validate_world(
    scenario_id: str,
    service: InvestigationService = Depends(get_service),
):
    try:
        problems = await service.admin_validate_world(scenario_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown scenario")
    return {"valid": not problems, "problems": problems}


@router.get("/investigations/{investigation_id}/logs")
async def admin_logs(
    investigation_id: str,
    service: InvestigationService = Depends(get_service),
    session: AsyncSession = Depends(get_db_session),
):
    rows = await service.get_audit_logs(session, investigation_id=investigation_id)
    return [
        {
            "id": r.id,
            "actor": r.actor,
            "action": r.action,
            "metadata": r.metadata_json,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/scenarios")
async def admin_list_scenarios(registry: ScenarioRegistry = Depends(get_registry)):
    scenarios = registry.all()
    out = []
    for s in scenarios.values():
        problems = s.validate_firewall()
        out.append(
            {
                "id": s.id,
                "title": s.title,
                "domain": s.domain,
                "difficulty": s.difficulty.model_dump(),
                "agent_count": len(s.agents),
                "fact_count": len(s.facts),
                "valid": not problems,
            }
        )
    return out

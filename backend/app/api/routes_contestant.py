from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, get_registry, get_service
from app.core.investigation_service import InvestigationService, NotFoundError
from app.schemas.api import (
    AgentMessageRequest,
    CreateInvestigationRequest,
    HypothesisCreateRequest,
    SolutionSubmitRequest,
    StartWorldRequest,
)
from app.scenarios.loader import ScenarioRegistry

router = APIRouter(prefix="/api", tags=["contestant"])


@router.get("/worlds")
async def list_worlds(registry: ScenarioRegistry = Depends(get_registry)):
    scenarios = registry.all()
    return [
        {
            "scenario_id": s.id,
            "title": s.title,
            "domain": s.domain,
            "briefing_preview": s.briefing.strip()[:180],
        }
        for s in scenarios.values()
    ]


@router.post("/worlds/{scenario_id}/start")
async def start_world(
    scenario_id: str,
    body: StartWorldRequest | None = None,
    service: InvestigationService = Depends(get_service),
    session: AsyncSession = Depends(get_db_session),
):
    seed = body.seed if body else None
    try:
        world_row = await service.start_world(session, scenario_id, seed=seed)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown scenario '{scenario_id}'")
    scenario = service.registry.get(scenario_id)
    return {
        "world_id": world_row.id,
        "scenario_id": scenario_id,
        "title": scenario.title,
        "status": world_row.status,
    }


@router.post("/investigations")
async def create_investigation(
    body: CreateInvestigationRequest,
    service: InvestigationService = Depends(get_service),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        inv = await service.create_investigation(
            session, body.world_id, body.contestant_label
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    world_row = await service._get_world_row(session, body.world_id)
    scenario = service.registry.get(world_row.scenario_id)
    return {
        "investigation_id": inv.id,
        "world_id": inv.world_id,
        "status": inv.status,
        "briefing": scenario.briefing,
        "agents": [
            {"id": a.id, "role": a.role, "display_name": a.display_name}
            for a in scenario.agents
        ],
    }


@router.get("/investigations/{investigation_id}")
async def get_investigation(
    investigation_id: str,
    service: InvestigationService = Depends(get_service),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        inv = await service.get_investigation(session, investigation_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    world_row = await service._get_world_row(session, inv.world_id)
    scenario = service.registry.get(world_row.scenario_id)
    return {
        "investigation_id": inv.id,
        "world_id": inv.world_id,
        "status": inv.status,
        "briefing": scenario.briefing,
        "agents": [
            {"id": a.id, "role": a.role, "display_name": a.display_name}
            for a in scenario.agents
        ],
    }


@router.get("/investigations/{investigation_id}/agents")
async def list_agents(
    investigation_id: str,
    service: InvestigationService = Depends(get_service),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        inv = await service.get_investigation(session, investigation_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    world_row = await service._get_world_row(session, inv.world_id)
    scenario = service.registry.get(world_row.scenario_id)
    return [
        {"id": a.id, "role": a.role, "display_name": a.display_name}
        for a in scenario.agents
    ]


@router.post("/investigations/{investigation_id}/agents/{agent_id}/message")
async def send_message(
    investigation_id: str,
    agent_id: str,
    body: AgentMessageRequest,
    service: InvestigationService = Depends(get_service),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        result = await service.send_agent_message(
            session, investigation_id, agent_id, body.message
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result


@router.get("/investigations/{investigation_id}/evidence")
async def list_evidence(
    investigation_id: str,
    service: InvestigationService = Depends(get_service),
    session: AsyncSession = Depends(get_db_session),
):
    rows = await service.list_evidence(session, investigation_id)
    return [
        {
            "id": r.id,
            "source_agent_id": r.source_agent_id,
            "content": r.content,
            "evidence_type": r.evidence_type,
            "confidence": r.confidence,
        }
        for r in rows
    ]


@router.post("/investigations/{investigation_id}/hypotheses")
async def create_hypothesis(
    investigation_id: str,
    body: HypothesisCreateRequest,
    service: InvestigationService = Depends(get_service),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        h = await service.create_hypothesis(
            session,
            investigation_id,
            body.text,
            body.supporting_evidence,
            body.contradicting_evidence,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        "id": h.id,
        "text": h.text,
        "supporting_evidence": h.supporting_evidence,
        "contradicting_evidence": h.contradicting_evidence,
        "status": h.status,
    }


@router.get("/investigations/{investigation_id}/hypotheses")
async def list_hypotheses(
    investigation_id: str,
    service: InvestigationService = Depends(get_service),
    session: AsyncSession = Depends(get_db_session),
):
    rows = await service.list_hypotheses(session, investigation_id)
    return [
        {
            "id": r.id,
            "text": r.text,
            "supporting_evidence": r.supporting_evidence,
            "contradicting_evidence": r.contradicting_evidence,
            "status": r.status,
        }
        for r in rows
    ]


@router.post("/investigations/{investigation_id}/solution")
async def submit_solution(
    investigation_id: str,
    body: SolutionSubmitRequest,
    service: InvestigationService = Depends(get_service),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        result = await service.submit_solution(session, investigation_id, body.model_dump())
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result

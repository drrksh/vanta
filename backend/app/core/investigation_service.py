"""
Investigation service.

The orchestration layer that ties together:
  - ScenarioRegistry (static, human-authored truth)
  - World (per-run deterministic state machine)
  - Agent (LLM-backed, knowledge-scoped conversational windows)
  - Evaluator (deterministic verdicts)
  - Persistence (SQLAlchemy async)

This is the CONTROL PLANE described in spec section 4. It is where
contestant-facing and admin-facing operations are kept clearly separated:
admin_* methods are the only ones allowed to call World.admin_* accessors.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.agent import Agent
from app.core.config import Settings
from app.core.enums import AuditAction, InvestigationStatus, WorldStatus
from app.evaluator.evaluator import Evaluator
from app.llm.base import LLMMessage
from app.models.orm import (
    AuditLogRow,
    EvaluationRow,
    EvidenceRow,
    HypothesisRow,
    InvestigationRow,
    MessageRow,
    SolutionRow,
    WorldRow,
)
from app.scenarios.loader import ScenarioRegistry
from app.security.guards import is_suspicious_message
from app.world.engine import World


class NotFoundError(Exception):
    pass


class InvestigationService:
    def __init__(self, registry: ScenarioRegistry, settings: Settings):
        self.registry = registry
        self.settings = settings
        # In-memory cache of live World objects keyed by world_id. Runtime
        # state (sim time, RNG) lives here; durable facts live in the DB.
        self._live_worlds: dict[str, World] = {}

    # ------------------------------------------------------------------
    # World lifecycle
    # ------------------------------------------------------------------

    def _get_or_build_world(self, world_row: WorldRow) -> World:
        if world_row.id not in self._live_worlds:
            scenario = self.registry.get(world_row.scenario_id)
            world = World(world_row.id, scenario, seed=world_row.seed)
            world.state.status = world_row.status
            self._live_worlds[world_row.id] = world
        return self._live_worlds[world_row.id]

    async def start_world(
        self, session: AsyncSession, scenario_id: str, seed: int | None = None
    ) -> WorldRow:
        scenario = self.registry.get(scenario_id)  # raises KeyError if unknown
        effective_seed = seed if seed is not None else scenario.seed
        world_row = WorldRow(
            scenario_id=scenario_id,
            seed=effective_seed,
            status=WorldStatus.RUNNING.value,
            difficulty_json=scenario.difficulty.model_dump(),
            state_json={},
        )
        session.add(world_row)
        await session.flush()

        world = World(world_row.id, scenario, seed=effective_seed)
        world.start()
        self._live_worlds[world_row.id] = world

        await self._log(
            session,
            world_id=world_row.id,
            investigation_id=None,
            actor="admin",
            action=AuditAction.WORLD_STARTED,
            metadata={"scenario_id": scenario_id, "seed": effective_seed},
        )
        return world_row

    async def reset_world(self, session: AsyncSession, world_id: str) -> WorldRow:
        world_row = await self._get_world_row(session, world_id)
        world = self._get_or_build_world(world_row)
        world.reset()
        world_row.status = WorldStatus.RESET.value
        world_row.state_json = {}
        await session.flush()
        await self._log(
            session,
            world_id=world_id,
            investigation_id=None,
            actor="admin",
            action=AuditAction.WORLD_RESET,
            metadata={},
        )
        return world_row

    async def tick_world(
        self, session: AsyncSession, world_id: str, seconds: int = 60
    ) -> World:
        world_row = await self._get_world_row(session, world_id)
        world = self._get_or_build_world(world_row)
        world.tick(seconds)
        world_row.state_json = {
            "sim_time_seconds": world.state.sim_time_seconds,
            "tick_count": world.state.tick_count,
        }
        await session.flush()
        await self._log(
            session,
            world_id=world_id,
            investigation_id=None,
            actor="admin",
            action=AuditAction.WORLD_TICKED,
            metadata={"seconds": seconds},
        )
        return world

    async def _get_world_row(self, session: AsyncSession, world_id: str) -> WorldRow:
        row = await session.get(WorldRow, world_id)
        if row is None:
            raise NotFoundError(f"World '{world_id}' not found")
        return row

    # ------------------------------------------------------------------
    # Investigations
    # ------------------------------------------------------------------

    async def create_investigation(
        self, session: AsyncSession, world_id: str, contestant_label: str
    ) -> InvestigationRow:
        world_row = await self._get_world_row(session, world_id)
        inv = InvestigationRow(
            world_id=world_row.id,
            contestant_label=contestant_label,
            status=InvestigationStatus.ACTIVE.value,
        )
        session.add(inv)
        await session.flush()
        return inv

    async def get_investigation(
        self, session: AsyncSession, investigation_id: str
    ) -> InvestigationRow:
        row = await session.get(InvestigationRow, investigation_id)
        if row is None:
            raise NotFoundError(f"Investigation '{investigation_id}' not found")
        return row

    async def _discovered_fact_ids(
        self, session: AsyncSession, investigation_id: str
    ) -> set[str]:
        result = await session.execute(
            select(EvidenceRow.fact_id).where(
                EvidenceRow.investigation_id == investigation_id
            )
        )
        return {row[0] for row in result.all()}

    # ------------------------------------------------------------------
    # Conversation
    # ------------------------------------------------------------------

    async def send_agent_message(
        self,
        session: AsyncSession,
        investigation_id: str,
        agent_id: str,
        user_message: str,
    ) -> dict:
        inv = await self.get_investigation(session, investigation_id)
        world_row = await self._get_world_row(session, inv.world_id)
        world = self._get_or_build_world(world_row)
        scenario = world.scenario

        agent_def = next((a for a in scenario.agents if a.id == agent_id), None)
        if agent_def is None:
            raise NotFoundError(f"Agent '{agent_id}' not found in this world")

        agent = Agent(agent_def, world)

        history_rows = await session.execute(
            select(MessageRow)
            .where(
                MessageRow.investigation_id == investigation_id,
                MessageRow.agent_id == agent_id,
            )
            .order_by(MessageRow.created_at)
        )
        history = [
            LLMMessage(
                role="user" if row.role == "contestant" else "assistant",
                content=row.content,
            )
            for row in history_rows.scalars().all()
        ][-self.settings.conversation_history_limit :]

        discovered = await self._discovered_fact_ids(session, investigation_id)

        suspicious = is_suspicious_message(user_message)

        result = await agent.respond(
            history=history,
            user_message=user_message,
            discovered_fact_ids=discovered,
            settings=self.settings,
        )

        session.add(
            MessageRow(
                investigation_id=investigation_id,
                agent_id=agent_id,
                role="contestant",
                content=user_message,
                flagged_injection=suspicious,
            )
        )
        session.add(
            MessageRow(
                investigation_id=investigation_id,
                agent_id=agent_id,
                role="agent",
                content=result.text,
                provider_used=result.provider_used,
            )
        )

        if suspicious:
            await self._log(
                session,
                world_id=inv.world_id,
                investigation_id=investigation_id,
                actor=f"contestant:{inv.contestant_label}",
                action=AuditAction.SECURITY_FLAG_RAISED,
                metadata={"agent_id": agent_id, "message": user_message},
            )

        new_evidence = []
        for fact_id in result.revealed_fact_ids:
            if fact_id in discovered:
                continue
            fact = world.get_fact(fact_id)
            if fact is None:
                continue
            evidence_row = EvidenceRow(
                investigation_id=investigation_id,
                fact_id=fact_id,
                source_agent_id=agent_id,
                content=fact.text,
                evidence_type="observation",
                confidence=1.0,
            )
            session.add(evidence_row)
            new_evidence.append(
                {
                    "fact_id": fact_id,
                    "content": fact.text,
                    "source_agent_id": agent_id,
                }
            )
            await self._log(
                session,
                world_id=inv.world_id,
                investigation_id=investigation_id,
                actor=agent_id,
                action=AuditAction.EVIDENCE_REVEALED,
                metadata={"fact_id": fact_id},
            )

        await self._log(
            session,
            world_id=inv.world_id,
            investigation_id=investigation_id,
            actor=f"contestant:{inv.contestant_label}",
            action=AuditAction.AGENT_MESSAGE,
            metadata={"agent_id": agent_id, "provider": result.provider_used},
        )

        await session.flush()

        return {
            "agent_id": agent_id,
            "text": result.text,
            "new_evidence": new_evidence,
            "flagged_injection": result.flagged_injection,
        }

    # ------------------------------------------------------------------
    # Evidence / Hypotheses
    # ------------------------------------------------------------------

    async def list_evidence(
        self, session: AsyncSession, investigation_id: str
    ) -> list[EvidenceRow]:
        result = await session.execute(
            select(EvidenceRow)
            .where(EvidenceRow.investigation_id == investigation_id)
            .order_by(EvidenceRow.discovered_at)
        )
        return list(result.scalars().all())

    async def create_hypothesis(
        self,
        session: AsyncSession,
        investigation_id: str,
        text: str,
        supporting_evidence: str,
        contradicting_evidence: str,
    ) -> HypothesisRow:
        await self.get_investigation(session, investigation_id)  # 404 check
        h = HypothesisRow(
            investigation_id=investigation_id,
            text=text,
            supporting_evidence=supporting_evidence,
            contradicting_evidence=contradicting_evidence,
        )
        session.add(h)
        await session.flush()
        await self._log(
            session,
            world_id=None,
            investigation_id=investigation_id,
            actor="contestant",
            action=AuditAction.HYPOTHESIS_CREATED,
            metadata={"text": text},
        )
        return h

    async def list_hypotheses(
        self, session: AsyncSession, investigation_id: str
    ) -> list[HypothesisRow]:
        result = await session.execute(
            select(HypothesisRow)
            .where(HypothesisRow.investigation_id == investigation_id)
            .order_by(HypothesisRow.created_at)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Solution + Evaluation
    # ------------------------------------------------------------------

    async def submit_solution(
        self, session: AsyncSession, investigation_id: str, payload: dict
    ) -> dict:
        inv = await self.get_investigation(session, investigation_id)
        world_row = await self._get_world_row(session, inv.world_id)
        world = self._get_or_build_world(world_row)
        scenario = world.scenario

        solution_row = SolutionRow(investigation_id=investigation_id, payload_json=payload)
        session.add(solution_row)
        await session.flush()

        await self._log(
            session,
            world_id=inv.world_id,
            investigation_id=investigation_id,
            actor="contestant",
            action=AuditAction.SOLUTION_SUBMITTED,
            metadata={},
        )
        await self._log(
            session,
            world_id=inv.world_id,
            investigation_id=investigation_id,
            actor="evaluator",
            action=AuditAction.EVALUATION_STARTED,
            metadata={},
        )

        evaluator = Evaluator(self.settings)
        result = await evaluator.evaluate(scenario, payload)

        for outcome in result.outcomes:
            await self._log(
                session,
                world_id=inv.world_id,
                investigation_id=investigation_id,
                actor="evaluator",
                action=(
                    AuditAction.EVALUATION_TEST_PASSED
                    if outcome.passed
                    else AuditAction.EVALUATION_TEST_FAILED
                ),
                metadata={"test_id": outcome.test_id},
            )

        eval_row = EvaluationRow(
            solution_id=solution_row.id,
            verdict=result.verdict.value,
            tests_json=result.admin_view()["tests"],
        )
        session.add(eval_row)

        inv.status = (
            InvestigationStatus.ACCEPTED.value
            if result.verdict.value == "accepted"
            else InvestigationStatus.REJECTED.value
        )

        await self._log(
            session,
            world_id=inv.world_id,
            investigation_id=investigation_id,
            actor="evaluator",
            action=AuditAction.EVALUATION_COMPLETED,
            metadata={"verdict": result.verdict.value},
        )
        await session.flush()

        return result.contestant_view()

    # ------------------------------------------------------------------
    # Admin
    # ------------------------------------------------------------------

    async def admin_ground_truth(self, session: AsyncSession, world_id: str) -> dict:
        world_row = await self._get_world_row(session, world_id)
        world = self._get_or_build_world(world_row)
        return world.admin_ground_truth()

    async def admin_agent_knowledge(
        self, session: AsyncSession, world_id: str, agent_id: str
    ) -> dict:
        world_row = await self._get_world_row(session, world_id)
        world = self._get_or_build_world(world_row)
        return world.admin_agent_knowledge(agent_id)

    async def admin_validate_world(self, world_id_or_scenario_id: str) -> list[str]:
        scenario = self.registry.get(world_id_or_scenario_id)
        return scenario.validate_firewall()

    async def admin_red_team_ask(
        self, session: AsyncSession, world_id: str, agent_id: str, message: str
    ) -> dict:
        """
        Same code path as a normal contestant message, but callable directly
        against a world (no investigation needed) for admin verification that
        the firewall holds under direct interrogation (spec section 19).
        """
        world_row = await self._get_world_row(session, world_id)
        world = self._get_or_build_world(world_row)
        scenario = world.scenario
        agent_def = next((a for a in scenario.agents if a.id == agent_id), None)
        if agent_def is None:
            raise NotFoundError(f"Agent '{agent_id}' not found")
        agent = Agent(agent_def, world)
        result = await agent.respond(
            history=[],
            user_message=message,
            discovered_fact_ids=set(),
            settings=self.settings,
        )
        return {
            "text": result.text,
            "flagged_injection": result.flagged_injection,
            "provider_used": result.provider_used,
        }

    async def get_audit_logs(
        self, session: AsyncSession, investigation_id: str | None = None, limit: int = 200
    ) -> list[AuditLogRow]:
        stmt = select(AuditLogRow).order_by(AuditLogRow.created_at.desc()).limit(limit)
        if investigation_id:
            stmt = stmt.where(AuditLogRow.investigation_id == investigation_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _log(
        self,
        session: AsyncSession,
        *,
        world_id: str | None,
        investigation_id: str | None,
        actor: str,
        action: AuditAction,
        metadata: dict,
    ) -> None:
        session.add(
            AuditLogRow(
                world_id=world_id,
                investigation_id=investigation_id,
                actor=actor,
                action=action.value,
                metadata_json=metadata,
            )
        )

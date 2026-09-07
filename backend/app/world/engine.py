"""
World Engine.

    The LLM interprets reality. The server owns reality.

This module is the single source of truth for a running World. It is plain
deterministic Python -- no LLM calls happen here. Everything downstream
(agents, evaluator) reads through accessor methods that enforce the
Information Firewall; nothing downstream gets a raw reference to
GroundTruth.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from app.core.enums import InfoClass
from app.schemas.scenario import KnowledgeFact, ScenarioDefinition, TimelineEvent


@dataclass
class WorldRuntimeState:
    """Mutable state that can change as the world 'ticks'."""

    sim_time_seconds: int = 0
    tick_count: int = 0
    status: str = "draft"


class World:
    """
    A running instance of a ScenarioDefinition, bound to a seed.

    Construction is deterministic: the same (scenario, seed) always yields
    the same derived ordering/state, per spec section 16.
    """

    def __init__(self, world_id: str, scenario: ScenarioDefinition, seed: int | None = None):
        self.id = world_id
        self.scenario = scenario
        self.seed = seed if seed is not None else scenario.seed
        self._rng = random.Random(self.seed)
        self.state = WorldRuntimeState(status="draft")

        self._facts_by_id: dict[str, KnowledgeFact] = {
            f.id: f for f in scenario.facts
        }
        self._timeline_by_id: dict[str, TimelineEvent] = {
            e.id: e for e in scenario.timeline
        }

        # Deterministic shuffle of "discoverable order hints" -- used only
        # for things like false-lead ordering, never for the ground truth
        # itself (the ground truth is fixed, authored data; only *incidental*
        # presentation details are seed-randomized).
        self._shuffled_fact_ids = [f.id for f in scenario.facts]
        self._rng.shuffle(self._shuffled_fact_ids)

    # ---------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------

    def start(self) -> None:
        self.state.status = "running"

    def pause(self) -> None:
        self.state.status = "paused"

    def resume(self) -> None:
        self.state.status = "running"

    def reset(self) -> None:
        self._rng = random.Random(self.seed)
        self.state = WorldRuntimeState(status="draft")

    def tick(self, seconds: int = 60) -> None:
        self.state.tick_count += 1
        self.state.sim_time_seconds += seconds

    # ---------------------------------------------------------------
    # GREEN (public) accessors -- safe for contestant / evidence board
    # ---------------------------------------------------------------

    def briefing(self) -> str:
        return self.scenario.briefing

    def public_timeline(self) -> list[TimelineEvent]:
        """
        Events visible without any discovery gating, up to current sim time.
        Hidden events are excluded entirely (they must be earned via
        evidence discovery -- see reveal_timeline_event).
        """
        return [
            e
            for e in self.scenario.timeline
            if not e.hidden_until_discovered
            and e.classification == InfoClass.GREEN
            and e.at_seconds <= self.state.sim_time_seconds
        ]

    def get_timeline_event(self, event_id: str) -> TimelineEvent | None:
        return self._timeline_by_id.get(event_id)

    # ---------------------------------------------------------------
    # YELLOW accessors -- gated by agent authorization, used by AgentLayer
    # ---------------------------------------------------------------

    def get_fact(self, fact_id: str) -> KnowledgeFact | None:
        return self._facts_by_id.get(fact_id)

    def facts_for_agent(self, agent_id: str) -> list[KnowledgeFact]:
        """
        Returns the full set of facts (YELLOW+GREEN) an agent is authorized
        to hold in its knowledge base. RED facts are filtered out here as a
        defense-in-depth measure even though scenario validation should have
        already guaranteed no agent lists a RED fact id.
        """
        agent_def = self._agent_def(agent_id)
        ids = set(agent_def.knowledge_ids)
        facts = [
            self._facts_by_id[fid]
            for fid in ids
            if fid in self._facts_by_id
            and self._facts_by_id[fid].classification != InfoClass.RED
        ]
        # Agents automatically also know all GREEN facts (public knowledge).
        green_facts = [
            f for f in self.scenario.facts if f.classification == InfoClass.GREEN
        ]
        seen = {f.id for f in facts}
        for gf in green_facts:
            if gf.id not in seen:
                facts.append(gf)
                seen.add(gf.id)
        return facts

    def conditional_facts_unlocked(
        self, agent_id: str, discovered_fact_ids: set[str]
    ) -> list[KnowledgeFact]:
        """
        Facts that become available to reveal once the contestant's evidence
        board already contains certain prerequisite facts.
        """
        agent_def = self._agent_def(agent_id)
        unlocked = []
        for fact_id, prereqs in agent_def.conditional_knowledge_ids.items():
            if fact_id in self._facts_by_id and set(prereqs).issubset(
                discovered_fact_ids
            ):
                fact = self._facts_by_id[fact_id]
                if fact.classification != InfoClass.RED:
                    unlocked.append(fact)
        return unlocked

    # ---------------------------------------------------------------
    # RED accessors -- WorldEngine/Evaluator/Admin ONLY.
    # Callers of these must be explicitly privileged (admin API, evaluator).
    # ---------------------------------------------------------------

    def admin_ground_truth(self) -> dict:
        gt = self.scenario.ground_truth
        return {
            "root_cause_id": gt.root_cause_id,
            "root_cause_summary": gt.root_cause_summary,
            "mechanism": gt.mechanism,
            "hidden_state": gt.hidden_state,
        }

    def admin_all_facts(self) -> list[dict]:
        return [
            {
                "id": f.id,
                "text": f.text,
                "classification": f.classification.value,
                "tags": f.tags,
            }
            for f in self.scenario.facts
        ]

    def admin_agent_knowledge(self, agent_id: str) -> dict:
        agent_def = self._agent_def(agent_id)
        return {
            "agent_id": agent_id,
            "knowledge_ids": agent_def.knowledge_ids,
            "conditional_knowledge_ids": agent_def.conditional_knowledge_ids,
            "cannot_know": agent_def.cannot_know,
        }

    # ---------------------------------------------------------------
    # Internal
    # ---------------------------------------------------------------

    def _agent_def(self, agent_id: str):
        for a in self.scenario.agents:
            if a.id == agent_id:
                return a
        raise KeyError(f"Unknown agent id '{agent_id}' in world '{self.id}'")

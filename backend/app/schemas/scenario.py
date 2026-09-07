"""
Scenario schema: the structured, non-LLM-authored contract that defines a World.

A scenario is authored as YAML by a human (or a controlled generator pipeline),
never freely by an LLM at runtime. See docs/PHILOSOPHY.md, principle 29.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.core.enums import InfoClass


class KnowledgeFact(BaseModel):
    """
    A single atomic fact that exists in the world.

    classification determines who can ever see it:
      - RED:    never leaves the WorldEngine/Evaluator/Admin boundary.
      - YELLOW: may be given to an agent IF that agent's `knowledge_ids`
                lists this fact's id.
      - GREEN:  public; visible to the contestant directly (briefing/evidence
                board) and to every agent automatically.
    """

    id: str
    text: str
    classification: InfoClass
    tags: list[str] = Field(default_factory=list)
    # Optional: a fact can be tied to a point in the timeline.
    occurs_at_seconds: int | None = None

    @field_validator("id")
    @classmethod
    def id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("KnowledgeFact.id must not be empty")
        return v


class AgentDefinition(BaseModel):
    model_config = {"protected_namespaces": ()}

    id: str
    role: str
    display_name: str
    personality: str = Field(
        description="Short natural-language persona brief used ONLY to steer "
        "tone/style, never used to smuggle in facts."
    )
    provider: str = Field(default="gemini", description="gemini | groq | mock")
    model_override: str | None = None
    # IDs of KnowledgeFact this agent is authorized to know and may reveal.
    # Must never include a RED fact -- validated at scenario-load time.
    knowledge_ids: list[str] = Field(default_factory=list)
    # Explicit denial list for defense-in-depth / documentation clarity.
    cannot_know: list[str] = Field(default_factory=list)
    # Facts revealed only after some trigger (e.g. asking the right question,
    # or another fact already being known to the contestant). Kept simple for
    # the prototype: revealed once contestant's evidence board contains all
    # `requires_evidence_ids`.
    conditional_knowledge_ids: dict[str, list[str]] = Field(
        default_factory=dict,
        description="fact_id -> list of evidence_ids that must already be "
        "discovered before this agent will volunteer/confirm fact_id",
    )


class DifficultyConfig(BaseModel):
    technical_depth: float = 0.5
    information_sparsity: float = 0.5
    contradiction: float = 0.2
    false_leads: int = 2
    agent_count: int = 4
    evidence_noise: float = 0.1
    event_complexity: float = 0.3
    experiment_cost: float = 0.2
    solution_complexity: float = 0.4
    adversarial_pressure: float = 0.1
    dynamicity: float = 0.2


class TimelineEvent(BaseModel):
    id: str
    at_seconds: int
    description: str
    classification: InfoClass = InfoClass.GREEN
    # If true, this event is not shown on the contestant timeline until
    # discovered as evidence via an agent conversation.
    hidden_until_discovered: bool = False


class EvaluationTestCase(BaseModel):
    id: str
    description: str
    # Name of a registered deterministic check function in
    # app.evaluator.checks for this scenario's domain.
    check: str
    params: dict = Field(default_factory=dict)
    required: bool = True


class EvaluationConfig(BaseModel):
    invariants: list[str] = Field(default_factory=list)
    tests: list[EvaluationTestCase]
    # Structured-claim mechanisms the LLM parser is allowed to extract from
    # free text; deterministic checks then test for presence/absence of these.
    known_mechanisms: list[str] = Field(default_factory=list)


class GroundTruth(BaseModel):
    """
    RED by definition. Never serialized into any agent-facing payload.
    """

    root_cause_id: str
    root_cause_summary: str
    mechanism: str
    hidden_state: dict = Field(default_factory=dict)


class ScenarioDefinition(BaseModel):
    id: str
    title: str
    domain: str
    briefing: str
    seed: int = 0
    difficulty: DifficultyConfig = Field(default_factory=DifficultyConfig)
    ground_truth: GroundTruth
    facts: list[KnowledgeFact]
    agents: list[AgentDefinition]
    timeline: list[TimelineEvent] = Field(default_factory=list)
    evaluation: EvaluationConfig
    solution_schema: list[str] = Field(
        default_factory=lambda: [
            "root_cause",
            "explanation",
            "proposed_solution",
            "implementation",
        ]
    )

    # ---- Cross-field validation ----

    def validate_firewall(self) -> list[str]:
        """
        Returns a list of validation problems (empty = OK). This backs the
        admin [Validate World] button (spec section 19).
        """
        problems: list[str] = []
        fact_by_id = {f.id: f for f in self.facts}

        red_ids = {f.id for f in self.facts if f.classification == InfoClass.RED}
        yellow_green_ids = {
            f.id for f in self.facts if f.classification != InfoClass.RED
        }

        for agent in self.agents:
            for kid in agent.knowledge_ids:
                if kid not in fact_by_id:
                    problems.append(
                        f"Agent '{agent.id}' references unknown fact id '{kid}'"
                    )
                elif kid in red_ids:
                    problems.append(
                        f"FIREWALL BREACH: Agent '{agent.id}' is granted RED "
                        f"fact '{kid}'"
                    )
            for kid in agent.conditional_knowledge_ids:
                if kid not in fact_by_id:
                    problems.append(
                        f"Agent '{agent.id}' conditional knowledge references "
                        f"unknown fact id '{kid}'"
                    )
                elif kid in red_ids:
                    problems.append(
                        f"FIREWALL BREACH: Agent '{agent.id}' conditionally "
                        f"reveals RED fact '{kid}'"
                    )

        if not red_ids:
            problems.append(
                "No RED facts defined -- ground truth may not be adequately "
                "protected/hidden."
            )

        # Evaluation tests must not silently pass with zero tests.
        if not self.evaluation.tests:
            problems.append("No evaluation tests defined.")

        # Every agent id referenced anywhere should exist.
        agent_ids = {a.id for a in self.agents}
        if len(agent_ids) != len(self.agents):
            problems.append("Duplicate agent ids detected.")

        return problems

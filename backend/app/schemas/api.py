from __future__ import annotations

from pydantic import BaseModel


class WorldSummary(BaseModel):
    scenario_id: str
    title: str
    domain: str
    briefing_preview: str


class StartWorldRequest(BaseModel):
    scenario_id: str
    seed: int | None = None


class WorldPublic(BaseModel):
    world_id: str
    scenario_id: str
    title: str
    status: str


class CreateInvestigationRequest(BaseModel):
    world_id: str
    contestant_label: str = "contestant"


class InvestigationPublic(BaseModel):
    investigation_id: str
    world_id: str
    status: str
    briefing: str
    agents: list[dict]


class AgentMessageRequest(BaseModel):
    message: str


class AgentMessageResponse(BaseModel):
    agent_id: str
    text: str
    new_evidence: list[dict]
    flagged_injection: bool


class EvidenceItem(BaseModel):
    id: str
    source_agent_id: str
    content: str
    evidence_type: str
    confidence: float


class HypothesisCreateRequest(BaseModel):
    text: str
    supporting_evidence: str = ""
    contradicting_evidence: str = ""


class HypothesisPublic(BaseModel):
    id: str
    text: str
    supporting_evidence: str
    contradicting_evidence: str
    status: str


class SolutionSubmitRequest(BaseModel):
    root_cause: str = ""
    explanation: str = ""
    proposed_solution: str = ""
    implementation: str = ""


class EvaluationPublicResult(BaseModel):
    verdict: str
    message: str


class AdminGroundTruth(BaseModel):
    root_cause_id: str
    root_cause_summary: str
    mechanism: str
    hidden_state: dict


class AdminDifficultyUpdate(BaseModel):
    technical_depth: float | None = None
    information_sparsity: float | None = None
    contradiction: float | None = None
    false_leads: int | None = None
    agent_count: int | None = None
    evidence_noise: float | None = None
    event_complexity: float | None = None
    experiment_cost: float | None = None
    solution_complexity: float | None = None
    adversarial_pressure: float | None = None
    dynamicity: float | None = None


class AdminRedTeamRequest(BaseModel):
    agent_id: str
    message: str

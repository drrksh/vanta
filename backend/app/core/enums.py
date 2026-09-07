from __future__ import annotations

from enum import Enum


class InfoClass(str, Enum):
    """
    The Information Firewall.

    RED    - Secret ground truth. Only WorldEngine, Evaluator, Admin may read it.
              Agents must NEVER receive RED information in their context.
    YELLOW - Agent-specific knowledge. An agent may know a YELLOW fact if and
              only if that fact is explicitly listed in that agent's
              knowledge base (allowed_knowledge_ids).
    GREEN  - Public. Any agent, and the contestant directly, may see this.
    """

    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"


class WorldStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    RESET = "reset"
    ARCHIVED = "archived"


class InvestigationStatus(str, Enum):
    ACTIVE = "active"
    SOLUTION_SUBMITTED = "solution_submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ABANDONED = "abandoned"


class HypothesisStatus(str, Enum):
    UNDER_INVESTIGATION = "under_investigation"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    ABANDONED = "abandoned"


class EvaluationVerdict(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class LLMProviderName(str, Enum):
    GEMINI = "gemini"
    GROQ = "groq"
    MOCK = "mock"


class AuditAction(str, Enum):
    WORLD_STARTED = "world_started"
    WORLD_RESET = "world_reset"
    WORLD_TICKED = "world_ticked"
    AGENT_MESSAGE = "agent_message"
    EVIDENCE_REVEALED = "evidence_revealed"
    HYPOTHESIS_CREATED = "hypothesis_created"
    HYPOTHESIS_UPDATED = "hypothesis_updated"
    SOLUTION_SUBMITTED = "solution_submitted"
    EVALUATION_STARTED = "evaluation_started"
    EVALUATION_TEST_PASSED = "evaluation_test_passed"
    EVALUATION_TEST_FAILED = "evaluation_test_failed"
    EVALUATION_COMPLETED = "evaluation_completed"
    SECURITY_FLAG_RAISED = "security_flag_raised"
    ADMIN_ACTION = "admin_action"

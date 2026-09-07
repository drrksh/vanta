from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Boolean, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Base(DeclarativeBase):
    pass


class WorldRow(Base):
    __tablename__ = "worlds"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    scenario_id: Mapped[str] = mapped_column(String, index=True)
    seed: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, default="draft")
    difficulty_json: Mapped[dict] = mapped_column(JSON, default=dict)
    # Mutable runtime state (e.g. current sim time, tick count).
    state_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    investigations: Mapped[list["InvestigationRow"]] = relationship(
        back_populates="world", cascade="all, delete-orphan"
    )


class InvestigationRow(Base):
    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    world_id: Mapped[str] = mapped_column(ForeignKey("worlds.id"), index=True)
    contestant_label: Mapped[str] = mapped_column(String, default="contestant")
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    world: Mapped["WorldRow"] = relationship(back_populates="investigations")
    evidence: Mapped[list["EvidenceRow"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )
    hypotheses: Mapped[list["HypothesisRow"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )
    messages: Mapped[list["MessageRow"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )
    solutions: Mapped[list["SolutionRow"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )


class MessageRow(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigations.id"), index=True
    )
    agent_id: Mapped[str] = mapped_column(String, index=True)
    role: Mapped[str] = mapped_column(String)  # "contestant" | "agent"
    content: Mapped[str] = mapped_column(Text)
    provider_used: Mapped[str | None] = mapped_column(String, nullable=True)
    flagged_injection: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    investigation: Mapped["InvestigationRow"] = relationship(back_populates="messages")


class EvidenceRow(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigations.id"), index=True
    )
    fact_id: Mapped[str] = mapped_column(String)
    source_agent_id: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    evidence_type: Mapped[str] = mapped_column(String, default="observation")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    discovered_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    investigation: Mapped["InvestigationRow"] = relationship(back_populates="evidence")


class HypothesisRow(Base):
    __tablename__ = "hypotheses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigations.id"), index=True
    )
    text: Mapped[str] = mapped_column(Text)
    supporting_evidence: Mapped[str] = mapped_column(Text, default="")
    contradicting_evidence: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="under_investigation")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    investigation: Mapped["InvestigationRow"] = relationship(back_populates="hypotheses")


class SolutionRow(Base):
    __tablename__ = "solutions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigations.id"), index=True
    )
    payload_json: Mapped[dict] = mapped_column(JSON)
    submitted_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    investigation: Mapped["InvestigationRow"] = relationship(back_populates="solutions")
    evaluation: Mapped["EvaluationRow"] = relationship(
        back_populates="solution", uselist=False, cascade="all, delete-orphan"
    )


class EvaluationRow(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    solution_id: Mapped[str] = mapped_column(ForeignKey("solutions.id"), unique=True)
    verdict: Mapped[str] = mapped_column(String)
    tests_json: Mapped[list] = mapped_column(JSON)  # full detail, admin-only
    evaluated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    solution: Mapped["SolutionRow"] = relationship(back_populates="evaluation")


class AuditLogRow(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    world_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    investigation_id: Mapped[str | None] = mapped_column(
        String, nullable=True, index=True
    )
    actor: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

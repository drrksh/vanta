"""
Flaw Archetype interface.

An archetype is a PROGRAM, not stored content. Given a seed and a set of
difficulty "genes", it produces a complete, self-consistent world: buggy C
source, a matching hidden-test harness that actually exercises the real
defect, agent grounding, and metadata. Nobody -- including the archetype's
author -- knows in advance which concrete numbers or wording a given seed
produces, because the archetype fixes only the STRUCTURE of the flaw, not
its parameters. The flaw CATEGORY itself is chosen from a pool at
generation time (see registry / evolution layer).

This is what makes VANTA fact-free and hard to replicate: there is no
problem bank to scrape. The "answer" does not exist until generation, is
different every seed, and is proven to exist (the bug reliably manifests)
only by real compilation + execution in the evolution loop.

`genes` is the hook the evolutionary layer turns: a dict of normalized
0..1 difficulty dials the archetype reads to shape its output (system
size, constant ranges, how subtle the bug is, how much noise, etc.). An
archetype should degrade gracefully for any gene values in [0,1].
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class GeneratedAgentGrounding:
    """Per-agent facts this generation produced. Structured, not prose, so
    an LLM renders fresh wording each time and nothing is memorizable."""

    agent_role_key: str
    facts: dict = field(default_factory=dict)


@dataclass
class GeneratedWorld:
    archetype_id: str
    seed: int
    genes: dict
    title: str
    briefing: str
    specification: str
    starter_source: str
    function_name: str
    function_signature: str
    shared_header: str
    mandatory_properties: list[str]
    optional_objectives: list[str]
    sample_input_description: str
    agent_groundings: list[GeneratedAgentGrounding]
    harness_source: str
    ground_truth_summary: str  # admin/debug only; never shown to a contestant
    # Structured generation parameters (names, constants) that the
    # investigation layer needs to build probe harnesses and witness runs.
    # Admin/internal only -- never sent to a contestant verbatim.
    params: dict = field(default_factory=dict)


# Canonical difficulty genes. Every archetype reads what it understands and
# ignores the rest. The evolution layer mutates these; audience presets set
# starting points (beginner vs advanced).
DEFAULT_GENES: dict[str, float] = {
    "system_size": 0.4,         # how many components / how much code to read
    "bug_subtlety": 0.4,        # how hidden the defect is on casual inspection
    "constant_magnitude": 0.4,  # size of numbers (affects overflow risk, scale)
    "noise": 0.2,               # irrelevant/decoy elements
    "edge_density": 0.4,        # how many edge cases the hidden tests probe
    "reasoning_depth": 0.4,     # chain length from symptom to root cause
}


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


class FlawArchetype(ABC):
    id: str
    title: str
    domain: str
    # The bug variants this archetype can plant, and how many story domains
    # it can frame them in. A cohort pins one of each so every member faces
    # the same defect in the same setting, while names and constants still
    # vary per member.
    variants: list[str] = []
    domain_count: int = 1

    @abstractmethod
    def generate(self, seed: int, genes: dict | None = None,
                 pins: dict | None = None) -> GeneratedWorld:
        """Deterministic: the same (seed, genes, pins) always produces the same
        world. `pins` may fix {"variant": str, "domain": int}; everything else
        still comes from the seed."""
        raise NotImplementedError

    def random_pins(self, rng: random.Random) -> dict:
        return {"variant": rng.choice(self.variants), "domain": rng.randrange(self.domain_count)}

    def apply_pins(self, pins: dict | None, variant: str, domain_index: int) -> tuple[str, int]:
        if pins:
            if pins.get("variant") in self.variants:
                variant = pins["variant"]
            if isinstance(pins.get("domain"), int):
                domain_index = pins["domain"] % self.domain_count
        return variant, domain_index

    def rng(self, seed: int) -> random.Random:
        return random.Random(f"{self.id}:{seed}")

    @staticmethod
    def resolve_genes(genes: dict | None) -> dict:
        merged = dict(DEFAULT_GENES)
        if genes:
            for k, v in genes.items():
                if k in merged:
                    merged[k] = clamp01(float(v))
        return merged

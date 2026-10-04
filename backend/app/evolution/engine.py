"""
Evolutionary world generator.

This is the defensible core of VANTA. It does not store problems; it evolves
them. A world is a phenotype produced by an archetype from (seed, genes). We
score each candidate against a multi-criteria FITNESS function measured by
ACTUALLY COMPILING AND RUNNING it, then select and mutate toward a target
difficulty. The output is a world that is provably:

  1. Broken        -- the starter code genuinely fails its own hidden tests
                      (so the challenge isn't already solved).
  2. Fixable       -- at least one real, distinct fix passes (so it isn't
                      impossible or self-contradictory).
  3. Multi-solution-- at least two *architecturally different* fixes pass
                      (VANTA's defining property: many valid answers).
  4. On-target     -- its measured difficulty is close to what was asked.

Why this is hard to replicate even with resources: the artifact a scraper
could steal (one generated world) is worthless, because the next seed
produces a structurally different world, and the VALUE is the
generate-test-select-mutate loop plus the fitness function plus the archetype
pool -- not any stored answer. There is no answer key to leak.

Determinism: a given (archetype, base_seed, target genes) reproduces the
same evolved world, because all randomness flows through seeded RNGs derived
from base_seed.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from app.execution.c_sandbox import CSandbox
from app.worldgen.archetype import FlawArchetype, GeneratedWorld, clamp01
from app.worldgen.evaluate import evaluate_submission, parse_results


@dataclass
class FitnessReport:
    broken: bool = False           # starter fails its own tests
    fixable: bool = False          # >=1 reference fix passes
    distinct_fixes: int = 0        # how many architecturally different fixes pass
    difficulty_error: float = 1.0  # |measured - target|, 0 is perfect
    score: float = 0.0
    notes: list[str] = field(default_factory=list)

    @property
    def viable(self) -> bool:
        # A world is only servable if it is genuinely broken AND fixable by
        # more than one distinct approach. Everything else is a failed
        # candidate the loop discards.
        return self.broken and self.fixable and self.distinct_fixes >= 2


@dataclass
class EvolvedWorld:
    world: GeneratedWorld
    fitness: FitnessReport
    generation: int


# Reference fixes are provided per-archetype so the loop can test the
# "fixable" and "multi-solution" properties without a human in the loop.
# They are NOT shown to contestants -- they exist only so evolution can
# prove a world is solvable in more than one way. Each entry is a function
# (struct_name, func_name, checkout_name|None) -> C source string.
from app.evolution.reference_fixes import REFERENCE_FIXES  # noqa: E402


class EvolutionEngine:
    def __init__(self, sandbox: CSandbox | None = None):
        # Internal loop uses a fast (no-sanitizer) sandbox for throughput;
        # the harness is trusted and we only need pass/fail counts here.
        # Contestant-facing evaluation uses a separate, sanitized sandbox.
        self.sandbox = sandbox or CSandbox(timeout_seconds=20.0, fast=True)

    def _target_vector(self, target: float) -> dict:
        """Map a single 0..1 difficulty knob onto the gene vector. The admin
        can override individual genes; this is the convenient 1-D control."""
        t = clamp01(target)
        return {
            "system_size": t,
            "bug_subtlety": t,
            "constant_magnitude": 0.3 + 0.6 * t,
            "noise": t,
            "edge_density": 0.3 + 0.6 * t,
            "reasoning_depth": t,
        }

    def _mutate(self, genes: dict, rng: random.Random, strength: float) -> dict:
        out = dict(genes)
        for k in out:
            if rng.random() < 0.6:  # mutate ~60% of genes each step
                out[k] = clamp01(out[k] + rng.uniform(-strength, strength))
        return out

    async def _measure_fitness(
        self, archetype: FlawArchetype, world: GeneratedWorld, target: float
    ) -> FitnessReport:
        report = FitnessReport()

        # 1. Broken: the starter must fail its own hidden tests. A starter
        # that compiles, runs, and has >=1 failing test is genuinely broken.
        starter_eval = await evaluate_submission(world, world.starter_source, self.sandbox)
        if starter_eval.get("reason") == "compile_error":
            report.notes.append("starter failed to compile")
            report.score = 0.0
            return report
        failing = [t for t in starter_eval.get("tests", []) if not t["passed"]]
        report.broken = starter_eval["verdict"] == "rejected" and len(failing) > 0
        if not report.broken:
            report.notes.append("starter unexpectedly passed (bug not exercised)")

        # 2+3. Fixable and multi-solution: count distinct reference fixes that pass.
        fixes = REFERENCE_FIXES.get(archetype.id, [])
        passing = 0
        for make_fix in fixes:
            src = make_fix(world)
            if src is None:
                continue
            ev = await evaluate_submission(world, src, self.sandbox)
            if ev["verdict"] == "accepted":
                passing += 1
        report.fixable = passing >= 1
        report.distinct_fixes = passing

        # 4. Difficulty: measure how many hidden tests the starter fails as a
        # cheap proxy for "how much is wrong", plus gene-implied difficulty.
        measured = self._estimate_difficulty(world, starter_eval)
        report.difficulty_error = abs(measured - target)

        # Composite score. Viability gates dominate; difficulty is a tiebreak.
        s = 0.0
        s += 0.4 if report.broken else 0.0
        s += 0.3 if report.fixable else 0.0
        s += 0.2 * min(report.distinct_fixes, 2) / 2.0
        s += 0.1 * (1.0 - report.difficulty_error)
        report.score = s
        return report

    def _estimate_difficulty(self, world: GeneratedWorld, starter_eval: dict) -> float:
        # Blend gene-implied difficulty with observed fragility. More failing
        # hidden tests on the starter == a more "obvious" bug == easier.
        genes = world.genes
        gene_diff = (genes["bug_subtlety"] * 0.5 + genes["constant_magnitude"] * 0.2 +
                     genes["edge_density"] * 0.3)
        tests = starter_eval.get("tests", [])
        if tests:
            frac_failing = sum(1 for t in tests if not t["passed"]) / len(tests)
            # many failing -> obvious -> lower difficulty contribution
            observed_diff = 1.0 - frac_failing
        else:
            observed_diff = 0.5
        return clamp01(0.6 * gene_diff + 0.4 * observed_diff)

    async def evolve(
        self,
        archetype: FlawArchetype,
        base_seed: int,
        target_difficulty: float = 0.5,
        population: int = 6,
        generations: int = 4,
    ) -> EvolvedWorld:
        """Run the evolutionary loop and return the best viable world found.
        Falls back to the best candidate seen if none is fully viable within
        the budget (rare; the caller can retry with a new base_seed)."""
        rng = random.Random(f"evolve:{archetype.id}:{base_seed}:{target_difficulty}")
        base_genes = self._target_vector(target_difficulty)

        # Initial population: base genes plus mutated variants, distinct seeds.
        pop_genes = [base_genes] + [
            self._mutate(base_genes, rng, 0.25) for _ in range(population - 1)
        ]
        best: EvolvedWorld | None = None

        import asyncio
        for gen in range(generations):
            worlds = [
                archetype.generate(base_seed * 1000 + gen * 100 + i, genes)
                for i, genes in enumerate(pop_genes)
            ]
            # Evaluate the whole population concurrently -- each fitness check
            # is independent subprocess work, so this is a large speedup.
            fits = await asyncio.gather(
                *(self._measure_fitness(archetype, w, target_difficulty) for w in worlds)
            )
            scored: list[EvolvedWorld] = [
                EvolvedWorld(world=w, fitness=f, generation=gen) for w, f in zip(worlds, fits)
            ]
            for cand in scored:
                if best is None or cand.fitness.score > best.fitness.score:
                    best = cand
            # Early exit: a viable, near-target world is good enough.
            viable = [c for c in scored if c.fitness.viable]
            if viable:
                viable.sort(key=lambda c: (c.fitness.distinct_fixes, -c.fitness.difficulty_error),
                            reverse=True)
                top = viable[0]
                if top.fitness.difficulty_error < 0.2:
                    return top
                if best is None or top.fitness.score > best.fitness.score:
                    best = top
            # Select top half by score, breed next generation by mutation.
            scored.sort(key=lambda c: c.fitness.score, reverse=True)
            survivors = scored[: max(2, population // 2)]
            next_genes = [s.world.genes for s in survivors]
            while len(next_genes) < population:
                parent = rng.choice(survivors)
                next_genes.append(self._mutate(parent.world.genes, rng, 0.2))
            pop_genes = next_genes

        assert best is not None
        return best

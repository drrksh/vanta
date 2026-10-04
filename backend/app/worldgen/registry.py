"""
Archetype registry + the public world-generation entry point.

Picks a flaw archetype from the pool (deterministically from the seed, so
the flaw CATEGORY itself varies across sessions) and evolves a viable world
from it. This is the single call the service/API layer uses.
"""
from __future__ import annotations

import random

from app.evolution.engine import EvolutionEngine, EvolvedWorld
from app.worldgen.archetype import FlawArchetype
from app.worldgen.archetypes.pool_leak import PoolLeakArchetype
from app.worldgen.archetypes.starvation import StarvationArchetype

ARCHETYPE_POOL: list[FlawArchetype] = [
    StarvationArchetype(),
    PoolLeakArchetype(),
]

ARCHETYPES_BY_ID = {a.id: a for a in ARCHETYPE_POOL}


class WorldGenerationError(Exception):
    pass


async def generate_world(
    session_seed: int,
    target_difficulty: float = 0.5,
    archetype_id: str | None = None,
    engine: EvolutionEngine | None = None,
    max_restarts: int = 3,
) -> EvolvedWorld:
    """Evolve a viable world. If `archetype_id` is given, use that archetype;
    otherwise pick one deterministically from the seed so the flaw category
    varies. Retries with derived seeds if evolution can't find a viable
    world within its budget (rare)."""
    engine = engine or EvolutionEngine()

    if archetype_id:
        if archetype_id not in ARCHETYPES_BY_ID:
            raise WorldGenerationError(f"Unknown archetype '{archetype_id}'")
        archetype = ARCHETYPES_BY_ID[archetype_id]
    else:
        picker = random.Random(f"archetype_pick:{session_seed}")
        archetype = picker.choice(ARCHETYPE_POOL)

    last = None
    for attempt in range(max_restarts):
        seed = session_seed if attempt == 0 else session_seed * 7919 + attempt
        evolved = await engine.evolve(
            archetype, base_seed=seed, target_difficulty=target_difficulty,
            population=6, generations=3,
        )
        last = evolved
        if evolved.fitness.viable:
            return evolved
    # Could not find a fully viable world; return best effort. Caller decides.
    assert last is not None
    return last

from __future__ import annotations

import re

import pytest

from app.evolution.engine import EvolutionEngine
from app.execution.c_sandbox import CSandbox
from app.worldgen.archetypes.pool_leak import PoolLeakArchetype
from app.worldgen.archetypes.starvation import StarvationArchetype
from app.worldgen.evaluate import evaluate_submission
from app.worldgen.registry import generate_world


@pytest.fixture
def engine():
    return EvolutionEngine()


@pytest.mark.asyncio
async def test_pool_leak_evolves_viable_world(engine):
    arch = PoolLeakArchetype()
    r = await engine.evolve(arch, base_seed=1, target_difficulty=0.5, population=5, generations=2)
    assert r.fitness.broken
    assert r.fitness.fixable
    assert r.fitness.distinct_fixes >= 2
    assert r.fitness.viable


@pytest.mark.asyncio
async def test_starvation_evolves_viable_world(engine):
    arch = StarvationArchetype()
    r = await engine.evolve(arch, base_seed=2, target_difficulty=0.4, population=6, generations=3)
    assert r.fitness.viable


@pytest.mark.asyncio
async def test_same_seed_reproduces_same_world(engine):
    arch = PoolLeakArchetype()
    r1 = await engine.evolve(arch, base_seed=7, target_difficulty=0.5, population=4, generations=2)
    r2 = await engine.evolve(arch, base_seed=7, target_difficulty=0.5, population=4, generations=2)
    assert r1.world.starter_source == r2.world.starter_source
    assert r1.world.function_name == r2.world.function_name


@pytest.mark.asyncio
async def test_registry_picks_archetype_by_seed(engine):
    seen = set()
    for seed in range(1, 8):
        r = await generate_world(seed, target_difficulty=0.5, engine=engine)
        seen.add(r.world.archetype_id)
    assert seen == {"starvation_fairness", "pool_leak"}


@pytest.mark.asyncio
async def test_starter_rejected_correct_fix_accepted_pool(engine):
    arch = PoolLeakArchetype()
    r = await engine.evolve(arch, base_seed=3, target_difficulty=0.5, population=5, generations=2)
    world = r.world
    sanitized = CSandbox(timeout_seconds=15.0, fast=False)

    starter_eval = await evaluate_submission(world, world.starter_source, sanitized)
    assert starter_eval["verdict"] == "rejected"

    struct = re.search(r"struct (\w+) \{", world.shared_header).group(1)
    checkout = re.search(r"int (\w+)\(struct \w+ pool", world.shared_header).group(1)
    release = world.function_name
    fix = f"""
int {checkout}(struct {struct} pool[], int poolSize, int holderId) {{
    for (int i=0;i<poolSize;i++) if (pool[i].inUse && pool[i].holderId==holderId) return -1;
    for (int i=0;i<poolSize;i++) if (!pool[i].inUse) {{ pool[i].inUse=1; pool[i].holderId=holderId; return i; }}
    return -1;
}}
int {release}(struct {struct} pool[], int poolSize, int holderId) {{
    for (int i=0;i<poolSize;i++) if (pool[i].inUse && pool[i].holderId==holderId) {{ pool[i].inUse=0; return 1; }}
    return 0;
}}
"""
    fix_eval = await evaluate_submission(world, fix, sanitized)
    assert fix_eval["verdict"] == "accepted"

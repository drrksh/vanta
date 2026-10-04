"""
Reference fixes per archetype.

These are known-good solutions the EvolutionEngine uses to PROVE a generated
world is fixable -- and fixable in more than one architecturally distinct
way (VANTA's multi-solution property). They are never shown to contestants;
they exist only inside the generate-test loop.

Each fix is a callable (GeneratedWorld) -> str | None. It reads the world's
randomized struct/function names and returns compilable C. Returning None
means "not applicable to this variant".

"Architecturally distinct" matters: for each archetype we supply fixes that
differ in approach (e.g. forward vs backward scan, aging-guard vs
always-oldest), so distinct_fixes >= 2 means the world genuinely admits
different correct designs, not the same code twice.
"""
from __future__ import annotations

import re

from app.worldgen.archetype import GeneratedWorld


def _names_starvation(world: GeneratedWorld):
    struct = re.search(r"struct (\w+) \{", world.shared_header).group(1)
    func = world.function_name
    return struct, func


def _starvation_aging_guard(world: GeneratedWorld) -> str:
    struct, func = _names_starvation(world)
    # Shortest-job-first with an aging override: a job waiting past a large
    # bound is forced through. Respects close time. Distinct approach #1.
    return f"""
int {func}(struct {struct} jobs[], int count, int now, int minutesLeftToday) {{
    int forced = -1, best = -1;
    for (int i = 0; i < count; i++) {{
        if (jobs[i].isAbandoned || jobs[i].isFinished || jobs[i].isRejected) continue;
        if (jobs[i].startedAt != -1) continue;
        if (jobs[i].submittedAt > now) continue;
        if (jobs[i].minutesNeeded > minutesLeftToday) continue;
        int waited = now - jobs[i].submittedAt;
        if (waited >= 1200 && forced == -1) forced = i;
        if (best == -1 || jobs[i].minutesNeeded < jobs[best].minutesNeeded) best = i;
    }}
    return (forced != -1) ? forced : best;
}}
"""


def _starvation_oldest_first(world: GeneratedWorld) -> str:
    struct, func = _names_starvation(world)
    # Always serve the oldest eligible request that fits before close. A
    # genuinely different design (pure FCFS with a feasibility filter), no
    # size consideration at all. Distinct approach #2.
    return f"""
int {func}(struct {struct} jobs[], int count, int now, int minutesLeftToday) {{
    int oldest = -1;
    for (int i = 0; i < count; i++) {{
        if (jobs[i].isAbandoned || jobs[i].isFinished || jobs[i].isRejected) continue;
        if (jobs[i].startedAt != -1) continue;
        if (jobs[i].submittedAt > now) continue;
        if (jobs[i].minutesNeeded > minutesLeftToday) continue;
        if (oldest == -1 || jobs[i].submittedAt < jobs[oldest].submittedAt) oldest = i;
    }}
    return oldest;
}}
"""


def _names_pool(world: GeneratedWorld):
    struct = re.search(r"struct (\w+) \{", world.shared_header).group(1)
    checkout = re.search(r"int (\w+)\(struct \w+ pool", world.shared_header).group(1)
    release = world.function_name
    return struct, checkout, release


def _pool_forward(world: GeneratedWorld) -> str:
    struct, checkout, release = _names_pool(world)
    # Correct checkout (guards aliasing) + forward-scan release that checks
    # inUse. Distinct approach #1.
    return f"""
int {checkout}(struct {struct} pool[], int poolSize, int holderId) {{
    for (int i = 0; i < poolSize; i++)
        if (pool[i].inUse && pool[i].holderId == holderId) return -1;
    for (int i = 0; i < poolSize; i++)
        if (!pool[i].inUse) {{ pool[i].inUse = 1; pool[i].holderId = holderId; return i; }}
    return -1;
}}
int {release}(struct {struct} pool[], int poolSize, int holderId) {{
    for (int i = 0; i < poolSize; i++)
        if (pool[i].inUse && pool[i].holderId == holderId) {{ pool[i].inUse = 0; return 1; }}
    return 0;
}}
"""


def _pool_backward(world: GeneratedWorld) -> str:
    struct, checkout, release = _names_pool(world)
    # Same correctness, opposite traversal order throughout. Distinct
    # approach #2 (genuinely different slot-assignment behavior under load).
    return f"""
int {checkout}(struct {struct} pool[], int poolSize, int holderId) {{
    for (int i = poolSize - 1; i >= 0; i--)
        if (pool[i].inUse && pool[i].holderId == holderId) return -1;
    for (int i = poolSize - 1; i >= 0; i--)
        if (!pool[i].inUse) {{ pool[i].inUse = 1; pool[i].holderId = holderId; return i; }}
    return -1;
}}
int {release}(struct {struct} pool[], int poolSize, int holderId) {{
    for (int i = poolSize - 1; i >= 0; i--)
        if (pool[i].inUse && pool[i].holderId == holderId) {{ pool[i].inUse = 0; return 1; }}
    return 0;
}}
"""


REFERENCE_FIXES = {
    "starvation_fairness": [_starvation_aging_guard, _starvation_oldest_first],
    "pool_leak": [_pool_forward, _pool_backward],
}

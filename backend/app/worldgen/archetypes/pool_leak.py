"""
Pool Leak archetype.

A fixed-capacity resource pool hands out numbered slots and must reclaim
them on release. The "obvious" implementation leaks capacity: a
returned/released slot is not correctly cleared under some condition, so
the pool permanently loses capacity and eventually reports "full" while
physically empty.

Structurally different from the starvation archetype (state/bookkeeping
correctness under a checkout/release cycle, not scheduling order). Three
buggy variants:
  - linear_search_first_match: release matches on stale in-memory holderId
    without checking the slot is still in use, so a double-release frees a
    slot that was already free (and a correct impl must reject it).
  - off_by_one_index: release computes the slot index from holderId with an
    off-by-one, clearing the wrong slot or missing the target.
  - no_double_checkout_guard: checkout doesn't verify a slot is free before
    handing the same holder a second slot, enabling aliasing.

Genes:
  - constant_magnitude -> larger pool size
  - edge_density       -> more churn cycles in the stress test
"""
from __future__ import annotations

from app.worldgen.archetype import FlawArchetype, GeneratedAgentGrounding, GeneratedWorld

_DOMAINS = [
    {"noun": "vehicle", "unit": "parking spot", "place": "the campus parking garage"},
    {"noun": "book", "unit": "checkout slot", "place": "the university library"},
    {"noun": "kit", "unit": "locker", "place": "the equipment rental room"},
    {"noun": "laptop", "unit": "loaner unit", "place": "the IT help desk"},
]
_STRUCT_NAMES = ["Slot", "Unit", "Holding", "Checkout", "Bay"]
_CHECKOUT_FUNCS = ["checkoutItem", "acquireSlot", "reserveUnit", "takeSlot"]
_RELEASE_FUNCS = ["releaseItem", "returnSlot", "freeUnit", "giveBackSlot"]
_BUG_VARIANTS = ["linear_search_first_match", "off_by_one_index", "no_double_checkout_guard"]


class PoolLeakArchetype(FlawArchetype):
    id = "pool_leak"
    title = "Resource Pool Integrity"
    domain = "resource_pool"

    def generate(self, seed: int, genes: dict | None = None) -> GeneratedWorld:
        genes = self.resolve_genes(genes)
        rng = self.rng(seed)
        domain = rng.choice(_DOMAINS)
        struct_name = rng.choice(_STRUCT_NAMES)
        checkout_func = rng.choice(_CHECKOUT_FUNCS)
        release_func = rng.choice(_RELEASE_FUNCS)
        bug_variant = rng.choice(_BUG_VARIANTS)

        mag = genes["constant_magnitude"]
        pool_size = rng.choice([10, 12, 16, 20, 24])
        pool_size = max(6, int(pool_size * (0.7 + 0.8 * mag)))
        cycle_count = int(200 + 400 * genes["edge_density"])

        shared_header = f"""
#define MAX_POOL 128
struct {struct_name} {{
    int inUse;
    int holderId;
}};
int {checkout_func}(struct {struct_name} pool[], int poolSize, int holderId);
int {release_func}(struct {struct_name} pool[], int poolSize, int holderId);
"""
        starter_source = self._starter(struct_name, checkout_func, release_func, bug_variant)
        harness_source = self._harness(struct_name, checkout_func, release_func, pool_size, cycle_count)

        mandatory = [
            f"Every {domain['unit']} that is released must become available again.",
            f"Two checkouts must never hold the same {domain['unit']} at once.",
            f"{checkout_func}() must fail cleanly when the pool is genuinely full, never crash.",
            "Held count must equal checkouts minus matched releases after any sequence.",
            "The program terminates for every finite input.",
            f"Releasing a {domain['unit']} never checked out must be rejected.",
            f"Releasing the same {domain['unit']} twice must reject the second release.",
        ]
        optional = [
            "Minimize the time to find a free slot.",
            "Keep the bookkeeping simple.",
            "Make it easy to audit which holder has which slot.",
            "Handle very high churn gracefully.",
        ]
        briefing = (
            f"{domain['place'].capitalize()} manages a fixed number of {domain['unit']}s that get "
            f"checked out and returned constantly. Lately the system claims to be full even when "
            f"plenty of {domain['unit']}s should be free. Staff insist they process returns "
            f"correctly. Figure out what's happening to the missing capacity and fix it."
        )
        specification = (
            f"Implement {release_func}(), which reclaims a {domain['unit']} when its holder returns "
            f"it. You may also inspect {checkout_func}(). Multiple correct bookkeeping designs exist."
        )
        groundings = [
            GeneratedAgentGrounding("frequent_user", {"unit": domain["unit"]}),
            GeneratedAgentGrounding("staff", {"place": domain["place"]}),
            GeneratedAgentGrounding("developer", {"pool_size": pool_size, "variant": bug_variant}),
            GeneratedAgentGrounding("auditor", {"unit": domain["unit"]}),
        ]
        return GeneratedWorld(
            archetype_id=self.id, seed=seed, genes=genes,
            title=domain["place"].replace("the ", "").title(),
            briefing=briefing, specification=specification,
            starter_source=starter_source, function_name=release_func,
            function_signature=f"int {release_func}(struct {struct_name} pool[], int poolSize, int holderId)",
            shared_header=shared_header,
            mandatory_properties=mandatory, optional_objectives=optional,
            sample_input_description=f"The pool has {pool_size} {domain['unit']}s. Build your own checkout/release sequences.",
            agent_groundings=groundings, harness_source=harness_source,
            ground_truth_summary=(
                f"archetype={self.id} bug_variant={bug_variant} pool_size={pool_size} "
                f"cycle_count={cycle_count} checkout={checkout_func} release={release_func} mag={mag:.2f}"
            ),
            params={
                "struct_name": struct_name, "checkout_func": checkout_func,
                "release_func": release_func, "bug_variant": bug_variant,
                "pool_size": pool_size, "cycle_count": cycle_count, "domain": domain,
            },
        )

    def _checkout_impl(self, struct_name, checkout_func, bug_variant) -> str:
        if bug_variant == "no_double_checkout_guard":
            return f"""
int {checkout_func}(struct {struct_name} pool[], int poolSize, int holderId) {{
    for (int i = 0; i < poolSize; i++) {{
        if (!pool[i].inUse) {{ pool[i].inUse = 1; pool[i].holderId = holderId; return i; }}
    }}
    return -1;
}}
"""
        return f"""
int {checkout_func}(struct {struct_name} pool[], int poolSize, int holderId) {{
    for (int i = 0; i < poolSize; i++)
        if (pool[i].inUse && pool[i].holderId == holderId) return -1;
    for (int i = 0; i < poolSize; i++) {{
        if (!pool[i].inUse) {{ pool[i].inUse = 1; pool[i].holderId = holderId; return i; }}
    }}
    return -1;
}}
"""

    def _starter(self, struct_name, checkout_func, release_func, bug_variant) -> str:
        checkout_src = self._checkout_impl(struct_name, checkout_func, bug_variant)
        if bug_variant == "linear_search_first_match":
            release_src = f"""
/* Frees whichever slot's last-recorded holderId matches, without checking
   the slot is actually still in use. A slot released earlier still has its
   old holderId in memory, so a second release with the same holderId can
   "succeed" against an already-free slot. */
int {release_func}(struct {struct_name} pool[], int poolSize, int holderId) {{
    for (int i = 0; i < poolSize; i++) {{
        if (pool[i].holderId == holderId) {{ pool[i].inUse = 0; return 1; }}
    }}
    return 0;
}}
"""
        elif bug_variant == "off_by_one_index":
            release_src = f"""
int {release_func}(struct {struct_name} pool[], int poolSize, int holderId) {{
    int idx = holderId % (poolSize + 1);  /* off-by-one: should be % poolSize */
    if (idx >= 0 && idx < poolSize && pool[idx].inUse) {{ pool[idx].inUse = 0; return 1; }}
    return 0;
}}
"""
        else:
            release_src = f"""
int {release_func}(struct {struct_name} pool[], int poolSize, int holderId) {{
    for (int i = 0; i < poolSize; i++) {{
        if (pool[i].inUse && pool[i].holderId == holderId) {{ pool[i].inUse = 0; return 1; }}
    }}
    return 0;
}}
"""
        return checkout_src + "\n" + release_src

    def _harness(self, struct_name, checkout_func, release_func, pool_size, cycle_count) -> str:
        return f"""
#include <stdio.h>
#include <string.h>

static void reset(struct {struct_name} pool[], int poolSize) {{
    memset(pool, 0, sizeof(struct {struct_name}) * poolSize);
}}
static int countInUse(struct {struct_name} pool[], int poolSize) {{
    int c = 0; for (int i = 0; i < poolSize; i++) if (pool[i].inUse) c++; return c;
}}
static void report(const char *name, int pass, int *overall) {{
    printf("VANTA_TEST_RESULT|%s|%d|%d\\n", name, pass ? 0 : 1, pass);
    if (!pass) *overall = 0;
}}

int main(void) {{
    int overallPass = 1;
    struct {struct_name} pool[{pool_size}];

    {{
        reset(pool, {pool_size});
        int slot = {checkout_func}(pool, {pool_size}, 111);
        int rel = {release_func}(pool, {pool_size}, 111);
        report("public_basic", (slot != -1) && rel && countInUse(pool, {pool_size}) == 0, &overallPass);
    }}
    {{
        reset(pool, {pool_size});
        int allOk = 1;
        for (int i = 0; i < {pool_size}; i++)
            if ({checkout_func}(pool, {pool_size}, 1000 + i) == -1) allOk = 0;
        int overflow = {checkout_func}(pool, {pool_size}, 99999);
        report("public_full_rejected", allOk && overflow == -1, &overallPass);
    }}
    {{
        reset(pool, {pool_size});
        int leaked = 0;
        for (int round = 0; round < {cycle_count}; round++) {{
            int h = round * 7 + 3;
            int slot = {checkout_func}(pool, {pool_size}, h);
            if (slot == -1) {{ leaked = 1; break; }}
            if (!{release_func}(pool, {pool_size}, h)) {{ leaked = 1; break; }}
        }}
        report("hidden_churn_no_leak", !leaked && countInUse(pool, {pool_size}) == 0, &overallPass);
    }}
    {{
        reset(pool, {pool_size});
        int n = {pool_size} / 2, ids[64], ok = 1;
        for (int i = 0; i < n; i++) {{ ids[i] = 500 + i;
            if ({checkout_func}(pool, {pool_size}, ids[i]) == -1) ok = 0; }}
        for (int i = n - 1; i >= 0; i--)
            if (!{release_func}(pool, {pool_size}, ids[i])) ok = 0;
        report("hidden_reverse_release", ok && countInUse(pool, {pool_size}) == 0, &overallPass);
    }}
    {{
        reset(pool, {pool_size});
        report("hidden_release_never_checked_out", {release_func}(pool, {pool_size}, 424242) == 0, &overallPass);
    }}
    {{
        reset(pool, {pool_size});
        int slot = {checkout_func}(pool, {pool_size}, 55555);
        int first = {release_func}(pool, {pool_size}, 55555);
        int second = {release_func}(pool, {pool_size}, 55555);
        report("hidden_double_release", (slot != -1) && first && !second, &overallPass);
    }}
    {{
        reset(pool, {pool_size});
        int s1 = {checkout_func}(pool, {pool_size}, 777);
        int s2 = {checkout_func}(pool, {pool_size}, 777);
        report("hidden_no_aliasing", (s1 != -1) && (s2 == -1), &overallPass);
    }}
    {{
        reset(pool, {pool_size});
        int ids[{pool_size}], ok = 1;
        for (int i = 0; i < {pool_size}; i++) {{ ids[i] = 2000 + i;
            if ({checkout_func}(pool, {pool_size}, ids[i]) == -1) ok = 0; }}
        for (int i = 0; i < {pool_size}; i++)
            if (!{release_func}(pool, {pool_size}, ids[i])) ok = 0;
        for (int i = 0; i < {pool_size}; i++)
            if ({checkout_func}(pool, {pool_size}, ids[i] + 10000) == -1) ok = 0;
        report("hidden_capacity_reusable", ok, &overallPass);
    }}
    printf("VANTA_OVERALL|%d\\n", overallPass);
    return overallPass ? 0 : 1;
}}
"""

# Extending VANTA: adding a defect class {#ch-extending}

The most valuable way to grow VANTA is to add archetypes. Each new archetype automatically gets
evolution, grading, ratings, cohorts, originality analysis, the web UI and Discord. Only the probe
lab and witnesses need archetype-specific code. This chapter is a checklist.

## 1. Write the archetype

Create `backend/app/worldgen/archetypes/<name>.py`:

```python
from app.worldgen.archetype import FlawArchetype, GeneratedWorld

_DOMAINS = [{"noun": "...", "place": "..."}, ...]
_STRUCT_NAMES = [...]               # wide pools: cohorts need unique names
_BUG_VARIANTS = ["variant_a", "variant_b", "variant_c"]

class RingBufferArchetype(FlawArchetype):
    id = "ring_buffer"
    title = "Message Buffer Integrity"
    domain = "data_structures"
    variants = _BUG_VARIANTS
    domain_count = len(_DOMAINS)

    def generate(self, seed, genes=None, pins=None) -> GeneratedWorld:
        genes = self.resolve_genes(genes)
        rng = self.rng(seed)
        domain_index = rng.randrange(len(_DOMAINS))
        struct_name = rng.choice(_STRUCT_NAMES)
        variant = rng.choice(_BUG_VARIANTS)
        variant, domain_index = self.apply_pins(pins, variant, domain_index)
        # ... draw constants from rng, scaled by genes ...
        # ... build shared_header, starter_source (NO comments that explain the bug),
        #     harness_source (prints VANTA_TEST_RESULT / VANTA_OVERALL lines) ...
        return GeneratedWorld(..., params={"struct_name": struct_name, "func_name": ...,
                                           "bug_variant": variant, "domain": _DOMAINS[domain_index],
                                           "domain_index": domain_index, "pins": pins or None})
```

Rules that keep it correct (each one was learned the hard way in this project):

- **Every random choice must come from `rng`**, so a seed reproduces exactly.
- **The harness must exercise the real defect.** For example, a starvation test that lets the
  queue drain never starves anyone, so the bug is never triggered.
- **Every hidden test must check the full set of required properties**, not a subset. A narrow
  check let broken variants pass.
- **No hints in the starter.** No comments, and no `(void)param;` lines. A test enforces this.
- **Use `params` for every name and constant** that the probe lab, witnesses or originality
  analysis will need.

## 2. Add two different reference fixes

In `backend/app/evolution/reference_fixes.py`, add at least two functions `(world) -> str` that
solve the problem *in different ways*, and register them:

```python
REFERENCE_FIXES["ring_buffer"] = [_ring_modulo_indices, _ring_count_field]
```

Without at least two passing fixes, no world can be viable.

## 3. Register it

Add an instance to `ARCHETYPE_POOL` in `backend/app/worldgen/registry.py`. It now appears in
`/api/archetypes`, in the landing page chips, and in random picks. The Discord `defect` choices
are a fixed list in `discord_bot/bot.py` (`DEFECT_CHOICES`), so add it there too.

## 4. Probe kit (experiments)

Subclass `ProbeKit` in `backend/app/investigation/probes.py`:

- `describe` returns help text, limits and a template;
- `normalize` validates every field with `_int` and expands repeats;
- `harness` writes a C `main()` that only uses validated integers and ends with `PROBE_DONE`;
- `parse` reads your `PROBE_...` lines into a trace.

Add it to `PROBE_KITS`. The frontend `ProbeLab` renders `job_queue` and `pool` traces. A new
`kind` needs a result component next to `JobResult` and `PoolResult`.

## 5. Witness kit

Subclass `WitnessKit` in `backend/app/investigation/witnesses.py`:

- `cast(world)` returns the witnesses (each with topics and keywords) and one busy-period
  scenario whose entries carry an `owner`;
- `answer(world, cast, witness, topic, trace)` computes the text and evidence from that witness's
  slice of the trace only.

Add it to `WITNESS_KITS`.

## 6. Tests

Copy the patterns in `backend/tests/`:

- the archetype evolves a viable world;
- every pinned variant evolves a viable world;
- the starter is rejected and a fix is accepted under the sanitized sandbox;
- every witness answers every topic deterministically;
- a probe shows a difference between the original and a fix;
- `test_starter_code_never_explains_its_own_bug` covers it automatically.

## Adding an API endpoint or page

- **Endpoint:** add a function with `@router.get/post/delete` in `backend/app/api/routes.py`. Put
  logic in a `core/` or `investigation/` module, not in the route. Add a method to
  `frontend/src/api/client.ts` and a type to `frontend/src/types.ts`.
- **Page:** add a component in `frontend/src/pages/` and a `<Route>` in `frontend/src/App.tsx`.
  Reuse `Panel`, `Label`, `Chip` and `Button` from `components/ui.tsx`, and the CSS tokens from
  `index.css`, so it matches the rest of the UI.
- **Discord command:** add a method to `VantaCommands` (returning a `Reply`), wire it in
  `build_tree`, and add a test in `test_discord_commands.py`.

# Features in depth {#ch-features}

This chapter explains every feature: what it does, how it works inside, and the exact numbers the
code uses. Where a feature has a "why", it is given too, because the why is usually what a
professor or judge will ask about.

## World generation (archetypes)

### The archetype contract

Every archetype subclasses `FlawArchetype` (`backend/app/worldgen/archetype.py`) and provides:

| Member | Meaning |
|---|---|
| `id`, `title`, `domain` | Machine id (`pool_leak`), human title (*Resource Pool Integrity*), category |
| `variants` | List of bug variant names it can plant |
| `domain_count` | How many story settings it has |
| `generate(seed, genes=None, pins=None)` | Builds a complete `GeneratedWorld`; must be deterministic |
| `rng(seed)` | A `random.Random` seeded with `"<id>:<seed>"` |
| `resolve_genes(genes)` | Fills in missing genes from `DEFAULT_GENES` and clamps every value to 0–1 |
| `random_pins(rng)`, `apply_pins(...)` | Choose and apply a pinned variant and setting (used by cohorts) |

The generated world has these fields. `GeneratedAgentGrounding` and `agent_groundings` are a
leftover from the earlier chatbot design. They are generated but not stored or used.

| Field | Contents |
|---|---|
| `archetype_id`, `seed`, `genes` | Where the world came from |
| `title`, `briefing`, `specification` | The story and the task |
| `starter_source` | The broken C the contestant starts from |
| `function_name`, `function_signature` | The function the contestant must implement |
| `shared_header` | Struct and prototypes, prepended to both C files |
| `mandatory_properties` | Requirements (plain English) |
| `optional_objectives` | Nice-to-have goals (not graded) |
| `sample_input_description` | One line about scale, such as "A day is 436 simulated minutes" |
| `harness_source` | The hidden test program |
| `ground_truth_summary` | Admin-only one-line summary of the planted bug and constants |
| `params` | Structured names and constants used by the probe lab, witnesses and cohorts |

### Archetype 1: Shared Resource Fairness (`starvation_fairness`)

**Story.** One machine is shared by everyone, opens for part of each day, and runs one job at a
time. People complain that "certain people dominate it". The settings are:

| # | Job noun | Machine | Place |
|---|---|---|---|
| 0 | print job | 3D printer | the student fabrication lab |
| 1 | wash cycle | washing machine | the dormitory laundry room |
| 2 | render job | shared GPU workstation | the media lab |
| 3 | repair request | bike repair stand | the campus cycling co-op |
| 4 | scan request | document scanner | the library digitization desk |

**Names.** The struct name comes from 12 options (`Job`, `Task`, `Request`, `WorkItem`, `Ticket`,
`Order`, `Booking`, `Submission`, `QueueEntry`, `Batch`, `Run`, `Commission`). The function name
is a verb (8 options: `choose`, `select`, `pick`, `schedule`, `dispatch`, `elect`, `decide`,
`nominate`) plus a tail (7 options: `Next`, `NextJob`, `ToRun`, `Upcoming`, `Candidate`,
`NextUp`, `Successor`). That gives 672 combinations, for example `electUpcoming`.

**The struct** (in the shared header) always has these fields:

```c
struct Job {
    int id;
    int minutesNeeded;   /* how long the job takes */
    int submittedAt;     /* simulated minute it was handed in */
    int isAbandoned;     /* owner walked away */
    int isFinished;
    int isRejected;      /* longer than a whole day: refused up front */
    int startedAt;       /* -1 until started */
    int finishedAt;      /* -1 until finished */
};
int chooseToRun(struct Job jobs[], int count, int now, int minutesLeftToday);
```

The contestant's function receives every job, the current minute and the minutes left before
closing. It returns the index of the job to start, or -1 for none.

**Constants.** Every world draws its own numbers:

| Constant | How it is drawn |
|---|---|
| Day length *L* | One of 360/420/480/540/600, multiplied by `0.8 + 0.6 × constant_magnitude` |
| Long job | Random between `0.55·L` and `L − 10` minutes |
| Short job | 5–15 minutes |
| Short-job interval | 2 to (short job − 1) minutes, so the queue never drains |
| Long job submitted at | interval × (8–20), into a stream that is already flowing |
| Starvation bound | 1500–2500 minutes of waiting counts as "ignored forever" |

**Variants.** `bug_subtlety` biases the choice. The weights are `[1 − s, 0.5, 0.3 + s]` for
`no_close_check`, `pure_shortest_first` and `truncating_priority`.

```c
/* pure_shortest_first: always the shortest eligible job */
if (best == -1 || jobs[i].minutesNeeded < jobs[best].minutesNeeded) best = i;

/* no_close_check: oldest first, but never looks at minutesLeftToday */
if (oldest == -1 || jobs[i].submittedAt < jobs[oldest].submittedAt) oldest = i;

/* truncating_priority: integer division collapses the score to 0 */
int score = (waited > 0) ? (jobs[i].minutesNeeded / waited) : jobs[i].minutesNeeded;
```

**Requirements** shown to the contestant: no valid job is ignored forever; an abandoned job frees
the machine; never start a job that can't finish before close; reject a job longer than a full
day; always terminate; never start a job twice.

**Hidden tests** (8). The simulation runs up to 120 days, one tick per minute. A violation bitmask
records 1 = starvation, 4 = started too late and 16 = a bad pick (out of range, not yet submitted,
or already done or started). Every test fails on any of these.

| Test | Scenario |
|---|---|
| `public_simple` | Three short jobs a few minutes apart |
| `public_single` | One 30-minute job |
| `hidden_zero_jobs` | Empty list |
| `hidden_exact_fit` | One job exactly one day long |
| `hidden_oversized_rejected` | A job longer than a day must be rejected; a normal one must finish |
| `hidden_starvation_stream` | Up to 600 short jobs arriving faster than they finish, plus one long job submitted mid-stream |
| `hidden_abandonment` | An abandoned job must not block the next one |
| `hidden_reverse_order` | Jobs given in reverse submission order |

### Archetype 2: Resource Pool Integrity (`pool_leak`)

**Story.** A fixed number of units is checked out and returned all day. The system claims to be
full when plenty should be free. The settings are:

| # | Item | Unit | Place |
|---|---|---|---|
| 0 | vehicle | parking spot | the campus parking garage |
| 1 | book | checkout slot | the university library |
| 2 | kit | locker | the equipment rental room |
| 3 | laptop | loaner unit | the IT help desk |

**Names.** The struct name comes from 12 options. The checkout function is one of 8 verbs
(`checkout`, `acquire`, `reserve`, `take`, `claim`, `lease`, `borrow`, `grab`) plus one of 6
nouns. The release function is one of 8 verbs (`release`, `return`, `free`, `giveBack`,
`surrender`, `drop`, `vacate`, `handBack`) plus one of 6 nouns. The struct is always
`{ int inUse; int holderId; }`.

**Constants.** The pool size is one of 10/12/16/20/24, multiplied by
`0.7 + 0.8 × constant_magnitude`, with a minimum of 6. The churn test runs
`200 + 400 × edge_density` cycles.

**Variants** (chosen uniformly):

```c
/* linear_search_first_match: frees a slot whose OLD holderId matches,
   even if the slot is already free -> a second release "succeeds" */
if (pool[i].holderId == holderId) { pool[i].inUse = 0; return 1; }

/* off_by_one_index: the wrong modulus */
int idx = holderId % (poolSize + 1);

/* no_double_checkout_guard: checkout never asks "do you already hold one?" */
```

**Requirements:** a released unit becomes available again; two checkouts never hold the same unit;
checkout fails cleanly when the pool is truly full; the held count equals checkouts minus matched
releases; always terminate; releasing a never-checked-out unit is rejected; a second release of
the same unit is rejected.

**Hidden tests** (8): `public_basic`, `public_full_rejected`, `hidden_churn_no_leak`,
`hidden_reverse_release`, `hidden_release_never_checked_out`, `hidden_double_release`,
`hidden_no_aliasing` (the same holder can't check out twice) and `hidden_capacity_reusable` (fill,
empty, refill).

### The registry

`backend/app/worldgen/registry.py` holds `ARCHETYPE_POOL` (the list of archetype objects) and
`ARCHETYPES_BY_ID`. `generate_world(session_seed, target_difficulty, archetype_id, engine,
max_restarts=3, pins=None)` picks the archetype. It uses the requested one, or draws one with
`random.Random("archetype_pick:<seed>")` so the defect *class* itself varies. It then runs
evolution. If no viable world is found it retries with seed `seed × 7919 + attempt`.

## The evolution engine

<figure class="diagram">
<svg viewBox="0 0 760 330" xmlns="http://www.w3.org/2000/svg" font-family="Inter, sans-serif">
  <defs><marker id="a3" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#5b6475"/></marker></defs>
  <g font-size="11">
  <rect x="10" y="20" width="160" height="62" rx="8" fill="#f3f4f6" stroke="#8a93a3"/>
  <text x="90" y="44" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">Target difficulty</text>
  <text x="90" y="62" text-anchor="middle" fill="#4a5466">→ gene vector,</text>
  <text x="90" y="75" text-anchor="middle" fill="#4a5466">+5 mutated copies</text>
  <rect x="210" y="20" width="160" height="62" rx="8" fill="#e8f4f8" stroke="#1f7a99"/>
  <text x="290" y="44" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">Generate 6 worlds</text>
  <text x="290" y="62" text-anchor="middle" fill="#4a5466">archetype.generate(</text>
  <text x="290" y="75" text-anchor="middle" fill="#4a5466">seed·1000+gen·100+i)</text>
  <rect x="410" y="20" width="160" height="62" rx="8" fill="#fdf3e3" stroke="#c27a12"/>
  <text x="490" y="44" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">Run the starter</text>
  <text x="490" y="62" text-anchor="middle" fill="#4a5466">hidden tests must</text>
  <text x="490" y="75" text-anchor="middle" fill="#4a5466">FAIL → broken</text>
  <rect x="590" y="20" width="160" height="62" rx="8" fill="#eaf6f1" stroke="#2f8f72"/>
  <text x="670" y="44" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">Run 2 reference fixes</text>
  <text x="670" y="62" text-anchor="middle" fill="#4a5466">must PASS → fixable,</text>
  <text x="670" y="75" text-anchor="middle" fill="#4a5466">distinct_fixes</text>
  <rect x="590" y="140" width="160" height="62" rx="8" fill="#ffffff" stroke="#1d2433"/>
  <text x="670" y="164" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">Score fitness</text>
  <text x="670" y="182" text-anchor="middle" fill="#4a5466">0.4·broken + 0.3·fixable</text>
  <text x="670" y="195" text-anchor="middle" fill="#4a5466">+ 0.2·fixes + 0.1·on-target</text>
  <polygon points="490,140 575,171 490,202 405,171" fill="#ffffff" stroke="#1d2433"/>
  <text x="490" y="167" text-anchor="middle" font-weight="600" fill="#1d2433">viable and</text>
  <text x="490" y="181" text-anchor="middle" font-weight="600" fill="#1d2433">error &lt; 0.2?</text>
  <rect x="210" y="140" width="160" height="62" rx="8" fill="#eaf6f1" stroke="#2f8f72"/>
  <text x="290" y="166" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">Store and serve</text>
  <text x="290" y="184" text-anchor="middle" fill="#4a5466">world + fitness → SQLite</text>
  <rect x="410" y="250" width="160" height="62" rx="8" fill="#e8f4f8" stroke="#1f7a99"/>
  <text x="490" y="274" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">Select and mutate</text>
  <text x="490" y="292" text-anchor="middle" fill="#4a5466">keep best half, mutate</text>
  <text x="490" y="305" text-anchor="middle" fill="#4a5466">60% of genes by ±0.2</text>
  </g>
  <g stroke="#5b6475" stroke-width="1.2" fill="none" marker-end="url(#a3)">
    <line x1="170" y1="51" x2="208" y2="51"/><line x1="370" y1="51" x2="408" y2="51"/>
    <line x1="570" y1="51" x2="588" y2="51"/><line x1="670" y1="82" x2="670" y2="138"/>
    <line x1="590" y1="171" x2="577" y2="171"/>
    <line x1="405" y1="171" x2="372" y2="171"/>
    <line x1="490" y1="202" x2="490" y2="248"/>
    <path d="M410,281 C300,281 290,240 290,84"/>
  </g>
  <text x="386" y="164" text-anchor="middle" font-size="10.5" fill="#2f8f72">yes</text>
  <text x="503" y="230" font-size="10.5" fill="#c27a12">no (next generation, max 3)</text>
</svg>
<figcaption>Figure 4.1. One run of <code>EvolutionEngine.evolve</code>. Candidates in a generation are evaluated in parallel.</figcaption>
</figure>

### Step by step

1. **Gene vector.** `_target_vector(t)` maps a difficulty *t* to genes: `system_size = t`,
   `bug_subtlety = t`, `constant_magnitude = 0.3 + 0.6t`, `noise = t`,
   `edge_density = 0.3 + 0.6t` and `reasoning_depth = t`.
2. **Initial population.** The base vector plus 5 mutated copies. `_mutate` changes each gene
   with probability 0.6 by a random amount in ±0.25, then clamps it to 0–1.
3. **Generate.** Candidate *i* in generation *g* uses seed `base_seed × 1000 + g × 100 + i`.
4. **Measure fitness** (`_measure_fitness`, run for all candidates at once with `asyncio.gather`):
   - run the starter against the harness. A compile error means the score is 0. **Broken** means
     the verdict is "rejected" and at least one test failed;
   - run every reference fix. **Fixable** means at least 1 passes, and **distinct_fixes** counts
     how many pass;
   - **difficulty error** = |estimated − target|. The estimate is
     `0.6 × gene_part + 0.4 × observed_part`, where
     `gene_part = 0.5·bug_subtlety + 0.2·constant_magnitude + 0.3·edge_density`.
     `observed_part = 1 − (fraction of starter tests failing)`, because a starter that fails
     everything is an *obvious* bug.
5. **Score** = `0.4·broken + 0.3·fixable + 0.2·min(distinct, 2)/2 + 0.1·(1 − error)`.
6. **Early exit.** If any candidate is viable and its difficulty error is below 0.2, return it
   (preferring more distinct fixes, then lower error).
7. **Select and mutate.** Keep the top half (at least 2). Fill the population back up by mutating
   random survivors with strength 0.2. Repeat.
8. If no generation produced a near-target viable world, return the best candidate seen. The
   registry then retries with a new seed if that candidate isn't viable.

**Speed.** The loop uses the fast (unsanitized) sandbox with a 20-second limit, because it
compiles 3 programs per candidate (starter + 2 fixes) × 6 candidates × up to 3 generations. In
practice a pool world takes about 1 second and a scheduler world about 5–30 seconds.

**Why this matters.** Nobody writes problems by hand, and there is no answer key to leak. The
valuable part is the generate–test–select loop, the fitness function and the archetypes, not any
one world.

## Grading submissions

### The sandbox

`CSandbox(timeout_seconds, compiler="gcc", fast=False).compile_and_run(harness, candidate,
shared_header)` does the following:

1. Runs `static_safety_check(candidate)`. Any match of a forbidden pattern returns a compile error
   without compiling. The forbidden patterns are `system(`, `exec*(`, `fork(`, `popen(`,
   `fopen(`, `freopen(`, `remove(`, `unlink(`, `rename(`, `#include <unistd.h>`,
   `#include <sys/...>`, `#include <fcntl.h>`, `asm` and `__asm__`.
2. Creates a temporary folder and writes `harness_main.c` and `candidate.c`, each prefixed with
   the shared header. Each `.c` file is compiled separately, so both need the struct definition.
3. Compiles both into one binary. Sanitized mode uses `-Wall -Wextra
   -fsanitize=undefined,address -O0 -g`; fast mode uses `-w -O1`.
4. Runs the binary with a wall-clock timeout. A timeout kills it.
5. Returns a `CRunResult` with `success`, `stdout`, `stderr`, `compile_error`,
   `runtime_error`, `timed_out` and `exit_code`. The folder is always deleted.

### Turning output into a verdict

`evaluate_submission(world, source, sandbox)` (`backend/app/worldgen/evaluate.py`):

| Situation | Verdict | Reason |
|---|---|---|
| Compilation failed (or the safety check refused it) | rejected | `compile_error` (message returned) |
| Ran out of time | rejected | `timeout` |
| No `VANTA_OVERALL|` line printed (the program crashed) | rejected | `runtime_error` |
| `VANTA_OVERALL|1` | accepted | — |
| `VANTA_OVERALL|0` | rejected | `failed_tests` |

The harness deliberately exits with code 1 when a test fails. A non-zero exit is therefore normal
for a wrong answer, and VANTA always reads the printed results first.

### What the contestant sees

`routes._contestant_tests` renames checks before they leave the server. `public_basic` becomes
**"public: basic"**, and every hidden test becomes **"hidden check N"**. The web UI shows checks
as chips, separately from the requirements list, because one hidden check can test several
requirements at once.

## Probe lab (experiments)

A **ProbeKit** exists per archetype (`backend/app/investigation/probes.py`). It has four jobs:

| Method | Job |
|---|---|
| `describe(world)` | Returns help text, limits, and an example scenario (`GET /probe`) |
| `normalize(world, scenario)` | Validates the JSON and expands `repeat` entries; raises `ProbeError` with a contestant-safe message |
| `harness(world, norm, event_cap)` | Writes a C `main()` with the scenario baked in as constant data |
| `parse(world, norm, stdout)` | Turns `PROBE_...` lines into a trace dictionary |

`run()` puts these together. A compile error, timeout or crash comes back as `ok: false` with
`error` and `detail`. Sanitizer output is trimmed to 12 lines and sandbox paths are removed.

### Scheduler experiments (`job_queue`)

```json
{
  "days": 3,
  "jobs": [
    {"minutes": 20, "at": 0},
    {"minutes": 45, "at": 10},
    {"minutes": 10, "at": 15, "repeat": 4, "every": 30},
    {"minutes": 60, "at": 100, "abandon_after": 25}
  ]
}
```

| Field | Rule |
|---|---|
| `days` | 1–30 (default 3): how long to watch |
| `minutes` | 1–20000 |
| `at` | 0 to `days × L`: the minute it is submitted (day 2 opens at minute *L*) |
| `repeat`, `every` | Submit a stream: `repeat` copies, `every` minutes apart (at most 700 jobs in total) |
| `abandon_after` | The owner walks away this many minutes after submitting |

The generated harness runs the same simulation as the hidden tests, and also records events and
statistics. The trace contains:

- **jobs**: for every job, its submitted, started and finished times, its wait, and its status
  (`finished`, `rejected`, `abandoned`, `running` or `never_started`);
- **events**: `start`, `finish`, `freed`, `abandoned`, `rejected`, `refused_too_late`,
  `invalid_pick` and `invalid_index`. Repeated refusals are logged once per job per day. Probe
  runs keep up to 1500 events;
- **stats**: busy minutes, open minutes, idle minutes while something was waiting, too-late
  attempts, invalid picks, days simulated, and the longest queue.

The web UI draws a day-by-day timeline. Each day is a row, each run is a coloured bar, and amber
triangles mark refusals. It also shows a table summarizing each entry of the experiment.

### Pool experiments (`pool`)

```json
{"ops": [
  {"op": "checkout", "holder": 1},
  {"op": "release",  "holder": 1},
  {"op": "release",  "holder": 1},
  {"op": "cycle",    "holder": 100, "repeat": 40, "step": 7}
]}
```

`checkout` and `release` call the system once for a holder id (0–10,000,000). `cycle` does both.
`repeat` + `step` expand one entry into many holders (holder, holder+step, …). There are at most
3000 operations. After every operation the harness prints what the system returned, how many slots
are marked in use, and the **receipts** count (checkouts granted minus releases accepted). It ends
with the full slot table. The UI plots *in use* against *receipts*, highlights rows where they
differ, and draws the final pool as a grid.

### Safety

Scenarios never become C *text* written by the contestant. Every value must be a whole number in
range, otherwise `ProbeError` is raised. The harness is assembled from those integers only, so a
scenario like `"minutes": "5); system(\"x\"); ("` is refused before anything is compiled. This is
tested in `test_probe_rejects_bad_scenarios`.

## Witnesses

<figure class="diagram">
<svg viewBox="0 0 760 250" xmlns="http://www.w3.org/2000/svg" font-family="Inter, sans-serif">
  <defs><marker id="a4" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#5b6475"/></marker></defs>
  <g font-size="11">
  <rect x="10" y="30" width="140" height="66" rx="8" fill="#f3f4f6" stroke="#8a93a3"/>
  <text x="80" y="54" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">World params</text>
  <text x="80" y="72" text-anchor="middle" fill="#4a5466">names, constants,</text>
  <text x="80" y="86" text-anchor="middle" fill="#4a5466">seed</text>
  <rect x="185" y="30" width="150" height="66" rx="8" fill="#e8f4f8" stroke="#1f7a99"/>
  <text x="260" y="54" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">cast()</text>
  <text x="260" y="72" text-anchor="middle" fill="#4a5466">witnesses + a busy</text>
  <text x="260" y="86" text-anchor="middle" fill="#4a5466">period of real usage</text>
  <rect x="370" y="30" width="150" height="66" rx="8" fill="#fdf3e3" stroke="#c27a12"/>
  <text x="445" y="54" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">Run it in C</text>
  <text x="445" y="72" text-anchor="middle" fill="#4a5466">probe harness +</text>
  <text x="445" y="86" text-anchor="middle" fill="#4a5466">starter code</text>
  <rect x="555" y="30" width="190" height="66" rx="8" fill="#ffffff" stroke="#1d2433"/>
  <text x="650" y="54" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">One trace (cached)</text>
  <text x="650" y="72" text-anchor="middle" fill="#4a5466">every job / operation,</text>
  <text x="650" y="86" text-anchor="middle" fill="#4a5466">tagged with its owner</text>
  <rect x="185" y="160" width="150" height="66" rx="8" fill="#ffffff" stroke="#1d2433"/>
  <text x="260" y="184" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">Question</text>
  <text x="260" y="202" text-anchor="middle" fill="#4a5466">chip topic, or free text</text>
  <text x="260" y="216" text-anchor="middle" fill="#4a5466">routed by keywords</text>
  <rect x="370" y="160" width="150" height="66" rx="8" fill="#e8f4f8" stroke="#1f7a99"/>
  <text x="445" y="184" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">answer(topic)</text>
  <text x="445" y="202" text-anchor="middle" fill="#4a5466">only this witness's</text>
  <text x="445" y="216" text-anchor="middle" fill="#4a5466">slice of the trace</text>
  <rect x="555" y="160" width="190" height="66" rx="8" fill="#eaf6f1" stroke="#2f8f72"/>
  <text x="650" y="184" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">Text + the record</text>
  <text x="650" y="202" text-anchor="middle" fill="#4a5466">optional replay under</text>
  <text x="650" y="216" text-anchor="middle" fill="#4a5466">the contestant's code</text>
  <rect x="10" y="160" width="140" height="66" rx="8" fill="#fbecea" stroke="#d4725e"/>
  <text x="80" y="184" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">"How do I fix it?"</text>
  <text x="80" y="202" text-anchor="middle" fill="#4a5466">deflected: "I'm not</text>
  <text x="80" y="216" text-anchor="middle" fill="#4a5466">the one who wrote it"</text>
  </g>
  <g stroke="#5b6475" stroke-width="1.2" fill="none" marker-end="url(#a4)">
    <line x1="150" y1="63" x2="183" y2="63"/><line x1="335" y1="63" x2="368" y2="63"/>
    <line x1="520" y1="63" x2="553" y2="63"/><line x1="335" y1="193" x2="368" y2="193"/>
    <line x1="520" y1="193" x2="553" y2="193"/><path d="M650,96 C650,130 470,130 455,158"/>
    <line x1="185" y1="193" x2="152" y2="193" stroke-dasharray="4 3"/>
  </g>
</svg>
<figcaption>Figure 4.2. How a witness answer is produced. Nothing in the answer is written by hand; it is read from one execution.</figcaption>
</figure>

### Why witnesses exist

The old design had LLM characters with written backstories, and Discord sessions became
arguments: the contestant trying to get a bot to concede a stored "fact". Witnesses remove the
thing to argue about. They hold no facts, only a vantage point on one real run. Answers are
deterministic, bounded, and backed by an evidence table ("show the record behind this").

### The busy period for the scheduler

`StarvationWitnessKit.cast(world)` builds a 7-day load from the world's own constants, using a
generator seeded with the world:

| Owner | Load |
|---|---|
| `regular` | Short jobs every (short − 1) minutes during the first 50–65% of each day, for 6 days (at most 90 per day) |
| `big` | One long job submitted 15–60 minutes into day 1 |
| `midday` | A medium job (10–18% of a day) around midday on days 1, 3 and 5 |
| `late` | A job of 20–30% of a day submitted 8–15% of a day before closing, on days 1 and 4 |
| `operator` | No jobs; reads the machine's log |

Witness names are drawn from a pool of 24 first names, for example Priya, Arjun, Meera, Kabir and
Ananya.

| Witness | Can see | Questions (topics) |
|---|---|---|
| regular, big, midday, late | Their own jobs only | *story* (what happened), *worst* (worst wait), *timing* (when in the day jobs started), *machine* (what the machine ran while they waited, and whose jobs) |
| operator | The machine log | *utilization*, *refusals* (too-late or invalid picks), *queue* (longest queue, who is still waiting), *closing* (what happens near closing time) |

Times are shown as clock times. Each day opens at 08:00, so minute 0 is day 1, 08:00.

### The busy day for the pool

`PoolWitnessKit.cast(world)` builds one day of operations:

| Owner | Operations |
|---|---|
| background | Pool size − 4 long-term holders check out in the morning |
| `regular` | 6–9 borrow-and-return cycles |
| `staff` | Processes returns for about half the background holders, scanning every other one twice by accident, plus one scan of an id that never borrowed |
| `double` | Two people whose app froze, so each borrow request went through twice; they return once |
| `newcomer` | Four people trying to borrow at the end of the day |

The actor timelines are merged randomly, but each actor's own order is preserved. The pool
witnesses also reconstruct a **physical reality** from what people *did*, not what the system
recorded. A person physically gets an item when their checkout is granted and they have nothing in
hand. They physically hand one back whenever they go to return. This gives three numbers that
should always agree:

1. **receipts**: checkouts granted minus returns accepted;
2. **in use**: what the pool memory says;
3. **physically out**: what people actually have.

| Witness | Can see | Topics |
|---|---|---|
| regular | What the system told them | *story*, *denied* (told nothing available, while N were free), *returns* (were returns accepted) |
| staff | Each scan's response | *story*, *double* (what a second scan does), *unknown* (scanning someone who never borrowed) |
| double | What they received and what the app showed | *story* (duplicate requests), *returns* |
| newcomer | The shelf | *story*, *shelf* (how many were physically free) |
| auditor | Receipts, system and physical counts | *reconcile* (do the three agree), *first* (first transaction where they disagree), *stock* (end-of-day slot table: ghost slots, holders on two slots) |

### Routing and deflection

Clicking a question chip sends its `topic` directly. Free text is matched against each topic's
keyword list, and the topic with the most hits wins. Text matching the deflection pattern is
politely refused. The pattern covers words like *fix*, *solution*, *code*, *bug*, *algorithm*,
*implement*, *should I/you/we*, *how do/to/would*, *what's wrong*, *root cause*, *why does*,
*why is* and *patch*. Anything unmatched gets "I'm not sure what you're asking", plus the list of
questions the witness can answer.

### Replay and caching

When `c_source` is supplied and differs from the starter, the same busy period is run a second
time with the contestant's code. The same topic is then answered again. The UI shows both answers
side by side ("the original system" / "under your code"). A crash or compile error in the replay
is reported as text, never as a server error.

Traces are cached in memory (up to 96 entries, least recently used evicted), keyed by world id and
a SHA-256 hash of the code. Witness runs allow up to 8000 events. Caching a *result of running
code* is not a fact store: the result can always be recomputed.

**Trade-offs become visible.** In a real test world, a fair fix cut the long-job wait from about
6 days to 10 minutes. The same fix raised the short-job user's typical wait from 24 minutes to
over 5 hours, and that witness says so. Both fixes are correct, and they make different people
happy.

## Adaptive difficulty (ratings)

`backend/app/core/profiles.py` implements an Elo-style rating.

| Rule | Value |
|---|---|
| Starting rating | 1100 |
| A world's rating | `800 + 1200 × difficulty` (difficulty 0.5 → 1400) |
| Expected score | `1 / (1 + 10^((world − you) / 400))` |
| Accepted submission | rating += K × (1 − expected), with K = 48 for your first 5 worlds, then 32 |
| Rejected submission | rating += K × (0 − expected), with K = 8 for your first 5 worlds, then 5; only your first 5 rejections on a world count |
| Already solved this world | No change (no farming) |
| Recommended next difficulty | `(rating − 800) / 1200 + 0.06`, clamped to 0.10–0.95 |

A rejection can never *raise* a rating. Otherwise resubmitting the starter, which already passes
some tests, would earn points. Levels: under 1000 *Novice*, under 1200 *Apprentice*, under 1400
*Practitioner*, under 1600 *Engineer*, under 1800 *Expert*, then *Master*.

The profile also counts **activity**: experiments run (`probe`), and witness questions
(`witness`) and replays (`replay`). These are shown to the person and to cohort hosts.

**Example.** A new user (1100) solves a 0.45 world (rating 1340). Their expected score is about
0.20, so they gain 48 × 0.80 ≈ +38, reaching 1138. Their next calibrated world is 0.34.

## Cohorts

`backend/app/core/cohorts.py` (`CohortStore`).

1. **Create.** The host gives a name, optionally a defect class, and a difficulty (default 0.45).
   VANTA draws a cohort seed and picks the archetype (if not given). It pins one variant and one
   setting, and allocates a unique **6-character join code**. The code alphabet leaves out
   look-alike characters (no I, L, O, 0 or 1).
2. **Join.** A member's seed is the first 4 bytes of `SHA-256("<cohort seed>:<user id>:<attempt>")`.
   A world is evolved with the cohort's pins and difficulty. If its identifier set (struct name +
   function names) matches another member's, it is deleted and the next attempt is tried, up to 6
   times. So no two members share names, and copied code won't compile.
3. **Rejoin.** A member who joins again gets their same world back. If their world was deleted,
   they get a new one.
4. **Close.** No new members, but existing members can continue.
5. **Delete.** Removes the cohort, its members, its submissions, and every member's world.
6. **Host view.** For each member: identifiers, number of submissions, best checks passed,
   solved or not, and experiment and witness counts. For the whole cohort: the setting, the
   planted variant (hidden behind a "reveal" button in the UI), and the originality report.

Only the host (matching `host_id`) or an admin can close, delete, or see the host view.

## Originality analysis

<figure class="diagram">
<svg viewBox="0 0 760 120" xmlns="http://www.w3.org/2000/svg" font-family="Inter, sans-serif">
  <defs><marker id="a5" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#5b6475"/></marker></defs>
  <g font-size="10.5">
  <rect x="5" y="25" width="110" height="64" rx="7" fill="#f3f4f6" stroke="#8a93a3"/>
  <text x="60" y="50" text-anchor="middle" font-weight="600" font-size="11.5" fill="#1d2433">Submission</text>
  <text x="60" y="67" text-anchor="middle" fill="#4a5466">in its own world</text>
  <rect x="130" y="25" width="135" height="64" rx="7" fill="#e8f4f8" stroke="#1f7a99"/>
  <text x="197" y="47" text-anchor="middle" font-weight="600" font-size="11.5" fill="#1d2433">Normalize</text>
  <text x="197" y="63" text-anchor="middle" fill="#4a5466">names → STRUCT/FN/FN2</text>
  <text x="197" y="77" text-anchor="middle" fill="#4a5466">vars → V0, V1… nums → NUM</text>
  <rect x="280" y="25" width="110" height="64" rx="7" fill="#e8f4f8" stroke="#1f7a99"/>
  <text x="335" y="50" text-anchor="middle" font-weight="600" font-size="11.5" fill="#1d2433">Fingerprint</text>
  <text x="335" y="67" text-anchor="middle" fill="#4a5466">hashed 6-token runs</text>
  <rect x="405" y="25" width="120" height="64" rx="7" fill="#fdf3e3" stroke="#c27a12"/>
  <text x="465" y="50" text-anchor="middle" font-weight="600" font-size="11.5" fill="#1d2433">− own starter</text>
  <text x="465" y="67" text-anchor="middle" fill="#4a5466">keep what they wrote</text>
  <rect x="540" y="25" width="100" height="64" rx="7" fill="#ffffff" stroke="#1d2433"/>
  <text x="590" y="50" text-anchor="middle" font-weight="600" font-size="11.5" fill="#1d2433">Compare</text>
  <text x="590" y="67" text-anchor="middle" fill="#4a5466">Jaccard pairs</text>
  <rect x="655" y="25" width="100" height="64" rx="7" fill="#eaf6f1" stroke="#2f8f72"/>
  <text x="705" y="50" text-anchor="middle" font-weight="600" font-size="11.5" fill="#1d2433">Group</text>
  <text x="705" y="67" text-anchor="middle" fill="#4a5466">approaches ≥ 0.55</text>
  </g>
  <g stroke="#5b6475" stroke-width="1.2" marker-end="url(#a5)">
    <line x1="115" y1="57" x2="128" y2="57"/><line x1="265" y1="57" x2="278" y2="57"/>
    <line x1="390" y1="57" x2="403" y2="57"/><line x1="525" y1="57" x2="538" y2="57"/>
    <line x1="640" y1="57" x2="653" y2="57"/>
  </g>
</svg>
<figcaption>Figure 4.3. The originality pipeline in <code>backend/app/core/originality.py</code>.</figcaption>
</figure>

The problem is that every cohort member's code uses different names and different numbers, but
everyone also starts from the same shaped starter. Comparing raw text would call everyone
different. Comparing naively would call everyone the same. The steps, in the spirit of the
well-known MOSS plagiarism detector, are:

1. **Strip** comments, string and character literals, and `#` lines.
2. **Tokenize** the C into identifiers, numbers and operators.
3. **Normalize:**
   - the world's own struct name becomes `STRUCT`, the main function `FN`, and the checkout
     function `FN2`;
   - C keywords and the struct's field names are kept;
   - every other identifier becomes `V0`, `V1`, … in order of first appearance, so renaming
     variables changes nothing;
   - numbers other than 0 and 1 become `NUM`.
4. **Fingerprint:** hash every run of 6 consecutive tokens (BLAKE2b, 8 bytes).
5. **Subtract the starter:** remove the fingerprints of the member's own normalized starter. What
   remains is what that person actually added or changed. If fewer than 3 remain, the submission
   counts as "unchanged from starter".
6. **Compare** every pair with Jaccard similarity (shared ÷ total).
7. **Group** accepted solutions by single linkage: a solution joins a group if it is at least
   0.55 similar to any member. The number of groups is the number of **distinct approaches**.
   Pairs at 0.85 or above are listed as **near-identical**, for the host to check.

The tests check this on real worlds. The same forward-scan fix written in two different worlds
with renamed variables scores above 0.85. A forward-scan fix against a backward-scan fix scores
below 0.55.

## The web workbench

| Page (route) | What it does |
|---|---|
| Landing (`/`) | Choose a defect class (or *Surprise me*) and a difficulty (*Calibrated to you*, Gentle, Standard, Hard, Brutal), then generate. Join a cohort by code, host a cohort, see cohorts you host, and see your open worlds (open or delete them) |
| World (`/worlds/:id`) | Situation, task, signature, requirements, a cohort chip if relevant, an **Investigate** panel with *Witnesses* and *Probe lab* tabs, the source editor (with *Reset to original*), *Submit fix*, the verdict, checks and rating change |
| Cohort join (`/cohorts/:code`) | Cohort name, defect class and difficulty. Enter a display name to join, or open your world if already a member |
| Host console (`/cohorts/:code/host`) | Large join code, join link and Discord command; counts (joined, submitted, solved, distinct approaches); approach groups; most similar pairs; the member table; reveal the planted defect; close or delete |

The header shows your level and rating (`ProfileBadge`). The badge refreshes when a submission
fires the `vanta:profile-changed` browser event.

The visual language is a "blueprint / forensic workbench". It uses a deep ink-blue page with a
faint grid and cool neutrals for structure. One warm amber colour is reserved for "something is
wrong, look here". Teal means accepted and rust means rejected.

## The Discord bot

All commands live under `/vanta`. Slow commands are *deferred* (Discord shows "thinking…"),
because generating a world can take longer than Discord's 3-second reply limit.

| Command | Options | Notes |
|---|---|---|
| `create` | `defect` (Surprise me / Shared Resource Fairness / Resource Pool Integrity), `difficulty` (Calibrated to me / Gentle / Standard / Hard / Brutal) | Replies with an embed and the starter as `<function>.c` |
| `list` | — | Your worlds (private reply) |
| `info` | `world_id` | Briefing, requirements, signature, starter file |
| `submit` | `world_id`, `file` (.c attachment, up to 64 KB) or `code` (```c fences accepted) | Verdict, checks, rating change |
| `delete` | `world_id` | Only your own, unless you have Manage Server |
| `delete_all` | — | All of *your* worlds |
| `admin_delete_all` | — | Manage Server only; every world |
| `witnesses` | `world_id` | Who was there and what to ask (private) |
| `ask` | `world_id`, `witness` (autocomplete), `question` | One answer plus up to 8 rows of the record |
| `probe` | `world_id`, `scenario` (JSON, omit for help), `file` | Runs on the original, or on your attached code |
| `profile` | — | Level, rating, counts, next difficulty |
| `cohort_create` | `name`, `defect`, `difficulty` | Posts the join code |
| `join` | `code` | Your world arrives privately; uses your Discord display name |
| `cohort_status` | `code` | Host only: members, progress, approaches, near-identical pairs |
| `cohort_close` / `cohort_delete` | `code` | Host only |

Discord users are identified as `discord:<numeric id>`. These commands manage whole VANTA worlds.
They never create or delete Discord channels.

## Permissions and admin

| Action | Who may do it |
|---|---|
| Read a world, probe it, ask its witnesses, submit to it | Anyone with the world id |
| Delete a world | Its creator (`requested_by` must match `created_by`) or an admin |
| Delete all of one person's worlds | That person or an admin |
| Delete every world | Admin only |
| See ground truth (`/api/admin/worlds/{id}`) | Admin only |
| Close, delete or view the host console of a cohort | Its host or an admin |

A request is **admin** when it carries the `X-Vanta-Admin` header. If the server has
`VANTA_ADMIN_TOKEN` set, the header must equal that token, compared in constant time. If no token
is configured (local demo mode), any `X-Vanta-Admin` header is accepted. The Discord bot sends
the header only for users with the *Manage Server* or *Administrator* permission.

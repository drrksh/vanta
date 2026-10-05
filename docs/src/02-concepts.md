# Core concepts {#ch-concepts}

This chapter explains every idea VANTA is built from, in the order you meet them. Each concept
has a short definition, an example, and the file where it lives.

## World

A **world** is one complete challenge. It contains:

- a **story**: a title (for example *University Library*), a briefing, and a task description;
- a **shared header**: C declarations (a `struct` and function prototypes) that both the
  contestant's code and the test program see;
- **starter source**: the current, broken C code the contestant starts from;
- **requirements**: a list of properties a correct solution must satisfy, written in plain
  English;
- a **hidden test harness**: a C program with a `main()` that calls the contestant's functions
  and checks the requirements;
- **ground truth**: which bug was planted and which constants were used. Only admins can see this.

Every world has an 8-character `world_id` (for example `66614ce6`) and the `seed` it was grown
from. In code it is the `GeneratedWorld` dataclass (`backend/app/worldgen/archetype.py`). A stored
world is a `WorldRecord` (`backend/app/core/world_manager.py`).

Here is the shared header and starter source of a real generated world. It is a library locker
pool with the *off-by-one* bug:

```c
#define MAX_POOL 128
struct Locker {
    int inUse;
    int holderId;
};
int acquireSlot(struct Locker pool[], int poolSize, int holderId);
int returnItem(struct Locker pool[], int poolSize, int holderId);

int returnItem(struct Locker pool[], int poolSize, int holderId) {
    int idx = holderId % (poolSize + 1);
    if (idx >= 0 && idx < poolSize && pool[idx].inUse) { pool[idx].inUse = 0; return 1; }
    return 0;
}
```

The contestant sees the code, the story and the requirements. They don't see the comment that
would say what is wrong (there isn't one), the hidden tests, or the name of the bug.

## Archetype

An **archetype** is a *program that writes worlds*. It is a Python class with one important
method:

```python
generate(seed, genes=None, pins=None) -> GeneratedWorld
```

An archetype decides the *shape* of a defect, for example "a scheduler that can starve long
jobs". Everything concrete is drawn from a random number generator seeded with the seed: the
struct name, function names, story setting, numbers, and which of several bug *variants* to plant.
VANTA currently has two archetypes:

| Archetype id | Title | What breaks |
|---|---|---|
| `starvation_fairness` | Shared Resource Fairness | A scheduler for one shared machine (3D printer, washing machine, GPU…) picks the wrong job next, so some jobs wait forever or the machine stalls |
| `pool_leak` | Resource Pool Integrity | A fixed pool of slots (lockers, parking spots, loaner laptops…) loses track of what is checked out, so capacity leaks away |

Files: `backend/app/worldgen/archetype.py` (the base class),
`backend/app/worldgen/archetypes/starvation.py`, `backend/app/worldgen/archetypes/pool_leak.py`.

## Seed and determinism

A **seed** is an integer. Every random choice in VANTA comes from a random number generator
created from a string such as `"pool_leak:42"`. So the same seed always gives the same world.
This matters for three reasons. A bug report can be reproduced exactly. A cohort can give every
member a different but repeatable world. And the evolution loop's results can be tested
(`test_same_seed_reproduces_same_world`).

## Bug variant

Each archetype can plant one of several **variants** of its defect. They are different
mistakes that lead to the same kind of failure:

| Archetype | Variant | The mistake in the starter code |
|---|---|---|
| `starvation_fairness` | `no_close_check` | Serves the oldest job but ignores how many minutes are left before closing, so it picks jobs the machine can't finish today and the machine stalls |
| `starvation_fairness` | `pure_shortest_first` | Always serves the shortest job, so a long job can wait forever behind a stream of short ones |
| `starvation_fairness` | `truncating_priority` | Uses an integer-division score `minutesNeeded / waited` that collapses to 0, so the ordering stops meaning anything |
| `pool_leak` | `linear_search_first_match` | `release` matches a stale `holderId` on a slot that is already free, so a second release "succeeds" |
| `pool_leak` | `off_by_one_index` | `release` computes the slot as `holderId % (poolSize + 1)` and frees the wrong slot or none |
| `pool_leak` | `no_double_checkout_guard` | `checkout` lets one holder take a second slot, which is never given back |

## Genes and difficulty

**Genes** are six numbers between 0 and 1 that control *how hard* a world is. The evolution
layer turns these dials. Archetypes read the ones they understand.

| Gene | Meaning | Used by |
|---|---|---|
| `system_size` | How much code and how many components to read | (reserved) |
| `bug_subtlety` | How hidden the defect is | starvation: picks subtler variants more often |
| `constant_magnitude` | How big the numbers are (day length, pool size) | both |
| `noise` | Irrelevant or decoy material | (reserved) |
| `edge_density` | How many edge cases the hidden tests probe | pool: number of churn cycles |
| `reasoning_depth` | How long the chain is from symptom to cause | (reserved) |

A single **target difficulty** between 0 and 1 is mapped onto all six genes
(`EvolutionEngine._target_vector`). Contestants choose *Gentle* (0.2), *Standard* (0.45), *Hard*
(0.7) or *Brutal* (0.9), or let VANTA calibrate it to their rating.

## Pins

**Pins** fix some of an archetype's choices that would otherwise be random. Currently a pin can
lock the `variant` and the story `domain` (setting). A cohort pins both, so every member faces
the same bug in the same setting. Names and numbers are still drawn from each member's own seed.

## Hidden test harness

The **harness** is a C `main()` program generated alongside the world. It calls the
contestant's function in many scenarios and prints one line per test:

```text
VANTA_TEST_RESULT|hidden_starvation_stream|1|0
VANTA_OVERALL|0
```

The line format is `name | violation bitmask | passed (1/0)`. The Python side reads these lines
(`backend/app/worldgen/evaluate.py`). Contestants see public checks by name and hidden checks
only as "hidden check 3". A name like `hidden_starvation_stream` would give the scenario away.

## Sandbox and sanitizers

The **C sandbox** (`backend/app/execution/c_sandbox.py`) compiles the harness and the
contestant's file together with `gcc` and runs the result with a time limit. Two modes exist:

- **sanitized** (for contestants): `-Wall -Wextra -fsanitize=undefined,address -O0 -g`. Undefined
  behaviour, buffer overflows and use of invalid memory become crashes instead of silent luck.
- **fast** (for the internal evolution loop): `-w -O1`, no sanitizers, for speed.

Before compiling, a **static safety check** rejects code containing dangerous calls such as
`system(`, `fork(`, `fopen(` or `#include <unistd.h>`.

## Reference fixes

**Reference fixes** are known-good solutions written into VANTA
(`backend/app/evolution/reference_fixes.py`). Each archetype has two that differ in *approach*.
For the scheduler, one uses an "aging guard" and the other "oldest first". For the pool, one scans
forward and the other backward. They are never shown to contestants. They exist only so the
evolution loop can *prove* a world is fixable in more than one way.

## Fitness and viability

When the evolution loop builds a candidate world, it measures its **fitness**:

- **broken**: the starter fails at least one of its own hidden tests;
- **fixable**: at least one reference fix passes all tests;
- **distinct fixes**: how many architecturally different reference fixes pass;
- **difficulty error**: how far the world's measured difficulty is from the target.

A world is **viable** only if it is broken, fixable, *and* at least two distinct fixes pass.
Only viable worlds are served to contestants.

## Evolution

**Evolution** here is a *genetic-algorithm-style* search over worlds. VANTA generates a small
population (6 candidates) with slightly different genes and evaluates them all in parallel. It
keeps the best half and creates new candidates by *mutating* the survivors' genes. It repeats for
a few generations (3) and stops early as soon as it finds a viable world close to the target
difficulty. This is how one generator serves both beginners and experts without any stored
problem bank.

## Probe

A **probe** (an experiment) is a small JSON description of a situation, written by the
contestant. VANTA turns it into a custom C harness, compiles it with either the *original*
system or the contestant's *edited* code, runs it, and returns a trace of what happened. Example:

```json
{"days": 3, "jobs": [{"minutes": 10, "at": 0, "repeat": 50, "every": 5},
                     {"minutes": 300, "at": 30}]}
```

## Witness

A **witness** is a person who "lived through" one real run of the broken system. They aren't a
chatbot with a backstory. When a world's witnesses are first asked something, VANTA builds a busy
period of realistic usage (a week of jobs, or a day of checkouts and returns). It runs the
*actual starter code* on that period. Each witness then reports only what they could see from
their own vantage point. One example is "I submitted one long render on day 1 at 08:30; it
started on day 7". Asking the same question twice gives the same answer. Questions about the
code are politely declined.

**Replay** means asking a witness to live through the *same* period again under the
contestant's edited code, so the contestant can see how that person's experience changes.

## Rating and calibrated difficulty

Every person has a **rating** (starting at 1100), updated like a chess rating. A world of
difficulty *d* counts as an opponent rated `800 + 1200·d`. Solving a world above your level
raises your rating a lot. A failed attempt on an easy world lowers it a little. The
**recommended difficulty** for your next world is slightly above your current level.

## Cohort

A **cohort** is a group session, such as a class or a hackathon room. A host opens it and
gets a six-letter **join code**. Everyone who joins gets the *same defect in the same setting*,
but in *their own world*, with different names and numbers. The host console shows each person's
progress and how many different approaches the accepted solutions took.

## Originality

**Originality analysis** estimates how many genuinely different approaches were accepted in a
cohort. It normalizes each solution against its own world and removes the parts copied from the
starter. Then it compares what each person actually wrote. It measures *diversity*, not
plagiarism.

## Identity

VANTA has no accounts or passwords. The web UI gives each browser a random 8-character id stored
in `localStorage` (`vanta_uid`). The Discord bot uses `discord:<user id>`. Ratings, worlds and
cohort memberships are keyed by these ids.

# Bringing in DSA and competitive programming {#s-dsa}

## Why DSA fits VANTA naturally

Competitive programming tests whether you can find an algorithm that is *correct* and *fast
enough*. VANTA's engine already proves "the starter is wrong, and a correct fix exists". It needs
only one more measurement, time or operation count, to prove "the starter is too slow, and a
fast-enough fix exists". The other properties carry over unchanged: generation from seeds,
unique worlds per person, and at least two distinct reference fixes. For DSA, distinct fixes
naturally means *different algorithms*: a heap versus a balanced tree, hashing versus sorting,
BFS versus union-find.

## Four new kinds of world

| Kind | The starter is… | The contestant must… | Competitive-programming analogue |
|---|---|---|---|
| **A. Broken data structure** | A data structure with a planted bug, used by a realistic system | Find and fix the invariant violation | Implementation problems, debugging rounds |
| **B. Too slow** | Correct, but with the wrong complexity for the hidden input sizes | Choose a better structure or algorithm | Classic ICPC/Codeforces problems with time limits |
| **C. Optimization** | A valid but poor solution to a hard (often NP-hard) problem | Improve a score; there is no single optimum | AtCoder Heuristic Contest, the former Google Hash Code |
| **D. Adversarial** | A baseline bot in a generated game | Write a strategy that beats other people's code | Battlecode, CodinGame bot arenas |

Kinds A and B fit the current engine almost directly. Kind C needs score-based grading. Kind D
needs a game engine and a match runner (Chapter 5).

## Kind A: broken data structures

Each one is a realistic system with a data structure at its core and a planted invariant
violation. Some examples (Appendix A has the full catalogue):

| System | Structure | Planted variants | Distinct correct fixes |
|---|---|---|---|
| Hospital triage queue | Binary heap | sift-down compares with the wrong child; heap size not decremented; parent index off by one | array heap; pairing via sorted insertion (if the size allows); bucket queue for small priority ranges |
| Username registry | Open-addressing hash table | deletion breaks the probe chain (no tombstones); load factor never triggers a resize; hash uses a signed `%` | tombstones; backward-shift deletion; separate chaining |
| Course prerequisite checker | Graph traversal | BFS marks visited on pop, not push; a cycle is reported only from node 0 | Kahn's algorithm; DFS with three colours |
| Network outage regions | Union-find | union by the wrong root; `find` without returning the compressed root | union by rank; union by size; path halving |
| Seat finder | Binary search | `lo <= hi` with `mid = (lo + hi)/2` overflow; returns any match instead of the first | lower-bound style; half-open interval style |

## Kind B: "it's correct but too slow"

This is the new idea that brings competitive programming directly into VANTA.

**How it works.** The starter passes all *small* hidden tests and gives correct answers. Hidden
*large* tests exceed the time limit. For example, a log analyser that finds duplicate session ids
with nested loops (O(n²)). It is correct on 1,000 records and hopeless on 2,000,000.

**How the engine proves it.**

1. Evolution chooses the input size *N* from the `constant_magnitude` gene, so difficulty also
   means "how much better than the naive complexity you need to be".
2. The harness runs each reference fix on the large tests and measures it. The **time limit**
   is set from the measurement, for example 3× the slowest reference fix, rather than guessed.
3. The world is **viable** only if the starter *times out*, and at least two different
   efficient fixes (say, hash-based and sort-based) pass with margin.

**Fair timing.** Wall-clock time varies between machines and with load. Battlecode deals with
this by counting computation: its Java engine "accurately tracks how much computation a
competitor is using". VANTA can do the same in C in either of two ways:

- **Operation counters.** The harness provides the data-access functions and counts calls. This is
  exact and fully deterministic, but it constrains how contestants write code.
- **CPU time with repetition.** Measure process CPU time over several runs, take the median, and
  use a generous multiple of the reference. This is simple and works for any code.

Start with the second, and add the first for Arena bots, where per-turn fairness matters.

**Example performance worlds.**

| System | Naive starter | Faster designs (distinct fixes) |
|---|---|---|
| Duplicate session finder | O(n²) pair check | Hash set O(n); sort then scan O(n log n) |
| Top-k trending tags | Re-sort the whole list per query | Heap of size k; counting with bucket selection |
| Range booking checker | Scan every booking per query | Sort + sweep; interval tree; difference array (bounded ranges) |
| Route planner | BFS from scratch per query on a weighted graph | Dijkstra with a binary heap; precomputation per source |
| Rolling average service | Recompute the window sum each tick | Running sum; prefix sums |
| Friend-group counter | Re-run a flood fill per new friendship | Union-find; incremental BFS with merging |

## Kind C: optimization worlds

Some real problems have no perfect answer that can be found in time: scheduling with deadlines,
packing, routing, assignment. AtCoder's Heuristic Contest (AHC) is built around these. Its
statement describes the goal as creating "a better solution to a problem for which it is
difficult to find the optimal solution". Rankings shown during the contest are provisional, and
final standings use system tests on more inputs. Google's Hash Code used the same style.

A VANTA optimization world:

- **is generated** like any other world: a facility (labs, buses, servers) with stakeholders,
  constraints and a score, for example total weighted waiting time with a fairness penalty;
- **has a baseline** starter that is valid but poor (first-come-first-served, greedy);
- **is scored relatively** on hidden instances: your score on an instance divided by the best
  submitted score, summed across instances;
- **uses the witnesses as qualitative feedback**: who is unhappy with your schedule and why.

These worlds are where "many correct solutions" stops being a property and becomes the whole
point. They are good for multi-day Marathon contests and for teams.

## Kind D: adversarial worlds (games)

Chapter 5 describes the Battlecode-style Arena in full. In DSA terms, good bots need:

- pathfinding (BFS, A*);
- priority queues for scheduling actions;
- matching and assignment;
- caching under memory limits;
- careful complexity under a per-turn compute budget.

Arena is where DSA stops being exercises and becomes strategy.

## What changes in the engine

| Change | Needed for | Effort |
|---|---|---|
| Measured time limits from reference runs; CPU-time median over repeats | Kind B | Small |
| Large-input generation inside the harness (from a seed, not stored as files) | Kind B | Small |
| Score-based grading (`VANTA_SCORE|instance|value` lines) and relative scoring | Kind C | Medium |
| Viability rules per kind ("starter times out", "baseline score < reference score by X%") | B, C | Small |
| Deterministic game engine, match runner, replay format, compute budget | Kind D | Large |
| Archetype authoring kit: template, checklist, test helpers, "viability report" | All | Medium, and the most valuable long-term |

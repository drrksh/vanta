# Appendix C: Arena game sketch, "Contention" {#s-appC}

A first Battlecode-style game for VANTA Arena, designed around the defect classes VANTA already
knows: shared-resource scheduling, pools that can leak, and fairness.

## The world

- **A generated grid city** of 40×40 to 64×64 cells. The seed decides the layout. It contains:
  - roads, plus narrow one-lane bridges that only one courier can occupy;
  - depots where requests appear;
  - customers;
  - charging docks, a shared pool with limited slots.
- **Each team** (2–4 per match) controls 4–8 couriers. A courier carries one package and has a
  battery.
- **Requests** appear over time at depots. Each has a destination, a value, and a deadline. Late
  deliveries lose value, and very late ones lose all of it.
- **Docks** recharge batteries. A courier must *claim* a dock slot and *release* it when done.
  Slots that are claimed and never released are lost for the rest of the match, like a pool
  leak.

## A turn

```c
struct View   { /* your couriers, visible cells (radius 6), visible requests, dock states, turn */ };
struct Orders { /* per courier: MOVE dir | PICKUP | DROP | CLAIM_DOCK | RELEASE_DOCK | WAIT */ };

void act(const struct View *view, struct Orders *out);   /* one call per team per turn */
```

- The game runs a fixed number of turns (for example 1,500). It is fully deterministic given the
  map seed and the bots' code.
- **Compute budget.** Each `act` call may perform a fixed number of counted operations (for
  example 200,000 per turn, with a small bank for unused budget). Exceeding it ends the call, and
  unfinished orders become WAIT. This rewards efficient algorithms, as Battlecode's
  computation tracking does.
- **Fog of war.** A team sees only what its couriers can see. Shared knowledge must be
  communicated through a small team "radio" array, which adds a data-structure design question.

## Scoring a match

```text
score = Σ delivered value  −  Σ lateness penalties  −  5 × (dock slots leaked by your team)
```

Ties are broken by the earlier time of the last delivery, then by the number of deliveries.

## The baseline bot and its planted bugs

Every team receives the same starter bot. It plays, but badly, because it contains VANTA-style
defects. Finding them is week 1's challenge:

| Planted defect | Symptom in matches | What fixing it teaches |
|---|---|---|
| BFS pathfinder marks cells visited on pop, not push | Couriers stall when the map is crowded; budget runs out | BFS correctness; complexity under budget |
| Dispatcher always takes the nearest request (pure greedy) | High-value distant requests expire; witnesses report long waits | Fairness vs. throughput; priority with aging |
| Dock claim not released when a courier's battery fills during a wait | Docks leak; the team runs out of charging | Resource pool integrity |
| Radio array index computed with the wrong modulus | Teammates overwrite each other's notes | Off-by-one and ring-buffer logic |

**Arena witnesses.** After each scrimmage, the match trace drives witness answers. Examples: a
customer ("my parcel arrived 40 turns late"), a dock operator ("slot 3 was claimed by your
courier at turn 210 and never released"), and a rival ("your couriers blocked the north bridge for
90 turns"). Investigating your own matches is part of the strategy.

## The DSA a strong bot needs

- **BFS / A\*** for routing; multi-source BFS for distance maps.
- **Priority queues** for scheduling deliveries by value, deadline and distance.
- **Assignment** (greedy with repair, or Hungarian on small sets) to match couriers to requests.
- **Caching** of distance maps under the compute budget.
- **Ring buffers and compact encodings** for the team radio.

## A suggested season calendar (4 weeks)

| Week | Event |
|---|---|
| 0 | Release: rules, starter bot (with planted bugs), the replay viewer, a practice map pool |
| 1 | Scrimmage ladder opens; end of week: **Sprint tournament** (single elimination) |
| 2 | Rule tweak announced (e.g. a new building type) to reward adaptation, as Battlecode does |
| 3 | **Qualifier tournament** (double elimination); top 8 advance |
| 4 | **Live final** with replays on a big screen; winners present their strategies; post-season practice ladder stays open |

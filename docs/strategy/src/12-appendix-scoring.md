# Appendix B: Scoring formulas {#s-appB}

## Sprint (ICPC rules)

Rank teams by the number of worlds solved (more is better), then by total penalty time (less is
better):

```text
penalty = Σ over solved worlds ( minutes_until_accepted + 20 × rejected_runs_before_acceptance )
```

Rejected runs on worlds that were never solved add nothing. Optionally, compile errors don't
count as rejected runs. Tie-break by the earlier time of the last accepted run.

**Optional VANTA variant (decaying points).** Each world has a value *V* (for example 500 for A
up to 3000 for F) that decays with time *t* (minutes) and wrong attempts *w*:

```text
score(world) = max( 0.3 × V,  V × (1 − t / (2 × contest_minutes)) − 50 × w )
```

This rewards speed on easy worlds without making late solves worthless.

## Marathon (relative scoring)

For each hidden instance *i*, compare your result *rᵢ* with the best result submitted by anyone,
*bᵢ*:

```text
maximization:  sᵢ = 10⁹ × rᵢ / bᵢ          minimization:  sᵢ = 10⁹ × bᵢ / rᵢ
total = Σ sᵢ          (an invalid output on an instance scores 0 for that instance)
```

Show provisional standings on public instances during the contest. Compute final standings on a
separate hidden set, as AtCoder Heuristic Contest does with its system tests.

## Incident Night (dynamic points)

Each world starts at *initial* points and loses value as more teams solve it, down to a floor.
With *s* = number of solves so far and *d* = the number of solves at which the floor is reached:

```text
value(s) = max( floor,  initial − (initial − floor) × (s / d)² )
first-solve bonus = 10% of initial (awarded once)
```

Example: initial 500, floor 100, *d* = 20. Worth 500 at 0 solves, 400 after 10, and 100 from 20
solves on. Every team that solved the world gets its *current* value, so the scoreboard updates as
others solve.

## Arena (ratings and matches)

- **A match** is played on a seeded map. The winner has the higher score: delivered value minus
  lateness penalties (see Appendix C). The same seed and the same bots always give the same
  result.
- **Ladder rating.** Use Elo for simplicity. With rating *R*, opponent rating *O*, *K* = 24 and
  *S* = 1 for a win, 0.5 for a draw and 0 for a loss:

```text
expected = 1 / (1 + 10^((O − R) / 400));     R ← R + K × (S − expected)
```

  TrueSkill (as used by CodinGame) handles multi-player matches and uncertainty better, and is a
  good upgrade when matches have 3–4 teams.

- **Leagues.** Boss bots gate promotion: beat the league's boss bot in at least 60% of games over
  a fixed map set. No demotion within a season.

- **Tournaments.** The Sprint tournament is single elimination, with each pairing played over 5
  seeded maps. Qualifiers and finals are double elimination, with each pairing played over 7
  maps.

## Hackathon (rubric)

| Component | Weight | Formula |
|---|---|---|
| Correctness | 50 | 50 × (hidden checks passed ÷ total checks) |
| Stakeholder satisfaction | 20 | 20 × mean over witnesses of (their satisfaction under your code), each scaled 0–1 from their trace (e.g. waits and refusals relative to the reference fixes) |
| Performance | 10 | 10 × (large hidden tests within the limit ÷ total) |
| Engineering quality | 20 | Judges' rubric: clarity of explanation (8), trade-off awareness (6), code quality (6) |

## Practice points (Learn mode)

| Event | Points |
|---|---|
| Solve a world | 100 × (1 + difficulty) |
| Hint rung 1 / 2 / 3 / 4 | −10 / −20 / −30 / −40 |
| Solve without a rejected run | +20 |
| Explanation peer-rated as clear | +20 |
| Spaced-review world solved on time | +30 |

Practice points are for motivation only. The rating (Elo-style, already built) remains the
measure of skill used for calibration and divisions.

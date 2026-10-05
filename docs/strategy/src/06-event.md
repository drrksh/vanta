# Running the first event: VANTA Sprint #1 {#s-event}

A concrete playbook for a first contest at your own university. It is designed to be run by one
or two students with a faculty sponsor and almost no budget.

## The event at a glance

| Item | Plan |
|---|---|
| Name | VANTA Sprint #1: "Fix the Campus" |
| Who | 30–80 first- and second-year students; individual entries plus an optional Div. 1 for strong students |
| When | One weekday evening or a Saturday afternoon; 2.5 hours of contest, plus a 30-minute briefing and a 30-minute debrief |
| Problems | 5 worlds (A–E): 2 debugging, 2 broken data structures, 1 too-slow. Each is pinned for everyone, with a unique world per person |
| Scoring | ICPC: worlds solved, then penalty time (+20 minutes per rejected run); scoreboard frozen for the last 30 minutes |
| AI rule | "Classic": no AI for solutions. Language help is allowed. Explained in the briefing |
| Prizes | Certificates, department or club recognition, a sponsor's goodies if available; the top 3 present their approaches |
| Afterwards | Problems reopen as practice with new seeds; results write-up shared with participants and faculty |

## Timeline

| When | Task |
|---|---|
| T − 4 weeks | Agree date and room with the faculty sponsor; announce; open registration (a cohort join code works as registration) |
| T − 3 weeks | Build the missing pieces: contest timer, scoreboard, penalties (Chapter 7, Phase 1). Containerize the sandbox |
| T − 2 weeks | Choose and test the 5 defect classes; run a mock contest with 5 friends; fix the rough edges |
| T − 1 week | Load test: simulate 80 participants submitting at once; check generation and grading times |
| T − 2 days | Generate everyone's worlds in advance (warm the cache); print the AI rule and help sheet |
| Day | Briefing (rules, the guide, a 5-minute demo) → contest → freeze → reveal → debrief of each problem |
| T + 1 week | Send results, survey and practice links; write a 2-page report with the data |

## Infrastructure for about 80 people

The current single-process server is fine for a classroom demo. For a contest:

- **Pre-generate worlds.** Joining a pinned cohort triggers evolution. Do it for every registered
  participant the day before, so nobody waits at the start.
- **Separate the workers.** Run grading and probes on a small worker pool (separate processes or
  machines) with a queue. A submission then never blocks the website.
- **Sandbox in containers.** No network, a read-only filesystem except a temporary folder, and
  memory, CPU and process limits. Do this before any public event.
- **Budget the load.** Assume 3–5 submissions and 10–20 experiments per person per hour. A
  sanitized compile-and-run takes roughly 1–2 seconds. Eighty people is therefore a few
  submissions per second at peak, which a handful of CPU cores can handle with a queue.

## Roles

| Role | Responsibility |
|---|---|
| Contest director (you) | Problem selection, rules, the final call on disputes |
| Tech lead | Servers, workers, the scoreboard, monitoring during the contest |
| Helpdesk (1–2 people) | Answer clarification questions (through a form, so answers are logged and shared with everyone) |
| Faculty sponsor | Room, legitimacy, certificates, and the bridge to the department |

## What to measure at the first event

- Participants, completion (submitted at least once), and solves per problem.
- Median time-to-solve per problem, and the rejected-run count before acceptance.
- Experiments and witness questions per solve. Do investigators do better?
- Distinct approaches per problem (from the originality analysis).
- A 5-question survey: difficulty, fairness, learning, fun, would-come-again.
- Incidents: crashes, grading delays, disputes, integrity concerns.

These numbers become the first page of your pitch to the department, to the next college, and
eventually to companies.

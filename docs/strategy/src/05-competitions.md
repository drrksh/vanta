# Competition formats {#s-compete}

VANTA can run six kinds of competition on one engine. They differ in length, team size, and what
"winning" means. Run them one at a time. Sprint first.

| Format | Inspired by | Length | Teams | Worlds | Winner decided by |
|---|---|---|---|---|---|
| **Sprint** | ICPC, Codeforces rounds | 2–3 hours | 1–3 | 5–7 worlds of kinds A, B and debugging | Worlds solved, then penalty time |
| **Marathon** | AtCoder Heuristic Contest, Hash Code | 1–10 days | 1–4 | 1 optimization world (kind C) | Relative score on hidden instances |
| **Arena** | Battlecode, CodinGame bot programming | 3–4 weeks | 1–4 | 1 generated game (kind D) | Tournament results |
| **Hackathon** | Smart India Hackathon, company hackathons | 24–48 hours | 2–5 | 1 large multi-subsystem world | Hidden tests + stakeholder score + judges |
| **Incident Night** | Jeopardy-style CTFs, such as picoCTF | 3–6 hours | 1–4 | Board of 15–30 worlds by category | Points; first-solve bonus |
| **League** | Codeforces divisions, CodinGame leagues | A semester | 1 | Weekly practice + monthly Sprints | Rating and division promotion |

## Sprint (ICPC-style): the first format to build

**Format.** Around 2.5 hours, 6 problems (A to F) of increasing difficulty, individual or teams
of up to 3. Each *problem* is a defect class pinned for everyone (like a cohort). Each
*participant* gets a unique world for it, with their own names and constants. A suggested mix:

| Slot | Kind | Example | Target difficulty |
|---|---|---|---|
| A | Debugging (warm-up) | Pool leak, off-by-one variant | 0.2 |
| B | Broken data structure | Binary search returns any match, not the first | 0.35 |
| C | Debugging | Scheduler, no-close-check variant | 0.45 |
| D | Too slow | Duplicate session finder (O(n²) → hash or sort) | 0.55 |
| E | Broken data structure | Heap sift-down picks the wrong child | 0.65 |
| F | Too slow + trade-off | Top-k trending tags under memory limits | 0.8 |

**Scoring.** Use ICPC rules, which are simple and well understood. Contestants are ranked by
problems solved, then by total time. Total time is the sum, over solved problems, of the minutes
from the start of the contest until the accepted run, plus a 20-minute penalty for every
rejected run on that problem. (This is the published ICPC regional rule; CERC 2025's rules are
cited in the sources.) Compile errors can be exempted from penalties, which helps beginners.

**Divisions.** Use VANTA ratings, like Codeforces divisions:

- **Div. 3** for ratings below 1300;
- **Div. 2** for ratings below 1600;
- **Div. 1** for everyone.

Run them on the same day, with problems shifted in difficulty.

**Scoreboard.** Show it live and freeze it for the final 30 minutes. Reveal the final standings
at the closing session, which is the most exciting moment of an ICPC contest.

**What must be built.** A contest object holding the problem list (each problem a pinned cohort),
start and end times, and penalty rules. Add a scoreboard page, a contest view for contestants
(problem tabs, timer, per-problem verdicts), and team accounts.

## Marathon (heuristic optimization)

One optimization world (Chapter 4, kind C), for example *"Exam Hall Scheduler: assign 4,000
exam sittings to rooms and slots. Minimize student clashes and walking distance; no room may be
over capacity."*

- **Provisional and final scoring**, as in AtCoder Heuristic Contest. During the contest,
  submissions are scored on a public set of instances. Final standings use a separate hidden
  set, which discourages overfitting.
- **Relative scoring.** Per instance, score = your result ÷ the best result submitted. The total
  is the sum over instances, scaled to 10⁹ points or similar.
- **A minimum interval between submissions**, for example 15–30 minutes. This keeps compute fair
  and encourages local testing. AHC enforces a 30-minute interval.
- **Witnesses as qualitative feedback**: "My exams were scheduled back to back in buildings 2 km
  apart."

A Marathon is approachable for beginners, because any valid answer scores something. Experts can
keep climbing for days.

## Arena (Battlecode-style): the flagship

Battlecode, run at MIT since 2007, gives teams game rules in early January. Teams refine an
autonomous bot all month, play scrimmages, and compete in a single-elimination Sprint tournament
and double-elimination qualifier tournaments before finals at MIT. Its organizers stress that
the game changes every year, so strategies have to change too. CodinGame's bot arenas add
*leagues* (Wood → Bronze → Silver → Gold → Legend). Each league has a boss bot you must beat to be
promoted, and players are ranked within their league with TrueSkill.

**VANTA Arena** combines these with VANTA's own strengths:

- **A new generated game every season.** The game *family* is fixed by an archetype; maps and
  parameters come from seeds. Example family: **"Contention"**. Two to four teams' bots control
  couriers on a grid city and compete for shared resources: charging docks, delivery slots and
  narrow roads. Requests arrive over time, with deadlines and priorities.
- **Bots in C** (later C++ and Python) implement one function that is called every turn. Each
  turn runs under a **compute budget**: operations or instructions are counted, as Battlecode
  does by tracking computation, so efficient algorithms matter.

```c
void act(const struct View *view, struct Orders *out);   /* called once per turn */
```

- **A baseline bot with planted bugs.** Every team starts from a provided bot that has a few
  VANTA-style defects: a pathfinder that revisits nodes, a scheduler that starves a far-away
  request, a resource counter that leaks. Week 1 of the Arena becomes a debugging challenge, and
  finding the bugs early is a real competitive advantage. This is unique to VANTA.
- **A ranked ladder.** Scrimmages run continuously. Ratings use TrueSkill or Glicko. Leagues
  have boss bots: the baseline, then an improved baseline, then last season's winner.
- **Tournaments.** A Sprint tournament after week 1 (single elimination), qualifiers after
  week 3 (double elimination), and a live final with replays on a big screen.
- **Replays and post-mortems.** Every match produces a deterministic replay (same seed, same
  bots, same result). After the season, the top teams present their strategies.

<figure class="diagram">
<svg viewBox="0 0 760 230" xmlns="http://www.w3.org/2000/svg" font-family="Inter, sans-serif">
  <defs><marker id="m1" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#5b6475"/></marker></defs>
  <g font-size="11" text-anchor="middle">
    <rect x="10" y="30" width="135" height="64" rx="8" fill="#e8f4f8" stroke="#1f7a99"/>
    <text x="77" y="54" font-weight="700" font-size="12" fill="#1d2433">Team uploads bot</text>
    <text x="77" y="71" fill="#4a5466">C source → safety check</text><text x="77" y="85" fill="#4a5466">→ compile (sandbox)</text>
    <rect x="175" y="30" width="135" height="64" rx="8" fill="#fdf3e3" stroke="#c27a12"/>
    <text x="242" y="54" font-weight="700" font-size="12" fill="#1d2433">Match scheduler</text>
    <text x="242" y="71" fill="#4a5466">pairs by rating;</text><text x="242" y="85" fill="#4a5466">picks a seeded map</text>
    <rect x="340" y="30" width="150" height="64" rx="8" fill="#1d2433"/>
    <text x="415" y="54" font-weight="700" font-size="12" fill="#ffffff">Game engine (C)</text>
    <text x="415" y="71" fill="#c9d3e3">deterministic turns,</text><text x="415" y="85" fill="#c9d3e3">compute budget per turn</text>
    <rect x="520" y="30" width="110" height="64" rx="8" fill="#eaf6f1" stroke="#2f8f72"/>
    <text x="575" y="54" font-weight="700" font-size="12" fill="#1d2433">Result</text>
    <text x="575" y="71" fill="#4a5466">winner, score,</text><text x="575" y="85" fill="#4a5466">replay file</text>
    <rect x="650" y="30" width="100" height="64" rx="8" fill="#ffffff" stroke="#1d2433"/>
    <text x="700" y="54" font-weight="700" font-size="12" fill="#1d2433">Ladder</text>
    <text x="700" y="71" fill="#4a5466">TrueSkill /</text><text x="700" y="85" fill="#4a5466">Glicko update</text>
    <rect x="175" y="140" width="135" height="64" rx="8" fill="#ffffff" stroke="#8a93a3"/>
    <text x="242" y="164" font-weight="700" font-size="12" fill="#1d2433">Tournaments</text>
    <text x="242" y="181" fill="#4a5466">sprint · qualifier ·</text><text x="242" y="195" fill="#4a5466">final (brackets)</text>
    <rect x="340" y="140" width="150" height="64" rx="8" fill="#ffffff" stroke="#8a93a3"/>
    <text x="415" y="164" font-weight="700" font-size="12" fill="#1d2433">Replay viewer (web)</text>
    <text x="415" y="181" fill="#4a5466">step through turns,</text><text x="415" y="195" fill="#4a5466">see each bot's view</text>
    <rect x="520" y="140" width="230" height="64" rx="8" fill="#ffffff" stroke="#8a93a3"/>
    <text x="635" y="164" font-weight="700" font-size="12" fill="#1d2433">Witnesses for the arena</text>
    <text x="635" y="181" fill="#4a5466">"my delivery waited 40 turns at dock 3"</text><text x="635" y="195" fill="#4a5466">from your own matches</text>
  </g>
  <g stroke="#5b6475" stroke-width="1.2" marker-end="url(#m1)" fill="none">
    <line x1="145" y1="62" x2="173" y2="62"/><line x1="310" y1="62" x2="338" y2="62"/>
    <line x1="490" y1="62" x2="518" y2="62"/><line x1="630" y1="62" x2="648" y2="62"/>
    <line x1="242" y1="138" x2="242" y2="96"/><line x1="415" y1="96" x2="415" y2="138"/>
    <path d="M575,96 C575,118 610,120 620,138"/>
  </g>
</svg>
<figcaption>Figure 5.1. Arena architecture. The game engine and match runner are the largest new pieces; the sandbox, ratings and witnesses are reused.</figcaption>
</figure>

## Hackathon (24–48 hours, teams)

Each team gets a **large generated system**: several interacting subsystems (for example a campus
facilities platform with booking, a laundry scheduler and a locker pool). It has 4–8 planted
defects of different kinds, plus 2–3 **feature requests** from stakeholders that conflict with
each other.

| Component | Weight | How it's measured |
|---|---|---|
| Correctness | 50% | Hidden checks across all subsystems (automatic) |
| Stakeholder satisfaction | 20% | Witnesses relive the busy period under the team's code; each scores their experience (automatic, from traces) |
| Performance | 10% | Large hidden inputs (automatic) |
| Engineering quality | 20% | Judges review a 3-minute demo plus the "explain your changes" write-up |

Because several correct designs exist, judges see genuinely different solutions. The automated
80% makes judging fast and fair, even with many teams.

Smart India Hackathon shows the scale of the appetite. Its 2025 edition received 68,766 team idea
submissions, and 1,360 teams with more than 8,000 students reached the grand finale. VANTA can
offer organizers something that format lacks: an objective, automatically graded core that
can't be pre-prepared.

## Incident Night (CTF-style board)

A jeopardy board with columns by category (Memory, Scheduling, Data structures, Performance,
Optimization) and rows of 100–500 points.

- **Dynamic scoring.** Each world's value drops as more teams solve it, so rare solves are
  worth more. Appendix B gives a formula.
- **First-solve bonus** ("first blood"), announced live.
- **Unique worlds per team**, so a solution posted in a group chat doesn't work for anyone else.

The CTF world shows how competition and learning reinforce each other. picoCTF (Carnegie Mellon)
has over 600,000 users. Learners asked for the challenges to stay open after the competition,
which led to the non-competitive picoGym. VANTA should plan the same: **every contest becomes a
practice set afterwards**, with new seeds.

## League (a semester at a college)

| Cadence | Activity |
|---|---|
| Weekly | Practice sets in each track (Learn mode); a 45-minute lab session |
| Monthly | A Sprint, with divisions by rating |
| Each semester | One Arena season (4 weeks) or one Marathon |
| Each year | An inter-college Hackathon or Arena final |

Ratings carry across everything. Students are promoted between divisions, like Codeforces
divisions and CodinGame leagues. Promotion is visible and earned, and demotion is gentle. One
option is to never demote within a season, as CodinGame does within leagues.

## Integrity in the age of AI

This has to be designed in from the start, not added later.

**The facts:**

- Frontier AI now performs at gold-medal level in the hardest student contests. Gemini solved
  10 of 12 ICPC World Finals 2025 problems, which would have placed it 2nd.
- Codeforces (rule revised September 2024) allows AI for translating statements and minor code
  completion. It **forbids** feeding problems to AI for solutions, and using AI to diagnose errors
  from verdicts.
- Industry write-ups report AI-assisted cheating in technical interviews and assessments rising
  sharply in 2025. The numbers vary by source and should be read with caution. Vendors respond
  with plagiarism models, browser monitoring and proctoring. HackerRank, for example, lets
  organizations either allow AI with monitoring or restrict it.

**What VANTA should do:**

1. **Publish one clear AI rule per event, in tiers.**
   - *Open League*: AI assistants allowed and logged. This reflects real work, and the scoring
     values investigation and explanation.
   - *Classic*: no AI for solutions; allowed for language help, as in Codeforces' rule.
   - *Proctored*: for assessments and finals.
2. **Lean on what generation already gives you.** No two people share code. Nothing leaks
   before the contest, because nothing exists until generation. The originality analysis groups
   suspiciously similar novel code.
3. **Score the process, not just the result**, where it matters: experiments run, hypotheses in
   the journal, the explanation write-up. Add a short **"defend your fix" interview** for finals.
4. **Use formats where AI helps least.** In Arena strategy, multi-day Marathon optimization,
   hackathon trade-offs, and live finals, sustained human judgement and iteration still decide the
   winner.
5. **Don't overclaim.** An AI *can* read a VANTA world and fix it. VANTA's integrity comes from
   rules, uniqueness and process evidence, not from being unsolvable.

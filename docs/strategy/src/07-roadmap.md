# Roadmap {#s-roadmap}

Four phases. Each has a clear goal, a short build list, and an exit test that must pass before
moving on. The timings assume one student working part-time, with help from one or two friends
in later phases.

<figure class="diagram">
<svg viewBox="0 0 760 200" xmlns="http://www.w3.org/2000/svg" font-family="Inter, sans-serif">
  <line x1="30" y1="60" x2="740" y2="60" stroke="#8a93a3" stroke-width="2"/>
  <g font-size="11" text-anchor="middle">
    <circle cx="80" cy="60" r="9" fill="#2f8f72"/><text x="80" y="35" font-weight="700" fill="#1d2433">Phase 0 · done</text>
    <text x="80" y="88" fill="#4a5466">engine, 2 archetypes,</text><text x="80" y="102" fill="#4a5466">witnesses, probes,</text><text x="80" y="116" fill="#4a5466">cohorts, Discord</text>
    <circle cx="270" cy="60" r="9" fill="#1f7a99"/><text x="270" y="35" font-weight="700" fill="#1d2433">Phase 1 · 6–8 weeks</text>
    <text x="270" y="88" fill="#4a5466">learning loop, DSA +</text><text x="270" y="102" fill="#4a5466">too-slow worlds, Sprint,</text><text x="270" y="116" fill="#4a5466">container sandbox, pilot</text>
    <circle cx="470" cy="60" r="9" fill="#c27a12"/><text x="470" y="35" font-weight="700" fill="#1d2433">Phase 2 · next semester</text>
    <text x="470" y="88" fill="#4a5466">Arena season 1, tracks,</text><text x="470" y="102" fill="#4a5466">instructor console,</text><text x="470" y="116" fill="#4a5466">inter-college Sprint</text>
    <circle cx="670" cy="60" r="9" fill="#1d2433"/><text x="670" y="35" font-weight="700" fill="#1d2433">Phase 3 · year 2</text>
    <text x="670" y="88" fill="#4a5466">Assess pilot, C++/Python,</text><text x="670" y="102" fill="#4a5466">authoring kit, partners,</text><text x="670" y="116" fill="#4a5466">sustainable model</text>
  </g>
  <rect x="30" y="140" width="700" height="44" rx="8" fill="#f3f4f6" stroke="#d4d9e1"/>
  <text x="380" y="160" text-anchor="middle" font-size="11" fill="#1d2433" font-weight="600">Running throughout: one or two new archetypes every month, each with a viability report and tests</text>
  <text x="380" y="176" text-anchor="middle" font-size="10.5" fill="#5b6475">The archetype library is the content moat. Every mode gets better with every archetype.</text>
</svg>
<figcaption>Figure 7.1. The roadmap. Each phase ends with an exit test, not a date.</figcaption>
</figure>

## Phase 1: "It teaches, and it can host a contest" (6–8 weeks)

| Build | Why |
|---|---|
| Debrief screen (bug explained, evidence trail, approach gallery) | Turns attempts into learning |
| Hint ladder, rungs 1–2 (failing requirement; which witness) | Unblocks beginners without giving answers |
| 2 broken-data-structure archetypes (binary search, binary heap) | Brings DSA in |
| 1 too-slow archetype (duplicate finder: O(n²) → hash or sort) with measured time limits | Brings competitive programming in |
| Contest mode: problem list of pinned cohorts, timer, penalties, frozen scoreboard, team entries | Enables Sprint |
| Container sandbox + worker queue | Required before any public event |
| Pilot study (Chapter 3) + Sprint #1 (Chapter 6) | Produces evidence |

**Exit test:** at least 30 students have used it. The post-test shows a solve-rate improvement.
Sprint #1 ran without grading failures. At least 70% of participants would come again.

## Phase 2: "A season people look forward to" (next semester)

| Build | Why |
|---|---|
| Arena v1: one game family ("Contention"), deterministic engine, match runner, ladder, replay viewer, tournaments | The Battlecode-style flagship |
| Tracks and mastery, spaced review | Long-term learning |
| Instructor console (skill heatmap, common mistakes, stuck students) | Makes adoption in courses easy |
| 4–6 more archetypes (hash table, union-find, BFS/topological sort, top-k, range queries) | Breadth for contests and courses |
| An inter-college Sprint with 2–3 nearby colleges | Growth beyond one campus |

**Exit test:** an Arena season completes with 15 or more teams. At least one course or lab uses
VANTA for graded work. An inter-college event is held.

## Phase 3: "Something others pay for or depend on" (year 2)

| Build | Why |
|---|---|
| Assess pilot with 1–2 companies or a placement cell: proctoring options, recruiter report, validity study | The industry entry point |
| C++ and Python worlds | Matches what placement tests and contests use |
| Archetype authoring kit + contribution process (review, viability report) | Content can scale beyond you |
| Optimization worlds + a Marathon | A broader competition calendar |
| A sustainable model: sponsorships, university licences, or grants (Chapter 8) | It keeps running after you graduate |

**Exit test:** at least one paying or sponsoring partner, or a formal departmental adoption.
Assessment results correlate with an independent measure of skill.

## Building order inside each phase

1. Build the smallest version that can be used in a real session.
2. Use it with real students within two weeks.
3. Measure, fix the worst problem, and repeat.

Polish comes after evidence, not before.

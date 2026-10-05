# Clarifying the scope {#s-scope}

## Why the scope feels unclear

Over its development, VANTA has been described as several things: a hackathon platform, a
debugging trainer, a Discord game, an assessment tool, an evolutionary AI system, and now a
Battlecode-like competition. Each description is true. They feel like different projects because
they describe *what people do with VANTA*, not *what VANTA is*.

The fix is to separate four layers, so each idea has an obvious place:

<figure class="diagram">
<svg viewBox="0 0 760 420" xmlns="http://www.w3.org/2000/svg" font-family="Inter, sans-serif">
  <rect x="20" y="20" width="720" height="70" rx="10" fill="#f3f4f6" stroke="#8a93a3"/>
  <text x="40" y="44" font-size="11" font-weight="700" fill="#5b6475" letter-spacing="1.5">4 · AUDIENCES</text>
  <g font-size="12" fill="#1d2433" font-weight="600" text-anchor="middle">
    <rect x="60" y="54" width="140" height="26" rx="13" fill="#ffffff" stroke="#8a93a3"/><text x="130" y="72">Students</text>
    <rect x="230" y="54" width="140" height="26" rx="13" fill="#ffffff" stroke="#8a93a3"/><text x="300" y="72">Instructors</text>
    <rect x="400" y="54" width="140" height="26" rx="13" fill="#ffffff" stroke="#8a93a3"/><text x="470" y="72">Clubs &amp; organizers</text>
    <rect x="570" y="54" width="150" height="26" rx="13" fill="#ffffff" stroke="#8a93a3"/><text x="645" y="72">Companies</text>
  </g>
  <rect x="20" y="105" width="720" height="95" rx="10" fill="#e8f4f8" stroke="#1f7a99"/>
  <text x="40" y="129" font-size="11" font-weight="700" fill="#1f7a99" letter-spacing="1.5">3 · MODES (products)</text>
  <g font-size="11.5" fill="#1d2433" text-anchor="middle">
    <rect x="40" y="140" width="210" height="48" rx="8" fill="#ffffff" stroke="#1f7a99"/>
    <text x="145" y="160" font-weight="700" font-size="12.5">LEARN</text><text x="145" y="177" fill="#4a5466">tracks · hints · debriefs · review</text>
    <rect x="275" y="140" width="210" height="48" rx="8" fill="#ffffff" stroke="#c27a12"/>
    <text x="380" y="160" font-weight="700" font-size="12.5">COMPETE</text><text x="380" y="177" fill="#4a5466">sprint · arena · marathon · hackathon</text>
    <rect x="510" y="140" width="210" height="48" rx="8" fill="#ffffff" stroke="#2f8f72"/>
    <text x="615" y="160" font-weight="700" font-size="12.5">ASSESS</text><text x="615" y="177" fill="#4a5466">screening · placements · certification</text>
  </g>
  <rect x="20" y="215" width="720" height="85" rx="10" fill="#fdf3e3" stroke="#c27a12"/>
  <text x="40" y="239" font-size="11" font-weight="700" fill="#a0640d" letter-spacing="1.5">2 · CONTENT (the archetype library)</text>
  <g font-size="11" fill="#1d2433" text-anchor="middle">
    <rect x="40" y="250" width="160" height="38" rx="7" fill="#ffffff" stroke="#c27a12"/><text x="120" y="273">debugging &amp; correctness</text>
    <rect x="215" y="250" width="160" height="38" rx="7" fill="#ffffff" stroke="#c27a12"/><text x="295" y="273">broken data structures</text>
    <rect x="390" y="250" width="160" height="38" rx="7" fill="#ffffff" stroke="#c27a12"/><text x="470" y="273">performance (too slow)</text>
    <rect x="565" y="250" width="155" height="38" rx="7" fill="#ffffff" stroke="#c27a12"/><text x="642" y="273">optimization &amp; games</text>
  </g>
  <rect x="20" y="315" width="720" height="90" rx="10" fill="#1d2433"/>
  <text x="40" y="339" font-size="11" font-weight="700" fill="#7fd1e8" letter-spacing="1.5">1 · ENGINE (what exists today)</text>
  <g font-size="11" fill="#dde6f2" text-anchor="middle">
    <text x="130" y="368">generate from a seed</text><text x="130" y="385" fill="#93a3bd">archetypes, pins, genes</text>
    <text x="310" y="368">prove by execution</text><text x="310" y="385" fill="#93a3bd">broken · fixable · ≥2 fixes</text>
    <text x="480" y="368">investigate</text><text x="480" y="385" fill="#93a3bd">witnesses · probe lab</text>
    <text x="640" y="368">grade &amp; adapt</text><text x="640" y="385" fill="#93a3bd">sandbox · rating · cohorts</text>
  </g>
</svg>
<figcaption>Figure 2.1. The scope map. Layer 1 is built. Layer 2 is the main growth area. Layer 3 is where most of your ideas belong. Layer 4 is who pays attention, and later who pays.</figcaption>
</figure>

- **Engine** (built). Generates a world from a seed, proves it by compiling and running it, lets
  people investigate it, and grades and adapts. Every mode reuses it unchanged.
- **Content** (the main growth area). The *archetype library*. Each new archetype adds a whole
  family of problems to every mode at once. This is VANTA's equivalent of a problem bank, except
  that each entry is a generator rather than a fixed question.
- **Modes** (where your ideas go). Learn, Compete and Assess are three ways of packaging worlds:
  different rules, timing, scoring and screens, on the same engine.
- **Audiences.** Who uses each mode. Students and clubs come first because they are reachable
  and generate data. Instructors come next because they bring whole classes. Companies come last
  because they need evidence before they pay.

## What VANTA is today (honest inventory)

| Area | Built and tested | Not built yet |
|---|---|---|
| Engine | Generation from seeds; evolution proving viability; C sandbox with sanitizers; grading; Elo-style rating; cohorts with unique identifiers; originality analysis | Container-grade sandbox; compute budgets; non-C languages |
| Content | 2 archetypes (scheduler fairness, resource pool), 3 bug variants each | DSA archetypes, performance archetypes, optimization and game archetypes |
| Learn | Witnesses, probe lab, replay, calibrated difficulty, in-app guide | Debriefs, hints, tracks, spaced review, instructor console |
| Compete | Cohorts (same defect, unique worlds) and a host console | Timed contests, scoreboard, penalties, divisions, arena, team play |
| Assess | Contestant-safe API, hidden checks, admin ground truth | Proctoring options, reports for recruiters, validity studies |
| Interfaces | Web workbench, Discord bot (16 commands) | Replay viewer for games, mobile layout polish |

## The one thing VANTA has that others don't

Most platforms share the same basic design: a *bank of hand-written problems* plus a grader.
VANTA's design is different in five ways that matter:

1. **Generated, not stored.** There is no answer key to leak, sell or memorize. Two people can
   face the same problem without being able to share code.
2. **Proven before served.** Every world is compiled and run to show it is broken, fixable, and
   fixable in at least two different ways.
3. **Many right answers.** This makes VANTA suitable for design and trade-off thinking, not
   just "find the one trick".
4. **Investigation, not interrogation.** Evidence comes from running the system (witnesses and
   experiments), so learners practise the real debugging loop: hypothesis → experiment →
   conclusion.
5. **Adaptive by construction.** The same generator serves a first-year and a final-year student,
   because difficulty is a dial on the generator.

The positioning that follows from this:

> *LeetCode and Codeforces train you to write an algorithm from a blank page. VANTA trains you to
> take a real, broken system and make it correct, fast and fair. That is most of what software
> engineering jobs actually are.*

## In scope and out of scope

Saying "no" is how a student project stays finishable.

| In scope (do it) | Out of scope for now (don't) |
|---|---|
| C first, then C++ and Python once the archetype kit is stable | A general online IDE or a new programming language |
| Debugging, DSA correctness, performance and optimization worlds | Hand-written problem banks (this would throw away the advantage) |
| One contest format at a time, run well | Building all six formats before running one |
| Measuring learning with fresh seeds | Claiming learning gains without data |
| Universities, clubs and competitions first | Enterprise hiring sales before you have validity evidence |
| AI policy as a rule set (allowed or not allowed, logged) | Promising that AI can never solve VANTA worlds (it can) |
| An archetype authoring kit, so others can add content | You personally writing every archetype forever |

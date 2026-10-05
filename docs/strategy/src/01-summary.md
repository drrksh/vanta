# The answer on one page {#s-summary}

## The scope, in one sentence

> **VANTA is an engine that generates realistic, broken-but-fixable software systems on demand and
> proves them by running them. Everything else is a *mode* built on that engine:** practice,
> courses, timed contests, Battlecode-style arenas, hackathons and hiring assessments.

This is why the scope has felt unclear. Every new idea seemed to be a different project. They
are really the same engine with a different wrapper. Once that is clear, the scope becomes three
products that share one core:

| Product | For whom | What it is | Why VANTA wins here |
|---|---|---|---|
| **VANTA Learn** | Students, instructors | Tracks of generated worlds, with hints, debriefs and spaced review, tied to course topics (C, debugging, DSA, performance) | Every student gets a unique world for the same learning goal, so there is no answer key to copy |
| **VANTA Compete** | Clubs, colleges, hackathon organizers | Six contest formats, from a 2-hour ICPC-style Sprint to a month-long Battlecode-style Arena | Problems are generated per event and per person, proven solvable, and admit several correct designs |
| **VANTA Assess** | Companies, placement cells | Realistic "fix this system" assessments with process evidence (experiments run, witnesses asked) | Leak-resistant by construction, and closer to real engineering work than puzzle questions |

## What to do, in order

1. **Make it teach.** Add a *debrief* after every solve or give-up: what was wrong, the evidence
   that pointed to it, and the other correct approaches. Add a *hint ladder* and *tracks*. Without
   these, VANTA tests skills but doesn't build them (Chapter 3).
2. **Add DSA and performance worlds.** Add new archetypes where the bug is a broken data
   structure, or where the code is correct but too slow for the hidden large inputs. The
   evolution loop already proves "broken but fixable"; it extends naturally to "too slow but
   speedable" (Chapter 4).
3. **Run one contest format well before building six.** Start with **VANTA Sprint**: a 2–3 hour,
   ICPC-style contest of 5–6 generated worlds, with a scoreboard (Chapter 5). Then build the
   Battlecode-style **Arena** as the flagship for the next semester.
4. **Pilot at your own university and measure.** Run a pre-test and post-test with fresh seeds,
   collect solve data and surveys, and write it up. This data, more than features, is what will
   convince a professor, a department, or a company (Chapters 6–7).
5. **Then go to industry with evidence.** Start with universities and competitions, which are
   cheap to reach and produce data. Approach assessments once you can show validity and integrity
   (Chapter 8).

## Why this is worth doing now

- **The usual problem banks are breaking.** Assessment vendors now run automated leak detection
  and swap out questions found online. HackerRank, for example, scans the web for its library
  questions *daily* and replaces leaked ones automatically. Generated worlds remove that problem
  at the source.
- **AI has changed competitive programming.** Google DeepMind reports that Gemini solved 10 of 12
  problems at the 2025 ICPC World Finals, which would have placed it 2nd among university teams.
  Puzzle-style problems are increasingly solvable by AI. Work that needs investigation, judgement
  between trade-offs, and an explanation is where human skill still shows.
- **There is a gap in big public competitions.** Google closed Code Jam, Hash Code and Kick Start
  in February 2023. Together they had engaged more than 300,000 engineers a year. Battlecode
  shows the appetite for long-running strategy competitions; it has run at MIT since 2007.
- **Employability is a live problem in India.** The Mercer-Mettl India Graduate Skill Index 2025
  puts overall graduate employability at 42.6%. A tool that builds and proves practical
  engineering skill has an obvious audience.

<div class="callout good" markdown="1">
<span class="t">The honest bottom line</span>
VANTA's engine is genuinely novel, but today it is a strong prototype with two defect classes.
Its success depends on three things, in this order: a growing **library of archetypes**, a
**learning loop** that measurably improves students, and **one competition format** run so well
that people ask for the next one. Everything in this document serves those three.
</div>

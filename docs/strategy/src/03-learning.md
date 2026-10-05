# Making students actually learn {#s-learn}

Today VANTA is good at *testing* whether someone can fix a system. To *build* the skill, it needs
a learning loop around each world. This chapter covers which skills VANTA can teach, which
learning-science principles to use, and the concrete features that follow from them.

## Skills VANTA can teach

| Skill | Why it matters | How VANTA exercises it |
|---|---|---|
| **Debugging as a method** | Debugging is a core skill that is rarely taught explicitly. McCauley et al. (2008) reviewed the literature on this | Witnesses and experiments force hypothesis → test → conclusion instead of random edits |
| **Reading unfamiliar code** | Most professional work starts in someone else's code | Every world is new code with new names |
| **Designing test cases** | Edge cases are where bugs live | The probe lab is test design. Hidden checks reward thinking about empty input, exact fits and repeats |
| **C fundamentals** | Pointers, arrays, integer division, undefined behaviour | Sanitizers turn memory errors into visible failures; variants like integer-division scoring target misconceptions |
| **DSA selection** | Knowing *which* structure fits | DSA and performance worlds (Chapter 4) where the fix is a better structure |
| **Complexity analysis** | Correct but too slow is still wrong | Performance worlds with large hidden inputs and measured time limits |
| **Trade-off reasoning** | Real fixes help some users and hurt others | Witness replays show who wins and who loses under each correct design |
| **Explaining a decision** | Engineers must justify changes | "Explain your fix" write-ups, peer-reviewed in cohorts |

## Learning-science principles to build on

- **Productive failure.** Letting learners struggle with a problem *before* instruction can
  improve conceptual understanding and transfer. A meta-analysis by Sinha and Kapur (2021, *Review
  of Educational Research*) covered 53 studies and 166 comparisons, and found it works better for
  secondary and university students than for younger ones. VANTA is naturally "problem first".
  The missing piece is the *instruction after*: the debrief.
- **Deliberate practice at the edge of ability.** Practice is most effective when it is just
  beyond current skill, with immediate feedback. VANTA's calibrated difficulty already aims each
  world slightly above a person's rating.
- **Retrieval and spacing.** Coming back to a skill after a delay, without notes, strengthens it.
  VANTA can do this without repeating questions, because a new seed gives a new world for the
  same defect class.
- **Worked examples for beginners, fading as they improve.** Novices learn more from studying a
  solved example than from struggling blindly. Support should then fade as skill grows.
- **Feedback that explains, not just judges.** "Rejected: hidden check 3" tells a learner
  *that* they are wrong, not *why*. The debrief and hint ladder close that gap without giving the
  answer away up front.

## The learning loop

<figure class="diagram">
<svg viewBox="0 0 760 240" xmlns="http://www.w3.org/2000/svg" font-family="Inter, sans-serif">
  <defs><marker id="l1" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#5b6475"/></marker></defs>
  <g font-size="11" text-anchor="middle">
    <rect x="10" y="80" width="120" height="70" rx="9" fill="#e8f4f8" stroke="#1f7a99"/>
    <text x="70" y="106" font-weight="700" font-size="12" fill="#1d2433">1 · Attempt</text>
    <text x="70" y="123" fill="#4a5466">calibrated world</text><text x="70" y="137" fill="#4a5466">(productive failure)</text>
    <rect x="160" y="80" width="120" height="70" rx="9" fill="#fdf3e3" stroke="#c27a12"/>
    <text x="220" y="106" font-weight="700" font-size="12" fill="#1d2433">2 · Investigate</text>
    <text x="220" y="123" fill="#4a5466">witnesses, probes,</text><text x="220" y="137" fill="#4a5466">journal</text>
    <rect x="310" y="80" width="120" height="70" rx="9" fill="#ffffff" stroke="#8a93a3"/>
    <text x="370" y="106" font-weight="700" font-size="12" fill="#1d2433">3 · Hint ladder</text>
    <text x="370" y="123" fill="#4a5466">only if stuck;</text><text x="370" y="137" fill="#4a5466">costs points</text>
    <rect x="460" y="80" width="120" height="70" rx="9" fill="#e8f4f8" stroke="#1f7a99"/>
    <text x="520" y="106" font-weight="700" font-size="12" fill="#1d2433">4 · Submit</text>
    <text x="520" y="123" fill="#4a5466">hidden checks +</text><text x="520" y="137" fill="#4a5466">"explain your fix"</text>
    <rect x="610" y="80" width="140" height="70" rx="9" fill="#eaf6f1" stroke="#2f8f72"/>
    <text x="680" y="106" font-weight="700" font-size="12" fill="#1d2433">5 · Debrief</text>
    <text x="680" y="123" fill="#4a5466">the bug, the evidence,</text><text x="680" y="137" fill="#4a5466">other approaches</text>
  </g>
  <g stroke="#5b6475" stroke-width="1.3" marker-end="url(#l1)" fill="none">
    <line x1="130" y1="115" x2="158" y2="115"/><line x1="280" y1="115" x2="308" y2="115"/>
    <line x1="430" y1="115" x2="458" y2="115"/><line x1="580" y1="115" x2="608" y2="115"/>
    <path d="M520,80 C520,40 220,40 220,78" stroke-dasharray="4 3"/>
    <path d="M680,152 C680,215 70,215 70,152"/>
  </g>
  <text x="370" y="34" text-anchor="middle" font-size="10.5" fill="#c27a12">rejected → back to the evidence</text>
  <text x="375" y="232" text-anchor="middle" font-size="10.5" fill="#2f8f72">6 · spaced review: same defect class, new seed, after 2, 7 and 21 days</text>
</svg>
<figcaption>Figure 3.1. The learning loop. Steps 1, 2 and 4 exist today; 3, 5 and 6 are the additions that turn VANTA from a test into a teacher.</figcaption>
</figure>

## Features to add, and the principle each one serves

### The debrief (most important)

After an accepted fix, or after the learner chooses "I give up, show me", show:

1. **What was planted**, in plain words, for example "release matched a stale holder id on an
   already-free slot". The host console already has these descriptions.
2. **The evidence trail.** Which witness answer or experiment would have revealed it, with the
   record attached. This teaches *where to look* next time.
3. **The approach gallery.** The reference designs, plus other learners' accepted solutions from
   different approach groups (the originality analysis already clusters them), with a sentence on
   the trade-off each one makes.
4. **One check question** to confirm understanding, for example: "Which requirement would
   pure shortest-first violate on a saturated queue?"

*Principle:* productive failure needs instruction *after* the struggle.

### The hint ladder

Hints the learner unlocks one at a time, each costing practice points or contest score:

| Rung | Hint | How VANTA computes it |
|---|---|---|
| 1 | Which **requirement** your code still breaks | Map each hidden check to the requirement it targets (archetype metadata) |
| 2 | Which **witness** saw the symptom | Run the witnesses on the learner's code and pick one whose answer differs from a reference fix's |
| 3 | A **minimal experiment** that reproduces it | Shrink the failing hidden scenario into a probe scenario |
| 4 | The **region of code** involved | The variant's known location in the starter |

*Principle:* feedback that explains, faded support.

### Tracks and mastery

Group defect classes into **tracks** with an order, for example:

| Track | Contents | Unlock rule (example) |
|---|---|---|
| C Foundations | Off-by-one, integer division, array bounds, sanitizer errors | Start here |
| Debugging Method | Scheduler and pool worlds; witness and probe skills | 3 solves in C Foundations |
| DSA in the Wild | Broken heaps, hash tables, binary search, BFS, union-find | 2 solves at difficulty ≥ 0.4 in Debugging |
| Performance | Correct-but-slow worlds needing better complexity | 3 DSA solves |
| Systems & Trade-offs | Multi-subsystem worlds, optimization worlds | Track badges from all of the above |

Mastery means solving a defect class at or above a difficulty threshold *on more than one seed*,
not solving one world once.

*Principle:* deliberate practice; mastery before moving on.

### Spaced review

When someone fails or struggles with a defect class, bring it back later as a *new world*
(new seed) after about 2, 7 and 21 days. They can't remember the answer, because the answer is
different. They can only remember the *method*.

*Principle:* retrieval and spacing.

### The investigation journal

A side panel where the learner writes one-line hypotheses. Each experiment or witness question is
attached to the hypothesis it tests. On submit, the journal becomes part of the debrief and, in
cohorts, part of what the host sees.

*Principle:* making thinking visible, so instructors can teach the method, not just the answer.

### "Explain your fix"

After an accepted submission, ask for a 3–5 sentence explanation: what was wrong, why the change
fixes it, and what it costs. In a cohort, each learner reviews two explanations from *different*
approach groups. This turns the multi-solution property into peer learning.

### Instructor console

This extends the cohort host console:

- a skill heatmap (students × defect classes);
- the most common wrong submissions per variant, which shows the misconceptions;
- the time-to-solve distribution and hint usage;
- students who are stuck right now, for live help in a lab.

### Beginner mode

For the first two or three worlds:

- a worked example world, with a narrated walkthrough of an investigation;
- smaller code;
- witnesses whose first answers point more directly at the symptom.

This uses the `noise` and `reasoning_depth` genes, which the generator already carries but the
current archetypes don't yet read.

## Measuring whether students learn

Claims about learning need evidence. VANTA can collect it cheaply, because it can generate
equivalent but different tests on demand.

| Measure | How |
|---|---|
| **Learning gain** | Pre-test and post-test on *the same defect classes with fresh seeds*: solve rate, time, hints used |
| **Transfer** | Post-test on a defect class not practised, but needing the same skill |
| **Retention** | Re-test 3–4 weeks later with new seeds |
| **Method quality** | From the journal: hypotheses tested before the first submission; experiments per solve |
| **What helps** | A/B test: half the cohort gets debriefs or hints, half doesn't; compare post-test results |
| **Experience** | A 5-question survey after each session (difficulty, usefulness, would-recommend) |

<div class="callout" markdown="1">
<span class="t">A first study you can run this semester</span>
Recruit 20–40 first-year students. **Week 1:** a 40-minute pre-test (2 worlds). **Weeks 2–4:**
three 45-minute practice sessions with debriefs on. **Week 5:** a post-test with new seeds of the
same classes, plus one transfer world. Report the solve-rate change, the median time-to-solve,
and survey results. Even a small study like this is far more convincing to a professor than a
feature list.
</div>

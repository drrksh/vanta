# Making VANTA successful in industry {#s-industry}

## Four markets VANTA can serve

| Market | The customer's pain | What VANTA offers | Who pays |
|---|---|---|---|
| **Universities and courses** | Assignments are reused year to year; solutions circulate; plagiarism checks are after the fact; AI assistance blurs authorship | A unique world per student for the same learning goal; autograding; debriefs; an instructor console | Departments (per course or seat licence); later, institutions |
| **Competitions and communities** | Problem-setting is expensive and leaks; events are hard to grade fairly at scale | A generated, proven problem set per event; an automatic core score; formats from Sprint to Arena | Sponsors, event platforms, colleges' tech fests |
| **Hiring and placements** | Question banks leak; AI-assisted cheating; puzzle questions don't resemble the job | "Fix this real system" assessments; uniqueness per candidate; process evidence; trade-off reasoning | Companies (per candidate or per seat); placement cells |
| **Corporate training** | Onboarding to unfamiliar codebases; incident-response practice; upskilling | Incident drills on generated systems; debugging and performance tracks | Engineering teams, L&D budgets |

**Market size, with care.** Market-research estimates for assessment software vary widely
between publishers. As one data point, Verified Market Research puts *technical skills screening
software* at about US$340 million in 2024, growing to about US$581 million by 2031 (around 7% a
year). Its named players include HackerRank, Codility, HackerEarth and DevSkiller. Treat such
figures as rough orders of magnitude, not facts to build a plan on.

## Where VANTA sits

<figure class="diagram">
<svg viewBox="0 0 760 360" xmlns="http://www.w3.org/2000/svg" font-family="Inter, sans-serif">
  <defs><marker id="q1" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#5b6475"/></marker></defs>
  <rect x="110" y="20" width="620" height="290" fill="#fafbfc" stroke="#d4d9e1"/>
  <line x1="420" y1="20" x2="420" y2="310" stroke="#d4d9e1" stroke-dasharray="4 4"/>
  <line x1="110" y1="165" x2="730" y2="165" stroke="#d4d9e1" stroke-dasharray="4 4"/>
  <line x1="110" y1="330" x2="730" y2="330" stroke="#5b6475" marker-end="url(#q1)"/>
  <line x1="90" y1="310" x2="90" y2="22" stroke="#5b6475" marker-end="url(#q1)"/>
  <text x="420" y="350" text-anchor="middle" font-size="11" fill="#1d2433">Where problems come from: fixed bank → designed per season → generated per person and proven</text>
  <text x="70" y="165" text-anchor="middle" font-size="11" fill="#1d2433" transform="rotate(-90 70 165)">Task realism: puzzle → real system work</text>
  <g font-size="11.5" font-weight="600">
    <circle cx="170" cy="270" r="7" fill="#8a93a3"/><text x="182" y="274" fill="#1d2433">LeetCode / Codeforces</text>
    <circle cx="200" cy="205" r="7" fill="#8a93a3"/><text x="212" y="209" fill="#1d2433">HackerRank / CodeSignal / Codility</text>
    <circle cx="460" cy="240" r="7" fill="#8a93a3"/><text x="472" y="244" fill="#1d2433">Battlecode · CodinGame (games)</text>
    <circle cx="230" cy="120" r="7" fill="#8a93a3"/><text x="242" y="124" fill="#1d2433">picoCTF (security challenges)</text>
    <circle cx="250" cy="70" r="7" fill="#8a93a3"/><text x="262" y="74" fill="#1d2433">Real projects / take-home tasks</text>
    <circle cx="660" cy="80" r="10" fill="#1f7a99"/><text x="560" y="58" fill="#1f7a99" font-size="13" font-weight="700">VANTA</text>
  </g>
  <text x="600" y="290" font-size="10" fill="#5b6475" text-anchor="middle">generated + proven + realistic is an empty corner today</text>
</svg>
<figcaption>Figure 8.1. A qualitative positioning map (positions are judgement, not measurement). VANTA's opening is the top-right: realistic work, with problems that are generated per person and proven.</figcaption>
</figure>

## The competitive landscape

| Platform | What it does well | Where VANTA differs |
|---|---|---|
| LeetCode, Codeforces, AtCoder | Huge problem sets, strong communities, contests and ratings | Static, hand-written problems; blank-page algorithm puzzles. VANTA gives realistic broken systems, unique per person |
| HackerRank, CodeSignal, Codility, HackerEarth | Hiring assessments, proctoring, plagiarism and leak detection, ATS integrations | They fight leaks after the fact: HackerRank scans the web daily and replaces leaked questions. VANTA avoids leaks by generating every world |
| CodinGame | Bot-programming arenas with leagues, boss bots and TrueSkill ranking | Hand-designed games. VANTA Arena adds generated maps and seasons, and planted bugs in the baseline bot |
| Battlecode (MIT) | A legendary annual strategy contest with sprint, qualifier and final tournaments | One game a year, run by MIT. VANTA could offer the format to any college, any time |
| picoCTF | Competition as a learning on-ramp; 600,000+ users; a practice gym after contests | Security-focused. VANTA does the same for software engineering skills |
| Gradescope and other autograders | Course logistics and autograding, similarity checks | Grade whatever assignment you write. VANTA generates the assignment and proves it |

The honest conclusion: incumbents are strong at **distribution** (customers, integrations,
brand). VANTA is strong at **content generation and realism**. The realistic path is to win a
niche where generation matters most (courses and competitions), build evidence, and then either
grow into assessments or partner with a platform that already has distribution.

## Business models that fit

| Model | How it works | Fits phase |
|---|---|---|
| Free for students and clubs | Practice, leagues and small contests stay free | Phases 1–3 (growth and data) |
| Course licence | Per course per semester: unique assignments, instructor console, debriefs | Phases 2–3 |
| Sponsored seasons | A company sponsors an Arena season or a Sprint series for visibility with strong students | Phases 2–3 |
| Event-platform partnership | VANTA as the "generated problems" engine inside existing hackathon and contest platforms | Phase 3 |
| Per-candidate assessments | Companies pay per assessed candidate; placement cells pay per drive | Phase 3+, after validity evidence |
| Open core | The engine and archetype format are open source; hosted contests, the instructor console and assessments are paid | An option to decide in Phase 3 |

**Sponsored seasons** have a natural opening. Google's competitions engaged more than 300,000
engineers a year and helped Google hire thousands. They were closed in February 2023 as a cost
cut. Companies still want access to strong students. A low-cost, generated, fair format lowers the
cost of providing it.

## Going to market: start where you are

1. **Your university.** The pilot study and Sprint #1 (Chapters 3 and 6). A faculty sponsor and
   one course section.
2. **Student clubs and fests.** Coding clubs, ACM/IEEE chapters, tech fests: a Sprint or
   Incident Night as an event they can run themselves.
3. **Nearby colleges.** An inter-college Sprint, then an Arena season. Bengaluru has a dense
   college and tech-company ecosystem within reach.
4. **Instructors.** Offer a free semester of course use in exchange for data and a testimonial.
5. **Companies.** Once there is data, approach companies that hire from those colleges with a
   sponsored season or a placement-assessment pilot.

India context: the Mercer-Mettl India Graduate Skill Index 2025 reports 42.6% overall
employability among graduates it assessed (data from over 2,700 campuses). A tool that builds
*and* demonstrates practical skill speaks directly to that gap, for students, colleges and
employers alike.

## What makes it defensible

- **The archetype library and generator.** Each archetype is engineering work: realistic
  framing, variants, a harness that really triggers the bug, and two distinct fixes. A large,
  tested library is hard to copy quickly.
- **The proof loop.** "Served only if proven broken, fixable, and fixable in two ways" is a
  quality guarantee that static problem banks can't make.
- **Behavioural data.** How people investigate (which experiments, which witnesses, in what
  order) is unusual data. It can improve hints, difficulty calibration and, eventually,
  assessment validity.
- **Community and seasons.** Annual Arena seasons create a tradition, as Battlecode has shown
  since 2007.

## Metrics that matter

| Area | Metric | Good early target |
|---|---|---|
| Learning | Post-test solve-rate gain on fresh seeds | A clear, repeatable improvement over the pre-test |
| Engagement | Weekly active solvers; 30-day return rate | A growing base; students coming back without being required to |
| Competitions | Participants per event; completion rate; would-return % | ≥ 70% would return |
| Content | Archetypes live; viable-world rate; generation time | +1–2 archetypes a month; < 30 s generation |
| Operations | Grading p95 latency at peak; sandbox incidents | < 5 s; zero incidents |
| Assessment (later) | Correlation with an independent skill measure; fairness across groups | Evidence before selling |

## What a professor, a company, or an investor will want to see

1. A clear one-sentence scope (Chapter 1) and a working demo.
2. **Data from real students**: the pilot results, Sprint #1 numbers, survey quotes.
3. Breadth: 6–10 archetypes, covering debugging, DSA and performance.
4. Safety: a containerized sandbox, an AI policy, integrity features.
5. A partner: a course using it, a club running events, or a sponsor.
6. A plan for continuity after you graduate: a club, the department, or open source.

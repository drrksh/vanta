# Architecture {#ch-architecture}

## The big picture

VANTA has three runnable parts:

1. **The backend** (`backend/`): a Python web service built with FastAPI. It generates worlds,
   compiles and runs C, answers witness questions, keeps ratings and cohorts, and stores
   everything in one SQLite file. It listens on port **8811**.
2. **The web frontend** (`frontend/`): a React + TypeScript single-page app built with Vite. In
   development it runs on port **5173** and forwards every `/api/...` request to the backend.
3. **The Discord bot** (`discord_bot/`): a separate Python process that turns `/vanta` slash
   commands into calls to the same HTTP API.

<figure class="diagram">
<svg viewBox="0 0 760 500" xmlns="http://www.w3.org/2000/svg" font-family="Inter, sans-serif">
  <defs><marker id="a1" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#5b6475"/></marker></defs>
  <rect x="40" y="20" width="200" height="58" rx="8" fill="#e8f4f8" stroke="#1f7a99"/>
  <text x="140" y="45" text-anchor="middle" font-size="13" font-weight="600" fill="#1d2433">Web workbench</text>
  <text x="140" y="63" text-anchor="middle" font-size="11" fill="#4a5466">React + TypeScript · :5173</text>
  <rect x="280" y="20" width="200" height="58" rx="8" fill="#e8f4f8" stroke="#1f7a99"/>
  <text x="380" y="45" text-anchor="middle" font-size="13" font-weight="600" fill="#1d2433">Discord bot</text>
  <text x="380" y="63" text-anchor="middle" font-size="11" fill="#4a5466">discord.py · /vanta commands</text>
  <rect x="520" y="20" width="200" height="58" rx="8" fill="#f3f4f6" stroke="#8a93a3"/>
  <text x="620" y="45" text-anchor="middle" font-size="13" font-weight="600" fill="#1d2433">Tests / scripts</text>
  <text x="620" y="63" text-anchor="middle" font-size="11" fill="#4a5466">httpx · pytest</text>
  <line x1="140" y1="78" x2="300" y2="128" stroke="#5b6475" stroke-width="1.3" marker-end="url(#a1)"/>
  <line x1="380" y1="78" x2="380" y2="128" stroke="#5b6475" stroke-width="1.3" marker-end="url(#a1)"/>
  <line x1="620" y1="78" x2="460" y2="128" stroke="#5b6475" stroke-width="1.3" marker-end="url(#a1)"/>
  <text x="400" y="110" font-size="10.5" fill="#5b6475">HTTP JSON  /api/…</text>
  <rect x="160" y="130" width="440" height="52" rx="8" fill="#1d2433"/>
  <text x="380" y="153" text-anchor="middle" font-size="13" font-weight="600" fill="#ffffff">FastAPI routes · backend/app/api/routes.py · :8811</text>
  <text x="380" y="171" text-anchor="middle" font-size="11" fill="#c9d3e3">validation · permissions · contestant-safe responses</text>
  <g font-size="11.5">
    <rect x="20" y="222" width="135" height="64" rx="7" fill="#ffffff" stroke="#1f7a99"/>
    <text x="87" y="246" text-anchor="middle" font-weight="600" fill="#1d2433">World manager</text>
    <text x="87" y="263" text-anchor="middle" font-size="10.5" fill="#4a5466">create · get · list</text>
    <text x="87" y="277" text-anchor="middle" font-size="10.5" fill="#4a5466">delete</text>
    <rect x="167" y="222" width="135" height="64" rx="7" fill="#ffffff" stroke="#1f7a99"/>
    <text x="234" y="246" text-anchor="middle" font-weight="600" fill="#1d2433">Evolution engine</text>
    <text x="234" y="263" text-anchor="middle" font-size="10.5" fill="#4a5466">generate · test</text>
    <text x="234" y="277" text-anchor="middle" font-size="10.5" fill="#4a5466">select · mutate</text>
    <rect x="314" y="222" width="135" height="64" rx="7" fill="#ffffff" stroke="#1f7a99"/>
    <text x="381" y="246" text-anchor="middle" font-weight="600" fill="#1d2433">Investigation</text>
    <text x="381" y="263" text-anchor="middle" font-size="10.5" fill="#4a5466">probe lab</text>
    <text x="381" y="277" text-anchor="middle" font-size="10.5" fill="#4a5466">witnesses · replay</text>
    <rect x="461" y="222" width="135" height="64" rx="7" fill="#ffffff" stroke="#1f7a99"/>
    <text x="528" y="246" text-anchor="middle" font-weight="600" fill="#1d2433">Profiles</text>
    <text x="528" y="263" text-anchor="middle" font-size="10.5" fill="#4a5466">rating · activity</text>
    <text x="528" y="277" text-anchor="middle" font-size="10.5" fill="#4a5466">calibration</text>
    <rect x="608" y="222" width="135" height="64" rx="7" fill="#ffffff" stroke="#1f7a99"/>
    <text x="675" y="246" text-anchor="middle" font-weight="600" fill="#1d2433">Cohorts</text>
    <text x="675" y="263" text-anchor="middle" font-size="10.5" fill="#4a5466">join · host view</text>
    <text x="675" y="277" text-anchor="middle" font-size="10.5" fill="#4a5466">originality</text>
  </g>
  <g stroke="#5b6475" stroke-width="1.1" marker-end="url(#a1)">
    <line x1="230" y1="182" x2="95" y2="220"/><line x1="300" y1="182" x2="240" y2="220"/>
    <line x1="380" y1="182" x2="381" y2="220"/><line x1="460" y1="182" x2="525" y2="220"/>
    <line x1="530" y1="182" x2="665" y2="220"/>
  </g>
  <rect x="120" y="330" width="230" height="58" rx="8" fill="#fdf3e3" stroke="#c27a12"/>
  <text x="235" y="354" text-anchor="middle" font-size="12.5" font-weight="600" fill="#1d2433">Archetypes (worldgen)</text>
  <text x="235" y="372" text-anchor="middle" font-size="10.5" fill="#4a5466">starvation_fairness · pool_leak</text>
  <rect x="380" y="330" width="230" height="58" rx="8" fill="#fdf3e3" stroke="#c27a12"/>
  <text x="495" y="354" text-anchor="middle" font-size="12.5" font-weight="600" fill="#1d2433">C sandbox</text>
  <text x="495" y="372" text-anchor="middle" font-size="10.5" fill="#4a5466">safety check · gcc · sanitizers · timeout</text>
  <g stroke="#5b6475" stroke-width="1.1" marker-end="url(#a1)">
    <line x1="234" y1="286" x2="234" y2="328"/><line x1="250" y1="286" x2="440" y2="328"/>
    <line x1="381" y1="286" x2="470" y2="328"/><line x1="87" y1="286" x2="200" y2="328"/>
  </g>
  <rect x="200" y="430" width="360" height="52" rx="8" fill="#eaf6f1" stroke="#2f8f72"/>
  <text x="380" y="452" text-anchor="middle" font-size="12.5" font-weight="600" fill="#1d2433">SQLite · backend/vanta_worlds.db</text>
  <text x="380" y="470" text-anchor="middle" font-size="10.5" fill="#4a5466">worlds · profiles · attempts · activity · cohorts · members · submissions</text>
  <g stroke="#2f8f72" stroke-width="1.1" stroke-dasharray="4 3" fill="none">
    <path d="M40,286 C30,380 120,440 198,452"/><path d="M560,286 C650,300 650,420 562,448"/><path d="M700,286 C730,380 660,470 562,470"/>
  </g>
</svg>
<figcaption>Figure 3.1. Components and how they call each other. Solid arrows are calls; dashed lines are database access.</figcaption>
</figure>

## Technology stack

| Layer | Technology | Why |
|---|---|---|
| Web API | Python 3.13, FastAPI, Pydantic, Uvicorn | Async request handling; automatic request validation |
| C execution | `gcc` with AddressSanitizer + UndefinedBehaviorSanitizer | Real compilation and execution; memory errors become failures |
| Storage | SQLite (Python's built-in `sqlite3`) | One file, no server to install |
| Frontend | React 19, TypeScript 6, Vite 8, Tailwind CSS 4, React Router 7 | Fast development server; typed API client |
| Discord | discord.py 2.7, httpx | Slash commands; the bot is an HTTP client like the web UI |
| Testing | pytest, pytest-asyncio, httpx `ASGITransport`, Playwright (manual browser checks) | Tests run the real API in-process without a network |

## The contestant's journey

<figure class="diagram">
<svg viewBox="0 0 760 170" xmlns="http://www.w3.org/2000/svg" font-family="Inter, sans-serif">
  <defs><marker id="a2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#5b6475"/></marker></defs>
  <g font-size="11">
    <rect x="8" y="40" width="110" height="70" rx="8" fill="#e8f4f8" stroke="#1f7a99"/>
    <text x="63" y="66" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">1 · Get a world</text>
    <text x="63" y="84" text-anchor="middle" fill="#4a5466">generate, or</text>
    <text x="63" y="98" text-anchor="middle" fill="#4a5466">join a cohort</text>
    <rect x="133" y="40" width="110" height="70" rx="8" fill="#e8f4f8" stroke="#1f7a99"/>
    <text x="188" y="66" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">2 · Read</text>
    <text x="188" y="84" text-anchor="middle" fill="#4a5466">story, task,</text>
    <text x="188" y="98" text-anchor="middle" fill="#4a5466">requirements, code</text>
    <rect x="258" y="40" width="120" height="70" rx="8" fill="#fdf3e3" stroke="#c27a12"/>
    <text x="318" y="66" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">3 · Investigate</text>
    <text x="318" y="84" text-anchor="middle" fill="#4a5466">ask witnesses,</text>
    <text x="318" y="98" text-anchor="middle" fill="#4a5466">run experiments</text>
    <rect x="393" y="40" width="110" height="70" rx="8" fill="#e8f4f8" stroke="#1f7a99"/>
    <text x="448" y="66" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">4 · Fix</text>
    <text x="448" y="84" text-anchor="middle" fill="#4a5466">edit the C, re-run</text>
    <text x="448" y="98" text-anchor="middle" fill="#4a5466">experiments, replay</text>
    <rect x="518" y="40" width="110" height="70" rx="8" fill="#e8f4f8" stroke="#1f7a99"/>
    <text x="573" y="66" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">5 · Submit</text>
    <text x="573" y="84" text-anchor="middle" fill="#4a5466">hidden tests under</text>
    <text x="573" y="98" text-anchor="middle" fill="#4a5466">sanitizers</text>
    <rect x="643" y="40" width="110" height="70" rx="8" fill="#eaf6f1" stroke="#2f8f72"/>
    <text x="698" y="66" text-anchor="middle" font-weight="600" font-size="12" fill="#1d2433">6 · Rating moves</text>
    <text x="698" y="84" text-anchor="middle" fill="#4a5466">next world is</text>
    <text x="698" y="98" text-anchor="middle" fill="#4a5466">calibrated to you</text>
  </g>
  <g stroke="#5b6475" stroke-width="1.2" marker-end="url(#a2)">
    <line x1="118" y1="75" x2="131" y2="75"/><line x1="243" y1="75" x2="256" y2="75"/>
    <line x1="378" y1="75" x2="391" y2="75"/><line x1="503" y1="75" x2="516" y2="75"/>
    <line x1="628" y1="75" x2="641" y2="75"/>
  </g>
  <path d="M448,112 C448,150 318,150 318,114" fill="none" stroke="#c27a12" stroke-dasharray="4 3" marker-end="url(#a2)"/>
  <text x="383" y="160" text-anchor="middle" font-size="10.5" fill="#c27a12">loop until the evidence agrees with your fix</text>
  <path d="M698,38 C698,4 63,4 63,36" fill="none" stroke="#2f8f72" stroke-dasharray="4 3" marker-end="url(#a2)"/>
  <text x="380" y="16" text-anchor="middle" font-size="10.5" fill="#2f8f72">the next world is evolved at your new level</text>
</svg>
<figcaption>Figure 3.2. What a contestant does, and how the system adapts.</figcaption>
</figure>

## What happens on each request

### Creating a world — `POST /api/worlds`

1. `routes.create_world` reads `created_by`, `target_difficulty` (or `null`), and optionally
   `archetype_id`.
2. If `target_difficulty` is `null`, `ProfileStore.recommended(created_by)` turns the person's
   rating into a difficulty. The response then says `"calibrated": true`.
3. `WorldManager.create_world` picks a random seed and calls `registry.generate_world`.
4. `generate_world` chooses the archetype (the one requested, or one drawn from the seed). It
   then calls `EvolutionEngine.evolve` with population 6 and 3 generations.
5. The engine generates candidates and measures each one's fitness with the *fast* sandbox. That
   means compiling the starter with the harness and compiling each reference fix with the harness.
   It returns the best viable world. If none is viable, `generate_world` retries with a new seed
   (up to 3 attempts).
6. The world is serialized to JSON and stored in the `worlds` table with its fitness report.
7. The contestant-safe view of the world is returned. It contains no ground truth, genes or
   params.

### Submitting a fix — `POST /api/worlds/{id}/submit`

1. The stored world is loaded.
2. `evaluate_submission` sends the harness and the contestant's code to the *sanitized* sandbox.
3. The sandbox runs the static safety check, writes both files (each prefixed with the shared
   header) to a temporary folder, compiles, runs with a 15-second limit, and deletes the folder.
4. The `VANTA_TEST_RESULT` lines are parsed. The verdict is `accepted` only if `VANTA_OVERALL|1`
   was printed.
5. `ProfileStore.record_submission` updates the person's rating.
   `CohortStore.record_submission` stores the source if the world belongs to a cohort.
6. The response lists checks: public ones by name, hidden ones by number. It also includes the
   rating change and, for compile errors and timeouts, the compiler or runtime message.

### Running an experiment — `POST /api/worlds/{id}/probe`

1. The archetype's `ProbeKit` validates the JSON scenario. Every value must be a whole number in
   a range. Repeats are expanded.
2. The kit writes a custom C harness with the scenario baked in as constant data.
3. The sandbox compiles it with the original starter (if `c_source` is `null`) or the
   contestant's code, and runs it.
4. The harness prints `PROBE_...` lines. The kit parses them into a trace (jobs, events,
   statistics, or operations and slots).
5. The activity is logged for the person's profile and the cohort host console.

### Asking a witness — `POST /api/worlds/{id}/witnesses/{key}/ask`

1. The archetype's `WitnessKit` rebuilds the cast and the busy period deterministically from
   the world.
2. A free-text question is routed to a topic by keyword. Questions about the code or the fix get
   a polite deflection.
3. The busy period is run once with the starter code. The trace is cached per world and code
   hash. The answer for this witness and topic is computed from the trace.
4. If `c_source` is given, the same period is run again with that code and a second answer is
   returned under `replay`.

### Joining a cohort — `POST /api/cohorts/{code}/join`

1. If the person is already a member and their world still exists, they get it back.
2. Otherwise a seed is derived from the cohort seed and the person's id. A world is evolved with
   the cohort's pinned variant and setting. If its identifiers clash with another member's, VANTA
   tries again with the next seed (up to 6 times).
3. The membership is recorded, and the world is returned.

## Repository layout

```text
vanta/
├── README.md                 project overview and quick start
├── run_dev.sh                starts API (:8811) and web UI (:5173) in the background
├── .gitignore
├── backend/
│   ├── main.py               FastAPI application object
│   ├── pytest.ini            test configuration
│   ├── app/
│   │   ├── api/routes.py     every HTTP endpoint
│   │   ├── core/             world store, profiles, cohorts, originality
│   │   ├── evolution/        evolution engine, reference fixes
│   │   ├── execution/        C sandbox
│   │   ├── investigation/    probe lab, witnesses
│   │   └── worldgen/         archetype base, registry, evaluator, archetypes/
│   └── tests/                35 automated tests
├── discord_bot/              bot.py, commands.py, vanta_api.py
├── frontend/
│   ├── index.html, vite.config.ts, package.json, tsconfig*.json
│   └── src/                  App, pages/, components/, api/, lib/, types.ts, index.css
├── docs/                     this documentation and its sources
└── scenarios/                (empty, reserved)
```

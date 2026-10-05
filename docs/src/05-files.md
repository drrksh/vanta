# File-by-file reference {#ch-files}

This chapter goes through **every file in the repository**, grouped by folder. For each one you
get its size, its purpose, what it contains, and which other files depend on it. Line counts are
read from the repository when this document is built.

Files that are **generated** or **downloaded** (and not tracked by git) are covered at the end:
the database, logs, `node_modules/`, `.venv/`, `dist/` and caches.

## Repository root

### `README.md`
*{{lines:README.md}} lines · Markdown*

The front page of the project. It covers the motto, the four layers (archetypes, evolution,
investigation, adaptation), why witnesses can't be argued with, and why two people's solutions
differ. It also covers cohorts, the Discord command table, admin rights, how to run everything,
an API summary table, and a five-minute demo. Read it first. This document expands on it.

### `run_dev.sh`
*{{lines:run_dev.sh}} lines · Bash*

Starts the API (`uvicorn main:app` on 127.0.0.1:8811) and the web dev server (`npm run dev` on
127.0.0.1:5173), both in the background with `setsid nohup`. Output goes to `backend/server.log`
and `frontend/vite.log`. Requires that `backend/.venv` and `frontend/node_modules` already
exist.

### `.gitignore`
*{{lines:.gitignore}} lines*

Keeps generated and local files out of git: `__pycache__/`, `*.pyc`, `.venv/`, `node_modules/`,
`dist/`, `*.db` (the SQLite database), `.env`, `build/`, `*.o`, `*.out`, `.pytest_cache/` and
`*.log`.

## backend/ — the API service

### `backend/main.py`
*{{lines:backend/main.py}} lines · Python*

Creates the FastAPI application (`title="VANTA"`, `version="0.4.0"`). It adds CORS middleware
that allows any origin, so the web UI and tools can call it, and mounts the router from
`app/api/routes.py`. It also defines `GET /health`, which returns `{"status": "ok"}`. Uvicorn
loads `main:app`.

### `backend/pytest.ini`
*{{lines:backend/pytest.ini}} lines*

Sets `asyncio_mode = auto`, so `async def test_...` functions run without decorators.

### `backend/app/__init__.py` and every other `__init__.py`
*0 lines each*

Empty files that make each folder a Python *package*, so `from app.core.profiles import ...`
works. They exist in `app/`, `app/api/`, `app/core/`, `app/evolution/`, `app/execution/`,
`app/investigation/`, `app/worldgen/`, `app/worldgen/archetypes/` and `tests/`.

## backend/app/api/

### `backend/app/api/routes.py`
*{{lines:backend/app/api/routes.py}} lines · Python · FastAPI*

**Every HTTP endpoint lives here** (see Chapter 6 for the full reference). It creates the
long-lived objects shared by all requests:

| Object | What it is |
|---|---|
| `router` | `APIRouter(prefix="/api")` |
| `_manager` | `WorldManager(engine=EvolutionEngine())`, which uses the fast sandbox for generation |
| `_eval_sandbox` | `CSandbox(timeout_seconds=15.0, fast=False)`, the sanitized sandbox for contestants |
| `_profiles` | `ProfileStore()` |
| `_cohorts` | `CohortStore(_manager)` |

Request bodies are Pydantic models: `CreateWorldRequest`, `SubmitRequest`, `ProbeRequest`,
`AskRequest`, `CreateCohortRequest`, `JoinCohortRequest` and `HostRequest`. The helpers are:

| Helper | Purpose |
|---|---|
| `_is_admin(token)` | Checks the `X-Vanta-Admin` header against `VANTA_ADMIN_TOKEN` (any header in demo mode) |
| `_cohort_call(fn, ...)` | Turns `CohortError` subclasses into HTTP 400/403/404 |
| `_record(world_id)` | Loads a world or raises 404 |
| `_summary(r)`, `_public(r)` | The contestant-safe views of a world. They never include ground truth, genes or params |
| `_cohort_link(world_id)` | Adds `{code, name, display_name}` if the world belongs to a cohort |
| `_contestant_tests(tests)` | Renames checks: "public: …" or "hidden check N" |

The endpoints are the archetype list, world create/list/get/submit/delete, probe info and run,
witness list and ask, profiles, cohorts (create, list, get, join, host, close, delete), and the
admin world view.

## backend/app/core/ — state and bookkeeping

### `backend/app/core/world_manager.py`
*{{lines:backend/app/core/world_manager.py}} lines · Python · SQLite*

Creates, stores, reads, lists and deletes worlds.

| Name | Purpose |
|---|---|
| `DB_PATH` | `backend/vanta_worlds.db`. Every store reads it at call time, so tests can redirect it |
| `_connect()` | Opens SQLite and creates the `worlds` table if needed |
| `_WORLD_FIELDS`, `_serialize_world`, `_deserialize_world` | Convert a `GeneratedWorld` to and from JSON. `params` is included; `agent_groundings` is not stored |
| `WorldRecord` | A stored world: id, seed, archetype, title, creator, target difficulty, viable flag, created time, world and fitness |
| `WorldNotFoundError` | Raised for unknown ids |
| `WorldManager.create_world(created_by, seed, target_difficulty, archetype_id, pins)` | Evolves a world through the registry and stores it with its fitness report |
| `get_world`, `list_worlds(created_by)`, `delete_world`, `delete_all_worlds(created_by)` | Read and remove worlds |

### `backend/app/core/profiles.py`
*{{lines:backend/app/core/profiles.py}} lines · Python · SQLite*

Ratings and activity for adaptive difficulty (see section 4.6).

| Name | Purpose |
|---|---|
| `START_RATING`, `BASE`, `SPAN`, `_LEVELS` | 1100; 800; 1200; the level names and thresholds |
| `world_rating(d)`, `recommended_difficulty(r)`, `level_for(r)` | The rating maths |
| `_connect()` | Creates the `profiles`, `attempts` and `activity` tables |
| `RatingChange` | `before`, `after`, `counted` |
| `ProfileStore.rating / recommended` | Read a person's rating, or the difficulty to aim at |
| `ProfileStore.log_activity(user, world, kind)` | Records `probe`, `witness` or `replay` |
| `ProfileStore.record_submission(...)` | Applies the Elo update with the anti-farming rules and stores the attempt |
| `ProfileStore.profile(user)` | Everything the profile endpoint returns, including the last 12 attempts |

### `backend/app/core/cohorts.py`
*{{lines:backend/app/core/cohorts.py}} lines · Python · SQLite*

Group sessions (see section 4.7).

| Name | Purpose |
|---|---|
| `CohortError`, `CohortNotFound`, `CohortForbidden` | Errors carrying an HTTP status (400, 404, 403) |
| `Cohort` | Dataclass: id, code, name, host, archetype, pins, difficulty, seed, status and created time; `public()` gives the safe view |
| `_connect()` | Creates `cohorts`, `cohort_members`, `cohort_submissions` and `activity` |
| `_identifiers(world)`, `_signature(world)` | A member's struct and function names, used to guarantee they are unique |
| `CohortStore.create(host, name, archetype, difficulty)` | Draws the seed and pins and allocates a join code |
| `get`, `list_for_host`, `member_count`, `membership` | Lookups. Codes are case-insensitive |
| `join(code, user, display_name)` | Rejoin, or evolve a unique world (up to 6 attempts to avoid name clashes) |
| `close`, `delete` | Host or admin only. Delete also removes member worlds |
| `for_world(world_id)` | Which cohort and member a world belongs to |
| `record_submission(...)` | Stores the verdict and source for cohort worlds |
| `host_view(code, requester, is_admin)` | Members with progress and activity, setting, planted variant, and originality report |

### `backend/app/core/originality.py`
*{{lines:backend/app/core/originality.py}} lines · Python*

Approach-diversity analysis (see section 4.8). The constants are `K = 6` (tokens per
fingerprint), `APPROACH_THRESHOLD = 0.55` and `NEAR_IDENTICAL = 0.85`. The functions are:
`_strip` (remove comments, strings and preprocessor lines); `_world_names` and `_fields` (what
to canonicalize and what to keep); `normalize`; `fingerprints`; `novel_fingerprints` (submission
minus starter); `jaccard`; and `analyze(entries)`. `analyze` returns `submissions_compared`,
`unchanged_from_starter`, `accepted`, `distinct_approaches`, `approaches`, `pairs` (top 25),
`near_identical` and a `method` description.

## backend/app/evolution/ — the generator's search loop

### `backend/app/evolution/engine.py`
*{{lines:backend/app/evolution/engine.py}} lines · Python · asyncio*

| Name | Purpose |
|---|---|
| `FitnessReport` | `broken`, `fixable`, `distinct_fixes`, `difficulty_error`, `score`, `notes`, and the `viable` property |
| `EvolvedWorld` | A world, its fitness, and the generation it came from |
| `EvolutionEngine(sandbox=None)` | Defaults to `CSandbox(timeout_seconds=20.0, fast=True)` |
| `_target_vector(t)` | Difficulty → genes |
| `_mutate(genes, rng, strength)` | Changes about 60% of genes by up to ±strength |
| `_measure_fitness(archetype, world, target)` | Runs the starter and the reference fixes; computes the score |
| `_estimate_difficulty(world, starter_eval)` | Blends gene difficulty with how many starter tests fail |
| `evolve(archetype, base_seed, target_difficulty, population, generations, pins)` | The loop in Figure 4.1 |

### `backend/app/evolution/reference_fixes.py`
*{{lines:backend/app/evolution/reference_fixes.py}} lines · Python (generates C)*

Known-good solutions, used **only** inside the evolution loop to prove fixability. Each function
reads the world's randomized names (from the shared header) and returns C source:

| Function | Approach |
|---|---|
| `_starvation_aging_guard` | Shortest job first, but any job that has waited 1200+ minutes is forced through; respects closing time |
| `_starvation_oldest_first` | Plain first-come-first-served among jobs that fit before closing |
| `_pool_forward` | Correct checkout (refuses a holder who already has a slot) and release (must be in use *and* match), scanning 0 → n−1 |
| `_pool_backward` | The same rules scanning n−1 → 0, which gives different slot assignments under load |

`REFERENCE_FIXES` maps an archetype id to its list of fix functions.

## backend/app/execution/

### `backend/app/execution/c_sandbox.py`
*{{lines:backend/app/execution/c_sandbox.py}} lines · Python · gcc*

Compiles and runs C (see section 4.3). It contains `FORBIDDEN_PATTERNS` (14 regular
expressions), `UnsafeCSourceError`, `static_safety_check(source)`, `CRunResult`, and
`CSandbox.compile_and_run(harness_source, candidate_source, shared_header)`. The module docstring
states plainly that this is prototype-grade isolation (subprocess + sanitizers), not a container or
virtual machine.

## backend/app/investigation/ — probe lab and witnesses

### `backend/app/investigation/probes.py`
*{{lines:backend/app/investigation/probes.py}} lines · Python (generates C)*

| Name | Purpose |
|---|---|
| `ProbeError` | Bad scenario; the message is safe to show |
| `_int(value, name, lo, hi, default)` | Validates one whole number |
| `world_params(world)` | Returns `world.params`, regenerating it from seed, genes and pins for old stored worlds |
| `ProbeOutcome` | `ok`, `trace`, `error`, `detail` |
| `ProbeKit` | Base class: `describe`, `normalize`, `harness`, `parse`, `run` |
| `_trim_sanitizer(text)` | Keeps the first 12 useful lines of a crash report |
| `StarvationProbeKit` | `job_queue` experiments (700 jobs, 30 days at most) |
| `PoolProbeKit` | `pool` experiments (3000 operations at most) |
| `PROBE_KITS`, `probe_kit(world)` | Look up the kit for a world's archetype |

### `backend/app/investigation/witnesses.py`
*{{lines:backend/app/investigation/witnesses.py}} lines · Python*

| Name | Purpose |
|---|---|
| `_NAMES` | 24 first names for witnesses |
| `_DEFLECT` | Pattern for questions about code, fixes or causes |
| `Topic`, `WitnessSpec`, `Answer`, `Cast` | Data classes: a question with keywords; a witness; an answer with evidence; the witnesses plus the scenario |
| `_TraceCache` | In-memory LRU cache of executions (96 entries) |
| `_route(question, topics)` | Keyword matching from question to topic |
| `WitnessKit` | Base class: `cast`, `answer`, `lived_period` (cached run), `ask` (routing, deflection, replay), `public` (list for the UI) |
| `StarvationWitnessKit` | The 7-day load, four users plus the operator, clock formatting (`_clock`, `_adj`, `_dur`), and `_runs` (reconstructs running intervals) |
| `PoolWitnessKit` | The day of operations, five witnesses, `_physical` (ground reality), and `_said` (how a return value reads in words) |
| `WITNESS_KITS`, `witness_kit(world)` | Look up the kit for a world |

## backend/app/worldgen/ — world generation

### `backend/app/worldgen/archetype.py`
*{{lines:backend/app/worldgen/archetype.py}} lines · Python*

`GeneratedAgentGrounding` (legacy), `GeneratedWorld`, `DEFAULT_GENES` (all 0.4 except `noise`
0.2), `clamp01`, and the abstract base class `FlawArchetype` with `generate`, `random_pins`,
`apply_pins`, `rng` and `resolve_genes`. The module docstring explains the "programs, not
content" idea.

### `backend/app/worldgen/registry.py`
*{{lines:backend/app/worldgen/registry.py}} lines · Python*

`ARCHETYPE_POOL`, `ARCHETYPES_BY_ID`, `WorldGenerationError`, and
`generate_world(session_seed, target_difficulty, archetype_id, engine, max_restarts, pins)`.
**To add an archetype, add an instance to `ARCHETYPE_POOL`** (see Chapter 12).

### `backend/app/worldgen/evaluate.py`
*{{lines:backend/app/worldgen/evaluate.py}} lines · Python*

`parse_results(stdout)` reads `VANTA_TEST_RESULT|name|violations|passed` lines.
`evaluate_submission(world, source, sandbox)` returns `{"verdict", "reason", "detail", "tests"}`
(see the verdict table in section 4.3).

### `backend/app/worldgen/archetypes/starvation.py`
*{{lines:backend/app/worldgen/archetypes/starvation.py}} lines · Python (generates C)*

`StarvationArchetype` (`id = "starvation_fairness"`), with `_DOMAINS` (5 settings), the name
pools, and `_BUG_VARIANTS`. `generate` draws everything, builds the shared header, requirements,
story and params, and calls `_starter(struct, func, variant)` and `_harness(...)`. The harness
contains `allDone`, `runSimulation` (the minute-by-minute simulation with the violation bitmask)
and `report`, and runs the 8 tests from section 4.1.

### `backend/app/worldgen/archetypes/pool_leak.py`
*{{lines:backend/app/worldgen/archetypes/pool_leak.py}} lines · Python (generates C)*

`PoolLeakArchetype` (`id = "pool_leak"`), with `_DOMAINS` (4 settings), the name pools, and
`_BUG_VARIANTS`. It has `_checkout_impl` (with or without the double-checkout guard), `_starter`
(checkout + release for the chosen variant), and `_harness` (`reset`, `countInUse`, `report`,
and the 8 tests).

## backend/tests/ — automated tests

Chapter 9 describes every test. In short:

| File | Lines | Covers |
|---|---|---|
| `backend/tests/test_evolution.py` | {{lines:backend/tests/test_evolution.py}} | Viable worlds for both archetypes, determinism, archetype variety, starter rejected and fix accepted under sanitizers |
| `backend/tests/test_investigation.py` | {{lines:backend/tests/test_investigation.py}} | Probe lab behaviour and validation, witnesses (determinism, deflection, routing, replay), ratings, and an HTTP end-to-end test |
| `backend/tests/test_cohorts.py` | {{lines:backend/tests/test_cohorts.py}} | Pins, originality, cohort lifecycle, host view, HTTP permissions, starters never explaining their bug |
| `backend/tests/test_discord_commands.py` | {{lines:backend/tests/test_discord_commands.py}} | Every Discord command against the real API, and the slash-command tree built offline |

## discord_bot/ — the Discord adapter

### `discord_bot/__init__.py`
*{{lines:discord_bot/__init__.py}} line*

A package marker with a one-line description.

### `discord_bot/vanta_api.py`
*{{lines:discord_bot/vanta_api.py}} lines · Python · httpx*

`VantaApiError(status, detail)`, and `VantaApi(client, admin_token)` with one async method per
endpoint the bot uses: `create_world`, `list_worlds`, `get_world`, `submit`, `delete_world`,
`delete_my_worlds`, `delete_every_world`, `witnesses`, `ask`, `probe_info`, `probe`, `profile`,
`create_cohort`, `get_cohort`, `join_cohort`, `cohort_host`, `close_cohort` and `delete_cohort`.
Admin calls add the `X-Vanta-Admin` header.

### `discord_bot/commands.py`
*{{lines:discord_bot/commands.py}} lines · Python*

All command *logic*, with no Discord library involved, so it can be tested.

| Name | Purpose |
|---|---|
| `EmbedSpec`, `Reply` | A description of what to send: text, embeds (title, description, colour, fields, footer, link), files, and whether it is private |
| `COLOR_*`, `DIFFICULTIES` | The VANTA palette, and Gentle/Standard/Hard/Brutal → 0.2/0.45/0.7/0.9 |
| `_cut`, `discord_user`, `difficulty_value`, `extract_source` | Truncation to Discord's limits; `discord:<id>`; calibrated → `None`; strip ```c fences |
| `VantaCommands` | One method per slash command (`create`, `list`, `info`, `submit`, `delete`, `delete_all`, `admin_delete_all`, `witnesses`, `ask`, `probe`, `profile`, `cohort_create`, `join`, `cohort_status`, `cohort_close`, `cohort_delete`), plus `_world_reply` and `_probe_summary` for formatting |

### `discord_bot/bot.py`
*{{lines:discord_bot/bot.py}} lines · Python · discord.py*

The runnable bot. `to_discord(reply)` converts a `Reply` into `discord.Embed` and `discord.File`
objects. `_is_admin(interaction)` checks for Manage Server or Administrator.
`_read_attachment(att)` reads a `.c` attachment of up to 64 KB. `build_tree(client, cmds)`
registers the `/vanta` group with all 16 commands, the choice lists, and autocomplete for witness
names. `VantaBot` creates the HTTP client and syncs commands, either to one server (instant) or
globally. `main()` reads environment variables and runs the bot.

### `discord_bot/requirements.txt`
*{{lines:discord_bot/requirements.txt}} lines*

`discord.py>=2.4` and `httpx>=0.27`.

## frontend/ — configuration

| File | Lines | Purpose |
|---|---|---|
| `frontend/package.json` | {{lines:frontend/package.json}} | Scripts (`dev`, `build` = `tsc -b && vite build`, `lint` = oxlint, `preview`) and dependencies (react, react-dom, react-router-dom; dev: vite, tailwindcss, @tailwindcss/vite, typescript, oxlint, type packages) |
| `frontend/package-lock.json` | {{lines:frontend/package-lock.json}} | Exact dependency versions, generated by npm. Never edit it by hand |
| `frontend/vite.config.ts` | {{lines:frontend/vite.config.ts}} | React and Tailwind plugins; the dev-server **proxy** that sends `/api` to `http://127.0.0.1:8811` |
| `frontend/index.html` | {{lines:frontend/index.html}} | The single HTML page: favicon, Google Fonts (Space Grotesk, Inter, JetBrains Mono), `<div id="root">`, loads `src/main.tsx` |
| `frontend/tsconfig.json` | {{lines:frontend/tsconfig.json}} | Points to the two configs below |
| `frontend/tsconfig.app.json` | {{lines:frontend/tsconfig.app.json}} | TypeScript settings for `src/`: ES2023, bundler module resolution, `react-jsx`, no unused locals or parameters |
| `frontend/tsconfig.node.json` | {{lines:frontend/tsconfig.node.json}} | TypeScript settings for `vite.config.ts` |
| `frontend/.oxlintrc.json` | {{lines:frontend/.oxlintrc.json}} | Linter rules (React hooks rules, component-export warning) |
| `frontend/.gitignore` | {{lines:frontend/.gitignore}} | Ignores `node_modules`, `dist` and similar |
| `frontend/README.md` | {{lines:frontend/README.md}} | Vite template readme (scaffold leftover; not VANTA-specific) |

## frontend/src/ — application code

### `frontend/src/main.tsx`
*{{lines:frontend/src/main.tsx}} lines · TypeScript (React)*

The entry point. It mounts `<App/>` inside `<StrictMode>` and `<BrowserRouter>` into `#root`, and
imports the global CSS.

### `frontend/src/App.tsx`
*{{lines:frontend/src/App.tsx}} lines*

The page shell: the header (VANTA wordmark, tagline, Guide link, `ProfileBadge`) and the routes
`/`, `/guide`, `/worlds/:id`, `/cohorts/:code` and `/cohorts/:code/host`.

### `frontend/src/index.css`
*{{lines:frontend/src/index.css}} lines · CSS (Tailwind v4)*

Imports Tailwind and defines the design tokens: `--field` (page), `--panel`, `--panel-2`,
`--line`, `--line-bright`, `--ink`, `--ink-dim`, `--ink-faint`, `--structure` (cool accent),
`--signal` (amber, "look here"), `--accepted`, `--rejected`, and the three font stacks. It also
sets up the faint blueprint grid on the page background, focus outlines, and reduced-motion
support.

### `frontend/src/types.ts`
*{{lines:frontend/src/types.ts}} lines*

TypeScript interfaces that mirror the API responses: `WorldSummary`, `WorldFull`, `TestResult`,
`SubmitResult`, `SubmitResultWithRating`, `RatingChange`, `Archetype`, `ProbeInfo`, `JobRow`,
`JobEvent`, `JobTrace`, `PoolOp`, `PoolTrace`, `ProbeResult`, `Witness`, `Evidence`,
`WitnessAnswer`, `Profile`, `Cohort`, `CohortMember`, `Originality` and `CohortHostView`.

### `frontend/src/api/client.ts`
*{{lines:frontend/src/api/client.ts}} lines*

`req(method, path, body)` is a small `fetch` wrapper that throws an `Error` carrying the
server's `detail` message. `api` has one function per endpoint: `archetypes`, `create`, `list`,
`get`, `submit`, `remove`, `probeInfo`, `probe`, `witnesses`, `ask`, `profile`, `createCohort`,
`hostedCohorts`, `cohort`, `joinCohort`, `cohortHost`, `closeCohort` and `deleteCohort`.

### `frontend/src/lib/user.ts`
*{{lines:frontend/src/lib/user.ts}} lines*

`userId()` returns this browser's anonymous id. It is stored in `localStorage` under `vanta_uid`,
with an in-memory fallback if storage is blocked. `PROFILE_EVENT` and `notifyProfileChanged()`
tell the header badge to refresh.

### `frontend/src/components/ui.tsx`
*{{lines:frontend/src/components/ui.tsx}} lines*

Shared building blocks: `Panel` (bordered surface), `Label` (small caps heading), `Chip` (tones:
structure, signal, accepted, rejected, neutral), `Button` (primary, ghost, danger) and `Spinner`.

### `frontend/src/components/Witnesses.tsx`
*{{lines:frontend/src/components/Witnesses.tsx}} lines*

The Witnesses tab. It shows a list of witness cards and a conversation panel for the selected
one. The panel has question chips (grey once asked), a free-text box, and the "also live through
the same period under my edited code" checkbox (enabled once the code differs from the starter).
Each answer has a "show the record behind this" toggle. `TurnView` shows one question and answer,
side by side when there is a replay. `Bubble` shows one answer.

### `frontend/src/components/ProbeLab.tsx`
*{{lines:frontend/src/components/ProbeLab.tsx}} lines*

The Probe lab tab. It has a JSON editor (pre-filled with the template), help text, a
"run it against: the original system / my edited code" switch, and Run and Reset buttons.
Results are shown by `JobResult` (stat tiles, an SVG day-by-day timeline with refusal markers,
and a per-entry table) or `PoolResult` (stat tiles, the in-use versus receipts chart, the final
slot grid, and the operation log). `Stat` and `clock` are helpers.

### `frontend/src/components/EvidenceTable.tsx`
*{{lines:frontend/src/components/EvidenceTable.tsx}} lines*

Renders a witness's evidence (`columns`, `rows`, `total`) as a compact table, highlighting
"never started" in amber.

### `frontend/src/components/ProfileBadge.tsx`
*{{lines:frontend/src/components/ProfileBadge.tsx}} lines*

`useProfile()` is a hook that loads `/api/profiles/<uid>` and reloads on `PROFILE_EVENT`.
`ProfileBadge` shows the level and rating in the header.

### `frontend/src/pages/LandingPage.tsx`
*{{lines:frontend/src/pages/LandingPage.tsx}} lines*

The home page: the hero text, the generate panel (`ArchChip` buttons for the defect class and
difficulty, including *Calibrated to you* with your recommended value), join-by-code and
host-a-cohort panels, the list of cohorts you host, and your open worlds with Open and Delete.

### `frontend/src/pages/WorldPage.tsx`
*{{lines:frontend/src/pages/WorldPage.tsx}} lines*

One world. It loads the world, keeps the editor text in state, and shows the Investigate tabs
(both stay mounted, so switching tabs keeps their state). It submits with the user id, then shows
the verdict, check chips, a note about unnamed hidden checks, and the rating change, and finally
notifies the badge.

### `frontend/src/pages/CohortJoinPage.tsx`
*{{lines:frontend/src/pages/CohortJoinPage.tsx}} lines*

Shows the cohort's name, defect class, member count and difficulty. It offers a join form (your
display name) or "Open your world" if you are already a member, and links hosts to their console.

### `frontend/src/pages/CohortHostPage.tsx`
*{{lines:frontend/src/pages/CohortHostPage.tsx}} lines*

The host console. It refreshes every 8 seconds. It shows the join code panel (copy link, Discord
command), the four count tiles, approach groups, most similar pairs with bars (amber at 85% or
more), the member table, a hidden-by-default reveal of the planted defect (`VARIANT_LABEL` gives
plain-English names), and close and delete with confirmation.

### `frontend/src/pages/GuidePage.tsx`
*{{lines:frontend/src/pages/GuidePage.tsx}} lines*

The in-app guide for new users (route `/guide`). It explains what VANTA is, your first world in
six steps, how witnesses and the probe lab work (with copyable example experiments), checks and
ratings, cohorts for participants and hosts, Discord, a FAQ, and a glossary. It has a sticky
section menu on wide screens.

### Assets and scaffold leftovers

| File | Status |
|---|---|
| `frontend/public/favicon.svg` | The browser-tab icon (currently the default Vite logo) |
| `frontend/public/icons.svg` | Vite template social icons. **Unused** |
| `frontend/src/assets/hero.png`, `react.svg`, `vite.svg` | Vite template images. **Unused** (safe to delete) |

## docs/ — this documentation

| File | Purpose |
|---|---|
| `docs/src/*.md` | The chapters of this document, written in Markdown with inline SVG diagrams |
| `docs/build_docs.py` | Builds the PDF: Markdown → HTML (numbering, highlighting, live line counts) → Chromium PDF in two passes for exact page numbers in the contents; merges the cover; adds bookmarks |
| `docs/render_pdf.cjs` | The Node/Playwright script that prints an HTML file to PDF with page footers and an outline |
| `docs/VANTA-Technical-Documentation.pdf` | The built document |
| `docs/build/` | Intermediate files (ignored by git) |

`scenarios/` is an empty folder reserved for saved experiment scenarios.

## Generated and local files (not in git)

| Path | What it is |
|---|---|
| `backend/vanta_worlds.db` | The SQLite database (all worlds, ratings, cohorts). Delete it to start fresh |
| `backend/.venv/` | Python virtual environment (FastAPI, uvicorn, pytest, discord.py, …) |
| `backend/server.log`, `frontend/vite.log` | Output of `run_dev.sh` |
| `frontend/node_modules/` | Installed npm packages |
| `frontend/dist/` | Production build output of `npm run build` |
| `__pycache__/`, `.pytest_cache/` | Python caches |

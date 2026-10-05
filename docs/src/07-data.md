# Data model {#ch-data}

All persistent state lives in **one SQLite file**, `backend/vanta_worlds.db`. Each store creates
its own tables the first time it connects (`CREATE TABLE IF NOT EXISTS`), so there is no
migration step. Deleting the file resets VANTA completely.

## What "nothing is stored" means

VANTA stores *instances*, not *content*. No problem text, answer key, bug list or witness script
is written in advance anywhere. Once a world has been generated for someone, its generated text
and code are saved so they can come back to it. Ratings, cohorts and submissions are saved too.
Witness statements and experiment results are never saved: they are recomputed by running code,
and only cached in memory for speed.

## Table `worlds`

Created by `world_manager._connect()`.

| Column | Type | Meaning |
|---|---|---|
| `world_id` | TEXT, primary key | 8 characters from a UUID |
| `seed` | INTEGER | The seed requested for this world |
| `archetype_id` | TEXT | `starvation_fairness` or `pool_leak` |
| `title` | TEXT | Story title |
| `created_by` | TEXT | Owner id |
| `target_difficulty` | REAL | 0–1, used for ratings |
| `viable` | INTEGER (0/1) | Whether evolution proved it viable |
| `world_json` | TEXT | The serialized `GeneratedWorld` (see below) |
| `fitness_json` | TEXT | `broken`, `fixable`, `distinct_fixes`, `difficulty_error`, `score`, `generation` |
| `created_at` | TEXT | UTC timestamp, set by SQLite |

`world_json` holds `archetype_id`, `seed` (the winning candidate's own seed), `genes`, `title`,
`briefing`, `specification`, `starter_source`, `function_name`, `function_signature`,
`shared_header`, `mandatory_properties`, `optional_objectives`, `sample_input_description`,
`harness_source`, `ground_truth_summary` and `params`.

`params` contains the struct and function names, the variant, the constants, the `domain`
dictionary, `domain_index` and `pins`. Worlds saved before `params` existed are handled by
`world_params()`, which regenerates the params from the seed and genes.

## Table `profiles`

Created by `profiles._connect()`.

| Column | Type | Meaning |
|---|---|---|
| `user_id` | TEXT, primary key | Person id |
| `rating` | REAL | Current Elo-style rating |
| `updated_at` | TEXT | Last change |

## Table `attempts`

One row per submission, used for history and the anti-farming rules.

| Column | Type | Meaning |
|---|---|---|
| `id` | INTEGER, autoincrement | |
| `user_id`, `world_id` | TEXT | Who submitted, and to which world |
| `difficulty` | REAL | The world's target difficulty |
| `verdict` | TEXT | `accepted` or `rejected` |
| `passed`, `total` | INTEGER | Checks passed, and checks in total |
| `rating_before`, `rating_after` | REAL | The rating change (equal when it didn't count) |
| `created_at` | TEXT | Timestamp |

## Table `activity`

Investigation counters. This table is created by both the profiles store and the cohort store.

| Column | Type | Meaning |
|---|---|---|
| `id` | INTEGER | |
| `user_id`, `world_id` | TEXT | |
| `kind` | TEXT | `probe`, `witness` or `replay` |
| `created_at` | TEXT | |

## Table `cohorts`

| Column | Type | Meaning |
|---|---|---|
| `cohort_id` | TEXT, primary key | 8 characters |
| `code` | TEXT, unique | 6-character join code (uppercase) |
| `name` | TEXT | Up to 80 characters |
| `host_id` | TEXT | Who created it |
| `archetype_id` | TEXT | The defect class for everyone |
| `pins_json` | TEXT | `{"variant": "...", "domain": N}` |
| `target_difficulty` | REAL | One difficulty for everyone |
| `seed` | INTEGER | Cohort seed (31 random bits); member seeds are derived from it |
| `status` | TEXT | `open` or `closed` |
| `created_at` | TEXT | |

## Table `cohort_members`

Primary key `(cohort_id, user_id)`, so each person joins a given cohort once.

| Column | Type | Meaning |
|---|---|---|
| `cohort_id`, `user_id` | TEXT | |
| `display_name` | TEXT | Up to 40 characters, shown to the host |
| `world_id` | TEXT | Their personal world |
| `signature` | TEXT | Their identifier set, for example `Lease|leaseSlot|freeSpot`, kept unique within the cohort |
| `joined_at` | TEXT | |

## Table `cohort_submissions`

Every submission to a cohort world, *including the source code*, for the originality analysis.

| Column | Type | Meaning |
|---|---|---|
| `id` | INTEGER | |
| `cohort_id`, `user_id`, `world_id` | TEXT | |
| `verdict` | TEXT | |
| `passed`, `total` | INTEGER | |
| `source` | TEXT | The submitted C code |
| `created_at` | TEXT | |

## How the tables relate

<figure class="diagram">
<svg viewBox="0 0 760 250" xmlns="http://www.w3.org/2000/svg" font-family="Inter, sans-serif">
  <g font-size="10.5">
  <rect x="20" y="20" width="160" height="80" rx="7" fill="#e8f4f8" stroke="#1f7a99"/>
  <text x="100" y="40" text-anchor="middle" font-weight="700" font-size="12" fill="#1d2433">worlds</text>
  <text x="100" y="58" text-anchor="middle" fill="#4a5466">world_id (PK)</text>
  <text x="100" y="72" text-anchor="middle" fill="#4a5466">created_by</text>
  <text x="100" y="86" text-anchor="middle" fill="#4a5466">world_json, fitness_json</text>
  <rect x="300" y="20" width="160" height="80" rx="7" fill="#e8f4f8" stroke="#1f7a99"/>
  <text x="380" y="40" text-anchor="middle" font-weight="700" font-size="12" fill="#1d2433">attempts</text>
  <text x="380" y="58" text-anchor="middle" fill="#4a5466">user_id, world_id</text>
  <text x="380" y="72" text-anchor="middle" fill="#4a5466">verdict, passed/total</text>
  <text x="380" y="86" text-anchor="middle" fill="#4a5466">rating before/after</text>
  <rect x="580" y="20" width="160" height="80" rx="7" fill="#e8f4f8" stroke="#1f7a99"/>
  <text x="660" y="40" text-anchor="middle" font-weight="700" font-size="12" fill="#1d2433">profiles</text>
  <text x="660" y="58" text-anchor="middle" fill="#4a5466">user_id (PK)</text>
  <text x="660" y="72" text-anchor="middle" fill="#4a5466">rating</text>
  <rect x="300" y="150" width="160" height="80" rx="7" fill="#e8f4f8" stroke="#1f7a99"/>
  <text x="380" y="170" text-anchor="middle" font-weight="700" font-size="12" fill="#1d2433">activity</text>
  <text x="380" y="188" text-anchor="middle" fill="#4a5466">user_id, world_id</text>
  <text x="380" y="202" text-anchor="middle" fill="#4a5466">kind: probe/witness/replay</text>
  <rect x="20" y="150" width="160" height="80" rx="7" fill="#fdf3e3" stroke="#c27a12"/>
  <text x="100" y="170" text-anchor="middle" font-weight="700" font-size="12" fill="#1d2433">cohort_members</text>
  <text x="100" y="188" text-anchor="middle" fill="#4a5466">cohort_id + user_id (PK)</text>
  <text x="100" y="202" text-anchor="middle" fill="#4a5466">world_id, signature</text>
  <rect x="580" y="150" width="160" height="80" rx="7" fill="#fdf3e3" stroke="#c27a12"/>
  <text x="660" y="170" text-anchor="middle" font-weight="700" font-size="12" fill="#1d2433">cohorts</text>
  <text x="660" y="188" text-anchor="middle" fill="#4a5466">cohort_id (PK), code</text>
  <text x="660" y="202" text-anchor="middle" fill="#4a5466">pins_json, seed, status</text>
  <text x="660" y="216" text-anchor="middle" fill="#4a5466">+ cohort_submissions</text>
  </g>
  <g stroke="#5b6475" stroke-width="1.1" fill="none">
    <line x1="180" y1="60" x2="300" y2="60"/><line x1="460" y1="60" x2="580" y2="60"/>
    <line x1="100" y1="100" x2="100" y2="150"/><line x1="180" y1="190" x2="300" y2="190"/>
    <line x1="180" y1="210" x2="580" y2="210" stroke-dasharray="4 3"/>
    <path d="M160,100 C220,130 290,160 300,170"/>
  </g>
  <g font-size="9.5" fill="#5b6475">
    <text x="240" y="54" text-anchor="middle">world_id</text><text x="520" y="54" text-anchor="middle">user_id</text>
    <text x="108" y="130">world_id</text><text x="240" y="184" text-anchor="middle">user_id</text>
    <text x="440" y="224" text-anchor="middle">cohort_id</text>
  </g>
</svg>
<figcaption>Figure 7.1. Logical links between tables. SQLite foreign keys are not declared; the links are kept by the code.</figcaption>
</figure>

## What is kept only in memory

| Data | Where | Lifetime |
|---|---|---|
| Witness execution traces | `witnesses._cache` (LRU, 96 entries) | Until the server restarts |
| The browser's user id | `localStorage["vanta_uid"]` | Until browser storage is cleared |
| Witness conversations and probe results on screen | React state | Until the page is closed |

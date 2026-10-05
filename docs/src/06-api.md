# HTTP API reference {#ch-api}

All endpoints are under `/api` on the backend (default `http://127.0.0.1:8811`), except
`/health`. Requests and responses are JSON. Errors use FastAPI's shape `{"detail": "<message>"}`
with an HTTP status code.

FastAPI also serves interactive documentation of every endpoint at
`http://127.0.0.1:8811/docs` while the server is running.

## Conventions

| Item | Rule |
|---|---|
| Identity | `created_by`, `user_id`, `host_id` and `requested_by` are free-form strings: the browser's random id, or `discord:<id>` |
| Admin | Send the header `X-Vanta-Admin: <token>` (see section 4.11) |
| Status codes | 200 OK · 400 bad input or generation error · 403 not allowed · 404 not found · 422 invalid scenario, code or body · 500 generation failed |
| Contestant safety | No endpoint except the admin one returns ground truth, genes, params or reference fixes |

## Service and catalogue

### `GET /health`

Returns `{"status": "ok"}`. Used to check the server is up.

### `GET /api/archetypes`

Lists the defect classes in the pool.

```json
[{"id": "starvation_fairness", "title": "Shared Resource Fairness", "domain": "resource_allocation"},
 {"id": "pool_leak", "title": "Resource Pool Integrity", "domain": "resource_pool"}]
```

## Worlds

### `POST /api/worlds` — evolve a new world

| Body field | Type | Meaning |
|---|---|---|
| `created_by` | string, required | Owner id |
| `target_difficulty` | number 0–1, or `null` | `null` = calibrate to the owner's rating |
| `archetype_id` | string, optional | Force a defect class; omit for a random one |
| `seed` | integer, optional | Reproduce a specific world |

The response is the contestant view of the world, plus `calibrated`:

```json
{
 "world_id": "14fdd16f", "title": "Campus Parking Garage", "archetype_id": "pool_leak",
 "created_by": "docs-demo", "seed": 4242, "target_difficulty": 0.45, "viable": true,
 "briefing": "The campus parking garage manages a fixed number of parking spots that…",
 "specification": "Implement returnSlot(), which reclaims a parking spot when its holder returns it. …",
 "starter_source": "int claimSlot(struct Bay pool[], …",
 "function_name": "returnSlot",
 "function_signature": "int returnSlot(struct Bay pool[], int poolSize, int holderId)",
 "mandatory_properties": ["Every parking spot that is released must become available again.", "…"],
 "optional_objectives": ["Minimize the time to find a free slot.", "…"],
 "sample_input_description": "The pool has 12 parking spots. Build your own checkout/release sequences.",
 "cohort": null,
 "calibrated": false
}
```

Errors: 400 for an unknown `archetype_id`. This call can take from about 1 second (pool) to
around 30 seconds (scheduler), because the world is evolved and proven before it is returned.

### `GET /api/worlds?created_by=<id>`

Lists world summaries (`world_id`, `title`, `archetype_id`, `created_by`, `seed`,
`target_difficulty`, `viable`), newest first. Without `created_by` it lists every world.

### `GET /api/worlds/{world_id}`

The contestant view, the same shape as above but without `calibrated`. `cohort` is
`{code, name, display_name}` when the world belongs to a cohort member. Returns 404 if the world
is unknown.

### `POST /api/worlds/{world_id}/submit` — grade a fix

Body: `{"c_source": "<C code>", "user_id": "<id, optional; defaults to the world's creator>"}`.

```json
{
 "verdict": "rejected",
 "reason": "failed_tests",
 "detail": null,
 "tests": [
  {"test": "public: basic", "passed": false, "hidden": false},
  {"test": "public: full rejected", "passed": true, "hidden": false},
  {"test": "hidden check 1", "passed": false, "hidden": true},
  {"test": "hidden check 2", "passed": false, "hidden": true}
 ],
 "rating": {"before": 1100.0, "after": 1098.4, "counted": true}
}
```

`reason` is one of `null` (accepted), `failed_tests`, `compile_error`, `timeout` or
`runtime_error`. `detail` carries the compiler or timeout message only for `compile_error` and
`timeout`. `rating.counted` is `false` once the world has been solved, or after the 5th counted
rejection on that world.

### `DELETE /api/worlds/{world_id}?requested_by=<id>`

Deletes one world. Allowed if `requested_by` equals the world's creator, or with an admin header.
Returns `{"deleted": "<id>"}`, 403 if not allowed, or 404 if not found.

### `DELETE /api/worlds?created_by=<id>&requested_by=<id>`

Deletes all of one person's worlds (`requested_by` must match, or admin). Without `created_by` it
deletes **every** world and requires admin. Returns `{"deleted_count": N}`.

## Investigation

### `GET /api/worlds/{world_id}/probe`

Describes the experiment format for this world:

```json
{"kind": "pool", "pool_size": 12, "unit": "parking spot",
 "checkout_func": "claimSlot", "release_func": "returnSlot", "limits": {"ops": 3000},
 "help": "A list of operations run in order on an empty pool of 12 parking spots. …",
 "template": {"ops": [{"op": "checkout", "holder": 1}, {"op": "checkout", "holder": 2},
                      {"op": "release", "holder": 1},
                      {"op": "cycle", "holder": 100, "repeat": 3, "step": 1}]}}
```

For scheduler worlds, `kind` is `job_queue` and the response includes `day_length`, `noun`,
`machine` and `limits: {jobs: 700, days: 30}`.

### `POST /api/worlds/{world_id}/probe` — run an experiment

Body: `{"scenario": {...}, "c_source": "<C or null>", "user_id": "<id, optional>"}`. When
`c_source` is `null` the original starter is run.

```json
{"ok": true, "error": null, "detail": null, "ran": "original",
 "trace": {"kind": "pool", "pool_size": 12,
   "ops": [{"k": 0, "op": "checkout", "holder": 5, "returned": 0, "outcome": "got_slot",
            "in_use": 1, "ledger": 1, "entry": 0, "owner": null},
           {"k": 1, "op": "release", "holder": 5, "returned": 0, "outcome": "refused",
            "in_use": 1, "ledger": 1, "entry": 1, "owner": null}],
   "slots": [{"slot": 0, "in_use": true, "holder": 5}, "…"],
   "stats": {"pool_size": 12, "in_use": 1, "ledger": 1, "op_count": 2},
   "ops_truncated": false}}
```

Pool `outcome` values are `got_slot`, `denied`, `invalid_slot`, `accepted` and `refused`. For
scheduler traces see section 4.4: `jobs`, `events`, `stats`, `day_length` and
`events_truncated`. If the code does not compile, crashes or times out, the response has
`ok: false`, `error` set to `compile_error`, `runtime_error` or `timeout`, and `detail`. An
invalid scenario returns **422** with a message such as `'jobs[0].minutes' must be between 1 and
20000 (got 0)`.

### `GET /api/worlds/{world_id}/witnesses`

```json
[{"key": "regular", "name": "Zara",
  "role": "Borrows a parking spot and brings it back, many times a day",
  "vantage": "Sees what the system told them each time they borrowed or returned.",
  "questions": [{"topic": "story", "question": "How did borrowing go for you today?"},
                {"topic": "denied", "question": "Were you ever told there was nothing available?"},
                {"topic": "returns", "question": "Did your returns go through?"}]},
 "… staff, double, newcomer, auditor"]
```

### `POST /api/worlds/{world_id}/witnesses/{key}/ask`

Body: `{"topic": "<topic>"}` **or** `{"question": "<free text>"}`, plus optional `c_source`
(relive the period under this code) and `user_id`.

```json
{"witness": "auditor", "topic": "reconcile",
 "text": "At close: the desk's receipts say 9 out, the system marks 9 as in use, and 8 are physically out with people. They don't agree.",
 "evidence": {"columns": ["source", "parking spots out"],
              "rows": [["desk receipts", 9], ["system in use", 9], ["physically out", 8]]},
 "followups": ["When did the numbers first stop agreeing?", "What does the end-of-day stock check show?"]}
```

With `c_source`, the response also has `"replay": {"text": "...", "evidence": {...}}`, or
`"replay": {"error": "compile_error", "detail": "...", "text": "..."}`. A question about code or
fixes returns `"topic": "deflect"`. An unrecognized question returns `"topic": "unknown"` with
`followups`. An unknown witness key returns 404.

## Profiles

### `GET /api/profiles/{user_id}`

```json
{"user_id": "docs-demo", "rating": 1098.4, "level": "Apprentice", "recommended_difficulty": 0.31,
 "worlds_solved": 0, "worlds_attempted": 1, "submissions": 1,
 "experiments_run": 0, "witness_questions": 0,
 "history": [{"world_id": "14fdd16f", "difficulty": 0.45, "verdict": "rejected", "passed": 3,
              "total": 8, "rating_before": 1100.0, "rating_after": 1098.4,
              "at": "2026-10-05 04:37:05"}]}
```

Unknown users get a fresh profile (rating 1100), not an error.

## Cohorts

### `POST /api/cohorts`

Body: `{"host_id", "name", "archetype_id"?, "target_difficulty"? (default 0.45)}`. Returns the
public cohort:

```json
{"code": "GXDHH6", "name": "CS1 lab · week 6", "archetype_id": "pool_leak",
 "archetype_title": "Resource Pool Integrity", "target_difficulty": 0.45, "status": "open",
 "member_count": 0, "host_id": "k3j9x2ab", "created_at": "2026-10-05 04:17:12"}
```

### `GET /api/cohorts?host_id=<id>`

The cohorts this person hosts, each with its `member_count`.

### `GET /api/cohorts/{code}?user_id=<id>`

The public cohort, plus `membership` (`{user_id, display_name, world_id, joined_at}` or
`null`) when `user_id` is given. Codes are case-insensitive. Returns 404 if unknown.

### `POST /api/cohorts/{code}/join`

Body: `{"user_id", "display_name"}`. Returns `{"member": {"user_id", "display_name",
"world_id", "rejoined"}, "world": <contestant world view>}`. Returns 400 if the cohort is closed
to new members.

### `GET /api/cohorts/{code}/host?host_id=<id>`

Host or admin only (otherwise 403). Returns the public cohort plus:

| Field | Contents |
|---|---|
| `setting` | The story place, for example "the university library" |
| `defect_variant` | The planted variant id (the host UI hides it until revealed) |
| `defect_class` | The archetype title |
| `members` | `[{user_id, display_name, world_id, joined_at, world_exists, identifiers, submissions, solved, solved_at, best: {passed, total}, experiments, witness_questions}]` |
| `solved_count` | Members with an accepted submission |
| `originality` | The `analyze()` report (section 4.8) |

### `POST /api/cohorts/{code}/close`

Body: `{"host_id"}`. Host or admin. Sets the status to `closed`.

### `DELETE /api/cohorts/{code}?host_id=<id>`

Host or admin. Deletes the cohort and every member's world. Returns
`{"deleted": "<CODE>", "worlds_deleted": N}`.

## Admin

### `GET /api/admin/worlds/{world_id}`

Admin header required (403 otherwise). Returns the contestant view plus `ground_truth_summary`
(for example `archetype=pool_leak bug_variant=off_by_one_index pool_size=10 …`), `genes` and
`fitness` (`broken`, `fixable`, `distinct_fixes`, `difficulty_error`, `score`, `generation`).

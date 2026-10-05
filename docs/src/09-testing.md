# Testing {#ch-testing}

## Running the tests

```bash
cd backend
.venv/bin/python3 -m pytest tests -q          # all 35 tests, about 4 minutes
.venv/bin/python3 -m pytest tests/test_cohorts.py -q    # one file, about 10 seconds
```

The evolution tests are the slow ones, because they really compile and run dozens of C programs.
Tests that touch the database use a `tmp_db` fixture, which points `DB_PATH` at a temporary file,
so your real `vanta_worlds.db` is never modified. HTTP tests use `httpx.ASGITransport`, which
calls the FastAPI app in-process without opening a network port.

## `test_evolution.py` — the generator

| Test | What it proves |
|---|---|
| `test_pool_leak_evolves_viable_world` | Evolution finds a pool world that is broken, fixable, and has at least 2 distinct fixes |
| `test_starvation_evolves_viable_world` | The same for a scheduler world |
| `test_same_seed_reproduces_same_world` | Evolution is deterministic: the same seed gives the same starter and function name |
| `test_registry_picks_archetype_by_seed` | Over seeds 1–7, both defect classes are chosen, so the class itself varies |
| `test_starter_rejected_correct_fix_accepted_pool` | Under the *sanitized* sandbox, the starter is rejected and a hand-written correct fix is accepted |

## `test_investigation.py` — probe lab, witnesses, ratings

| Test | What it proves |
|---|---|
| `test_probe_reveals_starvation_and_fix_relieves_it` | In a `pure_shortest_first` world, an experiment shows the long job waiting far longer on the original than on a fix |
| `test_probe_on_pool_shows_double_release_difference` | In a `linear_search_first_match` world, a double release is "accepted" by the original and "refused" by a fix |
| `test_probe_rejects_bad_scenarios` (5 cases) | Empty lists, code-injection strings, negative times, too many jobs, and non-objects are all refused |
| `test_probe_reports_compile_errors_in_contestant_code` | Broken code gives `ok: false, error: compile_error`, not a crash |
| `test_every_witness_answers_every_question_deterministically` (2 cases) | For both archetypes, every witness answers every topic, with identical text each time |
| `test_witness_deflects_requests_for_the_solution` | "How do I fix the code?" is deflected; nonsense gets "unknown" plus suggestions |
| `test_free_text_routes_to_a_topic` | "How long did you have to wait?" routes to the *worst* topic |
| `test_auditor_books_disagree_originally_and_agree_under_a_fix` (3 cases) | For every pool variant, the auditor finds a mismatch in the original and none under a fix |
| `test_replay_with_broken_code_is_reported_not_raised` | A replay with code that won't compile returns `replay.error`, not a server error |
| `test_rating_moves_with_results` | A rejection lowers the rating, an accept raises it, a second accept doesn't count, and the recommended difficulty rises |
| `test_recommended_difficulty_spans_beginner_to_expert` | Recommendations stay within 0.10–0.95 and rise with rating |
| `test_investigation_api_end_to_end` | Over HTTP: calibrated create → probe → bad probe gives 422 → witnesses → ask → submit → profile counts |

## `test_cohorts.py` — cohorts, originality, permissions

| Test | What it proves |
|---|---|
| `test_pinned_worlds_share_defect_but_not_names` | Two pinned worlds share the variant and setting but not their identifiers |
| `test_originality_sees_through_renaming_and_separates_approaches` | The same approach in two worlds with renamed variables scores above 0.85; forward and backward scans score below 0.55; the report finds 2 approaches and flags the unchanged starter |
| `test_cohort_gives_each_member_a_unique_world_with_the_same_defect` | Three members get the same variant and setting, three different identifier sets and three different starters; rejoin returns the same world; only the host sees the console; closing blocks newcomers but not members |
| `test_host_view_tracks_progress_and_approaches` | The host view counts solved members, 2 distinct approaches, and the unchanged submission; delete removes 3 worlds |
| `test_cohort_api_and_world_ownership` | Over HTTP: cohort lifecycle, cohort link on the world, 403 for non-hosts, 403 for deleting someone else's world, admin-only "delete everything", admin-only ground truth |
| `test_starter_code_never_explains_its_own_bug` | No starter (any archetype, any variant) contains a comment or a `(void)` hint |

## `test_discord_commands.py` — the Discord bot

| Test | What it proves |
|---|---|
| `test_extract_source_handles_fences` | Code pasted inside ```c fences is unwrapped |
| `test_world_lifecycle_from_discord` | `create` → `list` → `submit` (rejected, with hidden checks unnamed) → `submit` a fix (accepted, rating shown) → others can't delete → non-admins can't delete everything → owner deletes |
| `test_witnesses_and_probe_from_discord` | `witnesses`, `ask` (including an unknown name), `probe` help, a probe run, invalid JSON, `profile`, `delete_all` |
| `test_cohort_from_discord` | `cohort_create`, two `join`s with different starter files, rejoin, a solve, `cohort_status` for host and non-host, `cohort_close`, a late join refused, `cohort_delete` |
| `test_slash_command_tree_builds_offline` | All 16 `/vanta` commands register and serialize correctly with discord.py, without connecting to Discord |

## Browser checks

Browser behaviour was verified with scripted headless Chromium (Playwright):

- generating a world, asking witnesses, opening evidence, running the probe lab, and submitting;
- a pool world fixed in the editor, with a witness replay showing "All three agree" and an
  accepted submission that moves the rating;
- a three-person cohort created from the landing page, joined from three separate browsers, with
  two different accepted fixes and one rejected starter. The host console showed 2 solved and
  2 distinct approaches.

These scripts are not part of the automated suite, because they need both servers running.

## Frontend type-checking

```bash
cd frontend && npx tsc -b      # type errors fail here
npm run build                  # type-check + production bundle in dist/
```

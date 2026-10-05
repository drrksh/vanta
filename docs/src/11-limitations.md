# Limitations, security and future work {#ch-limits}

A good project document is honest about what is not finished. Everything here is a known,
deliberate limit of the current prototype.

## Security limits

<div class="callout warn" markdown="1">
<span class="t">The C sandbox is prototype-grade.</span>
Contestant code runs as a normal process on the server, after a pattern check and with
sanitizers and a timeout. A determined attacker could find calls that aren't on the deny list.
Examples are raw `syscall()`, other ways of reaching the filesystem, or using up memory. For a
public deployment, run the sandbox inside a container or VM (for example Docker with no network,
a read-only filesystem, and memory and CPU limits, or nsjail or gVisor). `compile_and_run` is the
only function that would need to change.
</div>

| Area | Limit | What to do for real use |
|---|---|---|
| Identity | Browser ids live in `localStorage` and Discord ids are trusted; there are no passwords. Anyone who knows a world id can submit to it | Add real accounts (OAuth or university sign-in) and attach worlds to accounts |
| Admin | Demo mode (no `VANTA_ADMIN_TOKEN`) treats any `X-Vanta-Admin` header as admin | Always set the token outside a demo |
| Host rights | Proven only by knowing the host's id | The same fix as identity |
| Rate limits | None; generating worlds and probing cost CPU | Add per-user limits and a job queue |
| CORS | Allows every origin | Restrict to the deployed frontend's origin |

## Functional limits

- **Two defect classes.** The pool has `starvation_fairness` and `pool_leak`, with three variants
  each. More archetypes (Chapter 12) would broaden it, for example integer overflow in billing,
  a ring buffer, an LRU cache, string parsing, or a state machine.
- **Some genes are reserved.** `system_size`, `noise` and `reasoning_depth` are produced and
  evolved, but the current archetypes don't read them yet.
- **Difficulty is estimated, not measured on people.** The estimate uses genes and how obvious
  the starter's failures are. Real solve rates could be fed back to improve it.
- **Witness wording is templated.** Answers are computed from executions and phrased with fixed
  sentence templates. No language model is involved, which keeps them exact. A future option is
  an LLM that only rephrases the computed facts.
- **Single process, SQLite.** This is fine for a class or a hackathon room. Many simultaneous
  users would need a server database and background workers for evolution.
- **Discord not tested live.** The command logic is tested against the real API, and the command
  tree is built and serialized. The bot has not been run against Discord's servers from the
  development environment, because that needs a bot token.
- **The originality analysis measures diversity, not cheating.** Two honest people can make the
  same one-line fix. The host console says so.
- **Leaderboard.** Deliberately not built yet.
- **Scaffold leftovers.** The default Vite favicon and a few unused template images remain in
  `frontend/`.

## Ideas for future work

1. More archetypes, and per-archetype difficulty tuned from real solve data.
2. A container-based sandbox.
3. Accounts and a hackathon layer: rounds, time limits, and optionally a leaderboard.
4. Saving and sharing experiments (the `scenarios/` folder is reserved for this).
5. Letting the host pick which witnesses appear, or adding "decoy" witnesses driven by the
   `noise` gene.
6. Exporting a cohort's results (per member and per approach) as a spreadsheet.

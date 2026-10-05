"""
Probe Lab: run the generated system on a scenario the contestant designs.

This is how a contestant investigates without anyone (human or bot) holding
the answer. They write an experiment ("what happens if a long job arrives in
the middle of a stream of short ones?"), VANTA compiles the system -- either
the original broken code or their own patch -- into a probe harness built
for that experiment, runs it under sanitizers, and returns a trace of what
actually happened.

Nothing in a trace is stored or authored: every number in it is produced by
executing C. Two contestants who run different experiments see different
evidence, and the evidence is always true for the code they ran.

Scenarios are plain JSON of bounded integers. They are validated and turned
into C *literals* here, never pasted as text, so a scenario can't inject code.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.execution.c_sandbox import CRunResult, CSandbox
from app.worldgen.archetype import GeneratedWorld


class ProbeError(ValueError):
    """The scenario is malformed or out of bounds. Message is contestant-safe."""


def _int(v, name: str, lo: int, hi: int, default: int | None = None) -> int:
    if v is None:
        if default is None:
            raise ProbeError(f"'{name}' is required")
        return default
    if isinstance(v, bool) or not isinstance(v, (int, float)) or int(v) != v:
        raise ProbeError(f"'{name}' must be a whole number")
    v = int(v)
    if not lo <= v <= hi:
        raise ProbeError(f"'{name}' must be between {lo} and {hi} (got {v})")
    return v


def world_params(world: GeneratedWorld) -> dict:
    """Structured generation params. Worlds stored before params existed are
    regenerated deterministically from (seed, genes) to recover them."""
    if world.params:
        return world.params
    from app.worldgen.registry import ARCHETYPES_BY_ID

    regenerated = ARCHETYPES_BY_ID[world.archetype_id].generate(world.seed, world.genes)
    world.params = regenerated.params
    return world.params


@dataclass
class ProbeOutcome:
    ok: bool
    trace: dict = field(default_factory=dict)
    error: str | None = None        # compile_error | runtime_error | timeout
    detail: str | None = None


class ProbeKit:
    """Per-archetype: scenario schema, harness builder, trace parser."""

    archetype_id: str

    def describe(self, world: GeneratedWorld) -> dict:
        raise NotImplementedError

    def normalize(self, world: GeneratedWorld, scenario: dict) -> dict:
        raise NotImplementedError

    def harness(self, world: GeneratedWorld, norm: dict, event_cap: int) -> str:
        raise NotImplementedError

    def parse(self, world: GeneratedWorld, norm: dict, stdout: str) -> dict:
        raise NotImplementedError

    async def run(
        self, world: GeneratedWorld, scenario: dict, source: str, sandbox: CSandbox,
        event_cap: int = 1500, normalized: dict | None = None,
    ) -> ProbeOutcome:
        norm = normalized if normalized is not None else self.normalize(world, scenario)
        harness = self.harness(world, norm, event_cap)
        result: CRunResult = await sandbox.compile_and_run(harness, source, world.shared_header)
        if result.compile_error:
            return ProbeOutcome(ok=False, error="compile_error", detail=result.compile_error)
        if result.timed_out:
            return ProbeOutcome(ok=False, error="timeout",
                                detail="The system did not finish this scenario in time.")
        if "PROBE_DONE" not in result.stdout:
            return ProbeOutcome(
                ok=False, error="runtime_error",
                detail=_trim_sanitizer(result.stderr or result.runtime_error or "crashed"),
                trace=self._safe_parse(world, norm, result.stdout),
            )
        return ProbeOutcome(ok=True, trace=self.parse(world, norm, result.stdout))

    def _safe_parse(self, world, norm, stdout) -> dict:
        try:
            return self.parse(world, norm, stdout)
        except Exception:  # partial output from a crash; best effort only
            return {}


def _trim_sanitizer(text: str) -> str:
    # Keep the sanitizer headline and the first frames -- the useful part --
    # and drop sandbox paths.
    lines = [ln for ln in text.splitlines() if ln.strip()]
    keep = []
    for ln in lines:
        if "/tmp/" in ln:
            ln = ln[ln.rfind("/") + 1:]
        keep.append(ln)
        if len(keep) >= 12:
            break
    return "\n".join(keep)


# ---------------------------------------------------------------------------
# Starvation / fairness: a single machine and a queue of jobs
# ---------------------------------------------------------------------------

class StarvationProbeKit(ProbeKit):
    archetype_id = "starvation_fairness"
    MAX_JOBS = 700
    MAX_DAYS = 30

    def describe(self, world):
        p = world_params(world)
        L = p["day_length"]
        noun = p["domain"]["noun"]
        return {
            "kind": "job_queue",
            "day_length": L,
            "noun": noun,
            "machine": p["domain"]["machine"],
            "limits": {"jobs": self.MAX_JOBS, "days": self.MAX_DAYS},
            "help": (
                f"Each entry submits {noun}s. 'at' is the minute it is submitted "
                f"(minute 0 = opening of day 1; each day has {L} open minutes, so day 2 "
                f"opens at minute {L}). Optional: 'repeat' + 'every' to submit a stream, "
                f"'abandon_after' to have the person walk away N minutes after submitting. "
                f"'days' is how long to watch (max {self.MAX_DAYS})."
            ),
            "template": {
                "days": 3,
                "jobs": [
                    {"minutes": 20, "at": 0},
                    {"minutes": 45, "at": 10},
                    {"minutes": 10, "at": 15, "repeat": 4, "every": 30},
                ],
            },
        }

    def normalize(self, world, scenario):
        p = world_params(world)
        if not isinstance(scenario, dict):
            raise ProbeError("scenario must be an object with a 'jobs' list")
        days = _int(scenario.get("days"), "days", 1, self.MAX_DAYS, default=3)
        entries = scenario.get("jobs")
        if not isinstance(entries, list) or not entries:
            raise ProbeError("'jobs' must be a non-empty list")
        horizon = days * p["day_length"]
        jobs = []
        for n, e in enumerate(entries):
            if not isinstance(e, dict):
                raise ProbeError(f"jobs[{n}] must be an object")
            label = f"jobs[{n}]"
            minutes = _int(e.get("minutes"), f"{label}.minutes", 1, 20000)
            at = _int(e.get("at"), f"{label}.at", 0, horizon)
            repeat = _int(e.get("repeat"), f"{label}.repeat", 1, self.MAX_JOBS, default=1)
            every = _int(e.get("every"), f"{label}.every", 1, 100000, default=1)
            abandon = e.get("abandon_after")
            abandon = -1 if abandon is None else _int(abandon, f"{label}.abandon_after", 0, 1_000_000)
            owner = e.get("owner") if isinstance(e.get("owner"), str) else None
            for k in range(repeat):
                t = at + k * every
                if t > horizon:
                    break
                jobs.append({"id": len(jobs) + 1, "minutes": minutes, "at": t,
                             "abandon_at": -1 if abandon < 0 else t + abandon,
                             "entry": n, "owner": owner})
                if len(jobs) > self.MAX_JOBS:
                    raise ProbeError(f"at most {self.MAX_JOBS} jobs per experiment")
        return {"days": days, "jobs": jobs}

    def harness(self, world, norm, event_cap):
        p = world_params(world)
        S, F, L = p["struct_name"], p["func_name"], p["day_length"]
        jobs = norm["jobs"]
        n = max(1, len(jobs))
        inits = "\n    ".join(
            f"jobs[{i}] = (struct {S}){{{j['id']}, {j['minutes']}, {j['at']}, 0, 0, 0, -1, -1}}; "
            f"abandonAt[{i}] = {j['abandon_at']};"
            for i, j in enumerate(jobs)
        )
        return f"""
#include <stdio.h>
#include <string.h>
#define OPEN_MINUTES_PER_DAY {L}
#define PROBE_DAYS {norm['days']}
#define EVENT_CAP {event_cap}

static struct {S} jobs[{n}];
static int abandonAt[{n}];
static int lastRefusedDay[{n}];
static int events = 0;

static void ev(int t, const char *kind, int id) {{
    if (events < EVENT_CAP) printf("PROBE_EVENT|%d|%s|%d\\n", t, kind, id);
    events++;
}}
static int live(int i) {{
    return !jobs[i].isFinished && !jobs[i].isRejected && !jobs[i].isAbandoned;
}}

int main(void) {{
    int count = {len(jobs)};
    memset(jobs, 0, sizeof(jobs));
    {inits}
    for (int i = 0; i < count; i++) lastRefusedDay[i] = -1;
    for (int i = 0; i < count; i++)
        if (jobs[i].minutesNeeded > OPEN_MINUTES_PER_DAY) {{
            jobs[i].isRejected = 1; ev(jobs[i].submittedAt, "rejected", jobs[i].id);
        }}

    int currentJob = -1, deadline = -1, busy = 0, idleWaiting = 0, tooLate = 0, badPick = 0;
    int lastBadDay = -1, daysRun = 0, maxQueue = 0;
    for (int day = 0; day < PROBE_DAYS; day++) {{
        int dayStart = day * OPEN_MINUTES_PER_DAY, dayEnd = dayStart + OPEN_MINUTES_PER_DAY;
        daysRun = day + 1;
        for (int t = dayStart; t < dayEnd; t++) {{
            for (int i = 0; i < count; i++)
                if (abandonAt[i] == t && live(i) && jobs[i].submittedAt <= t) {{
                    jobs[i].isAbandoned = 1; ev(t, "abandoned", jobs[i].id);
                }}
            if (currentJob != -1 && jobs[currentJob].isAbandoned) {{
                ev(t, "freed", jobs[currentJob].id); currentJob = -1;
            }}
            if (currentJob != -1 && t >= deadline) {{
                jobs[currentJob].isFinished = 1; jobs[currentJob].finishedAt = t;
                ev(t, "finish", jobs[currentJob].id); currentJob = -1;
            }}
            if (currentJob == -1) {{
                int pick = {F}(jobs, count, t, dayEnd - t);
                if (pick != -1) {{
                    if (pick < 0 || pick >= count) {{
                        badPick++;
                        if (lastBadDay != day) {{ ev(t, "invalid_index", pick); lastBadDay = day; }}
                    }} else if (jobs[pick].submittedAt > t || !live(pick) || jobs[pick].startedAt != -1) {{
                        badPick++;
                        if (lastRefusedDay[pick] != day) {{ ev(t, "invalid_pick", jobs[pick].id); lastRefusedDay[pick] = day; }}
                    }} else if (t + jobs[pick].minutesNeeded > dayEnd) {{
                        tooLate++;
                        if (lastRefusedDay[pick] != day) {{ ev(t, "refused_too_late", jobs[pick].id); lastRefusedDay[pick] = day; }}
                    }} else {{
                        jobs[pick].startedAt = t; currentJob = pick;
                        deadline = t + jobs[pick].minutesNeeded;
                        ev(t, "start", jobs[pick].id);
                    }}
                }}
            }}
            int waiting = 0;
            for (int i = 0; i < count; i++)
                if (live(i) && jobs[i].startedAt == -1 && jobs[i].submittedAt <= t) waiting++;
            if (waiting > maxQueue) maxQueue = waiting;
            if (currentJob != -1) busy++; else if (waiting > 0) idleWaiting++;
        }}
        if (currentJob != -1) {{
            /* The harness never lets a job run past close; it was started
               only if it fit, so a running job here finished exactly at close. */
        }}
        int anyLive = 0;
        for (int i = 0; i < count; i++) if (live(i)) anyLive = 1;
        if (!anyLive) break;
    }}
    for (int i = 0; i < count; i++) {{
        const char *st = jobs[i].isFinished ? "finished" : jobs[i].isRejected ? "rejected"
                       : jobs[i].isAbandoned ? "abandoned" : jobs[i].startedAt != -1 ? "running"
                       : "never_started";
        printf("PROBE_JOB|%d|%d|%d|%d|%d|%s\\n", jobs[i].id, jobs[i].minutesNeeded,
               jobs[i].submittedAt, jobs[i].startedAt, jobs[i].finishedAt, st);
    }}
    printf("PROBE_STAT|%d|%d|%d|%d|%d|%d|%d|%d\\n", busy, daysRun * OPEN_MINUTES_PER_DAY,
           idleWaiting, tooLate, badPick, daysRun, events, maxQueue);
    printf("PROBE_DONE\\n");
    return 0;
}}
"""

    def parse(self, world, norm, stdout):
        meta = {j["id"]: j for j in norm["jobs"]}
        jobs, events, stat = [], [], {}
        for line in stdout.splitlines():
            parts = line.split("|")
            if parts[0] == "PROBE_JOB" and len(parts) == 7:
                jid = int(parts[1])
                start, fin = int(parts[4]), int(parts[5])
                sub = int(parts[3])
                m = meta.get(jid, {})
                jobs.append({
                    "id": jid, "minutes": int(parts[2]), "submitted_at": sub,
                    "started_at": None if start < 0 else start,
                    "finished_at": None if fin < 0 else fin,
                    "status": parts[6],
                    "wait": None if start < 0 else start - sub,
                    "abandon_at": None if m.get("abandon_at", -1) < 0 else m["abandon_at"],
                    "entry": m.get("entry"), "owner": m.get("owner"),
                })
            elif parts[0] == "PROBE_EVENT" and len(parts) == 4:
                events.append({"t": int(parts[1]), "kind": parts[2], "id": int(parts[3])})
            elif parts[0] == "PROBE_STAT" and len(parts) == 9:
                keys = ["busy_minutes", "open_minutes", "idle_while_waiting", "too_late_attempts",
                        "invalid_picks", "days_simulated", "event_count", "max_queue"]
                stat = dict(zip(keys, map(int, parts[1:])))
        p = world_params(world)
        return {
            "kind": "job_queue", "day_length": p["day_length"],
            "jobs": jobs, "events": events, "stats": stat,
            "events_truncated": bool(stat) and stat["event_count"] > len(events),
        }


# ---------------------------------------------------------------------------
# Pool leak: a fixed pool of slots checked out and released
# ---------------------------------------------------------------------------

class PoolProbeKit(ProbeKit):
    archetype_id = "pool_leak"
    MAX_OPS = 3000

    def describe(self, world):
        p = world_params(world)
        unit = p["domain"]["unit"]
        return {
            "kind": "pool",
            "pool_size": p["pool_size"],
            "unit": unit,
            "checkout_func": p["checkout_func"],
            "release_func": p["release_func"],
            "limits": {"ops": self.MAX_OPS},
            "help": (
                f"A list of operations run in order on an empty pool of {p['pool_size']} "
                f"{unit}s. 'checkout' and 'release' call the system for one holder id; "
                f"'cycle' does a checkout then a release for the same holder. Optional "
                f"'repeat' + 'step' expand one entry into many holders (holder, holder+step, …)."
            ),
            "template": {
                "ops": [
                    {"op": "checkout", "holder": 1},
                    {"op": "checkout", "holder": 2},
                    {"op": "release", "holder": 1},
                    {"op": "cycle", "holder": 100, "repeat": 3, "step": 1},
                ],
            },
        }

    def normalize(self, world, scenario):
        if not isinstance(scenario, dict):
            raise ProbeError("scenario must be an object with an 'ops' list")
        entries = scenario.get("ops")
        if not isinstance(entries, list) or not entries:
            raise ProbeError("'ops' must be a non-empty list")
        ops = []
        for n, e in enumerate(entries):
            if not isinstance(e, dict):
                raise ProbeError(f"ops[{n}] must be an object")
            kind = e.get("op")
            if kind not in ("checkout", "release", "cycle"):
                raise ProbeError(f"ops[{n}].op must be 'checkout', 'release' or 'cycle'")
            holder = _int(e.get("holder"), f"ops[{n}].holder", 0, 10_000_000)
            repeat = _int(e.get("repeat"), f"ops[{n}].repeat", 1, self.MAX_OPS, default=1)
            step = _int(e.get("step"), f"ops[{n}].step", 0, 100_000, default=0)
            owner = e.get("owner") if isinstance(e.get("owner"), str) else None
            for k in range(repeat):
                h = holder + k * step
                seq = ["checkout", "release"] if kind == "cycle" else [kind]
                for op in seq:
                    ops.append({"op": op, "holder": h, "entry": n, "owner": owner})
                if len(ops) > self.MAX_OPS:
                    raise ProbeError(f"at most {self.MAX_OPS} operations per experiment")
        return {"ops": ops}

    def harness(self, world, norm, event_cap):
        p = world_params(world)
        S, C, R, P = p["struct_name"], p["checkout_func"], p["release_func"], p["pool_size"]
        ops = norm["ops"]
        table = ", ".join(f"{{{0 if o['op'] == 'checkout' else 1}, {o['holder']}}}" for o in ops)
        return f"""
#include <stdio.h>
#include <string.h>
#define POOL_SIZE {P}
#define EVENT_CAP {event_cap}

static struct {S} pool[POOL_SIZE];
static const int ops[{len(ops)}][2] = {{ {table} }};

static int inUseCount(void) {{
    int c = 0; for (int i = 0; i < POOL_SIZE; i++) if (pool[i].inUse) c++; return c;
}}

int main(void) {{
    memset(pool, 0, sizeof(pool));
    int ledger = 0, printed = 0;
    for (int k = 0; k < {len(ops)}; k++) {{
        int r;
        if (ops[k][0] == 0) {{ r = {C}(pool, POOL_SIZE, ops[k][1]); if (r != -1) ledger++; }}
        else {{ r = {R}(pool, POOL_SIZE, ops[k][1]); if (r) ledger--; }}
        if (printed < EVENT_CAP) {{
            printf("PROBE_OP|%d|%d|%d|%d|%d|%d\\n", k, ops[k][0], ops[k][1], r, inUseCount(), ledger);
            printed++;
        }}
    }}
    for (int i = 0; i < POOL_SIZE; i++)
        printf("PROBE_SLOT|%d|%d|%d\\n", i, pool[i].inUse ? 1 : 0, pool[i].holderId);
    printf("PROBE_STAT|%d|%d|%d|%d\\n", POOL_SIZE, inUseCount(), ledger, {len(ops)});
    printf("PROBE_DONE\\n");
    return 0;
}}
"""

    def parse(self, world, norm, stdout):
        p = world_params(world)
        meta = norm["ops"]
        ops, slots, stat = [], [], {}
        for line in stdout.splitlines():
            parts = line.split("|")
            if parts[0] == "PROBE_OP" and len(parts) == 7:
                k = int(parts[1])
                kind = "checkout" if parts[2] == "0" else "release"
                ret = int(parts[4])
                if kind == "checkout":
                    outcome = "denied" if ret == -1 else ("got_slot" if 0 <= ret < p["pool_size"] else "invalid_slot")
                else:
                    outcome = "accepted" if ret else "refused"
                ops.append({
                    "k": k, "op": kind, "holder": int(parts[3]), "returned": ret,
                    "outcome": outcome, "in_use": int(parts[5]), "ledger": int(parts[6]),
                    "entry": meta[k]["entry"] if k < len(meta) else None,
                    "owner": meta[k]["owner"] if k < len(meta) else None,
                })
            elif parts[0] == "PROBE_SLOT" and len(parts) == 4:
                slots.append({"slot": int(parts[1]), "in_use": parts[2] == "1", "holder": int(parts[3])})
            elif parts[0] == "PROBE_STAT" and len(parts) == 5:
                stat = {"pool_size": int(parts[1]), "in_use": int(parts[2]),
                        "ledger": int(parts[3]), "op_count": int(parts[4])}
        return {
            "kind": "pool", "pool_size": p["pool_size"], "ops": ops, "slots": slots,
            "stats": stat, "ops_truncated": bool(stat) and stat["op_count"] > len(ops),
        }


PROBE_KITS: dict[str, ProbeKit] = {
    k.archetype_id: k for k in (StarvationProbeKit(), PoolProbeKit())
}


def probe_kit(world: GeneratedWorld) -> ProbeKit:
    kit = PROBE_KITS.get(world.archetype_id)
    if kit is None:
        raise ProbeError(f"No probe lab for archetype '{world.archetype_id}' yet")
    return kit

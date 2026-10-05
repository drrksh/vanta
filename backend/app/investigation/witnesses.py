"""
Execution-grounded witnesses.

The old VANTA had LLM characters with written backstories, and contestants
ended up arguing with them in Discord: the bots held "facts" the author had
typed in, so the game turned into getting a bot to concede. This layer
replaces that.

A witness here holds no facts. Each one is a vantage point on the system:
someone who uses it in a particular way. When a world is created, VANTA
builds a busy period of real usage for the cast (a week of jobs, or a day
of checkouts and returns), compiles the system, and runs it. Every witness
then lived through that one execution and can only report what was visible
from where they stood: their own jobs, what was on the shelf when they
looked, what the desk's books said. Nothing is authored. Ask the same
question twice and you get the same answer, because the system did the same
thing. Witnesses never speculate about the code and never argue; a question
outside what they saw gets "I don't know, I wasn't there", not a debate.

A contestant can also ask a witness to live the same period again under the
contestant's own code. The witness then reports how their experience
changed, including when a fix makes things worse for them, which is how
trade-offs between correct designs become visible.
"""
from __future__ import annotations

import hashlib
import random
import re
from collections import OrderedDict
from dataclasses import dataclass, field

from app.execution.c_sandbox import CSandbox
from app.investigation.probes import (
    PoolProbeKit, ProbeOutcome, StarvationProbeKit, world_params,
)
from app.worldgen.archetype import GeneratedWorld

_NAMES = [
    "Priya", "Arjun", "Meera", "Kabir", "Ananya", "Rohan", "Zara", "Vikram", "Isha",
    "Dev", "Nisha", "Farhan", "Leela", "Sam", "Tara", "Omar", "Aditi", "Neil", "Ritika",
    "Joel", "Sana", "Karthik", "Maya", "Imran",
]

_DEFLECT = re.compile(
    r"\b(fix|solution|solve|code|bug|algorithm|implement|should (you|i|we)|how (do|to|would)|"
    r"what('?s| is) wrong|root cause|why does|why is|patch)\b", re.I,
)


@dataclass
class Topic:
    key: str
    question: str
    keywords: tuple[str, ...]


@dataclass
class WitnessSpec:
    key: str
    name: str
    role: str
    vantage: str
    topics: list[Topic]


@dataclass
class Answer:
    topic: str
    text: str
    evidence: dict | None = None   # {"columns": [...], "rows": [[...]]}


@dataclass
class Cast:
    witnesses: list[WitnessSpec]
    scenario: dict
    context: dict = field(default_factory=dict)


class _TraceCache:
    """Memoized executions. Caching the *result of running code* is not a
    fact store -- it's just not compiling the same thing twice."""

    def __init__(self, size: int = 96):
        self.size = size
        self._d: OrderedDict[str, ProbeOutcome] = OrderedDict()

    def get(self, key):
        if key in self._d:
            self._d.move_to_end(key)
            return self._d[key]
        return None

    def put(self, key, value):
        self._d[key] = value
        self._d.move_to_end(key)
        while len(self._d) > self.size:
            self._d.popitem(last=False)


_cache = _TraceCache()


def _route(question: str, topics: list[Topic]) -> str | None:
    q = question.lower()
    best, best_hits = None, 0
    for t in topics:
        hits = sum(1 for kw in t.keywords if kw in q)
        if hits > best_hits:
            best, best_hits = t.key, hits
    return best


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


class WitnessKit:
    archetype_id: str
    probe = None

    def cast(self, world: GeneratedWorld) -> Cast:
        raise NotImplementedError

    def answer(self, world, cast, witness: WitnessSpec, topic: str, trace: dict) -> Answer:
        raise NotImplementedError

    def rng(self, world, salt: str) -> random.Random:
        return random.Random(f"witness:{world.archetype_id}:{world.seed}:{salt}")

    def pick_names(self, world, n: int) -> list[str]:
        return self.rng(world, "names").sample(_NAMES, n)

    async def lived_period(self, world, cast: Cast, source: str, sandbox: CSandbox,
                           cache_key: str) -> ProbeOutcome:
        digest = hashlib.sha256(source.encode()).hexdigest()[:16]
        key = f"{cache_key}:{digest}"
        hit = _cache.get(key)
        if hit is not None:
            return hit
        norm = self.probe.normalize(world, cast.scenario)
        out = await self.probe.run(world, cast.scenario, source, sandbox,
                                   event_cap=8000, normalized=norm)
        _cache.put(key, out)
        return out

    async def ask(
        self, world: GeneratedWorld, cache_key: str, witness_key: str, sandbox: CSandbox,
        question: str | None = None, topic: str | None = None, source: str | None = None,
    ) -> dict:
        cast = self.cast(world)
        w = next((x for x in cast.witnesses if x.key == witness_key), None)
        if w is None:
            raise KeyError(witness_key)
        topic_keys = {t.key for t in w.topics}

        if topic is None and question:
            if _DEFLECT.search(question):
                return {
                    "witness": w.key, "topic": "deflect",
                    "text": self.deflection(world, w),
                    "followups": [t.question for t in w.topics],
                }
            topic = _route(question, w.topics)
        if topic is None or topic not in topic_keys:
            return {
                "witness": w.key, "topic": "unknown",
                "text": (f"I'm not sure what you're asking. I can only tell you what I saw "
                         f"myself. Ask me something like: \"{w.topics[0].question}\""),
                "followups": [t.question for t in w.topics],
            }

        original = await self.lived_period(world, cast, world.starter_source, sandbox, cache_key)
        if not original.ok:
            return {"witness": w.key, "topic": topic, "error": original.error,
                    "text": "Something went badly wrong with the system that week -- it crashed.",
                    "detail": original.detail}
        base = self.answer(world, cast, w, topic, original.trace)
        result = {
            "witness": w.key, "topic": topic, "text": base.text, "evidence": base.evidence,
            "followups": [t.question for t in w.topics if t.key != topic],
        }
        if source is not None and source.strip() != world.starter_source.strip():
            replay = await self.lived_period(world, cast, source, sandbox, cache_key)
            if not replay.ok:
                result["replay"] = {
                    "error": replay.error, "detail": replay.detail,
                    "text": ("I tried to live that week again with your version, but the system "
                             + ("wouldn't even build." if replay.error == "compile_error"
                                else "crashed partway through." if replay.error == "runtime_error"
                                else "never finished."))
                }
            else:
                again = self.answer(world, cast, w, topic, replay.trace)
                result["replay"] = {"text": again.text, "evidence": again.evidence}
        return result

    def deflection(self, world, w: WitnessSpec) -> str:
        return (f"I couldn't tell you how it works inside -- I'm not the one who wrote it. "
                f"I can tell you what happened to me, and you can work out why.")

    def public(self, world: GeneratedWorld) -> list[dict]:
        return [
            {"key": w.key, "name": w.name, "role": w.role, "vantage": w.vantage,
             "questions": [{"topic": t.key, "question": t.question} for t in w.topics]}
            for w in self.cast(world).witnesses
        ]


# ---------------------------------------------------------------------------
# Starvation / fairness witnesses
# ---------------------------------------------------------------------------

_USER_TOPICS = [
    Topic("story", "What happened to your jobs that week?",
          ("happen", "story", "week", "experience", "tell me", "went", "your job", "submitted")),
    Topic("worst", "What was the worst wait you had?",
          ("worst", "longest", "never", "wait", "long", "slow", "stuck", "delay")),
    Topic("timing", "When in the day did your jobs actually start?",
          ("when", "time", "start", "morning", "evening", "day", "hour", "opening")),
    Topic("machine", "What was the machine doing while you waited?",
          ("machine", "doing", "running", "busy", "others", "who", "idle", "else", "instead")),
]
_OPERATOR_TOPICS = [
    Topic("utilization", "How busy was the machine that week?",
          ("busy", "utili", "use", "idle", "how much", "running")),
    Topic("refusals", "Did the system ever refuse to start something?",
          ("refus", "reject", "won't", "wouldn't", "error", "start", "invalid", "fail")),
    Topic("queue", "How long did the queue get, and who was in it?",
          ("queue", "line", "waiting", "backlog", "pile", "who", "longest")),
    Topic("closing", "What happens around closing time?",
          ("clos", "end of", "evening", "late", "night", "last")),
]


class StarvationWitnessKit(WitnessKit):
    archetype_id = "starvation_fairness"
    probe = StarvationProbeKit()

    def cast(self, world):
        p = world_params(world)
        L, s, B = p["day_length"], p["small_job_minutes"], p["big_job_minutes"]
        noun, machine = p["domain"]["noun"], p["domain"]["machine"]
        rng = self.rng(world, "load")
        names = self.pick_names(world, 5)
        days = 7

        # The regular floods the first ~60% of each day with short jobs at a
        # rate that roughly saturates the machine, then stops.
        every = max(1, s - 1)
        burst = int(L * rng.uniform(0.5, 0.65))
        per_day = max(1, min(90, burst // every))
        jobs = []
        for d in range(days - 1):
            jobs.append({"minutes": s, "at": d * L, "repeat": per_day, "every": every,
                         "owner": "regular"})
        # One long job, submitted early on day one, into the stream.
        jobs.append({"minutes": B, "at": rng.randint(15, 60), "owner": "big"})
        # Medium jobs around midday on three days.
        mid = max(s + 5, int(L * rng.uniform(0.1, 0.18)))
        for d in (0, 2, 4):
            jobs.append({"minutes": mid, "at": d * L + int(L * rng.uniform(0.35, 0.5)),
                         "owner": "midday"})
        # Someone who drops off a moderate job shortly before closing.
        late_len = max(s + 10, int(L * rng.uniform(0.2, 0.3)))
        for d in (0, 3):
            jobs.append({"minutes": late_len, "at": d * L + L - int(L * rng.uniform(0.08, 0.15)),
                         "owner": "late"})

        witnesses = [
            WitnessSpec("regular", names[0], f"Submits short {noun}s all morning, most days",
                        f"Sees only their own {noun}s and when each one came back.", _USER_TOPICS),
            WitnessSpec("big", names[1], f"Needed one long {noun} done this week",
                        f"Submitted a single large {noun} and watched it.", _USER_TOPICS),
            WitnessSpec("midday", names[2], f"Drops off a medium {noun} around lunch, now and then",
                        f"Sees their own few {noun}s.", _USER_TOPICS),
            WitnessSpec("late", names[3], f"Usually submits a {noun} just before closing",
                        f"Sees their own {noun}s, mostly around closing time.", _USER_TOPICS),
            WitnessSpec("operator", names[4], f"Opens and closes the {machine} every day",
                        f"Reads the {machine}'s log: what ran, what waited, what it refused.",
                        _OPERATOR_TOPICS),
        ]
        return Cast(witnesses, {"days": days, "jobs": jobs},
                    {"names": {w.key: w.name for w in witnesses}, "L": L, "noun": noun,
                     "machine": machine})

    # --- time formatting -------------------------------------------------
    @staticmethod
    def _clock(t: int, L: int) -> str:
        d, m = divmod(t, L)
        hh, mm = divmod(8 * 60 + m, 60)
        return f"day {d + 1}, {hh:02d}:{mm:02d}"

    @staticmethod
    def _adj(m: int) -> str:
        if m < 60:
            return f"{m}-minute"
        h, mm = divmod(m, 60)
        return f"{h} h {mm:02d} min"

    @staticmethod
    def _dur(m: int, L: int) -> str:
        if m < 60:
            return _plural(m, "minute")
        if m < L:
            h, mm = divmod(m, 60)
            return f"{h} h {mm:02d} min"
        return f"about {m / L:.1f} working days"

    def answer(self, world, cast, w, topic, trace):
        L = trace["day_length"]
        ctx = cast.context
        if w.key == "operator":
            return self._operator(topic, trace, ctx)
        mine = [j for j in trace["jobs"] if j["owner"] == w.key]
        noun = ctx["noun"]
        end_t = trace["stats"]["days_simulated"] * L
        clock = lambda t: self._clock(t, L)  # noqa: E731
        dur = lambda m: self._dur(m, L)  # noqa: E731

        def ev_rows(jobs):
            rows = []
            for j in jobs[:30]:
                rows.append([
                    f"#{j['id']}", dur(j["minutes"]), clock(j["submitted_at"]),
                    clock(j["started_at"]) if j["started_at"] is not None else "—",
                    dur(j["wait"]) if j["wait"] is not None else f"> {dur(end_t - j['submitted_at'])}",
                    j["status"].replace("_", " "),
                ])
            return {"columns": [noun, "length", "submitted", "started", "waited", "status"],
                    "rows": rows, "total": len(jobs)}

        never = [j for j in mine if j["status"] == "never_started"]
        done = [j for j in mine if j["status"] == "finished"]
        rejected = [j for j in mine if j["status"] == "rejected"]
        waits = sorted(j["wait"] for j in mine if j["wait"] is not None)

        adj = self._adj
        if topic == "story":
            parts = [f"I submitted {_plural(len(mine), noun)} that week."]
            if len(mine) == 1 and done:
                wt = done[0]["wait"]
                parts.append(f"It started {dur(wt)} after I handed it in and finished fine." if wt < 60
                             else f"It finished, but only after waiting {dur(wt)} to start.")
            elif done:
                med = waits[len(waits) // 2] if waits else 0
                parts.append(f"{len(done)} finished; a typical one waited {dur(med)} before it started.")
            if never:
                j = never[0]
                parts.append(
                    f"{'One' if len(never) == 1 else len(never)} never started at all"
                    + (f" -- the one I handed in at {clock(j['submitted_at'])} was still sitting "
                       f"there when the records end." if len(never) == 1 else ".")
                )
            if rejected:
                parts.append(f"{len(rejected)} got turned away outright as too long for a day.")
            return Answer("story", " ".join(parts), ev_rows(mine))

        if topic == "worst":
            if not mine:
                return Answer("worst", "I didn't submit anything that week.")
            if never:
                j = never[0]
                return Answer("worst", (
                    f"The {adj(j['minutes'])} {noun} I submitted at {clock(j['submitted_at'])}. "
                    f"It never started. I checked until the end of the records "
                    f"({clock(end_t - 1)}), so that's more than {dur(end_t - j['submitted_at'])} "
                    f"of waiting."), ev_rows(never))
            j = max((x for x in mine if x["wait"] is not None), key=lambda x: x["wait"])
            return Answer("worst", (
                f"The worst was the {adj(j['minutes'])} one from {clock(j['submitted_at'])}: "
                f"it started at {clock(j['started_at'])}, so I waited {dur(j['wait'])}."),
                ev_rows([j]))

        if topic == "timing":
            started = [j for j in mine if j["started_at"] is not None]
            if not started:
                return Answer("timing", f"None of my {noun}s ever started, so I can't tell you.")
            offs = [j["started_at"] % L for j in started]
            first_hour = sum(1 for o in offs if o < 60)
            last_part = sum(1 for o in offs if o >= L * 0.75)
            same_day = sum(1 for j in started if j["started_at"] // L == j["submitted_at"] // L)
            if len(started) == 1:
                j = started[0]
                txt = (f"My {noun} started at {clock(j['started_at'])}"
                       + (", the same day I handed it in. " if same_day else
                          f" -- I'd handed it in on day {j['submitted_at'] // L + 1}. "))
            else:
                n = len(started)
                if same_day == n:
                    txt = f"All {n} of my {noun}s started on the day I handed them in. "
                elif same_day == 0:
                    txt = f"None of my {n} {noun}s started on the day I handed them in. "
                else:
                    txt = (f"{same_day} of my {n} {noun}s started on the day I handed them in; "
                           f"{n - same_day} had to wait for a later day. ")
            if len(started) > 1:
                if first_hour == len(started):
                    txt += "Every one of them started in the first hour after opening."
                elif first_hour:
                    txt += f"{first_hour} started in the first hour after opening."
                if last_part:
                    txt += f" {last_part} only got going in the last quarter of the day."
            return Answer("timing", txt.strip(), ev_rows(started))

        if topic == "machine":
            target = never[0] if never else (
                max((x for x in mine if x["wait"] is not None), key=lambda x: x["wait"], default=None))
            if target is None or (target["wait"] is not None and target["wait"] < 5):
                return Answer("machine", f"I barely waited, so I didn't really notice.")
            a = target["submitted_at"]
            b = target["started_at"] if target["started_at"] is not None else end_t
            runs = self._runs(trace)
            by_id = {j["id"]: j for j in trace["jobs"]}
            busy = {"shorter": 0, "same": 0, "longer": 0}
            owners: dict[str, int] = {}
            covered = 0
            for (jid, s0, s1) in runs:
                lo, hi = max(a, s0), min(b, s1)
                if hi <= lo:
                    continue
                covered += hi - lo
                j = by_id[jid]
                cat = ("shorter" if j["minutes"] < target["minutes"] else
                       "same" if j["minutes"] == target["minutes"] else "longer")
                busy[cat] += hi - lo
                o = j["owner"] or "someone"
                owners[o] = owners.get(o, 0) + (hi - lo)
            # Only open hours count: the window is in simulated open minutes already.
            idle = max(0, (b - a) - covered)
            top = sorted(owners.items(), key=lambda kv: -kv[1])[:2]
            who = " and ".join(
                "my own" if o == w.key else f"{ctx['names'].get(o, 'someone')}'s" for o, _ in top)
            span = b - a
            bits = []
            for cat, label in (("shorter", "shorter than mine"), ("same", "the same size as mine"),
                               ("longer", "longer than mine")):
                if busy[cat] and round(100 * busy[cat] / span) > 0:
                    bits.append(f"something {label} {self._pct(busy[cat], span)} of the time")
            if idle and round(100 * idle / span) > 0:
                bits.append(f"nothing at all {self._pct(idle, span)} of the time")
            txt = (f"While my {adj(target['minutes'])} {noun} waited "
                   f"({dur(span)}), the {ctx['machine']} was running " + ", ".join(bits) + ".")
            if who:
                txt += f" Mostly {who} {noun}s."
            return Answer("machine", txt)
        return Answer(topic, "I don't know.")

    @staticmethod
    def _pct(x, total):
        return f"{round(100 * x / total)}%" if total > 0 else "0%"

    @staticmethod
    def _runs(trace):
        started = {}
        runs = []
        for e in trace["events"]:
            if e["kind"] == "start":
                started[e["id"]] = e["t"]
            elif e["kind"] in ("finish", "freed") and e["id"] in started:
                runs.append((e["id"], started.pop(e["id"]), e["t"]))
        return runs

    def _operator(self, topic, trace, ctx):
        L, st = trace["day_length"], trace["stats"]
        machine, noun = ctx["machine"], ctx["noun"]
        clock = lambda t: self._clock(t, L)  # noqa: E731
        if topic == "utilization":
            return Answer("utilization", (
                f"Over {st['days_simulated']} days the {machine} was running "
                f"{self._pct(st['busy_minutes'], st['open_minutes'])} of open hours. It sat idle for "
                f"{self._dur(st['idle_while_waiting'], L)} while at least one {noun} was waiting "
                f"and could have been started."),
                {"columns": ["measure", "value"], "rows": [
                    ["open minutes", st["open_minutes"]], ["busy minutes", st["busy_minutes"]],
                    ["idle while something waited", st["idle_while_waiting"]],
                ]})
        if topic == "refusals":
            ref = [e for e in trace["events"] if e["kind"] in ("refused_too_late", "invalid_pick",
                                                                "invalid_index", "rejected")]
            if not ref:
                return Answer("refusals", "No. Everything the scheduler picked, the "
                              f"{machine} started.")
            late = [e for e in ref if e["kind"] == "refused_too_late"]
            bad = [e for e in ref if e["kind"] in ("invalid_pick", "invalid_index")]
            rej = [e for e in ref if e["kind"] == "rejected"]
            parts = []
            if late:
                parts.append(
                    f"Yes. On {_plural(len({e['t'] // L for e in late}), 'day')}, the scheduler kept "
                    f"choosing a {noun} that couldn't finish before closing. The {machine} won't start "
                    f"those, so it just sat there -- {st['too_late_attempts']} minutes lost that way.")
            if bad:
                parts.append(f"It also picked something it shouldn't have "
                             f"{_plural(st['invalid_picks'], 'time')}.")
            if rej:
                parts.append(f"{len(rej)} {noun}(s) were turned away up front as longer than a day.")
            by_id = {j["id"]: j for j in trace["jobs"]}
            rows = [[clock(e["t"]), e["kind"].replace("_", " "), f"#{e['id']}",
                     ctx["names"].get((by_id.get(e["id"]) or {}).get("owner"), "—")]
                    for e in ref[:25]]
            return Answer("refusals", " ".join(parts),
                          {"columns": ["when", "what", noun, "whose"], "rows": rows,
                           "total": len(ref)})
        if topic == "queue":
            waiting = [j for j in trace["jobs"] if j["status"] == "never_started"]
            owners: dict[str, int] = {}
            for j in waiting:
                owners[j["owner"]] = owners.get(j["owner"], 0) + 1
            txt = f"At its worst there were {st['max_queue']} {noun}s waiting at once."
            if waiting:
                oldest = min(waiting, key=lambda j: j["submitted_at"])
                txt += (f" When the records end, {len(waiting)} still hadn't started. The oldest "
                        f"was handed in at {clock(oldest['submitted_at'])} by "
                        f"{ctx['names'].get(oldest['owner'], 'someone')}.")
            else:
                txt += " By the end of the week everything had been started."
            rows = [[ctx["names"].get(o, "someone"), n] for o, n in owners.items()]
            return Answer("queue", txt, {"columns": ["whose", "never started"], "rows": rows}
                          if rows else None)
        if topic == "closing":
            runs = self._runs(trace)
            idle_close = 0
            window = max(30, L // 6)
            busy_close = 0
            for d in range(st["days_simulated"]):
                lo, hi = d * L + L - window, d * L + L
                for (_, s0, s1) in runs:
                    busy_close += max(0, min(hi, s1) - max(lo, s0))
            total = window * st["days_simulated"]
            idle_close = total - busy_close
            late = [e for e in trace["events"] if e["kind"] == "refused_too_late"]
            txt = (f"In the last {window} minutes before closing, the {machine} was busy "
                   f"{self._pct(busy_close, total)} of the time across the week.")
            if late:
                txt += (f" A few times near the end of the day it tried to start something that "
                        f"was never going to finish in time, and just stalled.")
            else:
                txt += " I never saw it try to start something too long for the time left."
            return Answer("closing", txt)
        return Answer(topic, "I don't know.")


# ---------------------------------------------------------------------------
# Pool leak witnesses
# ---------------------------------------------------------------------------

class PoolWitnessKit(WitnessKit):
    archetype_id = "pool_leak"
    probe = PoolProbeKit()

    def cast(self, world):
        p = world_params(world)
        P, unit, place = p["pool_size"], p["domain"]["unit"], p["domain"]["place"]
        rng = self.rng(world, "load")
        names = self.pick_names(world, 5)
        ids = rng.sample(range(1000, 9999), 200)
        nxt = iter(ids)

        bg = max(2, P - 4)
        bg_ids = [next(nxt) for _ in range(bg)]
        actors: dict[str, list[dict]] = {}
        # Morning: most units go out to people who hold them all day.
        morning = [{"op": "checkout", "holder": h, "owner": "background"} for h in bg_ids]
        # The regular borrows and returns repeatedly.
        reg_id = next(nxt)
        actors["regular"] = []
        for _ in range(rng.randint(6, 9)):
            actors["regular"] += [{"op": "checkout", "holder": reg_id, "owner": "regular"},
                                  {"op": "release", "holder": reg_id, "owner": "regular"}]
        # The desk processes some background returns, sometimes scanning twice,
        # and once scans something that was never checked out.
        r = max(1, bg // 4)
        returning = rng.sample(bg_ids, min(bg, 2 * r))
        actors["staff"] = []
        for i, h in enumerate(returning):
            actors["staff"].append({"op": "release", "holder": h, "owner": "staff"})
            if i % 2 == 0:
                actors["staff"].append({"op": "release", "holder": h, "owner": "staff"})
        actors["staff"].insert(rng.randint(0, len(actors["staff"])),
                               {"op": "release", "holder": next(nxt), "owner": "staff"})
        # Someone who asks for a second unit while still holding the first.
        actors["double"] = []
        for _ in range(2):
            g = next(nxt)
            actors["double"] += [{"op": "checkout", "holder": g, "owner": "double"},
                                 {"op": "checkout", "holder": g, "owner": "double"},
                                 {"op": "release", "holder": g, "owner": "double"}]
        # Merge actor timelines, preserving each actor's own order.
        middle = []
        queues = {k: list(v) for k, v in actors.items()}
        while any(queues.values()):
            live = [k for k, v in queues.items() if v]
            k = rng.choices(live, weights=[len(queues[x]) for x in live])[0]
            middle.append(queues[k].pop(0))
        # Late in the day, newcomers try to borrow.
        evening = [{"op": "checkout", "holder": next(nxt), "owner": "newcomer"}
                   for _ in range(4)]
        ops = morning + middle + evening

        witnesses = [
            WitnessSpec("regular", names[0], f"Borrows a {unit} and brings it back, many times a day",
                        f"Sees what the system told them each time they borrowed or returned.",
                        [Topic("story", "How did borrowing go for you today?",
                               ("happen", "today", "go", "borrow", "experience", "story")),
                         Topic("denied", "Were you ever told there was nothing available?",
                               ("full", "denied", "nothing", "available", "refuse", "no ")),
                         Topic("returns", "Did your returns go through?",
                               ("return", "back", "give", "release"))]),
            WitnessSpec("staff", names[1], f"Works the returns desk at {place}",
                        "Scans returned items. Sees what the system said for each scan.",
                        [Topic("story", "How did the returns desk go today?",
                               ("happen", "today", "desk", "story", "go")),
                         Topic("double", "What happens if you scan the same return twice?",
                               ("twice", "double", "again", "same", "duplicate")),
                         Topic("unknown", "Did anything strange get scanned?",
                               ("strange", "unknown", "never", "wrong", "weird", "odd"))]),
            WitnessSpec("double", names[2], f"Their borrowing app sometimes freezes and sends a request twice",
                        f"Knows what they physically received and what the app showed them.",
                        [Topic("story", "What happened when your request went through twice?",
                               ("twice", "second", "freeze", "froze", "two", "duplicate", "happen", "story")),
                         Topic("returns", "What happened when you returned?",
                               ("return", "back", "give", "release"))]),
            WitnessSpec("newcomer", names[3], f"Came in late in the day to borrow a {unit}",
                        f"Could see the shelf: how many {unit}s were physically there.",
                        [Topic("story", "What happened when you tried to borrow?",
                               ("happen", "borrow", "try", "story", "go")),
                         Topic("shelf", "What did the shelf look like at the time?",
                               ("shelf", "see", "physical", "empty", "there", "look"))]),
            WitnessSpec("auditor", names[4], "Reconciles the books at the end of the day",
                        "Compares three things: the desk's receipts, what the system thinks is "
                        "in use, and what's physically out with people.",
                        [Topic("reconcile", "Do the books match reality?",
                               ("book", "match", "reconcil", "count", "ledger", "number", "audit")),
                         Topic("first", "When did the numbers first stop agreeing?",
                               ("first", "when", "start", "diverge", "begin", "earliest")),
                         Topic("stock", "What does the end-of-day stock check show?",
                               ("stock", "end", "final", "slot", "table", "who holds", "check"))]),
        ]
        return Cast(witnesses, {"ops": ops},
                    {"names": {w.key: w.name for w in witnesses}, "unit": unit, "P": P})

    @staticmethod
    def _physical(trace):
        """The world's ground reality, derived from what people DID rather than
        what the system recorded. A person is handed an item when the system
        grants their checkout and they don't already have one in hand (a
        duplicate request from a frozen app doesn't put a second item in
        their hand). Whenever they go to return, they hand one item back,
        whatever the system says about it."""
        holds: dict[int, int] = {}
        out = 0
        series, held_before = [], []
        P = trace["pool_size"]
        for o in trace["ops"]:
            h = o["holder"]
            held_before.append(holds.get(h, 0))
            if o["op"] == "checkout" and 0 <= o["returned"] < P and holds.get(h, 0) == 0:
                holds[h] = 1
                out += 1
            elif o["op"] == "release" and holds.get(h, 0) > 0:
                holds[h] -= 1
                out -= 1
            series.append(out)
        return series, holds, held_before

    def answer(self, world, cast, w, topic, trace):
        ctx = cast.context
        unit, P = ctx["unit"], ctx["P"]
        ops = trace["ops"]
        mine = [o for o in ops if o["owner"] == w.key]
        physical, holds, held_before = self._physical(trace)

        def rows(sel):
            return {"columns": ["transaction", "action", "holder", "system said"],
                    "rows": [[f"#{o['k'] + 1}", o["op"], o["holder"],
                              self._said(o)] for o in sel[:30]], "total": len(sel)}

        if w.key == "regular":
            co = [o for o in mine if o["op"] == "checkout"]
            rel = [o for o in mine if o["op"] == "release"]
            got = sum(1 for o in co if o["outcome"] == "got_slot")
            if topic == "story":
                return Answer("story", (
                    f"I tried to borrow {_plural(len(co), 'time')} and got a {unit} {got} of those. "
                    f"I went to return {_plural(len(rel), 'time')}; the system accepted "
                    f"{sum(1 for o in rel if o['outcome'] == 'accepted')}."), rows(mine))
            if topic == "denied":
                den = [o for o in co if o["outcome"] == "denied"]
                if not den:
                    return Answer("denied", "No, I always got one.")
                o = den[0]
                free = P - physical[o["k"]]
                empty_handed = held_before[o["k"]] == 0
                return Answer("denied", (
                    f"Yes, {_plural(len(den), 'time')}. The first was transaction #{o['k'] + 1}. "
                    + ("I'd handed back everything I had by then. " if empty_handed else
                       f"I did still have one {unit} at that point. ")
                    + f"From what I could see, {free} {unit}s were actually free."), rows(den))
            if topic == "returns":
                bad = [o for o in rel if o["outcome"] != "accepted"]
                if not bad:
                    return Answer("returns", "Yes, every return I made was accepted.")
                return Answer("returns", (
                    f"Not always. {_plural(len(bad), 'return')} of mine came back as not accepted, "
                    f"even though I'd only borrowed one at a time."), rows(bad))

        if w.key == "staff":
            if topic == "story":
                acc = sum(1 for o in mine if o["outcome"] == "accepted")
                return Answer("story", (
                    f"I scanned {_plural(len(mine), 'return')} today. The system accepted {acc} and "
                    f"refused {len(mine) - acc}."), rows(mine))
            if topic == "double":
                seen, pairs = set(), []
                for o in mine:
                    if o["holder"] in seen:
                        pairs.append(o)
                    seen.add(o["holder"])
                if not pairs:
                    return Answer("double", "I didn't scan anything twice today.")
                acc = sum(1 for o in pairs if o["outcome"] == "accepted")
                return Answer("double", (
                    f"I did it {_plural(len(pairs), 'time')} by accident today. The second scan was "
                    + ("refused every time." if acc == 0 else
                       "accepted every time, as if a second item had come back." if acc == len(pairs)
                       else f"accepted {acc} of those times.")), rows(pairs))
            if topic == "unknown":
                touched = {o["holder"] for o in ops if o["op"] == "checkout"}
                odd = [o for o in mine if o["holder"] not in touched]
                if not odd:
                    return Answer("unknown", "No, everything I scanned had been borrowed.")
                o = odd[0]
                return Answer("unknown", (
                    f"Once, transaction #{o['k'] + 1}: I scanned holder {o['holder']}, who had never "
                    f"borrowed anything. The system {self._said(o)}."), rows(odd))

        if w.key == "double":
            if topic == "story":
                dupes = [o for o in mine if o["op"] == "checkout" and held_before[o["k"]] > 0]
                given = sum(1 for o in dupes if o["outcome"] == "got_slot")
                return Answer("story", (
                    f"The app froze on me {_plural(len(dupes), 'time')} and my borrow request went "
                    f"through twice. I only ever actually had one {unit}. "
                    + ("Each time, the system refused the duplicate." if given == 0 else
                       f"{'Both times' if given == len(dupes) == 2 else f'{given} time(s)'} the "
                       f"system said yes to the duplicate too and gave me a second slot number.")),
                    rows(mine))
            if topic == "returns":
                rel = [o for o in mine if o["op"] == "release"]
                return Answer("returns", (
                    f"I went to return {_plural(len(rel), 'time')}, bringing back the one {unit} I had "
                    f"each time. The system: " + ", ".join(self._said(o) for o in rel) + "."),
                    rows(rel))

        if w.key == "newcomer":
            if topic == "story":
                got = sum(1 for o in mine if o["outcome"] == "got_slot")
                return Answer("story", (
                    f"We were {len(mine)} people trying to borrow at the end of the day. "
                    f"{got} of us got one."), rows(mine))
            if topic == "shelf":
                lines = []
                for o in mine:
                    free = P - physical[o["k"]]
                    lines.append([f"#{o['k'] + 1}", free, self._said(o)])
                o = mine[0]
                return Answer("shelf", (
                    f"When I walked up there were {P - physical[o['k']]} {unit}s physically free "
                    f"out of {P}."),
                    {"columns": ["transaction", f"{unit}s physically free", "system said"],
                     "rows": lines})

        if w.key == "auditor":
            if topic == "reconcile":
                last = ops[-1]
                txt = (f"At close: the desk's receipts say {last['ledger']} out, the system marks "
                       f"{last['in_use']} as in use, and {physical[-1]} are physically out with people.")
                if last["ledger"] == last["in_use"] == physical[-1]:
                    txt += " All three agree."
                else:
                    txt += " They don't agree."
                return Answer("reconcile", txt, {
                    "columns": ["source", f"{unit}s out"],
                    "rows": [["desk receipts", last["ledger"]], ["system in use", last["in_use"]],
                             ["physically out", physical[-1]]]})
            if topic == "first":
                for o, phys in zip(ops, physical):
                    if not (o["ledger"] == o["in_use"] == phys):
                        return Answer("first", (
                            f"Transaction #{o['k'] + 1}: holder {o['holder']} went to {o['op']}, and "
                            f"the system {self._said(o)}. Right after it, receipts said "
                            f"{o['ledger']}, the system said {o['in_use']}, and {phys} were "
                            f"physically out."),
                            rows(ops[max(0, o["k"] - 3): o["k"] + 2]))
                return Answer("first", "They never disagreed today.")
            if topic == "stock":
                slots = trace["slots"]
                used = [s for s in slots if s["in_use"]]
                by_holder: dict[int, int] = {}
                for s in used:
                    by_holder[s["holder"]] = by_holder.get(s["holder"], 0) + 1
                ghost = [s for s in used if holds.get(s["holder"], 0) == 0]
                multi = [h for h, n in by_holder.items() if n > 1]
                txt = f"{len(used)} of {P} {unit}s are marked in use."
                if ghost:
                    txt += (f" {len(ghost)} of those are marked against people who, by my count of "
                            f"who was actually handed what, don't have anything.")
                if multi:
                    txt += f" {len(multi)} holder(s) are marked against more than one {unit}."
                if not ghost and not multi:
                    txt += " Every one matches someone who really has it."
                return Answer("stock", txt, {
                    "columns": [unit, "marked in use", "holder on record", "holder really has it"],
                    "rows": [[s["slot"], "yes" if s["in_use"] else "no",
                              s["holder"] if s["in_use"] else "—",
                              ("yes" if holds.get(s["holder"], 0) > 0 else "no") if s["in_use"] else "—"]
                             for s in slots]})
        return Answer(topic, "I don't know.")

    @staticmethod
    def _said(o) -> str:
        return {"got_slot": f"gave slot {o['returned']}", "denied": "said none available",
                "invalid_slot": f"returned a slot number that doesn't exist ({o['returned']})",
                "accepted": "accepted it", "refused": "refused it"}[o["outcome"]]


WITNESS_KITS: dict[str, WitnessKit] = {
    k.archetype_id: k for k in (StarvationWitnessKit(), PoolWitnessKit())
}


def witness_kit(world: GeneratedWorld) -> WitnessKit:
    kit = WITNESS_KITS.get(world.archetype_id)
    if kit is None:
        raise KeyError(world.archetype_id)
    return kit

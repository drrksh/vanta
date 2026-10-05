"""
Discord command logic, kept free of discord.py so it can be tested against
the real API without a Discord connection. Each command returns a Reply
that bot.py turns into Discord embeds and file attachments.

Design rule carried over from the web UI: nothing here starts a
back-and-forth with a bot. A witness question gets one answer computed from
a real run of the system; there is no conversation to win.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from discord_bot.vanta_api import VantaApi, VantaApiError

COLOR_STRUCTURE = 0x7FD1E8
COLOR_SIGNAL = 0xE8A33D
COLOR_ACCEPTED = 0x58C7A6
COLOR_REJECTED = 0xD4725E

DIFFICULTIES = {"gentle": 0.2, "standard": 0.45, "hard": 0.7, "brutal": 0.9}


@dataclass
class EmbedSpec:
    title: str
    description: str = ""
    color: int = COLOR_STRUCTURE
    fields: list[tuple[str, str, bool]] = field(default_factory=list)
    footer: str | None = None
    url: str | None = None


@dataclass
class Reply:
    content: str | None = None
    embeds: list[EmbedSpec] = field(default_factory=list)
    files: list[tuple[str, bytes]] = field(default_factory=list)
    ephemeral: bool = False


def _cut(text: str, n: int) -> str:
    text = text or ""
    return text if len(text) <= n else text[: n - 1] + "…"


def discord_user(user_id: int | str) -> str:
    return f"discord:{user_id}"


def difficulty_value(choice: str | None) -> float | None:
    """None / 'calibrated' = pitch it at this person's rating."""
    if not choice or choice == "calibrated":
        return None
    return DIFFICULTIES.get(choice, 0.45)


def extract_source(text: str) -> str:
    """Accept raw C or a ```c fenced block pasted into Discord."""
    m = re.search(r"```(?:c|C)?\s*\n(.*?)```", text, flags=re.S)
    return (m.group(1) if m else text).strip() + "\n"


class VantaCommands:
    def __init__(self, api: VantaApi, web_url: str | None = None):
        self.api = api
        self.web_url = (web_url or "").rstrip("/") or None

    def _world_link(self, world_id: str) -> str | None:
        return f"{self.web_url}/worlds/{world_id}" if self.web_url else None

    @staticmethod
    def _error(exc: VantaApiError) -> Reply:
        return Reply(content=f"⚠️ {exc.detail}", ephemeral=True)

    # --- worlds -----------------------------------------------------------
    def _world_reply(self, w: dict, headline: str | None = None) -> Reply:
        reqs = "\n".join(f"• {p}" for p in w["mandatory_properties"])
        e = EmbedSpec(
            title=_cut(w["title"], 250),
            description=_cut(w["briefing"], 1500),
            url=self._world_link(w["world_id"]),
            fields=[
                ("Your task", _cut(w["specification"], 1000), False),
                ("Signature", f"```c\n{_cut(w['function_signature'], 900)}\n```", False),
                ("Requirements — all must hold", _cut(reqs, 1020), False),
            ],
            footer=f"world {w['world_id']} · difficulty {w['target_difficulty']:.2f}"
                   + (f" · cohort {w['cohort']['code']}" if w.get("cohort") else ""),
        )
        if w.get("sample_input_description"):
            e.fields.append(("Scale", _cut(w["sample_input_description"], 1000), False))
        name = f"{w['function_name']}.c"
        return Reply(
            content=headline,
            embeds=[e],
            files=[(name, w["starter_source"].strip().encode() + b"\n")],
        )

    async def create(self, user: str, defect: str | None, difficulty: str | None) -> Reply:
        try:
            w = await self.api.create_world(user, difficulty_value(difficulty), defect or None)
        except VantaApiError as exc:
            return self._error(exc)
        how = "calibrated to your rating" if w.get("calibrated") else f"difficulty {w['target_difficulty']:.2f}"
        return self._world_reply(
            w, f"🛠️ A new world was evolved and proven broken ({how}). The attached file is the "
               f"current, broken code. Investigate with `/vanta witnesses` and `/vanta probe`, "
               f"then `/vanta submit`.")

    async def list(self, user: str) -> Reply:
        try:
            worlds = await self.api.list_worlds(user)
        except VantaApiError as exc:
            return self._error(exc)
        if not worlds:
            return Reply(content="You have no open worlds. Make one with `/vanta create`.", ephemeral=True)
        lines = [f"`{w['world_id']}` · **{_cut(w['title'], 60)}** · difficulty {w['target_difficulty']:.2f}"
                 for w in worlds[:20]]
        more = f"\n…and {len(worlds) - 20} more" if len(worlds) > 20 else ""
        return Reply(embeds=[EmbedSpec(title=f"Your worlds ({len(worlds)})",
                                       description="\n".join(lines) + more)], ephemeral=True)

    async def info(self, world_id: str) -> Reply:
        try:
            return self._world_reply(await self.api.get_world(world_id))
        except VantaApiError as exc:
            return self._error(exc)

    async def submit(self, user: str, world_id: str, source_text: str) -> Reply:
        source = extract_source(source_text)
        if not source.strip():
            return Reply(content="Attach your `.c` file or paste the code.", ephemeral=True)
        try:
            r = await self.api.submit(world_id, source, user)
        except VantaApiError as exc:
            return self._error(exc)
        ok = r["verdict"] == "accepted"
        passed = sum(1 for t in r["tests"] if t["passed"])
        checks = "\n".join(f"{'✅' if t['passed'] else '❌'} {t['test']}" for t in r["tests"])
        why = ("Every required property holds." if ok
               else {"compile_error": "Your code did not compile.",
                     "timeout": "Your code ran too long.",
                     "runtime_error": "Your code crashed while being tested."}.get(
                   r.get("reason"), "Not every required property holds yet."))
        e = EmbedSpec(
            title=("ACCEPTED" if ok else "REJECTED") + f" · {passed}/{len(r['tests'])} checks",
            description=why, color=COLOR_ACCEPTED if ok else COLOR_REJECTED,
            footer=f"world {world_id}",
        )
        if checks:
            e.fields.append(("Checks", _cut(checks, 1020), False))
        if r.get("detail"):
            e.fields.append(("Compiler / runtime output", f"```\n{_cut(r['detail'], 950)}\n```", False))
        rt = r.get("rating")
        if rt and rt.get("counted"):
            delta = round(rt["after"] - rt["before"])
            e.fields.append(("Rating", f"{round(rt['before'])} → {round(rt['after'])} "
                                       f"({'+' if delta >= 0 else ''}{delta})", True))
        return Reply(embeds=[e])

    async def delete(self, user: str, world_id: str, is_admin: bool) -> Reply:
        try:
            await self.api.delete_world(world_id, requested_by=user, admin=is_admin)
        except VantaApiError as exc:
            return self._error(exc)
        return Reply(content=f"🗑️ World `{world_id}` was torn down.", ephemeral=True)

    async def delete_all(self, user: str) -> Reply:
        try:
            r = await self.api.delete_my_worlds(user)
        except VantaApiError as exc:
            return self._error(exc)
        return Reply(content=f"🗑️ Deleted {r['deleted_count']} of your worlds.", ephemeral=True)

    async def admin_delete_all(self, is_admin: bool) -> Reply:
        if not is_admin:
            return Reply(content="⚠️ Only server admins (Manage Server) can delete every world.",
                         ephemeral=True)
        try:
            r = await self.api.delete_every_world()
        except VantaApiError as exc:
            return self._error(exc)
        return Reply(content=f"🗑️ Deleted every VANTA world ({r['deleted_count']}).")

    # --- investigation ----------------------------------------------------
    async def witnesses(self, world_id: str) -> Reply:
        try:
            ws = await self.api.witnesses(world_id)
        except VantaApiError as exc:
            return self._error(exc)
        e = EmbedSpec(title="Who was there",
                      description="Each person lived through one real run of this system and only "
                                  "knows what they saw. Ask with `/vanta ask`.")
        for w in ws[:10]:
            qs = "\n".join(f"› {q['question']}" for q in w["questions"])
            e.fields.append((f"{w['name']} — {w['role']} (`{w['key']}`)", _cut(qs, 1000), False))
        return Reply(embeds=[e], ephemeral=True)

    async def ask(self, user: str, world_id: str, witness: str, question: str) -> Reply:
        try:
            ws = await self.api.witnesses(world_id)
            wit = next((w for w in ws if witness in (w["key"], w["name"], w["name"].lower())), None)
            if wit is None:
                names = ", ".join(f"{w['name']} (`{w['key']}`)" for w in ws)
                return Reply(content=f"No witness called '{witness}'. Try: {names}", ephemeral=True)
            a = await self.api.ask(world_id, wit["key"], question, user)
        except VantaApiError as exc:
            return self._error(exc)
        e = EmbedSpec(title=f"{wit['name']}", description=_cut(a["text"], 3500),
                      footer=f"{wit['role']} · world {world_id}")
        if a.get("evidence") and a["evidence"].get("rows"):
            ev = a["evidence"]
            rows = [" | ".join(str(c) for c in r) for r in ev["rows"][:8]]
            table = " | ".join(ev["columns"]) + "\n" + "\n".join(rows)
            more = ev.get("total", len(ev["rows"])) - len(rows)
            e.fields.append(("The record", f"```\n{_cut(table, 950)}\n```"
                             + (f"+{more} more rows" if more > 0 else ""), False))
        if a.get("followups"):
            e.fields.append(("You could also ask", _cut("\n".join(f"› {q}" for q in a["followups"][:4]), 1000), False))
        return Reply(content=f"> {_cut(question, 300)}", embeds=[e])

    async def probe(self, user: str, world_id: str, scenario_text: str | None,
                    source_text: str | None) -> Reply:
        try:
            if not scenario_text:
                info = await self.api.probe_info(world_id)
                return Reply(embeds=[EmbedSpec(
                    title="Probe lab — how to write an experiment", description=_cut(info["help"], 2000),
                    fields=[("Example", f"```json\n{_cut(json.dumps(info['template']), 950)}\n```", False)])],
                    ephemeral=True)
            try:
                scenario = json.loads(scenario_text)
            except json.JSONDecodeError as exc:
                return Reply(content=f"⚠️ That scenario isn't valid JSON: {exc.msg}", ephemeral=True)
            source = extract_source(source_text) if source_text else None
            r = await self.api.probe(world_id, scenario, source, user)
        except VantaApiError as exc:
            return self._error(exc)
        ran = "your code" if source else "the original system"
        if not r["ok"]:
            return Reply(embeds=[EmbedSpec(title=f"Experiment on {ran} failed", color=COLOR_REJECTED,
                                           description=f"```\n{_cut(r.get('detail') or r['error'], 1800)}\n```")])
        return Reply(embeds=[self._probe_summary(r["trace"], ran)])

    @staticmethod
    def _probe_summary(tr: dict, ran: str) -> EmbedSpec:
        if tr["kind"] == "job_queue":
            st, jobs = tr["stats"], tr["jobs"]
            never = [j for j in jobs if j["status"] == "never_started"]
            waits = [j["wait"] for j in jobs if j["wait"] is not None]
            by_entry: dict[int, list] = {}
            for j in jobs:
                by_entry.setdefault(j["entry"], []).append(j)
            lines = []
            for e, js in sorted(by_entry.items()):
                w = [j["wait"] for j in js if j["wait"] is not None]
                lines.append(f"jobs[{e}] ×{len(js)} ({js[0]['minutes']} min): "
                             f"{sum(1 for j in js if j['status'] == 'finished')} finished, "
                             f"{sum(1 for j in js if j['status'] == 'never_started')} never started, "
                             f"worst wait {max(w) if w else '—'}")
            return EmbedSpec(
                title=f"Experiment on {ran}",
                color=COLOR_SIGNAL if never or st["too_late_attempts"] else COLOR_STRUCTURE,
                description=(f"Busy {round(100 * st['busy_minutes'] / max(1, st['open_minutes']))}% over "
                             f"{st['days_simulated']} day(s) · idle while work waited "
                             f"{st['idle_while_waiting']} min · too-late picks {st['too_late_attempts']} · "
                             f"invalid picks {st['invalid_picks']} · longest queue {st['max_queue']} · "
                             f"never started {len(never)} · worst wait {max(waits) if waits else '—'} min"),
                fields=[("By entry", _cut("\n".join(lines), 1020), False)],
            )
        st = tr["stats"]
        diff = sum(1 for o in tr["ops"] if o["in_use"] != o["ledger"])
        log = "\n".join(
            f"#{o['k'] + 1} {o['op']}({o['holder']}) → {o['returned']} · in use {o['in_use']} · receipts {o['ledger']}"
            for o in tr["ops"][:15])
        return EmbedSpec(
            title=f"Experiment on {ran}",
            color=COLOR_SIGNAL if diff else COLOR_STRUCTURE,
            description=(f"{st['op_count']} operations · {st['in_use']}/{st['pool_size']} marked in use at "
                         f"the end · receipts say {st['ledger']} out · {diff} step(s) where the two differ"),
            fields=[("First operations", f"```\n{_cut(log, 950)}\n```", False)],
        )

    async def profile(self, user: str) -> Reply:
        try:
            p = await self.api.profile(user)
        except VantaApiError as exc:
            return self._error(exc)
        return Reply(embeds=[EmbedSpec(
            title=f"{p['level']} · {round(p['rating'])}",
            description=(f"{p['worlds_solved']} solved of {p['worlds_attempted']} attempted · "
                         f"{p['experiments_run']} experiments · {p['witness_questions']} witness questions.\n"
                         f"Your next calibrated world will be pitched at difficulty "
                         f"{p['recommended_difficulty']:.2f}."))], ephemeral=True)

    # --- cohorts ----------------------------------------------------------
    async def cohort_create(self, user: str, name: str, defect: str | None,
                            difficulty: str | None) -> Reply:
        d = difficulty_value(difficulty)
        try:
            c = await self.api.create_cohort(user, name, defect or None, 0.45 if d is None else d)
        except VantaApiError as exc:
            return self._error(exc)
        return Reply(
            content=f"📣 **{c['name']}** is open. Everyone joins with `/vanta join code:{c['code']}`",
            embeds=[EmbedSpec(
                title=f"Join code: {c['code']}",
                description=(f"Defect class: **{c['archetype_title']}** · difficulty "
                             f"{c['target_difficulty']:.2f}\nEveryone gets the same defect in the same "
                             f"setting, but in their own world, with their own names and numbers. "
                             f"Copied code won't compile against anyone else's system."),
                footer="Host: /vanta cohort_status to follow progress"),
            ])

    async def join(self, user: str, code: str, display_name: str) -> Reply:
        try:
            j = await self.api.join_cohort(code, user, display_name)
        except VantaApiError as exc:
            return self._error(exc)
        head = ("👋 Welcome back. This is your world in **{n}**." if j["member"]["rejoined"]
                else "🧩 You're in **{n}**. This world was evolved just for you.").format(
            n=j["world"]["cohort"]["name"] if j["world"].get("cohort") else code)
        reply = self._world_reply(j["world"], head)
        reply.ephemeral = True
        return reply

    async def cohort_status(self, user: str, code: str, is_admin: bool) -> Reply:
        try:
            v = await self.api.cohort_host(code, user, admin=is_admin)
        except VantaApiError as exc:
            return self._error(exc)
        o = v["originality"]
        lines = []
        for m in v["members"][:25]:
            mark = "✅" if m["solved"] else ("🔸" if m["submissions"] else "·")
            best = f"{m['best']['passed']}/{m['best']['total']}" if m["best"] else "—"
            lines.append(f"{mark} **{_cut(m['display_name'], 30)}** · {m['submissions']} submits · best {best} · "
                         f"{m['experiments']} exp · {m['witness_questions']} q")
        approaches = (f"{o['distinct_approaches']} distinct approach(es) among {o['accepted']} accepted"
                      if o["accepted"] else "No accepted solutions yet")
        e = EmbedSpec(
            title=f"{v['name']} · {v['code']} · {v['status']}",
            description=(f"**{v['defect_class']}** in {v.get('setting') or 'a generated setting'} · "
                         f"{v['member_count']} members · {v['solved_count']} solved\n{approaches}"),
            fields=[("Members", _cut("\n".join(lines) or "Nobody has joined yet.", 1020), False)],
            footer="Only the host sees this.",
        )
        if o["near_identical"]:
            pairs = "\n".join(f"{p['a']} ↔ {p['b']} ({round(100 * p['similarity'])}%)"
                              for p in o["near_identical"][:8])
            e.fields.append(("Near-identical solutions (check, don't assume)", _cut(pairs, 1000), False))
        return Reply(embeds=[e], ephemeral=True)

    async def cohort_close(self, user: str, code: str, is_admin: bool) -> Reply:
        try:
            c = await self.api.close_cohort(code, user, admin=is_admin)
        except VantaApiError as exc:
            return self._error(exc)
        return Reply(content=f"🔒 **{c['name']}** ({c['code']}) is closed to new members. "
                             f"Existing members can still work and submit.")

    async def cohort_delete(self, user: str, code: str, is_admin: bool) -> Reply:
        try:
            r = await self.api.delete_cohort(code, user, admin=is_admin)
        except VantaApiError as exc:
            return self._error(exc)
        return Reply(content=f"🗑️ Cohort {r['deleted']} deleted, with {r['worlds_deleted']} member world(s).")

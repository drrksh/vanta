"""
Cohorts: one problem for a whole room, a different world for each person.

A host opens a cohort. VANTA fixes the defect class, the exact bug variant
and the story setting for everyone (drawn at random from the pool unless the
host picks a class) plus one difficulty. Each member who joins gets their own
world evolved from a seed derived from their identity: the same defect in the
same setting, but their own struct and function names and their own
constants. Joining also checks that no two members share an identifier set,
so code copied from a neighbour won't even compile against your system.

The host console shows who has joined, how far each person has got, how
much they investigated, and how many genuinely different approaches the
accepted solutions represent (see originality.py).
"""
from __future__ import annotations

import hashlib
import json
import random
import secrets
import sqlite3
import uuid
from dataclasses import dataclass

from app.core import world_manager as wm
from app.core.originality import analyze
from app.core.world_manager import WorldManager, WorldNotFoundError, WorldRecord
from app.worldgen.registry import ARCHETYPE_POOL, ARCHETYPES_BY_ID

_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


class CohortError(Exception):
    status = 400


class CohortNotFound(CohortError):
    status = 404


class CohortForbidden(CohortError):
    status = 403


@dataclass
class Cohort:
    cohort_id: str
    code: str
    name: str
    host_id: str
    archetype_id: str
    pins: dict
    target_difficulty: float
    seed: int
    status: str
    created_at: str

    def public(self, member_count: int) -> dict:
        arch = ARCHETYPES_BY_ID[self.archetype_id]
        return {"code": self.code, "name": self.name, "archetype_id": self.archetype_id,
                "archetype_title": arch.title, "target_difficulty": self.target_difficulty,
                "status": self.status, "member_count": member_count,
                "host_id": self.host_id, "created_at": self.created_at}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(wm.DB_PATH)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS cohorts (
            cohort_id TEXT PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            host_id TEXT NOT NULL,
            archetype_id TEXT NOT NULL,
            pins_json TEXT NOT NULL,
            target_difficulty REAL NOT NULL,
            seed INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS cohort_members (
            cohort_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            world_id TEXT NOT NULL,
            signature TEXT NOT NULL,
            joined_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (cohort_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS cohort_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cohort_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            world_id TEXT NOT NULL,
            verdict TEXT NOT NULL,
            passed INTEGER NOT NULL,
            total INTEGER NOT NULL,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            world_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    return conn


def _row(r) -> Cohort:
    return Cohort(cohort_id=r[0], code=r[1], name=r[2], host_id=r[3], archetype_id=r[4],
                  pins=json.loads(r[5]), target_difficulty=r[6], seed=r[7], status=r[8],
                  created_at=r[9])


_COLS = "cohort_id, code, name, host_id, archetype_id, pins_json, target_difficulty, seed, status, created_at"


_NAME_KEYS = ("struct_name", "func_name", "checkout_func", "release_func")


def _identifiers(world) -> list[str]:
    p = world.params or {}
    return [p[k] for k in _NAME_KEYS if p.get(k)]


def _signature(world) -> str:
    return "|".join(_identifiers(world))


class CohortStore:
    MAX_NAME_RETRIES = 6

    def __init__(self, manager: WorldManager):
        self.manager = manager

    # --- lifecycle --------------------------------------------------------
    def create(self, host_id: str, name: str, archetype_id: str | None = None,
               target_difficulty: float = 0.45) -> Cohort:
        name = (name or "").strip()[:80] or "Untitled cohort"
        if archetype_id and archetype_id not in ARCHETYPES_BY_ID:
            raise CohortError(f"Unknown defect class '{archetype_id}'")
        seed = secrets.randbits(31)
        rng = random.Random(f"cohort:{seed}")
        arch = ARCHETYPES_BY_ID[archetype_id] if archetype_id else rng.choice(ARCHETYPE_POOL)
        pins = arch.random_pins(rng)
        d = max(0.0, min(1.0, float(target_difficulty)))
        conn = _connect()
        try:
            for _ in range(20):
                code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
                try:
                    conn.execute(
                        "INSERT INTO cohorts (cohort_id, code, name, host_id, archetype_id, pins_json, "
                        "target_difficulty, seed) VALUES (?,?,?,?,?,?,?,?)",
                        (str(uuid.uuid4())[:8], code, name, host_id, arch.id, json.dumps(pins), d, seed))
                    conn.commit()
                    break
                except sqlite3.IntegrityError:
                    continue
            else:
                raise CohortError("Could not allocate a join code")
        finally:
            conn.close()
        return self.get(code)

    def get(self, code: str) -> Cohort:
        conn = _connect()
        try:
            r = conn.execute(f"SELECT {_COLS} FROM cohorts WHERE code = ?",
                             ((code or "").strip().upper(),)).fetchone()
        finally:
            conn.close()
        if r is None:
            raise CohortNotFound(f"No cohort with code '{code}'")
        return _row(r)

    def list_for_host(self, host_id: str) -> list[dict]:
        conn = _connect()
        try:
            rows = conn.execute(f"SELECT {_COLS} FROM cohorts WHERE host_id = ? ORDER BY created_at DESC",
                                (host_id,)).fetchall()
            out = []
            for r in rows:
                c = _row(r)
                n = conn.execute("SELECT COUNT(*) FROM cohort_members WHERE cohort_id = ?",
                                 (c.cohort_id,)).fetchone()[0]
                out.append(c.public(n))
        finally:
            conn.close()
        return out

    def member_count(self, cohort: Cohort) -> int:
        conn = _connect()
        try:
            return conn.execute("SELECT COUNT(*) FROM cohort_members WHERE cohort_id = ?",
                                (cohort.cohort_id,)).fetchone()[0]
        finally:
            conn.close()

    def _authorize(self, cohort: Cohort, requester: str | None, is_admin: bool) -> None:
        if not is_admin and requester != cohort.host_id:
            raise CohortForbidden("Only the cohort's host can do that")

    def close(self, code: str, requester: str | None, is_admin: bool = False) -> Cohort:
        c = self.get(code)
        self._authorize(c, requester, is_admin)
        conn = _connect()
        try:
            conn.execute("UPDATE cohorts SET status = 'closed' WHERE cohort_id = ?", (c.cohort_id,))
            conn.commit()
        finally:
            conn.close()
        return self.get(code)

    def delete(self, code: str, requester: str | None, is_admin: bool = False) -> int:
        """Tear the cohort down, including every member's world."""
        c = self.get(code)
        self._authorize(c, requester, is_admin)
        conn = _connect()
        try:
            worlds = [r[0] for r in conn.execute(
                "SELECT world_id FROM cohort_members WHERE cohort_id = ?", (c.cohort_id,)).fetchall()]
            conn.execute("DELETE FROM cohort_submissions WHERE cohort_id = ?", (c.cohort_id,))
            conn.execute("DELETE FROM cohort_members WHERE cohort_id = ?", (c.cohort_id,))
            conn.execute("DELETE FROM cohorts WHERE cohort_id = ?", (c.cohort_id,))
            conn.commit()
        finally:
            conn.close()
        for w in worlds:
            try:
                self.manager.delete_world(w)
            except WorldNotFoundError:
                pass
        return len(worlds)

    # --- membership -------------------------------------------------------
    def _member(self, conn, cohort_id: str, user_id: str):
        return conn.execute(
            "SELECT user_id, display_name, world_id, signature, joined_at FROM cohort_members "
            "WHERE cohort_id = ? AND user_id = ?", (cohort_id, user_id)).fetchone()

    def membership(self, code: str, user_id: str) -> dict | None:
        c = self.get(code)
        conn = _connect()
        try:
            m = self._member(conn, c.cohort_id, user_id)
        finally:
            conn.close()
        if m is None:
            return None
        return {"user_id": m[0], "display_name": m[1], "world_id": m[2], "joined_at": m[4]}

    async def join(self, code: str, user_id: str, display_name: str) -> tuple[dict, WorldRecord]:
        c = self.get(code)
        display_name = (display_name or "").strip()[:40] or "Anonymous"
        conn = _connect()
        try:
            existing = self._member(conn, c.cohort_id, user_id)
            taken = {r[0] for r in conn.execute(
                "SELECT signature FROM cohort_members WHERE cohort_id = ? AND user_id != ?",
                (c.cohort_id, user_id)).fetchall()}
        finally:
            conn.close()
        if existing is not None:
            try:
                rec = self.manager.get_world(existing[2])
                return ({"user_id": user_id, "display_name": existing[1], "world_id": existing[2],
                         "rejoined": True}, rec)
            except WorldNotFoundError:
                pass  # their world was deleted; give them a fresh one below
        if c.status != "open" and existing is None:
            raise CohortError("This cohort is closed to new members")

        rec = None
        for attempt in range(self.MAX_NAME_RETRIES):
            h = hashlib.sha256(f"{c.seed}:{user_id}:{attempt}".encode()).digest()
            seed = int.from_bytes(h[:4], "big") % (2**31)
            candidate = await self.manager.create_world(
                created_by=user_id, seed=seed, target_difficulty=c.target_difficulty,
                archetype_id=c.archetype_id, pins=c.pins)
            if _signature(candidate.world) not in taken:
                rec = candidate
                break
            self.manager.delete_world(candidate.world_id)
        if rec is None:
            raise CohortError("Could not give you a world with unique names; try again")

        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO cohort_members (cohort_id, user_id, display_name, world_id, signature) "
                "VALUES (?,?,?,?,?) ON CONFLICT(cohort_id, user_id) DO UPDATE SET "
                "world_id = excluded.world_id, signature = excluded.signature, "
                "display_name = excluded.display_name",
                (c.cohort_id, user_id, display_name, rec.world_id, _signature(rec.world)))
            conn.commit()
        finally:
            conn.close()
        return {"user_id": user_id, "display_name": display_name, "world_id": rec.world_id,
                "rejoined": False}, rec

    def for_world(self, world_id: str) -> dict | None:
        conn = _connect()
        try:
            r = conn.execute(
                "SELECT c.code, c.name, c.cohort_id, m.user_id, m.display_name FROM cohort_members m "
                "JOIN cohorts c ON c.cohort_id = m.cohort_id WHERE m.world_id = ?", (world_id,)).fetchone()
        finally:
            conn.close()
        if r is None:
            return None
        return {"code": r[0], "name": r[1], "cohort_id": r[2], "user_id": r[3], "display_name": r[4]}

    def record_submission(self, world_id: str, verdict: str, passed: int, total: int,
                          source: str) -> None:
        link = self.for_world(world_id)
        if link is None:
            return
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO cohort_submissions (cohort_id, user_id, world_id, verdict, passed, total, "
                "source) VALUES (?,?,?,?,?,?,?)",
                (link["cohort_id"], link["user_id"], world_id, verdict, passed, total, source))
            conn.commit()
        finally:
            conn.close()

    # --- host console -----------------------------------------------------
    def host_view(self, code: str, requester: str | None, is_admin: bool = False) -> dict:
        c = self.get(code)
        self._authorize(c, requester, is_admin)
        conn = _connect()
        try:
            members = conn.execute(
                "SELECT user_id, display_name, world_id, joined_at FROM cohort_members "
                "WHERE cohort_id = ? ORDER BY joined_at, display_name", (c.cohort_id,)).fetchall()
            rows, entries = [], []
            for user_id, name, world_id, joined_at in members:
                subs = conn.execute(
                    "SELECT verdict, passed, total, source, created_at FROM cohort_submissions "
                    "WHERE cohort_id = ? AND user_id = ? AND world_id = ? ORDER BY id",
                    (c.cohort_id, user_id, world_id)).fetchall()
                act = dict(conn.execute(
                    "SELECT kind, COUNT(*) FROM activity WHERE user_id = ? AND world_id = ? GROUP BY kind",
                    (user_id, world_id)).fetchall())
                solved_at = next((s[4] for s in subs if s[0] == "accepted"), None)
                best = max(subs, key=lambda s: (s[0] == "accepted", s[1]), default=None)
                try:
                    world = self.manager.get_world(world_id).world
                except WorldNotFoundError:
                    world = None
                rows.append({
                    "user_id": user_id, "display_name": name, "world_id": world_id,
                    "joined_at": joined_at, "world_exists": world is not None,
                    "identifiers": _identifiers(world) if world else [],
                    "submissions": len(subs), "solved": solved_at is not None, "solved_at": solved_at,
                    "best": {"passed": best[1], "total": best[2]} if best else None,
                    "experiments": act.get("probe", 0),
                    "witness_questions": act.get("witness", 0) + act.get("replay", 0),
                })
                if world is not None and subs:
                    # Prefer the accepted solution; otherwise their latest try.
                    chosen = next((s for s in reversed(subs) if s[0] == "accepted"), subs[-1])
                    entries.append({"member": name, "world": world, "source": chosen[3],
                                    "accepted": chosen[0] == "accepted"})
        finally:
            conn.close()
        arch = ARCHETYPES_BY_ID[c.archetype_id]
        sample = arch.generate(c.seed, pins=c.pins).params  # no compile; just the framing
        return {
            **c.public(len(rows)),
            "setting": sample["domain"].get("place"),
            "defect_variant": c.pins.get("variant"),   # host-only: the planted bug
            "members": rows,
            "originality": analyze(entries),
            "solved_count": sum(1 for r in rows if r["solved"]),
            "defect_class": arch.title,
        }

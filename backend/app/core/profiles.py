"""
Per-user adaptive difficulty.

Each contestant has a rating that moves with what they actually do, scored
the way chess ratings are: a world of difficulty d is treated as an opponent
rated 800 + 1200*d, and every submission is a game against it. Solving a
world above your level moves you up a lot; a near miss on an easy one moves
you down a little. The next world VANTA evolves for you is aimed slightly
above where you are now, so beginners get gentle systems with obvious
defects and strong contestants get large systems with subtle ones -- from
the same generator, with no separate beginner or expert problem set.

This is the "evolves around the user" half of the evolutionary layer: the
generator evolves worlds toward a target, and the target evolves toward the
person.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.core.world_manager import DB_PATH

START_RATING = 1100.0
BASE, SPAN = 800.0, 1200.0

_LEVELS = [(1000, "Novice"), (1200, "Apprentice"), (1400, "Practitioner"),
           (1600, "Engineer"), (1800, "Expert"), (10_000, "Master")]


def world_rating(difficulty: float) -> float:
    return BASE + SPAN * max(0.0, min(1.0, difficulty))


def recommended_difficulty(rating: float) -> float:
    # Aim a little above current skill: a stretch, not a wall.
    d = (rating - BASE) / SPAN + 0.06
    return round(max(0.1, min(0.95, d)), 2)


def level_for(rating: float) -> str:
    for bound, name in _LEVELS:
        if rating < bound:
            return name
    return _LEVELS[-1][1]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            user_id TEXT PRIMARY KEY,
            rating REAL NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            world_id TEXT NOT NULL,
            difficulty REAL NOT NULL,
            verdict TEXT NOT NULL,
            passed INTEGER NOT NULL,
            total INTEGER NOT NULL,
            rating_before REAL NOT NULL,
            rating_after REAL NOT NULL,
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


@dataclass
class RatingChange:
    before: float
    after: float
    counted: bool


class ProfileStore:
    def rating(self, user_id: str) -> float:
        conn = _connect()
        try:
            row = conn.execute("SELECT rating FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        finally:
            conn.close()
        return row[0] if row else START_RATING

    def recommended(self, user_id: str) -> float:
        return recommended_difficulty(self.rating(user_id))

    def log_activity(self, user_id: str | None, world_id: str, kind: str) -> None:
        if not user_id:
            return
        conn = _connect()
        try:
            conn.execute("INSERT INTO activity (user_id, world_id, kind) VALUES (?,?,?)",
                         (user_id, world_id, kind))
            conn.commit()
        finally:
            conn.close()

    def record_submission(
        self, user_id: str, world_id: str, difficulty: float, verdict: str,
        passed: int, total: int,
    ) -> RatingChange:
        conn = _connect()
        try:
            before = self._rating(conn, user_id)
            solved_already = conn.execute(
                "SELECT 1 FROM attempts WHERE user_id = ? AND world_id = ? AND verdict = 'accepted'",
                (user_id, world_id)).fetchone() is not None
            worlds_seen = conn.execute(
                "SELECT COUNT(DISTINCT world_id) FROM attempts WHERE user_id = ?", (user_id,)
            ).fetchone()[0]
            rejections_here = conn.execute(
                "SELECT COUNT(*) FROM attempts WHERE user_id = ? AND world_id = ? AND verdict != 'accepted'",
                (user_id, world_id)).fetchone()[0]
            after = before
            # Once solved, a world stops counting. Rejections only count for
            # the first few tries on a world: debugging is normal and
            # shouldn't sink anyone, and a rejection can never RAISE a rating
            # (otherwise resubmitting the starter would farm points).
            counted = not solved_already and (verdict == "accepted" or rejections_here < 5)
            if counted:
                expected = 1.0 / (1.0 + 10 ** ((world_rating(difficulty) - before) / 400.0))
                provisional = worlds_seen < 5
                if verdict == "accepted":
                    k, score = (48.0 if provisional else 32.0), 1.0
                else:
                    k, score = (8.0 if provisional else 5.0), 0.0
                after = round(before + k * (score - expected), 1)
            conn.execute(
                "INSERT INTO attempts (user_id, world_id, difficulty, verdict, passed, total, "
                "rating_before, rating_after) VALUES (?,?,?,?,?,?,?,?)",
                (user_id, world_id, difficulty, verdict, passed, total, before, after))
            conn.execute(
                "INSERT INTO profiles (user_id, rating) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET rating = excluded.rating, "
                "updated_at = datetime('now')", (user_id, after))
            conn.commit()
        finally:
            conn.close()
        return RatingChange(before=before, after=after, counted=counted)

    def profile(self, user_id: str) -> dict:
        conn = _connect()
        try:
            rating = self._rating(conn, user_id)
            solved = conn.execute(
                "SELECT COUNT(DISTINCT world_id) FROM attempts WHERE user_id = ? AND verdict = 'accepted'",
                (user_id,)).fetchone()[0]
            attempted = conn.execute(
                "SELECT COUNT(DISTINCT world_id) FROM attempts WHERE user_id = ?", (user_id,)
            ).fetchone()[0]
            submissions = conn.execute(
                "SELECT COUNT(*) FROM attempts WHERE user_id = ?", (user_id,)).fetchone()[0]
            act = dict(conn.execute(
                "SELECT kind, COUNT(*) FROM activity WHERE user_id = ? GROUP BY kind", (user_id,)
            ).fetchall())
            history = [
                {"world_id": r[0], "difficulty": r[1], "verdict": r[2], "passed": r[3],
                 "total": r[4], "rating_before": r[5], "rating_after": r[6], "at": r[7]}
                for r in conn.execute(
                    "SELECT world_id, difficulty, verdict, passed, total, rating_before, "
                    "rating_after, created_at FROM attempts WHERE user_id = ? "
                    "ORDER BY id DESC LIMIT 12", (user_id,)).fetchall()
            ]
        finally:
            conn.close()
        return {
            "user_id": user_id, "rating": rating, "level": level_for(rating),
            "recommended_difficulty": recommended_difficulty(rating),
            "worlds_solved": solved, "worlds_attempted": attempted, "submissions": submissions,
            "experiments_run": act.get("probe", 0),
            "witness_questions": act.get("witness", 0) + act.get("replay", 0),
            "history": history,
        }

    @staticmethod
    def _rating(conn, user_id) -> float:
        row = conn.execute("SELECT rating FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        return row[0] if row else START_RATING

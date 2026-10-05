"""
World Manager: lifecycle (create / list / get / delete) of live VANTA world
instances, persisted in SQLite so they survive restarts and are reachable
from the web UI and the Discord adapter against one store.

Creating a world runs the evolutionary generator (generate -> compile ->
test -> select) and stores the resulting, proven-viable world. Deleting is a
real, permanent teardown.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.evolution.engine import EvolutionEngine
from app.worldgen.archetype import GeneratedWorld
from app.worldgen.registry import generate_world

DB_PATH = Path(__file__).resolve().parent.parent.parent / "vanta_worlds.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS worlds (
            world_id TEXT PRIMARY KEY,
            seed INTEGER NOT NULL,
            archetype_id TEXT NOT NULL,
            title TEXT NOT NULL,
            created_by TEXT NOT NULL,
            target_difficulty REAL NOT NULL,
            viable INTEGER NOT NULL,
            world_json TEXT NOT NULL,
            fitness_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    return conn


_WORLD_FIELDS = (
    "archetype_id seed genes title briefing specification starter_source function_name "
    "function_signature shared_header mandatory_properties optional_objectives "
    "sample_input_description harness_source ground_truth_summary"
).split()


def _serialize_world(world: GeneratedWorld) -> str:
    d = {f: getattr(world, f) for f in _WORLD_FIELDS}
    d["params"] = world.params
    return json.dumps(d)


def _deserialize_world(raw: str) -> GeneratedWorld:
    d = json.loads(raw)
    return GeneratedWorld(
        agent_groundings=[], params=d.get("params") or {}, **{f: d[f] for f in _WORLD_FIELDS}
    )


@dataclass
class WorldRecord:
    world_id: str
    seed: int
    archetype_id: str
    title: str
    created_by: str
    target_difficulty: float
    viable: bool
    created_at: str
    world: GeneratedWorld
    fitness: dict


class WorldNotFoundError(Exception):
    pass


class WorldManager:
    def __init__(self, engine: EvolutionEngine | None = None):
        self.engine = engine or EvolutionEngine()

    async def create_world(
        self, created_by: str, seed: int | None = None,
        target_difficulty: float = 0.5, archetype_id: str | None = None,
    ) -> WorldRecord:
        if seed is None:
            seed = uuid.uuid4().int % (2**31)
        evolved = await generate_world(
            seed, target_difficulty=target_difficulty,
            archetype_id=archetype_id, engine=self.engine,
        )
        world = evolved.world
        fitness = {
            "broken": evolved.fitness.broken,
            "fixable": evolved.fitness.fixable,
            "distinct_fixes": evolved.fitness.distinct_fixes,
            "difficulty_error": round(evolved.fitness.difficulty_error, 3),
            "score": round(evolved.fitness.score, 3),
            "generation": evolved.generation,
        }
        world_id = str(uuid.uuid4())[:8]
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO worlds (world_id, seed, archetype_id, title, created_by, "
                "target_difficulty, viable, world_json, fitness_json) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (world_id, seed, world.archetype_id, world.title, created_by,
                 target_difficulty, int(evolved.fitness.viable),
                 _serialize_world(world), json.dumps(fitness)),
            )
            conn.commit()
        finally:
            conn.close()
        return WorldRecord(
            world_id=world_id, seed=seed, archetype_id=world.archetype_id,
            title=world.title, created_by=created_by, target_difficulty=target_difficulty,
            viable=evolved.fitness.viable, created_at="", world=world, fitness=fitness,
        )

    def get_world(self, world_id: str) -> WorldRecord:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT world_id, seed, archetype_id, title, created_by, target_difficulty, "
                "viable, world_json, fitness_json, created_at FROM worlds WHERE world_id = ?",
                (world_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            raise WorldNotFoundError(f"World '{world_id}' not found.")
        return WorldRecord(
            world_id=row[0], seed=row[1], archetype_id=row[2], title=row[3], created_by=row[4],
            target_difficulty=row[5], viable=bool(row[6]), world=_deserialize_world(row[7]),
            fitness=json.loads(row[8]), created_at=row[9],
        )

    def list_worlds(self, created_by: str | None = None) -> list[WorldRecord]:
        conn = _connect()
        try:
            if created_by:
                rows = conn.execute(
                    "SELECT world_id, seed, archetype_id, title, created_by, target_difficulty, "
                    "viable, world_json, fitness_json, created_at FROM worlds "
                    "WHERE created_by = ? ORDER BY created_at DESC", (created_by,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT world_id, seed, archetype_id, title, created_by, target_difficulty, "
                    "viable, world_json, fitness_json, created_at FROM worlds "
                    "ORDER BY created_at DESC"
                ).fetchall()
        finally:
            conn.close()
        return [
            WorldRecord(
                world_id=r[0], seed=r[1], archetype_id=r[2], title=r[3], created_by=r[4],
                target_difficulty=r[5], viable=bool(r[6]), world=_deserialize_world(r[7]),
                fitness=json.loads(r[8]), created_at=r[9],
            )
            for r in rows
        ]

    def delete_world(self, world_id: str) -> None:
        conn = _connect()
        try:
            cur = conn.execute("DELETE FROM worlds WHERE world_id = ?", (world_id,))
            conn.commit()
            if cur.rowcount == 0:
                raise WorldNotFoundError(f"World '{world_id}' not found.")
        finally:
            conn.close()

    def delete_all_worlds(self, created_by: str | None = None) -> int:
        conn = _connect()
        try:
            if created_by:
                cur = conn.execute("DELETE FROM worlds WHERE created_by = ?", (created_by,))
            else:
                cur = conn.execute("DELETE FROM worlds")
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()

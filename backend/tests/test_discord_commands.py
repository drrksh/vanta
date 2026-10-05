"""Discord adapter tests: the command layer runs against the real API (in
process), and the slash-command tree is built offline. No Discord
connection is needed."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core import profiles as profiles_mod  # noqa: E402
from app.core import world_manager as wm_mod  # noqa: E402
from discord_bot.commands import VantaCommands, extract_source  # noqa: E402
from discord_bot.vanta_api import VantaApi  # noqa: E402


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db = tmp_path / "vanta_discord.db"
    monkeypatch.setattr(wm_mod, "DB_PATH", db)
    monkeypatch.setattr(profiles_mod, "DB_PATH", db)
    return db


@pytest.fixture
async def cmds(tmp_db):
    from main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t", timeout=120) as c:
        yield VantaCommands(VantaApi(c), web_url="http://web.example")


def _pool_fix(starter: str) -> str:
    S = re.search(r"struct (\w+) pool\[\]", starter).group(1)
    C, R = re.findall(r"^int (\w+)\(struct", starter, flags=re.M)[:2]
    return f"""
int {C}(struct {S} pool[], int poolSize, int holderId) {{
    for (int i = 0; i < poolSize; i++)
        if (pool[i].inUse && pool[i].holderId == holderId) return -1;
    for (int i = 0; i < poolSize; i++)
        if (!pool[i].inUse) {{ pool[i].inUse = 1; pool[i].holderId = holderId; return i; }}
    return -1;
}}
int {R}(struct {S} pool[], int poolSize, int holderId) {{
    for (int i = 0; i < poolSize; i++)
        if (pool[i].inUse && pool[i].holderId == holderId) {{ pool[i].inUse = 0; return 1; }}
    return 0;
}}
"""


def test_extract_source_handles_fences():
    assert extract_source("```c\nint x;\n```") == "int x;\n"
    assert extract_source("int y;") == "int y;\n"


async def test_world_lifecycle_from_discord(cmds):
    me, other = "discord:1", "discord:2"
    r = await cmds.create(me, "pool_leak", "standard")
    e = r.embeds[0]
    world_id = e.footer.split()[1]
    assert e.url == f"http://web.example/worlds/{world_id}"
    name, data = r.files[0]
    assert name.endswith(".c") and b"int " in data
    starter = data.decode()

    assert world_id in (await cmds.list(me)).embeds[0].description
    assert (await cmds.list(other)).embeds == []

    rej = await cmds.submit(me, world_id, f"```c\n{starter}```")
    assert rej.embeds[0].title.startswith("REJECTED")
    checks = rej.embeds[0].fields[0][1]
    assert "hidden check" in checks and "hidden_" not in checks

    acc = await cmds.submit(me, world_id, _pool_fix(starter))
    assert acc.embeds[0].title.startswith("ACCEPTED")
    assert any(f[0] == "Rating" for f in acc.embeds[0].fields)

    # Somebody else can't tear down my world; admins can't be faked.
    assert "own worlds" in (await cmds.delete(other, world_id, is_admin=False)).content
    assert "Only server admins" in (await cmds.admin_delete_all(is_admin=False)).content
    assert "torn down" in (await cmds.delete(me, world_id, is_admin=False)).content
    assert "not found" in (await cmds.info(world_id)).content


async def test_witnesses_and_probe_from_discord(cmds):
    me = "discord:7"
    r = await cmds.create(me, "pool_leak", "gentle")
    world_id = r.embeds[0].footer.split()[1]
    w = await cmds.witnesses(world_id)
    assert len(w.embeds[0].fields) >= 4
    key = re.search(r"\(`(\w+)`\)", w.embeds[0].fields[-1][0]).group(1)
    a = await cmds.ask(me, world_id, key, "Do the books match reality?")
    assert a.embeds[0].description and a.content.startswith(">")
    assert "No witness" in (await cmds.ask(me, world_id, "nobody", "hi")).content

    help_ = await cmds.probe(me, world_id, None, None)
    assert "Example" in help_.embeds[0].fields[0][0]
    p = await cmds.probe(me, world_id, '{"ops": [{"op": "cycle", "holder": 5, "repeat": 3, "step": 1}]}', None)
    assert p.embeds[0].title == "Experiment on the original system"
    assert "isn't valid JSON" in (await cmds.probe(me, world_id, "{nope", None)).content
    prof = await cmds.profile(me)
    assert "experiments" in prof.embeds[0].description

    assert "Deleted 1" in (await cmds.delete_all(me)).content


async def test_cohort_from_discord(cmds):
    host, a, b = "discord:100", "discord:101", "discord:102"
    c = await cmds.cohort_create(host, "Friday lab", "pool_leak", "standard")
    code = c.embeds[0].title.split(": ")[1]
    ja = await cmds.join(a, code, "Asha")
    jb = await cmds.join(b, code.lower(), "Bo")
    assert ja.ephemeral and ja.files and jb.files
    assert ja.files[0][1] != jb.files[0][1]           # different worlds, different code
    again = await cmds.join(a, code, "Asha")
    assert "Welcome back" in again.content and again.files[0][1] == ja.files[0][1]

    wid = ja.embeds[0].footer.split()[1]
    await cmds.submit(a, wid, _pool_fix(ja.files[0][1].decode()))
    status = await cmds.cohort_status(host, code, is_admin=False)
    body = status.embeds[0].fields[0][1]
    assert "Asha" in body and "Bo" in body and "✅" in body
    assert "1 solved" in status.embeds[0].description
    assert "host" in (await cmds.cohort_status(a, code, is_admin=False)).content
    assert "closed" in (await cmds.cohort_close(host, code, is_admin=False)).content
    assert "closed to new members" in (await cmds.join("discord:103", code, "Late")).content
    assert "2 member world" in (await cmds.cohort_delete(host, code, is_admin=False)).content


async def test_slash_command_tree_builds_offline():
    import discord

    from discord_bot.bot import build_tree

    client = discord.Client(intents=discord.Intents.default())
    tree = build_tree(client, VantaCommands(VantaApi(httpx.AsyncClient(base_url="http://x"))))
    group = tree.get_command("vanta")
    names = {c.name for c in group.commands}
    assert {"create", "list", "info", "submit", "delete", "delete_all", "admin_delete_all",
            "witnesses", "ask", "probe", "profile", "cohort_create", "join", "cohort_status",
            "cohort_close", "cohort_delete"} <= names
    payload = group.to_dict(tree)
    assert payload["name"] == "vanta" and len(payload["options"]) == len(names)

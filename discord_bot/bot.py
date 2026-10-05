"""
VANTA Discord bot.

    DISCORD_TOKEN=...  VANTA_API_URL=http://127.0.0.1:8811  python -m discord_bot.bot

Optional: VANTA_WEB_URL (links worlds to the web workbench), VANTA_ADMIN_TOKEN
(must match the API's, sent only for server admins), DISCORD_GUILD_ID (sync
commands to one server instantly instead of globally).

Every command is a slash command under /vanta. World commands create and
tear down whole VANTA worlds -- nothing here creates or deletes Discord
channels.
"""
from __future__ import annotations

import io
import logging
import os

import discord
import httpx
from discord import app_commands

from discord_bot.commands import Reply, VantaCommands, discord_user
from discord_bot.vanta_api import VantaApi

log = logging.getLogger("vanta.discord")

DEFECT_CHOICES = [
    app_commands.Choice(name="Surprise me", value="surprise"),
    app_commands.Choice(name="Shared Resource Fairness", value="starvation_fairness"),
    app_commands.Choice(name="Resource Pool Integrity", value="pool_leak"),
]
DIFFICULTY_CHOICES = [
    app_commands.Choice(name="Calibrated to me", value="calibrated"),
    app_commands.Choice(name="Gentle", value="gentle"),
    app_commands.Choice(name="Standard", value="standard"),
    app_commands.Choice(name="Hard", value="hard"),
    app_commands.Choice(name="Brutal", value="brutal"),
]
MAX_SOURCE_BYTES = 64 * 1024


def to_discord(reply: Reply) -> dict:
    embeds = []
    for e in reply.embeds:
        em = discord.Embed(title=e.title, description=e.description or None, color=e.color, url=e.url)
        for name, value, inline in e.fields:
            em.add_field(name=name[:256], value=value[:1024] or "—", inline=inline)
        if e.footer:
            em.set_footer(text=e.footer[:2048])
        embeds.append(em)
    files = [discord.File(io.BytesIO(data), filename=name) for name, data in reply.files]
    out: dict = {"embeds": embeds, "files": files, "ephemeral": reply.ephemeral}
    if reply.content:
        out["content"] = reply.content[:2000]
    return out


def _is_admin(interaction: discord.Interaction) -> bool:
    perms = getattr(interaction, "permissions", None)
    return bool(perms and (perms.manage_guild or perms.administrator))


async def _read_attachment(att: discord.Attachment | None) -> str | None:
    if att is None:
        return None
    if att.size > MAX_SOURCE_BYTES:
        raise ValueError(f"{att.filename} is larger than {MAX_SOURCE_BYTES // 1024} KB")
    return (await att.read()).decode("utf-8", errors="replace")


def build_tree(client: discord.Client, cmds: VantaCommands) -> app_commands.CommandTree:
    tree = app_commands.CommandTree(client)
    vanta = app_commands.Group(name="vanta", description="Generated broken systems you investigate and fix in C")

    async def respond(interaction: discord.Interaction, reply: Reply):
        await interaction.followup.send(**to_discord(reply))

    def who(interaction: discord.Interaction) -> str:
        return discord_user(interaction.user.id)

    # ---- worlds ----
    @vanta.command(name="create", description="Evolve a brand-new broken world for you")
    @app_commands.describe(defect="Which defect class (default: surprise)", difficulty="Default: calibrated to you")
    @app_commands.choices(defect=DEFECT_CHOICES, difficulty=DIFFICULTY_CHOICES)
    async def create(interaction: discord.Interaction, defect: app_commands.Choice[str] | None = None,
                     difficulty: app_commands.Choice[str] | None = None):
        await interaction.response.defer(thinking=True)
        d = None if defect is None or defect.value == "surprise" else defect.value
        await respond(interaction, await cmds.create(who(interaction), d, difficulty.value if difficulty else None))

    @vanta.command(name="list", description="List your open worlds")
    async def list_(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await respond(interaction, await cmds.list(who(interaction)))

    @vanta.command(name="info", description="Show a world's briefing, requirements and starter code")
    async def info(interaction: discord.Interaction, world_id: str):
        await interaction.response.defer()
        await respond(interaction, await cmds.info(world_id))

    @vanta.command(name="submit", description="Submit a fix (attach a .c file or paste code)")
    @app_commands.describe(file="Your .c file", code="Or paste the code (```c fences are fine)")
    async def submit(interaction: discord.Interaction, world_id: str,
                     file: discord.Attachment | None = None, code: str | None = None):
        await interaction.response.defer(thinking=True)
        try:
            src = await _read_attachment(file) or code or ""
        except ValueError as exc:
            await respond(interaction, Reply(content=f"⚠️ {exc}", ephemeral=True))
            return
        await respond(interaction, await cmds.submit(who(interaction), world_id, src))

    @vanta.command(name="delete", description="Tear down one of your worlds")
    async def delete(interaction: discord.Interaction, world_id: str):
        await interaction.response.defer(ephemeral=True)
        await respond(interaction, await cmds.delete(who(interaction), world_id, _is_admin(interaction)))

    @vanta.command(name="delete_all", description="Tear down all of your worlds")
    async def delete_all(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await respond(interaction, await cmds.delete_all(who(interaction)))

    @vanta.command(name="admin_delete_all", description="Admins: tear down every VANTA world")
    @app_commands.default_permissions(manage_guild=True)
    async def admin_delete_all(interaction: discord.Interaction):
        await interaction.response.defer()
        await respond(interaction, await cmds.admin_delete_all(_is_admin(interaction)))

    # ---- investigation ----
    @vanta.command(name="witnesses", description="Who lived through a real run of this world")
    async def witnesses(interaction: discord.Interaction, world_id: str):
        await interaction.response.defer(ephemeral=True)
        await respond(interaction, await cmds.witnesses(world_id))

    @vanta.command(name="ask", description="Ask a witness one question; the answer comes from a real run")
    async def ask(interaction: discord.Interaction, world_id: str, witness: str, question: str):
        await interaction.response.defer(thinking=True)
        await respond(interaction, await cmds.ask(who(interaction), world_id, witness, question))

    @ask.autocomplete("witness")
    async def ask_witness_autocomplete(interaction: discord.Interaction, current: str):
        world_id = getattr(interaction.namespace, "world_id", None)
        if not world_id:
            return []
        try:
            ws = await cmds.api.witnesses(world_id)
        except Exception:
            return []
        cur = current.lower()
        return [app_commands.Choice(name=f"{w['name']} — {w['role']}"[:100], value=w["key"])
                for w in ws if cur in w["name"].lower() or cur in w["key"]][:25]

    @vanta.command(name="probe", description="Run an experiment on the system (omit scenario for help)")
    @app_commands.describe(scenario="JSON experiment", file="Optional: run it on your .c instead of the original")
    async def probe(interaction: discord.Interaction, world_id: str, scenario: str | None = None,
                    file: discord.Attachment | None = None):
        await interaction.response.defer(thinking=True)
        try:
            src = await _read_attachment(file)
        except ValueError as exc:
            await respond(interaction, Reply(content=f"⚠️ {exc}", ephemeral=True))
            return
        await respond(interaction, await cmds.probe(who(interaction), world_id, scenario, src))

    @vanta.command(name="profile", description="Your rating and what difficulty you'll get next")
    async def profile(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await respond(interaction, await cmds.profile(who(interaction)))

    # ---- cohorts ----
    @vanta.command(name="cohort_create", description="Host a cohort: one problem, a unique world per person")
    @app_commands.choices(defect=DEFECT_CHOICES, difficulty=DIFFICULTY_CHOICES[1:])
    async def cohort_create(interaction: discord.Interaction, name: str,
                            defect: app_commands.Choice[str] | None = None,
                            difficulty: app_commands.Choice[str] | None = None):
        await interaction.response.defer()
        d = None if defect is None or defect.value == "surprise" else defect.value
        await respond(interaction, await cmds.cohort_create(
            who(interaction), name, d, difficulty.value if difficulty else "standard"))

    @vanta.command(name="join", description="Join a cohort with its code and get your own world")
    async def join(interaction: discord.Interaction, code: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await respond(interaction, await cmds.join(who(interaction), code, interaction.user.display_name))

    @vanta.command(name="cohort_status", description="Host: members, progress and distinct approaches")
    async def cohort_status(interaction: discord.Interaction, code: str):
        await interaction.response.defer(ephemeral=True)
        await respond(interaction, await cmds.cohort_status(who(interaction), code, _is_admin(interaction)))

    @vanta.command(name="cohort_close", description="Host: stop new members joining")
    async def cohort_close(interaction: discord.Interaction, code: str):
        await interaction.response.defer()
        await respond(interaction, await cmds.cohort_close(who(interaction), code, _is_admin(interaction)))

    @vanta.command(name="cohort_delete", description="Host: delete the cohort and every member's world")
    async def cohort_delete(interaction: discord.Interaction, code: str):
        await interaction.response.defer()
        await respond(interaction, await cmds.cohort_delete(who(interaction), code, _is_admin(interaction)))

    tree.add_command(vanta)
    return tree


class VantaBot(discord.Client):
    def __init__(self, api_url: str, web_url: str | None, admin_token: str | None,
                 guild_id: int | None):
        super().__init__(intents=discord.Intents.default())
        self.http_client = httpx.AsyncClient(base_url=api_url, timeout=180)
        self.cmds = VantaCommands(VantaApi(self.http_client, admin_token), web_url)
        self.tree = build_tree(self, self.cmds)
        self.guild_id = guild_id

    async def setup_hook(self):
        if self.guild_id:
            guild = discord.Object(id=self.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def close(self):
        await self.http_client.aclose()
        await super().close()


def main():
    logging.basicConfig(level=logging.INFO)
    token = os.environ["DISCORD_TOKEN"]
    guild = os.environ.get("DISCORD_GUILD_ID")
    bot = VantaBot(
        api_url=os.environ.get("VANTA_API_URL", "http://127.0.0.1:8811"),
        web_url=os.environ.get("VANTA_WEB_URL"),
        admin_token=os.environ.get("VANTA_ADMIN_TOKEN"),
        guild_id=int(guild) if guild else None,
    )
    bot.run(token)


if __name__ == "__main__":
    main()

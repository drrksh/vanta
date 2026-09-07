from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.adapters.state import BotState
from bot.adapters.vanta_client import VantaAPIError, VantaClient


def _is_admin_role(interaction: discord.Interaction) -> bool:
    """
    Gate on a Discord role named 'VANTA Admin' (created by /vanta-admin setup)
    rather than Discord's own administrator permission, so the person
    running the demo can grant it narrowly to judges/organizers without
    giving full server admin.
    """
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        return False
    return any(role.name == "VANTA Admin" for role in interaction.user.roles)


def admin_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        if _is_admin_role(interaction):
            return True
        await interaction.response.send_message(
            "This command requires the `VANTA Admin` role.", ephemeral=True
        )
        return False

    return app_commands.check(predicate)


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot, client: VantaClient, state: BotState):
        self.bot = bot
        self.client = client
        self.state = state

    admin_group = app_commands.Group(name="vanta-admin", description="VANTA admin controls")

    @admin_group.command(name="setup", description="Create the locked VANTA Admin category and role")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_admin(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild = interaction.guild
        if guild is None:
            await interaction.followup.send("Server only.")
            return

        role = discord.utils.get(guild.roles, name="VANTA Admin")
        if role is None:
            role = await guild.create_role(name="VANTA Admin", mentionable=False)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        category = discord.utils.get(guild.categories, name="VANTA Admin")
        if category is None:
            category = await guild.create_category("VANTA Admin", overwrites=overwrites)
        self.state.admin_categories[guild.id] = category.id
        self.state.save()

        control_channel = discord.utils.get(category.text_channels, name="control-panel")
        if control_channel is None:
            control_channel = await guild.create_text_channel(
                "control-panel", category=category
            )

        await interaction.followup.send(
            f"Admin category ready: {category.name}. "
            f"Assign the **VANTA Admin** role to organizers/judges. "
            f"Control panel: <#{control_channel.id}>",
            ephemeral=True,
        )

    @admin_group.command(name="truth", description="[ADMIN] Show ground truth for a running world")
    @admin_only()
    async def truth(self, interaction: discord.Interaction, world_id: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            gt = await self.client.admin_ground_truth(world_id)
        except VantaAPIError as exc:
            await interaction.followup.send(f"Error: {exc.detail}")
            return
        embed = discord.Embed(title="GROUND TRUTH (admin only)", color=discord.Color.dark_red())
        embed.add_field(name="Root Cause ID", value=gt["root_cause_id"], inline=False)
        embed.add_field(name="Summary", value=gt["root_cause_summary"][:1024], inline=False)
        embed.add_field(name="Mechanism", value=gt["mechanism"][:1024], inline=False)
        if gt.get("hidden_state"):
            embed.add_field(
                name="Hidden State",
                value="\n".join(f"{k}: {v}" for k, v in gt["hidden_state"].items())[:1024],
                inline=False,
            )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @admin_group.command(name="knowledge", description="[ADMIN] Inspect what an agent is allowed to know")
    @admin_only()
    async def knowledge(self, interaction: discord.Interaction, world_id: str, agent_id: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            data = await self.client.admin_agent_knowledge(world_id, agent_id)
        except VantaAPIError as exc:
            await interaction.followup.send(f"Error: {exc.detail}")
            return
        embed = discord.Embed(
            title=f"Knowledge boundaries: {agent_id}", color=discord.Color.orange()
        )
        embed.add_field(
            name="Knowledge IDs",
            value="\n".join(data["knowledge_ids"]) or "(none)",
            inline=False,
        )
        if data["conditional_knowledge_ids"]:
            embed.add_field(
                name="Conditional (unlocked after prerequisites)",
                value="\n".join(
                    f"{k} <- {v}" for k, v in data["conditional_knowledge_ids"].items()
                ),
                inline=False,
            )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @admin_group.command(name="redteam", description="[ADMIN] Directly probe an agent to test the firewall")
    @admin_only()
    async def redteam(self, interaction: discord.Interaction, world_id: str, agent_id: str, message: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            result = await self.client.admin_red_team(world_id, agent_id, message)
        except VantaAPIError as exc:
            await interaction.followup.send(f"Error: {exc.detail}")
            return
        embed = discord.Embed(title="Red-team probe result", color=discord.Color.dark_orange())
        embed.add_field(name="Message sent", value=message[:1000], inline=False)
        embed.add_field(name="Agent response", value=result["text"][:1000], inline=False)
        embed.add_field(
            name="Flagged as injection?", value=str(result["flagged_injection"]), inline=True
        )
        embed.add_field(name="Provider used", value=result["provider_used"], inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @admin_group.command(name="validate", description="[ADMIN] Validate a scenario's firewall integrity")
    @admin_only()
    async def validate(self, interaction: discord.Interaction, scenario_id: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            result = await self.client.admin_validate(scenario_id)
        except VantaAPIError as exc:
            await interaction.followup.send(f"Error: {exc.detail}")
            return
        if result["valid"]:
            await interaction.followup.send(f"✅ `{scenario_id}` passes validation.", ephemeral=True)
        else:
            problems = "\n".join(f"- {p}" for p in result["problems"])
            await interaction.followup.send(
                f"❌ `{scenario_id}` has problems:\n{problems}", ephemeral=True
            )

    @admin_group.command(name="scenarios", description="[ADMIN] List all scenarios with validation status")
    @admin_only()
    async def scenarios(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        rows = await self.client.admin_list_scenarios()
        embed = discord.Embed(title="Scenarios", color=discord.Color.blurple())
        for r in rows:
            status = "✅" if r["valid"] else "❌"
            embed.add_field(
                name=f"{status} {r['title']} (`{r['id']}`)",
                value=f"domain={r['domain']} agents={r['agent_count']} facts={r['fact_count']}",
                inline=False,
            )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @admin_group.command(name="reset", description="[ADMIN] Reset a running world")
    @admin_only()
    async def reset(self, interaction: discord.Interaction, world_id: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            result = await self.client.admin_reset_world(world_id)
        except VantaAPIError as exc:
            await interaction.followup.send(f"Error: {exc.detail}")
            return
        await interaction.followup.send(f"World reset. Status: {result['status']}", ephemeral=True)

    @admin_group.command(name="tick", description="[ADMIN] Advance world time")
    @admin_only()
    async def tick(self, interaction: discord.Interaction, world_id: str, seconds: int = 60):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            result = await self.client.admin_tick_world(world_id, seconds)
        except VantaAPIError as exc:
            await interaction.followup.send(f"Error: {exc.detail}")
            return
        await interaction.followup.send(
            f"Advanced to sim_time={result['sim_time_seconds']}s (tick #{result['tick_count']})",
            ephemeral=True,
        )

    @admin_group.command(name="logs", description="[ADMIN] Show audit log for an investigation")
    @admin_only()
    async def logs(self, interaction: discord.Interaction, investigation_id: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            rows = await self.client.admin_logs(investigation_id)
        except VantaAPIError as exc:
            await interaction.followup.send(f"Error: {exc.detail}")
            return
        lines = [
            f"`{r['created_at']}` **{r['action']}** ({r['actor']}) {r['metadata']}"
            for r in rows[:25]
        ]
        await interaction.followup.send("\n".join(lines) or "No logs yet.", ephemeral=True)


async def setup(bot: commands.Bot, client: VantaClient, state: BotState):
    await bot.add_cog(AdminCog(bot, client, state))

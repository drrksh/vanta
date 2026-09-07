from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.adapters.state import BotState, InvestigationChannels
from bot.adapters.vanta_client import VantaAPIError, VantaClient

log = logging.getLogger("vanta.contestant")

MAX_DISCORD_MESSAGE = 1900  # leave headroom under Discord's 2000 char limit


def _truncate(text: str) -> str:
    if len(text) <= MAX_DISCORD_MESSAGE:
        return text
    return text[: MAX_DISCORD_MESSAGE - 20] + "\n...(truncated)"


class SolutionModal(discord.ui.Modal, title="Submit Your Solution"):
    root_cause = discord.ui.TextInput(
        label="Root Cause", style=discord.TextStyle.paragraph, required=True, max_length=400
    )
    explanation = discord.ui.TextInput(
        label="Explanation", style=discord.TextStyle.paragraph, required=True, max_length=1000
    )
    proposed_solution = discord.ui.TextInput(
        label="Proposed Solution", style=discord.TextStyle.paragraph, required=True, max_length=1000
    )
    implementation = discord.ui.TextInput(
        label="Implementation / Architecture",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
    )

    def __init__(self, cog: "ContestantCog", investigation_id: str):
        super().__init__()
        self._cog = cog
        self._investigation_id = investigation_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        try:
            result = await self._cog.client.submit_solution(
                self._investigation_id,
                {
                    "root_cause": str(self.root_cause),
                    "explanation": str(self.explanation),
                    "proposed_solution": str(self.proposed_solution),
                    "implementation": str(self.implementation) or "",
                },
            )
        except VantaAPIError as exc:
            await interaction.followup.send(f"Error submitting solution: {exc.detail}")
            return

        verdict = result["verdict"]
        emoji = "✅" if verdict == "accepted" else "❌"
        embed = discord.Embed(
            title=f"{emoji} {result['message'].splitlines()[0]}",
            description="\n".join(result["message"].splitlines()[1:]),
            color=discord.Color.green() if verdict == "accepted" else discord.Color.red(),
        )
        await interaction.followup.send(embed=embed)


class HypothesisModal(discord.ui.Modal, title="Add Hypothesis"):
    hypothesis_text = discord.ui.TextInput(
        label="Hypothesis", style=discord.TextStyle.paragraph, required=True, max_length=400
    )
    supporting = discord.ui.TextInput(
        label="Supporting Evidence", style=discord.TextStyle.paragraph, required=False, max_length=600
    )
    contradicting = discord.ui.TextInput(
        label="Contradicting Evidence", style=discord.TextStyle.paragraph, required=False, max_length=600
    )

    def __init__(self, cog: "ContestantCog", investigation_id: str):
        super().__init__()
        self._cog = cog
        self._investigation_id = investigation_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        try:
            h = await self._cog.client.create_hypothesis(
                self._investigation_id,
                str(self.hypothesis_text),
                str(self.supporting) or "",
                str(self.contradicting) or "",
            )
        except VantaAPIError as exc:
            await interaction.followup.send(f"Error: {exc.detail}")
            return
        embed = discord.Embed(
            title="Hypothesis added",
            description=h["text"],
            color=discord.Color.blurple(),
        )
        if h["supporting_evidence"]:
            embed.add_field(name="Supporting", value=h["supporting_evidence"], inline=False)
        if h["contradicting_evidence"]:
            embed.add_field(name="Contradicting", value=h["contradicting_evidence"], inline=False)
        embed.set_footer(text=f"Status: {h['status']}")
        await interaction.followup.send(embed=embed)


class ContestantCog(commands.Cog):
    def __init__(self, bot: commands.Bot, client: VantaClient, state: BotState):
        self.bot = bot
        self.client = client
        self.state = state

    vanta_group = app_commands.Group(name="vanta", description="VANTA investigation commands")

    @vanta_group.command(name="worlds", description="List available VANTA worlds")
    async def worlds(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        worlds = await self.client.list_worlds()
        if not worlds:
            await interaction.followup.send("No worlds are configured yet.")
            return
        embed = discord.Embed(title="Available VANTA Worlds", color=discord.Color.blurple())
        for w in worlds:
            embed.add_field(
                name=f"{w['title']}  ({w['domain']})",
                value=f"`{w['scenario_id']}`\n{w['briefing_preview']}...",
                inline=False,
            )
        await interaction.followup.send(embed=embed)

    @vanta_group.command(name="start", description="Start a new investigation")
    @app_commands.describe(scenario_id="The world's scenario id, see /vanta worlds")
    async def start(self, interaction: discord.Interaction, scenario_id: str):
        await interaction.response.defer(thinking=True)
        guild = interaction.guild
        if guild is None:
            await interaction.followup.send("This command must be used in a server.")
            return

        try:
            world = await self.client.start_world(scenario_id)
            inv = await self.client.create_investigation(
                world["world_id"], contestant_label=interaction.user.display_name
            )
        except VantaAPIError as exc:
            await interaction.followup.send(f"Could not start world: {exc.detail}")
            return

        category = await guild.create_category(f"VANTA - {world['title']}"[:100])

        briefing_channel = await guild.create_text_channel("briefing", category=category)
        evidence_channel = await guild.create_text_channel("evidence-board", category=category)
        hypotheses_channel = await guild.create_text_channel("hypotheses", category=category)
        solution_channel = await guild.create_text_channel("solution", category=category)

        agent_channels: dict[str, int] = {}
        for agent in inv["agents"]:
            safe_name = agent["id"].replace("_", "-")
            ch = await guild.create_text_channel(safe_name, category=category)
            agent_channels[agent["id"]] = ch.id
            await ch.send(
                f"**{agent['display_name']}** ({agent['role']})\n"
                f"Talk to this agent by just typing messages in this channel -- no slash command needed."
            )

        ic = InvestigationChannels(
            investigation_id=inv["investigation_id"],
            world_id=world["world_id"],
            scenario_id=scenario_id,
            guild_id=guild.id,
            category_id=category.id,
            briefing_channel_id=briefing_channel.id,
            evidence_channel_id=evidence_channel.id,
            hypotheses_channel_id=hypotheses_channel.id,
            solution_channel_id=solution_channel.id,
            agent_channels=agent_channels,
        )
        self.state.add_investigation(ic)

        await briefing_channel.send(
            f"# {world['title']}\n\n{inv['briefing']}\n\n"
            f"**Agents you can talk to:** "
            + ", ".join(f"<#{cid}>" for cid in agent_channels.values())
            + "\n\nUse `/vanta hypothesis` to record hypotheses, `/vanta evidence` to "
            "review your evidence board, and `/vanta submit` when you're ready to "
            "propose a solution."
        )

        await interaction.followup.send(
            f"Investigation started! Head to <#{briefing_channel.id}> to begin."
        )

    def _require_investigation(self, interaction: discord.Interaction) -> InvestigationChannels | None:
        category = interaction.channel.category if interaction.channel else None
        if category is None:
            return None
        return self.state.find_by_category(category.id)

    @vanta_group.command(name="evidence", description="Show your evidence board")
    async def evidence(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        ic = self._require_investigation(interaction)
        if ic is None:
            await interaction.followup.send(
                "Run this inside a VANTA investigation category (any channel under it)."
            )
            return
        items = await self.client.list_evidence(ic.investigation_id)
        if not items:
            await interaction.followup.send("No evidence discovered yet -- go talk to some agents!")
            return
        embed = discord.Embed(title="Evidence Board", color=discord.Color.gold())
        for item in items[:25]:
            embed.add_field(
                name=f"From {item['source_agent_id']}",
                value=_truncate(item["content"])[:1000],
                inline=False,
            )
        await interaction.followup.send(embed=embed)

    @vanta_group.command(name="hypothesis", description="Add a hypothesis")
    async def hypothesis(self, interaction: discord.Interaction):
        ic = self._require_investigation(interaction)
        if ic is None:
            await interaction.response.send_message(
                "Run this inside a VANTA investigation category.", ephemeral=True
            )
            return
        await interaction.response.send_modal(HypothesisModal(self, ic.investigation_id))

    @vanta_group.command(name="hypotheses", description="List your hypotheses")
    async def hypotheses(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        ic = self._require_investigation(interaction)
        if ic is None:
            await interaction.followup.send("Run this inside a VANTA investigation category.")
            return
        items = await self.client.list_hypotheses(ic.investigation_id)
        if not items:
            await interaction.followup.send("No hypotheses recorded yet. Use `/vanta hypothesis`.")
            return
        embed = discord.Embed(title="Hypotheses", color=discord.Color.purple())
        for h in items:
            value = h["text"]
            if h["supporting_evidence"]:
                value += f"\n✅ {h['supporting_evidence']}"
            if h["contradicting_evidence"]:
                value += f"\n❌ {h['contradicting_evidence']}"
            embed.add_field(name=f"[{h['status']}]", value=value[:1000], inline=False)
        await interaction.followup.send(embed=embed)

    @vanta_group.command(name="submit", description="Submit your proposed solution")
    async def submit(self, interaction: discord.Interaction):
        ic = self._require_investigation(interaction)
        if ic is None:
            await interaction.response.send_message(
                "Run this inside a VANTA investigation category.", ephemeral=True
            )
            return
        await interaction.response.send_modal(SolutionModal(self, ic.investigation_id))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        found = self.state.find_by_channel(message.channel.id)
        if not found:
            return
        ic, agent_id = found
        async with message.channel.typing():
            try:
                result = await self.client.send_message(
                    ic.investigation_id, agent_id, message.content
                )
            except VantaAPIError as exc:
                await message.reply(f"(error contacting agent: {exc.detail})")
                return

        await message.reply(_truncate(result["text"]))

        if result.get("new_evidence"):
            guild = message.guild
            evidence_channel = guild.get_channel(ic.evidence_channel_id) if guild else None
            if evidence_channel:
                for ev in result["new_evidence"]:
                    embed = discord.Embed(
                        description=_truncate(ev["content"]),
                        color=discord.Color.gold(),
                    )
                    embed.set_footer(text=f"New evidence from {ev['source_agent_id']}")
                    await evidence_channel.send(embed=embed)


async def setup(bot: commands.Bot, client: VantaClient, state: BotState):
    await bot.add_cog(ContestantCog(bot, client, state))

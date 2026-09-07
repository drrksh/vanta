from __future__ import annotations

import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from bot.adapters.state import BotState
from bot.adapters.vanta_client import VantaClient
from bot.cogs import admin as admin_cog
from bot.cogs import contestant as contestant_cog

load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("vanta.bot")

DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class VantaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!vanta-unused-", intents=intents)
        self.vanta_client = VantaClient()
        self.vanta_state = BotState()

    async def setup_hook(self):
        await contestant_cog.setup(self, self.vanta_client, self.vanta_state)
        await admin_cog.setup(self, self.vanta_client, self.vanta_state)


bot = VantaBot()


@bot.event
async def on_ready():
    log.info("Logged in as %s (id=%s)", bot.user, bot.user.id if bot.user else "?")
    try:
        synced = await bot.tree.sync()
        log.info("Synced %d application commands", len(synced))
    except Exception:
        log.exception("Failed to sync application commands")


def main():
    if not DISCORD_BOT_TOKEN:
        raise SystemExit(
            "DISCORD_BOT_TOKEN is not set. Copy discord_bot/.env.example to "
            "discord_bot/.env and fill it in."
        )
    bot.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()

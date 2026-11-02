"""Discord bot that posts the WARDOGS gold bar price every hour, with a chart."""

import logging
import os
from datetime import time, timezone

import aiohttp
import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv

from message import build_message, check_alert, load_state, save_state

load_dotenv()
TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
CHART_DAYS = int(os.getenv("CHART_DAYS", "30"))
# "true" = skip the hourly post when the price hasn't moved since the last one.
ONLY_ON_CHANGE = os.getenv("ONLY_POST_ON_CHANGE", "false").lower() == "true"
# Ping @everyone when the price drops below this (0 turns the alert off).
ALERT_BELOW = int(os.getenv("ALERT_BELOW", "200000"))

EVERY_HOUR = [time(hour=h, minute=0, tzinfo=timezone.utc) for h in range(24)]
RANGES = {"7d": 7, "30d": 30, "90d": 90, "all": None}

log = logging.getLogger("gold-bot")


class GoldBot(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.http_session: aiohttp.ClientSession | None = None

    async def setup_hook(self) -> None:
        self.http_session = aiohttp.ClientSession()
        await self.tree.sync()
        self.hourly_post.start()

    async def close(self) -> None:
        if self.http_session:
            await self.http_session.close()
        await super().close()

    @tasks.loop(time=EVERY_HOUR)
    async def hourly_post(self) -> None:
        channel = self.get_channel(CHANNEL_ID) or await self.fetch_channel(CHANNEL_ID)
        state = load_state()
        last = state.get("last_posted_price")
        try:
            market, embed, file = await build_message(self.http_session, CHART_DAYS, last)
        except Exception:
            log.exception("Could not fetch the gold price")
            return
        if ONLY_ON_CHANGE and last == market.current:
            log.info("Price unchanged at %s, skipping post", market.current)
            return
        alert = check_alert(market.current, state, ALERT_BELOW)
        await channel.send(
            content=alert,
            embed=embed,
            file=file,
            allowed_mentions=discord.AllowedMentions(everyone=True),
        )
        state["last_posted_price"] = market.current
        save_state(state)
        log.info("Posted gold price %s", market.current)

    @hourly_post.before_loop
    async def before_hourly_post(self) -> None:
        await self.wait_until_ready()


bot = GoldBot()


@bot.tree.command(name="gold", description="Show the current WARDOGS gold bar price with a chart")
@app_commands.describe(period="How much history to chart")
@app_commands.choices(period=[app_commands.Choice(name=k, value=k) for k in RANGES])
async def gold(interaction: discord.Interaction, period: app_commands.Choice[str] | None = None) -> None:
    await interaction.response.defer(thinking=True)
    days = RANGES[period.value] if period else CHART_DAYS
    try:
        _, embed, file = await build_message(bot.http_session, days, None)
    except Exception:
        log.exception("Could not fetch the gold price")
        await interaction.followup.send("Couldn't reach MetaForge right now, try again in a minute.")
        return
    await interaction.followup.send(embed=embed, file=file)


@bot.event
async def on_ready() -> None:
    log.info("Logged in as %s, posting to channel %s every hour", bot.user, CHANNEL_ID)


if __name__ == "__main__":
    bot.run(TOKEN, root_logger=True)

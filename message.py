"""Builds the Discord message (embed + chart) shared by the bot and the webhook poster."""

import json
from pathlib import Path

import aiohttp
import discord

from chart import render_chart, short_cash
from market import Market, fetch_market

STATE_FILE = Path(__file__).with_name("state.json")
GOLD = discord.Colour.from_str("#eda100")


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state))


def check_alert(price: int, state: dict, threshold: int) -> str | None:
    """@everyone text when the price first drops below `threshold`, else None.

    Pings once per drop: it re-arms only after the price goes back above the threshold,
    so the channel isn't pinged every hour while the price stays low.
    """
    if threshold <= 0:
        return None
    below = price < threshold
    already_alerted = state.get("alerted_below", False)
    state["alerted_below"] = below
    if below and not already_alerted:
        return f"@everyone 🚨 Gold bars are below **{threshold:,}** cash! Now **{price:,}** per bar."
    return None


def pct(change: float | None) -> str:
    if change is None:
        return "n/a"
    arrow = "🟢 ▲" if change > 0 else "🔴 ▼" if change < 0 else "⚪"
    return f"{arrow} {change * 100:+.1f}%"


def build_embed(market: Market, last_posted: int | None) -> discord.Embed:
    cur = market.current
    embed = discord.Embed(
        title="🪙 WARDOGS gold bar price",
        description=f"## {cur:,} cash per gold bar",
        colour=GOLD,
        url="https://metaforge.app/wardogs/market",
    )
    if last_posted is not None:
        delta = cur - last_posted
        embed.add_field(
            name="Since last post",
            value="No change" if delta == 0 else f"{pct(delta / last_posted)} ({delta:+,})",
            inline=False,
        )
    embed.add_field(name="24 hours", value=pct(market.change(1)))
    embed.add_field(name="7 days", value=pct(market.change(7)))
    embed.add_field(name="30 days", value=pct(market.change(30)))

    avg30 = market.average(30)
    embed.add_field(name="30-day average", value=f"{short_cash(avg30)} ({pct((cur - avg30) / avg30)})")
    embed.add_field(name="All-time low", value=f"{market.all_time_low:,}")
    embed.add_field(name="All-time high", value=f"{market.all_time_high:,}")

    embed.add_field(
        name="Rate last updated",
        value=f"<t:{int(market.updated_at.timestamp())}:R>",
        inline=False,
    )
    embed.set_image(url="attachment://gold.png")
    embed.set_footer(text="Data: metaforge.app · the in-game rate changes about once a day")
    return embed


async def build_message(
    session: aiohttp.ClientSession, days: int | None, last_posted: int | None
) -> tuple[Market, discord.Embed, discord.File]:
    market = await fetch_market(session)
    chart = render_chart(market, days)
    file = discord.File(chart, filename="gold.png")
    return market, build_embed(market, last_posted), file

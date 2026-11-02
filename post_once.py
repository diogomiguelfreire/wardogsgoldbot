"""Posts the gold price once through a Discord webhook, then exits.

Used by the hourly GitHub Actions workflow. Run with --dry-run to print the
message and save the chart to gold_preview.png instead of posting.
"""

import asyncio
import os
import sys

import aiohttp
import discord
from dotenv import load_dotenv

from message import build_message, check_alert, load_state, save_state

load_dotenv()
CHART_DAYS = int(os.getenv("CHART_DAYS") or "30")
ONLY_ON_CHANGE = (os.getenv("ONLY_POST_ON_CHANGE") or "false").lower() == "true"
ALERT_BELOW = int(os.getenv("ALERT_BELOW") or "200000")


async def main(dry_run: bool) -> None:
    state = load_state()
    last = state.get("last_posted_price")

    async with aiohttp.ClientSession() as session:
        market, embed, file = await build_message(session, CHART_DAYS, last)

        if ONLY_ON_CHANGE and last == market.current:
            print(f"Price unchanged at {market.current:,}, skipping post")
            return

        alert = check_alert(market.current, state, ALERT_BELOW)

        if dry_run:
            with open("gold_preview.png", "wb") as f:
                f.write(file.fp.read())
            if alert:
                print(alert)
            print(embed.description)
            for field in embed.fields:
                print(f"  {field.name}: {field.value}")
            print("Chart saved to gold_preview.png (nothing posted)")
            return

        webhook = discord.Webhook.from_url(os.environ["DISCORD_WEBHOOK_URL"], session=session)
        await webhook.send(
            content=alert,
            embed=embed,
            file=file,
            username="WARDOGS Gold Price",
            allowed_mentions=discord.AllowedMentions(everyone=True),
            wait=True,
        )

    state["last_posted_price"] = market.current
    save_state(state)
    print(f"Posted gold price {market.current:,}")


if __name__ == "__main__":
    asyncio.run(main(dry_run="--dry-run" in sys.argv))

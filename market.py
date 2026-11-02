"""Fetches the WARDOGS gold bar exchange rate from MetaForge."""

from dataclasses import dataclass
from datetime import datetime, timezone

import aiohttp

API_URL = "https://metaforge.app/api/wardogs/market"
USER_AGENT = "wardogs-gold-discord-bot/1.0"


@dataclass
class Point:
    when: datetime
    price: int


@dataclass
class Market:
    points: list[Point]
    updated_at: datetime
    all_time_low: int
    all_time_high: int

    @property
    def current(self) -> int:
        return self.points[-1].price

    def window(self, days: int | None) -> list[Point]:
        """Last `days` daily points (all of them when days is None)."""
        if days is None:
            return self.points
        return self.points[-(days + 1):]

    def change(self, days: int) -> float | None:
        """Fractional change versus `days` ago, or None if history is too short."""
        if len(self.points) <= days:
            return None
        then = self.points[-1 - days].price
        return (self.current - then) / then

    def average(self, days: int) -> float:
        pts = self.points[-days:]
        return sum(p.price for p in pts) / len(pts)


def _ms(ts: int) -> datetime:
    return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)


async def fetch_market(session: aiohttp.ClientSession) -> Market:
    async with session.get(
        API_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=aiohttp.ClientTimeout(total=20),
    ) as resp:
        resp.raise_for_status()
        data = await resp.json()

    points = [Point(_ms(p["t"]), int(p["price"])) for p in data["points"]]
    points.sort(key=lambda p: p.when)
    if not points:
        raise ValueError("MetaForge returned no price points")

    stats = data.get("stats", {})
    prices = [p.price for p in points]
    return Market(
        points=points,
        updated_at=_ms(data["updatedAt"]),
        all_time_low=int(stats.get("min", min(prices))),
        all_time_high=int(stats.get("max", max(prices))),
    )

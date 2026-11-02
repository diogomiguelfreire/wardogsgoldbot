"""Renders the gold bar price chart as a PNG for Discord."""

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from market import Market, Point  # noqa: E402

# Dark theme, since most Discord clients run dark.
SURFACE = "#1a1a19"
INK = "#f0efec"
INK_2 = "#c3c2b7"
MUTED = "#898781"
GRID = "#2c2c2a"
AXIS = "#383835"
SERIES = "#3987e5"
SERIES_SOFT = "#184f95"


def short_cash(value: float, _pos=None) -> str:
    if value < 0:
        return ""  # padding below the lowest point, not a real price
    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:.0f}"


def _style(ax) -> None:
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.grid(axis="x", visible=False)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)
    ax.yaxis.set_major_formatter(FuncFormatter(short_cash))


def _label(ax, point: Point, text: str, above: bool) -> None:
    ax.annotate(
        f"{text} {short_cash(point.price)}",
        (point.when, point.price),
        xytext=(0, 10 if above else -14),
        textcoords="offset points",
        ha="center",
        va="bottom" if above else "top",
        fontsize=9,
        color=INK_2,
    )


def render_chart(market: Market, days: int | None = 30) -> io.BytesIO:
    recent = market.window(days)
    # Context panel: last 90 days, or everything when the main window is already that wide.
    wide = days is None or days >= 90
    history = market.points if wide else market.window(90)

    if days is None:
        # The main panel already shows everything, so skip the context panel.
        fig, top = plt.subplots(figsize=(10, 4.6), dpi=110)
        bottom = None
    else:
        fig, (top, bottom) = plt.subplots(
            2, 1, figsize=(10, 6.2), dpi=110,
            gridspec_kw={"height_ratios": [3, 1.2], "hspace": 0.45},
        )
    fig.patch.set_facecolor(SURFACE)

    # Top: the selected window, with markers and labels on the key points.
    xs = [p.when for p in recent]
    ys = [p.price for p in recent]
    _style(top)
    top.plot(xs, ys, color=SERIES, linewidth=2, solid_capstyle="round", zorder=3)
    if len(recent) <= 45:
        top.scatter(xs, ys, s=22, color=SERIES, edgecolors=SURFACE, linewidths=1.5, zorder=4)
    span = max(ys) - min(ys) or max(ys) * 0.1
    floor = min(ys) - span * 0.18
    top.set_ylim(floor, max(ys) + span * 0.18)
    top.fill_between(xs, ys, floor, color=SERIES, alpha=0.08, zorder=2)

    hi = max(recent, key=lambda p: p.price)
    lo = min(recent, key=lambda p: p.price)
    cur = recent[-1]
    _label(top, hi, "High", above=True)
    if lo is not hi:
        _label(top, lo, "Low", above=False)
    if cur is not hi and cur is not lo:
        _label(top, cur, "Now", above=True)

    top.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y" if days is None else "%d %b"))
    top.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=8))
    window_name = f"last {days} days" if days else "all time"
    top.set_title(
        f"WARDOGS gold bar price ({window_name})",
        loc="left", color=INK, fontsize=13, fontweight="bold", pad=26,
    )
    top.text(
        0, 1.03, "Cash per gold bar, one reading per day",
        transform=top.transAxes, color=MUTED, fontsize=9, va="bottom",
    )

    # Bottom: wider history for context, with the top window shaded.
    if bottom is not None:
        _style(bottom)
        bottom.plot(
            [p.when for p in history], [p.price for p in history],
            color=SERIES_SOFT, linewidth=1.5,
        )
        bottom.axvspan(xs[0], xs[-1], color=SERIES, alpha=0.15, linewidth=0)
        bottom.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y" if wide else "%d %b"))
        bottom.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=7))
        bottom.yaxis.set_major_locator(plt.MaxNLocator(3))
        bottom.set_title(
            "Full history (shaded = above)" if wide else "Last 90 days (shaded = above)",
            loc="left", color=INK_2, fontsize=10, pad=6,
        )

    fig.text(0.99, 0.01, "Data: metaforge.app", color=MUTED, fontsize=8, ha="right")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=SURFACE, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    buf.seek(0)
    return buf

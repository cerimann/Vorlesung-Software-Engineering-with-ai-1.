"""Stack Overflow questions over time, with AI milestone markers.

Fetches the number of new Stack Overflow questions per month from the
Stack Exchange API, caches them as CSV and plots the monthly totals together
with a 12-month moving average and markers for major AI breakthroughs.

Usage:
    uv run v1.py                  # fetch (resumes from cache) + plot 2008-08..2024-12
    uv run v1.py --end 2025-12    # extend the data range
    uv run v1.py --no-fetch       # plot from the cached CSV only

Without an API key the Stack Exchange API allows 300 requests per IP and day;
one request is needed per month. Set SE_API_KEY to raise the quota to 10,000.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import requests  # noqa: E402

API_URL = "https://api.stackexchange.com/2.3/questions"
ROOT = Path(__file__).parent
CACHE_CSV = ROOT / "data" / "so_questions_monthly.csv"
OUTPUT_PNG = ROOT / "output" / "stackoverflow_questions.png"

# Stack Overflow opened its public beta on 2008-07-31, so July 2008 holds a
# single day of questions and would distort the start of the curve.
DEFAULT_START = "2008-08"
DEFAULT_END = "2024-12"

# (month, label, colour) - from the course's interactive AI timeline.
MILESTONES = [
    ("2017-06", "Transformer\nJun 2017", "#6a3d9a"),
    ("2022-11", "ChatGPT\nNov 2022", "#e31a1c"),
    ("2023-03", "GPT-4\nMär 2023", "#ff7f00"),
    ("2023-08", "Cursor & KI-IDEs\nAug 2023", "#1f78b4"),
    ("2025-02", "Claude Code\nFeb 2025", "#b15928"),
    ("2025-02", "GitHub Copilot\nAgent Mode\nFeb 2025", "#33a02c"),
]

# strftime's %b depends on the OS locale; spell German month names explicitly.
MONTHS_DE = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
             "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]


def month_de(ts: pd.Timestamp) -> str:
    return f"{MONTHS_DE[ts.month - 1]} {ts.year}"


def month_bounds(period: pd.Period) -> tuple[int, int]:
    """Return the inclusive [first, last] second of a month as UTC epoch seconds."""
    start = int(period.start_time.tz_localize("UTC").timestamp())
    end = int((period + 1).start_time.tz_localize("UTC").timestamp()) - 1
    return start, end


def fetch_month(
    session: requests.Session, period: pd.Period, api_key: str | None = None
) -> int:
    """Ask the API how many (non-deleted) questions were created in `period`."""
    fromdate, todate = month_bounds(period)
    params = {
        "site": "stackoverflow",
        "fromdate": fromdate,
        "todate": todate,
        "filter": "total",  # built-in filter: return only the count, no items
    }
    if api_key:
        params["key"] = api_key

    for attempt in range(5):
        response = session.get(API_URL, params=params, timeout=30)
        data = response.json()
        if response.ok and "total" in data:
            if "backoff" in data:  # the API asks clients to pause sometimes
                time.sleep(data["backoff"])
            return int(data["total"])
        if data.get("error_id") == 502:  # throttle_violation: daily quota used up
            raise RuntimeError(f"API quota exhausted: {data.get('error_message')}")
        time.sleep(2**attempt)
    raise RuntimeError(f"API request for {period} failed: {data}")


def load_cache(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    df = pd.read_csv(path, dtype={"month": str, "questions": int})
    return dict(zip(df["month"], df["questions"]))


def save_cache(counts: dict[str, int], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(sorted(counts.items()), columns=["month", "questions"])
    df.to_csv(path, index=False)


def fetch_range(start: str, end: str, cache: Path = CACHE_CSV) -> dict[str, int]:
    """Fetch every month in [start, end], skipping months already in the cache."""
    counts = load_cache(cache)
    missing = [p for p in pd.period_range(start, end, freq="M") if str(p) not in counts]
    if not missing:
        return counts

    print(f"Fetching {len(missing)} month(s) from the Stack Exchange API ...")
    api_key = os.environ.get("SE_API_KEY")
    with requests.Session() as session:
        for i, period in enumerate(missing, 1):
            counts[str(period)] = fetch_month(session, period, api_key)
            # Save after every month so an interrupted run can resume.
            save_cache(counts, cache)
            print(f"  [{i:3}/{len(missing)}] {period}: {counts[str(period)]:>7,}")
            time.sleep(0.2)  # stay far below the 30 requests/second limit
    return counts


def build_series(counts: dict[str, int], start: str, end: str) -> pd.DataFrame:
    """Monthly counts in [start, end] plus a trailing 12-month moving average."""
    months = pd.period_range(start, end, freq="M")
    missing = [str(p) for p in months if str(p) not in counts]
    if missing:
        raise ValueError(f"No data for {len(missing)} month(s), e.g. {missing[0]}")

    df = pd.DataFrame(
        {"questions": [counts[str(p)] for p in months]},
        index=months.to_timestamp(),
    )
    # Trailing window; the first 11 months stay NaN instead of showing a
    # misleading average over fewer than 12 values.
    df["ma12"] = df["questions"].rolling(window=12, min_periods=12).mean()
    return df


def plot(df: pd.DataFrame, out: Path = OUTPUT_PNG) -> Path:
    fig, ax = plt.subplots(figsize=(14, 7), dpi=150)

    ax.plot(df.index, df["questions"], color="#9ecae1", linewidth=1.2,
            label="Fragen pro Monat")
    ax.plot(df.index, df["ma12"], color="#08519c", linewidth=2.6,
            label="Gleitender Durchschnitt (12 Monate)")

    peak_month = df["questions"].idxmax()
    peak = df.loc[peak_month, "questions"]
    ax.annotate(
        f"Höchststand\n{peak:,.0f} ({month_de(peak_month)})".replace(",", "."),
        xy=(peak_month, peak), xytext=(-120, 25), textcoords="offset points",
        fontsize=9, arrowprops={"arrowstyle": "->", "color": "#555"},
    )

    # The 2025 milestones lie after the default data range, so extend the
    # x-axis far enough to show them.
    last_milestone = pd.Timestamp(max(m for m, _, _ in MILESTONES))
    x_max = max(df.index[-1], last_milestone) + pd.DateOffset(months=5)
    ax.set_xlim(df.index[0], x_max)
    y_max = df["questions"].max() * 1.32
    ax.set_ylim(0, y_max)

    if df.index[-1] < last_milestone:
        ax.axvspan(df.index[-1] + pd.DateOffset(months=1), x_max,
                   color="#d9d9d9", alpha=0.6, zorder=0,
                   label="außerhalb des Datenzeitraums")

    ax.axvspan(pd.Timestamp("2022-11"), x_max, color="#fde0dd", alpha=0.35,
               zorder=0, label="Ära generativer KI")

    # Staggered label heights (in axis fractions) so close milestones don't overlap.
    levels = [0.97, 0.97, 0.85, 0.73, 0.61, 0.46]
    for (month, label, colour), level in zip(MILESTONES, levels):
        x = pd.Timestamp(month)
        ax.axvline(x, color=colour, linestyle="--", linewidth=1.4, alpha=0.9)
        ax.annotate(
            label, xy=(x, level), xycoords=("data", "axes fraction"),
            xytext=(-6, 0), textcoords="offset points", ha="right", va="top",
            fontsize=9, color=colour, fontweight="bold",
            bbox={"boxstyle": "round,pad=0.3", "facecolor": "white",
                  "edgecolor": colour, "alpha": 0.9},
        )

    ax.set_title(
        f"Stack Overflow: neue Fragen pro Monat "
        f"({df.index[0]:%Y}–{df.index[-1]:%Y}) und KI-Meilensteine",
        fontsize=15, fontweight="bold", loc="left",
    )
    ax.set_ylabel("Neue Fragen pro Monat")
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"{v / 1000:.0f}k" if v else "0"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    # 2015-2020 below ~130k is empty, so the legend sits there.
    ax.legend(loc="lower left", bbox_to_anchor=(0.43, 0.03), frameon=True,
              facecolor="white", edgecolor="#ddd", framealpha=0.95)
    fig.text(0.01, 0.01,
             "Quelle: Stack Exchange API (api.stackexchange.com/2.3/questions), "
             f"nur nicht gelöschte Fragen. Daten {month_de(df.index[0])} – "
             f"{month_de(df.index[-1])}.",
             fontsize=8, color="#777")

    fig.tight_layout(rect=(0, 0.02, 1, 1))
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    plt.close(fig)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", default=DEFAULT_START, help="erster Monat, YYYY-MM")
    parser.add_argument("--end", default=DEFAULT_END, help="letzter Monat, YYYY-MM")
    parser.add_argument("--no-fetch", action="store_true",
                        help="nur den CSV-Cache verwenden, keine API-Anfragen")
    parser.add_argument("--out", type=Path, default=OUTPUT_PNG)
    args = parser.parse_args(argv)

    if pd.Period(args.end, freq="M") >= pd.Period.now(freq="M"):
        parser.error("--end muss ein abgeschlossener Monat sein")

    counts = load_cache(CACHE_CSV) if args.no_fetch else fetch_range(args.start, args.end)
    df = build_series(counts, args.start, args.end)
    out = plot(df, args.out)
    print(f"Plot gespeichert: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

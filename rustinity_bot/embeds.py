from __future__ import annotations

import logging
from datetime import datetime
from typing import Collection, Dict, Mapping

import discord
import pytz

from .config import settings
from .rustinity_client import METRICS
from .storage import get_clan_metric_changes

logger = logging.getLogger(__name__)

# Which metrics get shown in the main leaderboard embed
DISPLAY_METRICS = [
    "kill_player",  # PvP kills
    "looted_hackable",  # Hackable crates looted
    "gathered_sulfur_ore",  # Sulfur ore gathered
    "boom_rocket_basic",  # Rockets fired
    "looted_bradley_crates",  # Bradley crates looted
]

# Metrics to use in the 12h trend embed
TREND_METRICS = DISPLAY_METRICS


# ---------------------------------------------------------------------------
# HELP / STATUS EMBEDS
# ---------------------------------------------------------------------------


def build_help_embed() -> discord.Embed:
    """
    Build an embed that documents all bot slash commands.
    """
    embed = discord.Embed(
        title="Rustinity Bot Commands",
        description=(
            "These are the available **slash** commands.\n"
            "Type `/` in the chat box to see them."
        ),
        color=0x2ECC71,
    )

    embed.add_field(
        name="/help",
        value="Show this help message.",
        inline=False,
    )
    embed.add_field(
        name="/link `<steamId64>`",
        value="Link your Steam account so the bot can look up your stats.",
        inline=False,
    )
    embed.add_field(
        name="/me",
        value="Show your linked player stats (requires that you already used `/link`).",
        inline=False,
    )
    embed.add_field(
        name="/status",
        value="Show the current tracking status and list of watched clans.",
        inline=False,
    )
    embed.add_field(
        name="/clear",
        value="Clear recent messages in the channel (keeps the persistent bot embeds).",
        inline=False,
    )
    embed.add_field(
        name="/toggle",
        value="Toggle tracking on or off.",
        inline=False,
    )
    embed.add_field(
        name="/track `<clan>`",
        value="Add a clan to the watch list.",
        inline=False,
    )
    embed.add_field(
        name="/untrack `<clan>`",
        value="Remove a clan from the watch list.",
        inline=False,
    )
    embed.add_field(
        name="/trackplayer `<steamId64>`",
        value="Start tracking a specific player by SteamID on all leaderboards.",
        inline=False,
    )
    embed.add_field(
        name="/untrackplayer `<steamId64>`",
        value="Stop tracking a previously tracked player.",
        inline=False,
    )
    embed.add_field(
        name="/addplayer `<clan>` `<steamId64>`",
        value=(
            "Associate a player with a clan for our manual checks and track them even "
            "if they don't show under that clan on the leaderboard."
        ),
        inline=False,
    )
    embed.add_field(
        name="/unaddplayer `<steamId64>`",
        value="Remove a player's manual clan association.",
        inline=False,
    )

    return embed


def build_status_embed(
    tracking_enabled: bool,
    watched_clans: Collection[str],
) -> discord.Embed:
    """
    Build an embed that shows current tracking status and watched clans.

    Args:
        tracking_enabled: Whether tracking is currently enabled.
        watched_clans:    Collection of clan names being watched.
    """
    tracking_state = "🟢 ON" if tracking_enabled else "🔴 OFF"
    color = 0x2ECC71 if tracking_enabled else 0xE74C3C

    if watched_clans:
        watched_list = "\n".join(f"• `{name}`" for name in sorted(set(watched_clans)))
    else:
        watched_list = "_No clans are currently monitored_"

    embed = discord.Embed(
        title="📊 Bot Tracking Status",
        description="Current tracking state and watched clans.",
        color=color,
    )

    embed.add_field(
        name="Tracking",
        value=tracking_state,
        inline=False,
    )

    embed.add_field(
        name="Watched Clans",
        value=watched_list,
        inline=False,
    )

    embed.add_field(
        name="Total Watched",
        value=str(len(set(watched_clans))),
        inline=True,
    )

    embed.set_footer(
        text=(
            "Use /toggle to toggle tracking • "
            "Use /track <clan> / /untrack <clan> to manage watched clans"
        )
    )

    return embed


# ---------------------------------------------------------------------------
# MAIN LEADERBOARD (WALOBOTS) EMBED
# ---------------------------------------------------------------------------


def build_walobots_embed(
    stats_for_metrics: Mapping[str, Mapping[str, dict]],
) -> discord.Embed:
    """
    Build main leaderboard embed showing #1 and #2 clans per metric.

    Args:
        stats_for_metrics: mapping like {metric_key: {"top1": row, "top2": row_or_none}, ...}
                           rows should be leaderboard entries returned from the API.
    """
    embed = discord.Embed(
        title="Clan Leaderboard (Top 2)",
        color=0x00AAFF,
    )

    # Time footer: Berlin + EST (time only)
    berlin = pytz.timezone("Europe/Berlin")
    time_berlin = datetime.now(berlin).strftime("%H:%M:%S")
    eastern = pytz.timezone("US/Eastern")
    time_eastern = datetime.now(eastern).strftime("%H:%M:%S")

    server_label = settings.server_id or "unknown"
    embed.set_footer(
        text=(
            f"Server: {server_label}  •  "
            f"Updated: {time_berlin} (Berlin) / {time_eastern} (EST)"
        )
    )

    for metric_key in DISPLAY_METRICS:
        metric_info = METRICS.get(metric_key)
        if not metric_info:
            logger.debug("Metric %s not defined in METRICS, skipping.", metric_key)
            continue

        label = metric_info["label"]
        sort_by = metric_info["sortBy"]

        metric_stats = stats_for_metrics.get(metric_key)
        if not metric_stats:
            embed.add_field(name=label, value="No data.", inline=False)
            continue

        lines = []

        top1 = metric_stats.get("top1")
        top2 = metric_stats.get("top2")

        if top1:
            clan1 = top1.get("clanName", "Unknown")
            rank1 = top1.get("rank", "?")
            stats1 = top1.get("stats", {}) or {}
            val1 = stats1.get(sort_by, 0)
            try:
                val1_int = int(val1)
            except (TypeError, ValueError):
                val1_int = 0
            lines.append(f"🥇 #{rank1} **{clan1}** — {val1_int:,}")

        if top2:
            clan2 = top2.get("clanName", "Unknown")
            rank2 = top2.get("rank", "?")
            stats2 = top2.get("stats", {}) or {}
            val2 = stats2.get(sort_by, 0)
            try:
                val2_int = int(val2)
            except (TypeError, ValueError):
                val2_int = 0
            lines.append(f"🥈 #{rank2} **{clan2}** — {val2_int:,}")

        if not lines:
            lines = ["No data."]

        embed.add_field(
            name=label,
            value="\n".join(lines),
            inline=False,
        )

    return embed


# ---------------------------------------------------------------------------
# 12-HOUR TREND EMBED
# ---------------------------------------------------------------------------


def build_trend_embed() -> discord.Embed:
    """
    Build a separate embed showing 12h trends for each trend metric.

    Uses the historical metric data saved in SQLite via storage.get_clan_metric_changes.
    """
    embed = discord.Embed(title="12-Hour Clan Trend (Top 5)", color=0xFFAA00)

    # Time footer: Berlin + EST, time only
    berlin = pytz.timezone("Europe/Berlin")
    time_berlin = datetime.now(berlin).strftime("%H:%M:%S")
    eastern = pytz.timezone("US/Eastern")
    time_eastern = datetime.now(eastern).strftime("%H:%M:%S")

    server_label = settings.server_id or "unknown"
    embed.set_footer(
        text=(
            f"Server: {server_label}  •  "
            f"Trend window: last 12h  •  "
            f"Updated: {time_berlin} (Berlin) / {time_eastern} (EST)"
        )
    )

    for metric_key in TREND_METRICS:
        metric_info = METRICS.get(metric_key)
        if not metric_info:
            logger.debug(
                "Trend metric %s not defined in METRICS, skipping.", metric_key
            )
            continue

        label = metric_info["label"]
        trend = get_clan_metric_changes(metric_key, hours=12)

        if not trend:
            embed.add_field(name=label, value="No data yet.", inline=False)
            continue

        # Compute delta and latest for each clan
        rows = []
        for clan, info in trend.items():
            start_val = info.get("start", 0.0)
            end_val = info.get("end", 0.0)
            rank = info.get("rank", 0)
            delta = end_val - start_val
            rows.append((clan, delta, end_val, rank))

        # Sort by biggest gain
        rows.sort(key=lambda r: r[1], reverse=True)
        top5 = rows[:5]

        lines = []
        for clan, delta, end_val, rank in top5:
            if delta <= 0:
                continue
            lines.append(
                f"#{rank} **{clan}** — {int(end_val):,}  "
                f"_(Δ +{int(delta):,} in 12h)_"
            )

        if not lines:
            lines = ["No positive gains in last 12 hours."]

        embed.add_field(
            name=label,
            value="\n".join(lines),
            inline=False,
        )

    return embed

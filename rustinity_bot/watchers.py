from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Mapping, Optional, Set, Tuple

import discord
import pytz

from .config import settings
from .embeds import build_trend_embed, build_walobots_embed
from .rustinity_client import (
    METRICS,
    fetch_leaderboard_for_metric,
    fetch_player_leaderboard,
    parse_leaderboard_rows,
)
from .storage import (
    add_clan_metric_snapshot,
    get_watch_clans,
    get_watch_players,
)

logger = logging.getLogger(__name__)

# Alert thresholds for specific metrics. If delta >= threshold, we send a "spike" alert.
ALERT_THRESHOLDS: Mapping[str, float] = {
    "gathered_sulfur_ore": 5000.0,
    "looted_hackable": 2.0,
    "boom_rocket_basic": 50.0,
    "looted_bradley_crates": 2.0,
}

TREND_TOP_N = 5  # how many clans we log per metric

# In-memory caches of last-seen values, for delta calculations between updates.
# Keys:
#   WATCH_CLAN_LAST_VALUES: (group, clan_name, stat_key) -> float
#   WATCH_PLAYER_LAST_VALUES: (group, steam_id, stat_key) -> float
#   LAST_CLAN_METRIC_VALUES: (metric_key, clan_name) -> float
WATCH_CLAN_LAST_VALUES: Dict[Tuple[str, str, str], float] = {}
WATCH_PLAYER_LAST_VALUES: Dict[Tuple[str, str, str], float] = {}
LAST_CLAN_METRIC_VALUES: Dict[Tuple[str, str], float] = {}

# Simple toggle for whether tracking is active. This is in-memory; if you
# want persistence across restarts, you could store this in the DB later.
_tracking_enabled: bool = False


def is_tracking_enabled() -> bool:
    return _tracking_enabled


def set_tracking_enabled(enabled: bool) -> None:
    global _tracking_enabled
    _tracking_enabled = enabled
    state = "ON" if enabled else "OFF"
    logger.info("Tracking toggled %s", state)


async def track_watch_clan_all_stats(
    group: str,
    rows: List[dict],
    alert_channel: discord.abc.Messageable,
) -> int:
    """Compare all stat keys for watched clans in a leaderboard and alert on increases.

    Args:
        group:         Rustinated group name (e.g., "pvp", "pve").
        rows:          Leaderboard entries for this group/metric.
        alert_channel: Where to send alert messages.

    Returns:
        Number of alerts sent.
    """
    watched_clans: Set[str] = {c.lower() for c in get_watch_clans()}
    if not watched_clans:
        return 0

    if not rows:
        return 0

    alerts_sent = 0
    found_any = False

    eastern = pytz.timezone("US/Eastern")

    for row in rows:
        clan_name_raw = str(row.get("name") or row.get("clanName") or "").strip()
        if not clan_name_raw:
            continue

        clan_name = clan_name_raw.lower()
        if clan_name not in watched_clans:
            continue

        found_any = True
        stats = row.get("stats", {}) or {}
        rank = row.get("rank")

        for stat_key, current_val in stats.items():
            # Ignore non-numeric stats
            try:
                current_val = float(current_val)
            except (TypeError, ValueError):
                continue

            cache_key = (group, clan_name, stat_key)
            last_val = WATCH_CLAN_LAST_VALUES.get(cache_key)
            delta = 0.0 if last_val is None else current_val - last_val

            WATCH_CLAN_LAST_VALUES[cache_key] = current_val

            if delta <= 0:
                continue

            time_str = datetime.now(eastern).strftime("%Y-%m-%d %H:%M:%S")
            msg = (
                f"[WATCH] Clan `{clan_name_raw}` had a stat change "
                f"for `{stat_key}` in group `{group}`:\n"
                f"Δ +{int(delta):,} (now {int(current_val):,})\n"
                f"Time: {time_str}"
            )
            if rank is not None:
                msg += f" • Rank #{rank}"

            if settings.alert_role_id:
                msg = f"<@&{settings.alert_role_id}> " + msg

            try:
                await alert_channel.send(msg)
                alerts_sent += 1
            except Exception as exc:  # noqa: BLE001
                logger.exception("Error sending clan all-stats alert: %s", exc)

    if not found_any:
        logger.debug("No watched clans found in this leaderboard (group=%s).", group)

    return alerts_sent


async def track_watch_players_all_stats(
    group: str,
    rows: List[dict],
    alert_channel: discord.abc.Messageable,
) -> int:
    """Compare all stat keys for watched players in a leaderboard and alert on increases.

    Args:
        group:         Rustinated group name (e.g., "pvp", "pve").
        rows:          Player leaderboard entries for this group.
        alert_channel: Where to send alert messages.

    Returns:
        Number of alerts sent.
    """
    watched_players: Set[str] = set(get_watch_players())
    extra_clans = settings.player_clan_overrides

    if not watched_players and not extra_clans:
        return 0

    if not rows:
        return 0

    alerts_sent = 0
    found_any = False
    eastern = pytz.timezone("US/Eastern")

    for row in rows:
        steam_id = str(row.get("steamId", "")).strip()
        if not steam_id:
            continue

        # Only track if explicitly watched or manually associated
        if steam_id not in watched_players and steam_id not in extra_clans:
            continue

        found_any = True
        username = row.get("username", "Unknown")
        rank = row.get("rank")
        stats = row.get("stats", {}) or {}

        clan_label = extra_clans.get(steam_id) or row.get("clanName") or "Unknown"

        for stat_key, current_val in stats.items():
            try:
                current_val = float(current_val)
            except (TypeError, ValueError):
                continue

            cache_key = (group, steam_id, stat_key)
            last_val = WATCH_PLAYER_LAST_VALUES.get(cache_key)
            delta = 0.0 if last_val is None else current_val - last_val

            WATCH_PLAYER_LAST_VALUES[cache_key] = current_val

            if delta <= 0:
                continue

            time_str = datetime.now(eastern).strftime("%Y-%m-%d %H:%M:%S")
            msg = (
                f"[PLAYER WATCH] `{username}` ({clan_label}) had a stat change for "
                f"`{stat_key}` in group `{group}`:\n"
                f"Δ +{int(delta):,} (now {int(current_val):,})\n"
                f"Time: {time_str}"
            )
            if rank is not None:
                msg += f" • Rank #{rank}"

            if settings.alert_role_id:
                msg = f"<@&{settings.alert_role_id}> " + msg

            try:
                await alert_channel.send(msg)
                alerts_sent += 1
            except Exception as exc:  # noqa: BLE001
                logger.exception("Error sending player all-stats alert: %s", exc)

    if not found_any:
        logger.debug("No watched players found in this leaderboard (group=%s).", group)

    return alerts_sent


async def log_top_and_detect_spikes(
    metric_key: str,
    rows: List[dict],
    sort_by: str,
    alert_channel: discord.abc.Messageable,
) -> int:
    """Log top clans for a metric and detect large spikes in value.

    - Logs top TREND_TOP_N clans into clan_metric_history.
    - Compares current vs last value per clan.
    - Sends alert to alert_channel if delta >= threshold.
    - Excludes the primary clan_name from spike alerts (to avoid spam).

    Returns:
        Number of spike alerts sent.
    """
    threshold = ALERT_THRESHOLDS.get(metric_key)
    alerts_sent = 0

    if not rows:
        return 0

    # Only consider the top N rows for spike detection + logging
    top_rows = rows[:TREND_TOP_N]
    eastern = pytz.timezone("US/Eastern")

    for row in top_rows:
        clan_name_raw = str(row.get("name") or row.get("clanName") or "").strip()
        if not clan_name_raw:
            continue

        stats = row.get("stats", {}) or {}
        raw_val = stats.get(sort_by)
        try:
            current_val = float(raw_val)
        except (TypeError, ValueError):
            continue

        # Log to DB, regardless of threshold
        rank = row.get("rank")
        add_clan_metric_snapshot(
            metric_key=metric_key,
            clan_name=clan_name_raw,
            rank=int(rank) if rank is not None else None,
            value=current_val,
        )

        # No spike detection configured for this metric
        if threshold is None:
            continue

        cache_key = (metric_key, clan_name_raw)
        last_val = LAST_CLAN_METRIC_VALUES.get(cache_key)
        delta = 0.0 if last_val is None else current_val - last_val
        LAST_CLAN_METRIC_VALUES[cache_key] = current_val

        if delta < threshold:
            continue

        # Don't spam alerts for our own clan, if configured
        if clan_name_raw.lower() == settings.clan_name.lower():
            continue

        time_str = datetime.now(eastern).strftime("%Y-%m-%d %H:%M:%S")
        msg = (
            f"[SPIKE] Clan `{clan_name_raw}` had a large increase in **{metric_key}**:\n"
            f"Δ +{int(delta):,} (now {int(current_val):,})\n"
            f"Time: {time_str}"
        )
        if rank is not None:
            msg += f" • Rank #{rank}"

        if settings.alert_role_id:
            msg = f"<@&{settings.alert_role_id}> " + msg

        try:
            await alert_channel.send(msg)
            alerts_sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error sending spike alert: %s", exc)

    return alerts_sent


async def post_walobots_update(bot: discord.Client) -> None:
    """Fetch latest metrics, update the Walobots + trend embeds, and run watchers."""
    channel = bot.get_channel(settings.channel_id)
    if channel is None:
        logger.error("Channel is None — invalid DISCORD_CHANNEL_ID?")
        return

    if not isinstance(channel, discord.abc.Messageable):
        logger.error("Configured channel is not messageable.")
        return

    stats_for_leaderboard: Dict[str, Dict[str, dict]] = {}
    alert_count = 0
    player_rows_cache: Dict[str, List[dict]] = {}

    # 1) Fetch metrics, build top-2 stats, log top clans & detect spikes.
    # We only need to fetch metrics that are:
    #   - shown in the main leaderboard (DISPLAY_METRICS), or
    #   - part of the trend view (TREND_METRICS), or
    #   - have spike alerts configured (ALERT_THRESHOLDS keys).
    metric_keys_to_fetch = set(METRICS.keys())
    # Optionally, if you want to limit to display/trend/alerts only, you could do:
    # from .embeds import DISPLAY_METRICS, TREND_METRICS
    # metric_keys_to_fetch = set(DISPLAY_METRICS) | set(TREND_METRICS) | set(ALERT_THRESHOLDS.keys())

    for metric_key in metric_keys_to_fetch:
        metric_info = METRICS.get(metric_key)
        if not metric_info:
            continue

        try:
            data = fetch_leaderboard_for_metric(metric_key)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error fetching leaderboard for %s: %s", metric_key, exc)
            continue

        rows = parse_leaderboard_rows(data)
        if not rows:
            logger.debug("No rows for metric %s", metric_key)
            continue

        sort_by = metric_info["sortBy"]

        # Build top2 summary for main walobots embed
        top1 = rows[0] if rows else None
        top2 = rows[1] if len(rows) > 1 else None
        stats_for_leaderboard[metric_key] = {"top1": top1, "top2": top2}

        # Store history + detect spikes (only for metrics with a threshold)
        if metric_key in ALERT_THRESHOLDS:
            alert_count += await log_top_and_detect_spikes(
                metric_key=metric_key,
                rows=rows,
                sort_by=sort_by,
                alert_channel=channel,
            )

        # Run clan watcher if tracking is enabled
        if is_tracking_enabled() and get_watch_clans():
            group = metric_info["group"]
            alert_count += await track_watch_clan_all_stats(
                group=group,
                rows=rows,
                alert_channel=channel,
            )

        # Run player watcher if tracking is enabled and we have watchers
        if is_tracking_enabled() and (
            get_watch_players() or settings.player_clan_overrides
        ):
            group = metric_info["group"]
            if group not in player_rows_cache:
                try:
                    pdata = fetch_player_leaderboard(group=group, sort_by=sort_by)
                    player_rows_cache[group] = parse_leaderboard_rows(pdata)
                except Exception as exc:  # noqa: BLE001
                    logger.exception(
                        "Error fetching player leaderboard for group=%s: %s",
                        group,
                        exc,
                    )
                    continue

            alert_count += await track_watch_players_all_stats(
                group=group,
                rows=player_rows_cache[group],
                alert_channel=channel,
            )

    # 2) Update main Walobots embed
    walobots_embed = build_walobots_embed(stats_for_leaderboard)

    if settings.message_id:
        try:
            msg = await channel.fetch_message(settings.message_id)
            await msg.edit(embed=walobots_embed)
        except (discord.NotFound, discord.HTTPException) as exc:
            logger.warning(
                "Failed to edit Walobots message (ID=%s): %s. "
                "Sending a new message instead.",
                settings.message_id,
                exc,
            )
            await channel.send(embed=walobots_embed)
    else:
        await channel.send(embed=walobots_embed)

    # 3) Update trend embed, if configured
    trend_id = settings.trend_message_id
    trend_embed = build_trend_embed()
    if trend_id:
        try:
            tmsg = await channel.fetch_message(trend_id)
            await tmsg.edit(embed=trend_embed)
        except (discord.NotFound, discord.HTTPException) as exc:
            logger.warning(
                "Failed to edit trend message (ID=%s): %s. Sending new one.",
                trend_id,
                exc,
            )
            await channel.send(embed=trend_embed)
    else:
        await channel.send(embed=trend_embed)

    logger.info(
        "Walobots update complete. Metrics=%d, alerts_sent=%d",
        len(stats_for_leaderboard),
        alert_count,
    )

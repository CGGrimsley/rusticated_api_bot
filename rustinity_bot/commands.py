from __future__ import annotations

import asyncio
import logging
from typing import Dict, List

import discord
from discord import app_commands

from .client import bot, refresh_help_embed, refresh_status_embed
from .config import settings
from .embeds import build_help_embed, build_status_embed, build_trend_embed
from .rustinity_client import (
    METRICS,
    fetch_leaderboard_for_metric,
    fetch_player_leaderboard,
    parse_leaderboard_rows,
)
from .storage import (
    add_watch_clan,
    add_watch_player,
    get_linked_steam_id,
    get_watch_clans,
    get_watch_players,
    link_user,
    remove_watch_clan,
    remove_watch_player,
)
from .watchers import is_tracking_enabled, set_tracking_enabled

logger = logging.getLogger(__name__)


# Walobots members: SteamID64 -> Discord user ID
WALOBOTS_PLAYERS: Dict[str, int] = {
    "Steam 64 id here": "discord user id here",  # Replace with actual Discord user ID
    "Steam 64 id here": "discord user id here",  # Replace with actual Discord user ID
    "Steam 64 id here": "discord user id here",  # Replace with actual Discord user ID
    "Steam 64 id here": "discord user id here",  # Replace with actual Discord user ID
    "Steam 64 id here": "discord user id here",  # Replace with actual Discord user ID
    "Steam 64 id here": "discord user id here",  # Replace with actual Discord user ID
}


# ---------------------------------------------------------------------------
# Small async wrappers around the sync Rustinity API client
# ---------------------------------------------------------------------------


async def fetch_player_leaderboard_async(
    group: str,
    sort_by: str,
    limit: int = 50,
) -> dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, fetch_player_leaderboard, group, sort_by, limit
    )


async def fetch_leaderboard_for_metric_async(metric_key: str, limit: int = 50) -> dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, fetch_leaderboard_for_metric, metric_key, limit
    )


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _is_valid_steam_id(steam_id: str) -> bool:
    """Very minimal SteamID64 check."""
    cleaned = steam_id.strip()
    return cleaned.isdigit() and len(cleaned) == 17


def _build_player_stats_embed(
    username: str,
    steam_id: str,
    row: dict,
) -> discord.Embed:
    """Build a stats embed for a single player row (PvP kills group)."""
    stats = row.get("stats", {}) or {}

    kills = stats.get("kill_player", 0)
    deaths = stats.get("death_player", 0)
    kdr = stats.get("kdr", 0)
    playtime = stats.get("playtime", 0)  # seconds
    rank = row.get("rank", "?")

    try:
        kills = int(kills)
    except (TypeError, ValueError):
        kills = 0

    try:
        deaths = int(deaths)
    except (TypeError, ValueError):
        deaths = 0

    try:
        kdr_val = float(kdr)
    except (TypeError, ValueError):
        kdr_val = 0.0

    try:
        playtime = int(playtime)
    except (TypeError, ValueError):
        playtime = 0

    hours = playtime // 3600
    minutes = (playtime % 3600) // 60

    embed = discord.Embed(
        title=f"Stats for {username}",
        description=f"SteamID: `{steam_id}`",
        color=0x00AAFF,
    )
    embed.add_field(
        name="Leaderboard Rank (PvP kills)",
        value=str(rank),
        inline=False,
    )
    embed.add_field(name="Kills", value=str(kills), inline=True)
    embed.add_field(name="Deaths", value=str(deaths), inline=True)
    embed.add_field(name="K/D Ratio", value=f"{kdr_val:.2f}", inline=True)
    embed.add_field(
        name="Playtime (this wipe)",
        value=f"{hours}h {minutes}m",
        inline=False,
    )

    return embed


# ---------------------------------------------------------------------------
# Core commands
# ---------------------------------------------------------------------------


@bot.tree.command(
    name="refreshhelp",
    description="Rebuild and update the persistent help embed message.",
)
@app_commands.default_permissions(manage_guild=True)
async def refresh_help_command(interaction: discord.Interaction) -> None:
    """Regenerate the help embed for the configured HELP_MESSAGE_ID."""
    await interaction.response.defer(ephemeral=True)
    await refresh_help_embed()
    await interaction.followup.send(
        "Help embed refreshed (if HELP_MESSAGE_ID is set).", ephemeral=True
    )


@bot.tree.command(
    name="link",
    description="Link your Discord account to your SteamID (from Rustinated stats).",
)
async def link_command(interaction: discord.Interaction, steam_id: str) -> None:
    """Link the current Discord user to a SteamID64."""
    cleaned = steam_id.strip()

    if not _is_valid_steam_id(cleaned):
        await interaction.response.send_message(
            "Please provide a valid 17-digit numeric SteamID, e.g. `/link 76561198375218320`.",
            ephemeral=True,
        )
        return

    link_user(interaction.user.id, cleaned)
    await interaction.response.send_message(
        f"Linked your Discord account to SteamID: `{cleaned}`",
        ephemeral=True,
    )


@bot.tree.command(
    name="me",
    description="Show your personal stats based on linked SteamID.",
)
async def me_command(interaction: discord.Interaction) -> None:
    """Show personal PvP stats for the caller using their linked SteamID."""
    steam_id = get_linked_steam_id(interaction.user.id)
    if not steam_id:
        await interaction.response.send_message(
            "You don't have a linked SteamID yet. Use `/link 7656...` first.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)

    try:
        data = await fetch_player_leaderboard_async(group="pvp", sort_by="kill_player")
        rows = parse_leaderboard_rows(data)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error fetching player leaderboard for /me: %s", exc)
        await interaction.followup.send(
            "Error fetching player stats from Rustinated. Please try again later.",
            ephemeral=True,
        )
        return

    # Find row by SteamID
    target_row = None
    for row in rows:
        if str(row.get("steamId", "")).strip() == steam_id:
            target_row = row
            break

    if not target_row:
        await interaction.followup.send(
            "I couldn't find you on the current PvP leaderboard. "
            "Make sure you've played this wipe on the configured server.",
            ephemeral=True,
        )
        return

    username = target_row.get("username", "Unknown")
    embed = _build_player_stats_embed(
        username=username, steam_id=steam_id, row=target_row
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(
    name="clear",
    description="Clear recent messages in the channel (keeps main bot embeds).",
)
@app_commands.default_permissions(manage_messages=True)
async def clear_command(interaction: discord.Interaction) -> None:
    """Clear recent messages but keep the persistent Walobots / trend / help / status embeds."""
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(
            "This command can only be used in a text channel.",
            ephemeral=True,
        )
        return

    keep_ids = {
        settings.message_id,
        settings.trend_message_id,
        settings.help_message_id,
        settings.status_message_id,
    }
    keep_ids = {mid for mid in keep_ids if mid}

    await interaction.response.defer(ephemeral=True)

    deleted: List[discord.Message] = []

    async for message in channel.history(limit=200):
        if message.id in keep_ids:
            continue
        if message.pinned:
            continue
        try:
            await message.delete()
            deleted.append(message)
        except discord.HTTPException:
            continue

    confirm = await interaction.followup.send(
        f"Cleared {len(deleted)} messages (kept main embeds).",
        ephemeral=True,
    )

    try:
        await asyncio.sleep(5)
        await confirm.delete()
    except discord.HTTPException:
        pass


@bot.tree.command(
    name="toggle",
    description="Toggle on/off the watch-clan tracking + trend alerts.",
)
@app_commands.default_permissions(administrator=True)
async def toggle_tracking_command(interaction: discord.Interaction) -> None:
    """Toggle tracking on or off."""
    current = is_tracking_enabled()
    new_state = not current
    set_tracking_enabled(new_state)

    state = "enabled" if new_state else "disabled"
    await interaction.response.send_message(
        f"✅ Watch-clan tracking is now **{state}**.",
        ephemeral=True,
    )

    await refresh_status_embed()


@bot.tree.command(
    name="track",
    description="Add a clan to the watch list.",
)
@app_commands.default_permissions(manage_guild=True)
async def track_command(
    interaction: discord.Interaction,
    *,
    clan_name: str | None = None,
) -> None:
    """Add a clan to the DB-backed watch list."""
    if not clan_name or not clan_name.strip():
        await interaction.response.send_message(
            "Usage: `/track <clan name>` (e.g. `/track Walobots`)",
            ephemeral=True,
        )
        return

    cleaned = clan_name.strip()
    add_watch_clan(cleaned)

    await interaction.response.send_message(
        f"✅ Added `{cleaned}` to the watched clans list.",
        ephemeral=True,
    )

    await refresh_status_embed()


@bot.tree.command(
    name="untrack",
    description="Remove a clan from the watch list.",
)
@app_commands.default_permissions(manage_guild=True)
async def untrack_command(
    interaction: discord.Interaction,
    *,
    clan_name: str | None = None,
) -> None:
    """Remove a clan from the DB-backed watch list."""
    if not clan_name or not clan_name.strip():
        await interaction.response.send_message(
            "Usage: `/untrack <clan name>`",
            ephemeral=True,
        )
        return

    cleaned = clan_name.strip()
    remove_watch_clan(cleaned)

    await interaction.response.send_message(
        f"✅ Removed `{cleaned}` from the watched clans list.",
        ephemeral=True,
    )

    await refresh_status_embed()


@bot.tree.command(
    name="help",
    description="Show an embed with available bot commands.",
)
async def help_command(interaction: discord.Interaction) -> None:
    """Send a help embed to the caller (ephemeral)."""
    embed = build_help_embed()
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(
    name="inithelp",
    description="Create a persistent help embed message in this channel.",
)
@app_commands.default_permissions(manage_guild=True)
async def init_help_command(interaction: discord.Interaction) -> None:
    """Create a persistent help embed in the current channel and print its ID."""
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(
            "This command can only be used in a text channel.",
            ephemeral=True,
        )
        return

    embed = build_help_embed()
    msg = await channel.send(embed=embed)

    await interaction.response.send_message(
        f"Help message created with ID `{msg.id}`.\n"
        "To keep it persistent across restarts, set `HELP_MESSAGE_ID` in your `.env` file.",
        ephemeral=True,
    )


@bot.tree.command(
    name="status",
    description="Show current tracking status and watched clans.",
)
async def status_command(interaction: discord.Interaction) -> None:
    """Show current tracking status and watched clans."""
    tracking = is_tracking_enabled()
    watched_clans = get_watch_clans()
    embed = build_status_embed(tracking_enabled=tracking, watched_clans=watched_clans)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(
    name="initstatus",
    description="Create a persistent status embed message in this channel.",
)
@app_commands.default_permissions(manage_guild=True)
async def init_status_command(interaction: discord.Interaction) -> None:
    """Create a persistent status embed in the current channel and print its ID."""
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(
            "This command can only be used in a text channel.",
            ephemeral=True,
        )
        return

    tracking = is_tracking_enabled()
    watched_clans = get_watch_clans()
    embed = build_status_embed(tracking_enabled=tracking, watched_clans=watched_clans)
    msg = await channel.send(embed=embed)

    await interaction.response.send_message(
        f"Status message created with ID `{msg.id}`.\n"
        "To keep it persistent across restarts, set `STATUS_MESSAGE_ID` in your `.env` file.",
        ephemeral=True,
    )


@bot.tree.command(
    name="trackplayer",
    description="Start tracking a specific player by SteamID.",
)
@app_commands.default_permissions(manage_guild=True)
async def track_player_command(
    interaction: discord.Interaction,
    steam_id: str | None = None,
) -> None:
    """Start tracking a specific player by SteamID."""
    if not steam_id or not steam_id.strip():
        await interaction.response.send_message(
            "Usage: `/trackplayer <steamId64>` (17-digit numeric SteamID).",
            ephemeral=True,
        )
        return

    cleaned = steam_id.strip()
    if not _is_valid_steam_id(cleaned):
        await interaction.response.send_message(
            "Please provide a valid 17-digit numeric SteamID.",
            ephemeral=True,
        )
        return

    existing = set(get_watch_players())
    if cleaned in existing:
        await interaction.response.send_message(
            f"Player `{cleaned}` is already being tracked.",
            ephemeral=True,
        )
        return

    add_watch_player(cleaned)
    await interaction.response.send_message(
        f"✅ Now tracking player SteamID `{cleaned}`.",
        ephemeral=True,
    )


@bot.tree.command(
    name="untrackplayer",
    description="Stop tracking a specific player by SteamID.",
)
@app_commands.default_permissions(manage_guild=True)
async def untrack_player_command(
    interaction: discord.Interaction,
    steam_id: str | None = None,
) -> None:
    """Stop tracking a specific player by SteamID."""
    if not steam_id or not steam_id.strip():
        await interaction.response.send_message(
            "Usage: `/untrackplayer <steamId64>`.",
            ephemeral=True,
        )
        return

    cleaned = steam_id.strip()
    remove_watch_player(cleaned)

    await interaction.response.send_message(
        f"✅ Stopped tracking player `{cleaned}`.",
        ephemeral=True,
    )


@bot.tree.command(
    name="walowins",
    description="Announce all leaderboard items where Walobots is #1 this wipe, plus member stats.",
)
async def walowins_command(interaction: discord.Interaction) -> None:
    """
    Announce all leaderboard items where our clan is #1 for this wipe,
    then print individual stats for each Walobots member, @'ing each one.
    """
    await interaction.response.defer()  # public

    clan_display = settings.clan_name or "Walobots"
    clan_lower = clan_display.lower()

    server_id = settings.server_id or "unknown"
    wipe_id = settings.server_wipe_id or "unknown"

    # 1) Clan wins embed
    wins: List[str] = []

    for metric_key, metric_info in METRICS.items():
        try:
            data = await fetch_leaderboard_for_metric_async(metric_key)
            rows = parse_leaderboard_rows(data)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Error fetching leaderboard for walowins (%s): %s", metric_key, exc
            )
            continue

        if not rows:
            continue

        top = rows[0]
        top_name = (top.get("clanName") or top.get("clanTag") or "").strip()
        if top_name.lower() == clan_lower:
            wins.append(metric_info["label"])

    if not wins:
        wins_embed = discord.Embed(
            title=f"{clan_display} — Wipe {wipe_id} Results",
            description=(
                f"{clan_display} has **not** secured 1st place in any tracked "
                f"categories yet for wipe `{wipe_id}`.\n\n"
                "Keep grinding! 💪"
            ),
            color=0xFF5555,
        )
    else:
        items_list = "\n".join(f"• {label}" for label in wins)
        wins_embed = discord.Embed(
            title=f"{clan_display} Wipe Wins 🎉",
            description=(
                f"{clan_display} has won the competition for the following categories "
                f"on wipe `{wipe_id}`:\n\n{items_list}"
            ),
            color=0x55FF55,
        )

    wins_embed.set_footer(
        text=f"Server: {server_id} • Data from Rusticated stats",
    )
    await interaction.followup.send(embed=wins_embed)

    # 2) Player stat print-outs
    try:
        pdata = await fetch_player_leaderboard_async(group="pvp", sort_by="kill_player")
        player_rows = parse_leaderboard_rows(pdata)
    except Exception as exc:  # noqa: BLE001
        await interaction.followup.send(
            f"Error fetching player stats for Walobots members: `{exc}`",
        )
        return

    by_steam: Dict[str, dict] = {}
    for row in player_rows:
        steam = str(row.get("steamId", "")).strip()
        if steam:
            by_steam[steam] = row

    guild = interaction.guild

    for steam_id, discord_id in WALOBOTS_PLAYERS.items():
        row = by_steam.get(steam_id)
        if not row:
            await interaction.followup.send(
                f"Could not find stats for SteamID `{steam_id}` on the PvP leaderboard."
            )
            continue

        username = row.get("username", "Unknown")
        embed = _build_player_stats_embed(username=username, steam_id=steam_id, row=row)

        mention_text = f"<@{discord_id}>"
        if guild is not None:
            member = guild.get_member(discord_id)
            if member:
                mention_text = member.mention

        await interaction.followup.send(content=mention_text, embed=embed)


@bot.tree.command(
    name="inittrend",
    description="Create the initial trend embed message (run once per channel).",
)
@app_commands.default_permissions(administrator=True)
async def init_trend_message(interaction: discord.Interaction) -> None:
    """
    Create the initial trend embed message in this channel.

    You should then set `TREND_MESSAGE_ID` in your `.env` file to keep it
    persistent across restarts so the bot can edit it instead of creating
    new messages every update.
    """
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(
            "This command can only be used in a text channel.",
            ephemeral=True,
        )
        return

    embed = build_trend_embed()
    msg = await channel.send(embed=embed)

    await interaction.response.send_message(
        f"Trend message created with ID `{msg.id}`.\n"
        "To keep it persistent across restarts, set `TREND_MESSAGE_ID` in your `.env` file.",
        ephemeral=True,
    )

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import tasks

from .config import settings
from .embeds import build_help_embed, build_status_embed
from .storage import get_watch_clans
from .watchers import is_tracking_enabled, post_walobots_update

logger = logging.getLogger(__name__)

# Configure basic intents – only enable what we actually need
intents = discord.Intents.default()
intents.message_content = (
    True  # needed if you ever add prefix commands / message parsing
)


class RustinityBot(discord.Client):
    """Core Discord client for the Rustinity bot.

    Exposes:
      - `tree` for slash commands
      - Events (on_ready, etc.)
      - Background tasks (periodic leaderboard updates)
    """

    def __init__(self) -> None:
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        """Called by discord.py when the bot is starting up.

        We sync application commands here once all commands have been registered.
        (Commands are registered in a separate module before `run()` is called.)
        """
        # Sync commands globally (you can also use guild-specific syncs if you prefer)
        synced = await self.tree.sync()
        logger.info("Synced %d application commands.", len(synced))


# Global bot instance used by commands & tasks
bot = RustinityBot()


@bot.event
async def on_ready() -> None:
    """Discord on_ready event handler."""
    logger.info("Bot logged in as %s (ID: %s)", bot.user, bot.user.id)

    # Start the periodic leaderboard/trend update loop if it's not already running
    if not periodic_update.is_running():
        periodic_update.start()

    # Kick off an immediate update once on startup
    await post_walobots_update(bot)


@tasks.loop(minutes=3)
async def periodic_update() -> None:
    """Periodic task that refreshes Walobots + trend embeds and runs watchers."""
    await post_walobots_update(bot)


# ---------------------------------------------------------------------------
# Persistent embed refresh helpers
# ---------------------------------------------------------------------------


async def refresh_help_embed() -> None:
    """Update the persistent help message (if configured) with the latest help embed."""
    if not settings.help_message_id:
        return

    channel = bot.get_channel(settings.channel_id)
    if channel is None or not isinstance(channel, discord.TextChannel):
        logger.warning("Cannot refresh help embed – invalid channel or type.")
        return

    embed = build_help_embed()

    try:
        msg = await channel.fetch_message(settings.help_message_id)
        await msg.edit(embed=embed)
    except discord.NotFound:
        logger.warning(
            "Help message (ID=%s) not found when trying to refresh.",
            settings.help_message_id,
        )
    except discord.HTTPException as exc:  # noqa: BLE001
        logger.exception("HTTPException while refreshing help embed: %s", exc)


async def refresh_status_embed() -> None:
    """Update the persistent status message (if configured) with fresh status data."""
    if not settings.status_message_id:
        return

    channel = bot.get_channel(settings.channel_id)
    if channel is None or not isinstance(channel, discord.TextChannel):
        logger.warning("Cannot refresh status embed – invalid channel or type.")
        return

    # build_status_embed now needs to know if tracking is enabled + which clans we watch
    tracking = is_tracking_enabled()
    watched_clans = get_watch_clans()
    embed = build_status_embed(tracking_enabled=tracking, watched_clans=watched_clans)

    try:
        msg = await channel.fetch_message(settings.status_message_id)
        await msg.edit(embed=embed)
    except discord.NotFound:
        logger.warning(
            "Status message (ID=%s) not found when trying to refresh.",
            settings.status_message_id,
        )
    except discord.HTTPException as exc:  # noqa: BLE001
        logger.exception("HTTPException while refreshing status embed: %s", exc)

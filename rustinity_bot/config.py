from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Set

from dotenv import load_dotenv

# ----------------- dotenv loading -----------------

# Try to load .env from project root. If it's not there, load_dotenv()
# still tries the current working directory, which is fine for most setups.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()


# ----------------- helpers -----------------


def _parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _parse_int(value: str | None, *, default: int | None = None) -> int | None:
    if value is None or value == "":
        return default
    try:
        return int(str(value).strip())
    except ValueError:
        return default


def _parse_overrides(value: str | None) -> Dict[str, str]:
    """
    Parse PLAYER_CLAN_OVERRIDES style value:
        "7656119...:fatalis, 7656111...:win"
    into:
        {"7656119...": "fatalis", "7656111...": "win"}
    """
    result: Dict[str, str] = {}
    if not value:
        return result

    for part in _parse_csv(value):
        if ":" not in part:
            continue
        steam_id, clan_name = part.split(":", 1)
        steam_id = steam_id.strip()
        clan_name = clan_name.strip()
        if steam_id and clan_name:
            result[steam_id] = clan_name
    return result


# ----------------- settings dataclass -----------------


@dataclass(frozen=True)
class Settings:
    # Discord / bot config
    discord_token: str
    channel_id: int
    message_id: int
    alert_role_id: int | None

    trend_message_id: int | None
    help_message_id: int | None
    status_message_id: int | None

    # Rust server / org config
    server_id: str
    server_wipe_id: str
    org_id: int | None

    # Clan / player tracking
    clan_name: str
    watch_clan_names: Set[str]
    watch_player_ids: Set[str]
    player_clan_overrides: Dict[str, str]

    # Storage
    db_path: Path


def load_settings() -> Settings:
    # Required
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set in the environment/.env file.")

    channel_id = _parse_int(os.getenv("DISCORD_CHANNEL_ID"))
    if channel_id is None or channel_id == 0:
        raise RuntimeError("DISCORD_CHANNEL_ID is not set or invalid.")

    message_id = _parse_int(os.getenv("DISCORD_MESSAGE_ID"))
    if message_id is None or message_id == 0:
        raise RuntimeError("DISCORD_MESSAGE_ID is not set or invalid.")

    # Optional but nice to have
    alert_role_id = _parse_int(os.getenv("ALERT_ROLE_ID"), default=None)
    trend_message_id = _parse_int(os.getenv("TREND_MESSAGE_ID"), default=None)
    help_message_id = _parse_int(os.getenv("HELP_MESSAGE_ID"), default=None)
    status_message_id = _parse_int(os.getenv("STATUS_MESSAGE_ID"), default=None)

    server_id = os.getenv("SERVER_ID", "us-2x-monthly-large")
    server_wipe_id = os.getenv("SERVER_WIPE_ID", "4033")
    org_id = _parse_int(os.getenv("ORG_ID"), default=None)

    clan_name = os.getenv("CLAN_NAME", "Walobots")

    watch_clan_names = {
        name.lower() for name in _parse_csv(os.getenv("WATCH_CLAN_NAME"))
    }
    watch_player_ids = set(_parse_csv(os.getenv("WATCH_PLAYER_IDS")))
    player_clan_overrides = _parse_overrides(os.getenv("PLAYER_CLAN_OVERRIDES"))

    # DB path (can be overridden via env if you ever want)
    db_path_str = os.getenv("DB_PATH", "trend.db")
    db_path = (PROJECT_ROOT / db_path_str).resolve()

    return Settings(
        discord_token=token,
        channel_id=channel_id,
        message_id=message_id,
        alert_role_id=alert_role_id,
        trend_message_id=trend_message_id,
        help_message_id=help_message_id,
        status_message_id=status_message_id,
        server_id=server_id,
        server_wipe_id=server_wipe_id,
        org_id=org_id,
        clan_name=clan_name,
        watch_clan_names=watch_clan_names,
        watch_player_ids=watch_player_ids,
        player_clan_overrides=player_clan_overrides,
        db_path=db_path,
    )


# Convenience: a module-level singleton you can import everywhere.
settings = load_settings()

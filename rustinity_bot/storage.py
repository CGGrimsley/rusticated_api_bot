from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Dict, Optional, Set

from .config import settings


def get_db() -> sqlite3.Connection:
    """Return a SQLite connection with row factory set to dict-like rows.

    Uses the DB path from configuration.
    """
    db_path: Path = settings.db_path
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables and apply simple migrations if needed.

    This is safe to call multiple times; it only creates/migrates when required.
    """
    conn = get_db()
    cur = conn.cursor()

    # Historical clan metric snapshots
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS clan_metric_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_key TEXT NOT NULL,
            clan_name  TEXT NOT NULL,
            ts         INTEGER NOT NULL,
            rank       INTEGER,
            value      REAL
        )
        """
    )

    # Discord user -> SteamID links
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_links (
            discord_id TEXT PRIMARY KEY,
            steam_id   TEXT NOT NULL
        )
        """
    )

    # Watched clans (for alerts / trend tracking)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS watch_clans (
            clan_name TEXT PRIMARY KEY
        )
        """
    )

    # Watched players (for player-specific tracking)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS watch_players (
            steam_id TEXT PRIMARY KEY
        )
        """
    )

    conn.commit()

    # Seed watch tables from env-based config (idempotent).
    # This keeps backwards compatibility with existing WATCH_CLAN_NAME
    # and WATCH_PLAYER_IDS env variables.
    for clan_name in settings.watch_clan_names:
        cur.execute(
            "INSERT OR IGNORE INTO watch_clans (clan_name) VALUES (?)",
            (clan_name.lower(),),
        )

    for steam_id in settings.watch_player_ids:
        cur.execute(
            "INSERT OR IGNORE INTO watch_players (steam_id) VALUES (?)",
            (steam_id,),
        )

    conn.commit()
    conn.close()


# ---------- clan metric history helpers ----------


def add_clan_metric_snapshot(
    metric_key: str,
    clan_name: str,
    *,
    rank: Optional[int],
    value: Optional[float],
    ts: Optional[int] = None,
) -> None:
    """Insert a snapshot row for a clan metric.

    Args:
        metric_key: The metric identifier (e.g., "pvp_kills").
        clan_name:  The clan name string as returned by the API.
        rank:       The current rank for this metric, if available.
        value:      The numeric value for this metric (kills, K/D, etc.).
        ts:         Unix timestamp; defaults to current time if not provided.
    """
    if ts is None:
        ts = int(time.time())

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO clan_metric_history (metric_key, clan_name, ts, rank, value)
        VALUES (?, ?, ?, ?, ?)
        """,
        (metric_key, clan_name, ts, rank, value),
    )
    conn.commit()
    conn.close()


def get_clan_metric_changes(
    metric_key: str, hours: int = 12
) -> Dict[str, Dict[str, float]]:
    """Return metric movement for each clan over a time window.

    Returns a dict of:
        {
          "ClanName": {
            "start": <first value in window>,
            "end":   <last value in window>,
            "rank":  <latest known rank in window or 0>,
          },
          ...
        }

    Only data from the last ``hours`` hours is considered (default 12).
    """
    now = int(time.time())
    cutoff = now - hours * 3600

    conn = get_db()
    cur = conn.cursor()

    # For each clan, find earliest and latest timestamps in the window.
    cur.execute(
        """
        SELECT clan_name, MIN(ts) AS first_ts, MAX(ts) AS last_ts
        FROM clan_metric_history
        WHERE metric_key = ? AND ts >= ?
        GROUP BY clan_name
        """,
        (metric_key, cutoff),
    )

    rows = cur.fetchall()
    result: Dict[str, Dict[str, float]] = {}

    for row in rows:
        clan = row["clan_name"]
        first_ts = row["first_ts"]
        last_ts = row["last_ts"]

        # first value
        cur.execute(
            """
            SELECT value
            FROM clan_metric_history
            WHERE metric_key = ? AND clan_name = ? AND ts = ?
            LIMIT 1
            """,
            (metric_key, clan, first_ts),
        )
        first_row = cur.fetchone()
        start_val = first_row["value"] if first_row is not None else None

        # last value + last rank
        cur.execute(
            """
            SELECT value, rank
            FROM clan_metric_history
            WHERE metric_key = ? AND clan_name = ? AND ts = ?
            LIMIT 1
            """,
            (metric_key, clan, last_ts),
        )
        last_row = cur.fetchone()
        if last_row is not None:
            end_val = last_row["value"]
            latest_rank = last_row["rank"]
        else:
            end_val = None
            latest_rank = None

        result[clan] = {
            "start": float(start_val) if start_val is not None else 0.0,
            "end": float(end_val) if end_val is not None else 0.0,
            "rank": int(latest_rank) if latest_rank is not None else 0,
        }

    conn.close()
    return result


# ---------- user link helpers (Discord -> SteamID) ----------


def link_user(discord_id: int, steam_id: str) -> None:
    """Store or update the SteamID associated with a Discord user ID."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO user_links (discord_id, steam_id)
        VALUES (?, ?)
        ON CONFLICT(discord_id) DO UPDATE SET steam_id = excluded.steam_id
        """,
        (str(discord_id), steam_id),
    )
    conn.commit()
    conn.close()


def get_linked_steam_id(discord_id: int) -> Optional[str]:
    """Get the linked SteamID for a given Discord user, if any."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT steam_id FROM user_links WHERE discord_id = ?",
        (str(discord_id),),
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return str(row["steam_id"])
    return None


# ---------- watch list helpers (clans & players) ----------


def add_watch_clan(clan_name: str) -> None:
    """Add a clan to the watched list (case-insensitive)."""
    if not clan_name:
        return

    clan_name = clan_name.lower()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO watch_clans (clan_name) VALUES (?)",
        (clan_name,),
    )
    conn.commit()
    conn.close()


def remove_watch_clan(clan_name: str) -> None:
    """Remove a clan from the watched list."""
    if not clan_name:
        return

    clan_name = clan_name.lower()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM watch_clans WHERE clan_name = ?",
        (clan_name,),
    )
    conn.commit()
    conn.close()


def get_watch_clans() -> Set[str]:
    """Return the set of watched clan names (lowercased)."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT clan_name FROM watch_clans")
    rows = cur.fetchall()
    conn.close()
    return {str(row["clan_name"]) for row in rows}


def add_watch_player(steam_id: str) -> None:
    """Add a SteamID to the watched player list."""
    if not steam_id:
        return

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO watch_players (steam_id) VALUES (?)",
        (steam_id,),
    )
    conn.commit()
    conn.close()


def remove_watch_player(steam_id: str) -> None:
    """Remove a SteamID from the watched player list."""
    if not steam_id:
        return

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM watch_players WHERE steam_id = ?",
        (steam_id,),
    )
    conn.commit()
    conn.close()


def get_watch_players() -> Set[str]:
    """Return the set of watched SteamIDs."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT steam_id FROM watch_players")
    rows = cur.fetchall()
    conn.close()
    return {str(row["steam_id"]) for row in rows}

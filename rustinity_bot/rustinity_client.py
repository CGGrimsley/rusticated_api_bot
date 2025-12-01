from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import requests

from .config import settings

logger = logging.getLogger(__name__)


BASE_URL = "https://stats.rusticated.com/api/leaderboard"


class MetricConfig(Dict[str, str]):
    """Simple mapping: group, sortBy, label."""


# Core metric definitions used by the bot.
# You can add/remove entries as needed; keys are what the bot refers to.
METRICS: Dict[str, MetricConfig] = {
    # --- PvP ---
    "pvp_kills": {
        "group": "pvp",
        "sortBy": "kill_player",
        "label": "PvP Kills",
    },
    "pvp_deaths": {
        "group": "pvp",
        "sortBy": "death_player",
        "label": "PvP Deaths",
    },
    # --- PvE ---
    "pve_sharks": {
        "group": "pve",
        "sortBy": "killed_shark",
        "label": "Sharks Killed",
    },
    "pve_chickens": {
        "group": "pve",
        "sortBy": "killed_chicken",
        "label": "Chickens Killed",
    },
    "pve_patrol_heli": {
        "group": "pve",
        "sortBy": "killed_patrolheli",
        "label": "Patrol Helicopters Killed",
    },
    "pve_bradleys": {
        "group": "pve",
        "sortBy": "killed_bradley",
        "label": "Bradleys Killed",
    },
    "pve_scientists": {
        "group": "pve",
        "sortBy": "killed_scientist",
        "label": "Scientists Killed",
    },
    "pve_tunnel_dwellers": {
        "group": "pve",
        "sortBy": "killed_tunneldweller",
        "label": "Tunnel Dwellers Killed",
    },
    "pve_bears": {
        "group": "pve",
        "sortBy": "killed_bear",
        "label": "Bears Killed",
    },
    "pve_deer": {
        "group": "pve",
        "sortBy": "killed_deer",
        "label": "Deer Killed",
    },
    "pve_polar_bears": {
        "group": "pve",
        "sortBy": "killed_polarbear",
        "label": "Polar Bears Killed",
    },
    "pve_boars": {
        "group": "pve",
        "sortBy": "killed_boar",
        "label": "Boars Killed",
    },
    "pve_wolves": {
        "group": "pve",
        "sortBy": "killed_wolf",
        "label": "Wolves Killed",
    },
    "pve_underwater_dwellers": {
        "group": "pve",
        "sortBy": "killed_underwaterdweller",
        "label": "Underwater Dwellers Killed",
    },
    # --- Gambling ---
    "gambling_poker_won": {
        "group": "gambling",
        "sortBy": "gambling_pokerwon",
        "label": "Poker Winnings",
    },
    "gambling_poker_deposited": {
        "group": "gambling",
        "sortBy": "gambling_pokerdeposited",
        "label": "Poker Deposited",
    },
    "gambling_slot_won": {
        "group": "gambling",
        "sortBy": "gambling_slotwon",
        "label": "Slots Winnings",
    },
    "gambling_slot_deposited": {
        "group": "gambling",
        "sortBy": "gambling_slotdeposited",
        "label": "Slots Deposited",
    },
    "gambling_wheel_won": {
        "group": "gambling",
        "sortBy": "gambling_wheelwon",
        "label": "Wheel Winnings",
    },
    "gambling_wheel_deposited": {
        "group": "gambling",
        "sortBy": "gambling_wheeldeposited",
        "label": "Wheel Deposited",
    },
    "gambling_blackjack_deposited": {
        "group": "gambling",
        "sortBy": "gambling_blackjackdeposited",
        "label": "Blackjack Deposited",
    },
    "gambling_blackjack_won": {
        "group": "gambling",
        "sortBy": "gambling_blackjackwon",
        "label": "Blackjack Winnings",
    },
    # --- Looted ---
    "looted_oil_barrels": {
        "group": "looted",
        "sortBy": "looted_oilbarrel",
        "label": "Oil Barrels Looted",
    },
    "looted_crates": {
        "group": "looted",
        "sortBy": "looted_crate",
        "label": "Crates Looted",
    },
    "looted_hackable": {
        "group": "looted",
        "sortBy": "looted_hackablecrate",
        "label": "Hackable Crates Looted",
    },
    "looted_barrels": {
        "group": "looted",
        "sortBy": "looted_barrel",
        "label": "Barrels Looted",
    },
    "looted_bradley_crates": {
        "group": "looted",
        "sortBy": "looted_bradleycrate",
        "label": "Bradley Crates Looted",
    },
    "looted_heli_crates": {
        "group": "looted",
        "sortBy": "looted_helicrate",
        "label": "Heli Crates Looted",
    },
    "looted_supply_drops": {
        "group": "looted",
        "sortBy": "looted_supplydrop",
        "label": "Supply Drops Looted",
    },
    "looted_elite_crates": {
        "group": "looted",
        "sortBy": "looted_elitecrate",
        "label": "Elite Crates Looted",
    },
    # --- Building pieces (group: building) ---
    "build_foundation": {
        "group": "building",
        "sortBy": "build_foundation",
        "label": "Foundations Built",
    },
    "build_foundation_triangle": {
        "group": "building",
        "sortBy": "build_foundation.triangle",
        "label": "Triangle Foundations Built",
    },
    "build_floor_triangle": {
        "group": "building",
        "sortBy": "build_floor.triangle",
        "label": "Triangle Floors Built",
    },
    "build_floor": {
        "group": "building",
        "sortBy": "build_floor",
        "label": "Floors Built",
    },
    "build_foundation_steps": {
        "group": "building",
        "sortBy": "build_foundation.steps",
        "label": "Foundation Steps Built",
    },
    "build_floor_frame": {
        "group": "building",
        "sortBy": "build_floor.frame",
        "label": "Floor Frames Built",
    },
    "build_floor_triangle_frame": {
        "group": "building",
        "sortBy": "build_floor.triangle.frame",
        "label": "Triangle Floor Frames Built",
    },
    "build_wall_low": {
        "group": "building",
        "sortBy": "build_wall.low",
        "label": "Low Walls Built",
    },
    "build_wall": {
        "group": "building",
        "sortBy": "build_wall",
        "label": "Walls Built",
    },
    "build_wall_window": {
        "group": "building",
        "sortBy": "build_wall.window",
        "label": "Window Walls Built",
    },
    "build_wall_half": {
        "group": "building",
        "sortBy": "build_wall.half",
        "label": "Half Walls Built",
    },
    "build_wall_frame": {
        "group": "building",
        "sortBy": "build_wall.frame",
        "label": "Wall Frames Built",
    },
    "build_wall_doorway": {
        "group": "building",
        "sortBy": "build_wall.doorway",
        "label": "Doorways Built",
    },
    "build_stairs_spiral": {
        "group": "building",
        "sortBy": "build_stairs.spiral",
        "label": "Spiral Stairs Built",
    },
    "build_stairs_u": {
        "group": "building",
        "sortBy": "build_stairs.u",
        "label": "U Stairs Built",
    },
    "build_stairs_spiral_triangle": {
        "group": "building",
        "sortBy": "build_stairs.spiral.triangle",
        "label": "Spiral Triangle Stairs Built",
    },
    "build_stairs_l": {
        "group": "building",
        "sortBy": "build_stairs.l",
        "label": "L Stairs Built",
    },
    "build_roof": {
        "group": "building",
        "sortBy": "build_roof",
        "label": "Roofs Built",
    },
    "build_roof_triangle": {
        "group": "building",
        "sortBy": "build_roof.triangle",
        "label": "Triangle Roofs Built",
    },
    "build_ramp": {
        "group": "building",
        "sortBy": "build_ramp",
        "label": "Ramps Built",
    },
    # --- Items placed (group: item_placed) ---
    "placed_external_stone_gate": {
        "group": "item_placed",
        "sortBy": "build_gates.external.high.stone",
        "label": "Stone External Gates Placed",
    },
    "placed_sleeping_bags": {
        "group": "item_placed",
        "sortBy": "build_sleepingbag_leather_deployed",
        "label": "Sleeping Bags Placed",
    },
    "placed_beds": {
        "group": "item_placed",
        "sortBy": "build_bed_deployed",
        "label": "Beds Placed",
    },
    "placed_lockers": {
        "group": "item_placed",
        "sortBy": "build_locker.deployed",
        "label": "Lockers Placed",
    },
    "placed_gun_traps": {
        "group": "item_placed",
        "sortBy": "build_guntrap.deployed",
        "label": "Gun Traps Placed",
    },
    "placed_tc": {
        "group": "item_placed",
        "sortBy": "build_cupboard.tool.deployed",
        "label": "Tool Cupboards Placed",
    },
    "placed_vending_machines": {
        "group": "item_placed",
        "sortBy": "build_vendingmachine.deployed",
        "label": "Vending Machines Placed",
    },
    "placed_small_wood_boxes": {
        "group": "item_placed",
        "sortBy": "build_woodbox_deployed",
        "label": "Small Wood Boxes Placed",
    },
    "placed_flame_turrets": {
        "group": "item_placed",
        "sortBy": "build_flameturret.deployed",
        "label": "Flame Turrets Placed",
    },
    "placed_sam_sites": {
        "group": "item_placed",
        "sortBy": "build_sam_site_turret_deployed",
        "label": "SAM Sites Placed",
    },
    "placed_furnaces": {
        "group": "item_placed",
        "sortBy": "build_furnace",
        "label": "Furnaces Placed",
    },
    "placed_large_furnaces": {
        "group": "item_placed",
        "sortBy": "build_furnace.large",
        "label": "Large Furnaces Placed",
    },
    "placed_external_ice_walls": {
        "group": "item_placed",
        "sortBy": "build_wall.external.high.ice",
        "label": "High External Ice Walls Placed",
    },
    "placed_external_stone_walls": {
        "group": "item_placed",
        "sortBy": "build_wall.external.high.stone",
        "label": "High External Stone Walls Placed",
    },
    "placed_external_wood_walls": {
        "group": "item_placed",
        "sortBy": "build_wall.external.high.wood",
        "label": "High External Wood Walls Placed",
    },
    "placed_large_wood_boxes": {
        "group": "item_placed",
        "sortBy": "build_box.wooden.large",
        "label": "Large Wood Boxes Placed",
    },
    "placed_external_wood_gates": {
        "group": "item_placed",
        "sortBy": "build_gates.external.high.wood",
        "label": "Wood External Gates Placed",
    },
    # --- Recycled (group: recycled) ---
    "recycled_propanetanks": {
        "group": "recycled",
        "sortBy": "recycled_propanetank",
        "label": "Propane Tanks Recycled",
    },
    "recycled_techparts": {
        "group": "recycled",
        "sortBy": "recycled_techparts",
        "label": "Tech Trash Recycled",
    },
    "recycled_smg_bodies": {
        "group": "recycled",
        "sortBy": "recycled_smgbody",
        "label": "SMG Bodies Recycled",
    },
    "recycled_metal_blades": {
        "group": "recycled",
        "sortBy": "recycled_metalblade",
        "label": "Metal Blades Recycled",
    },
    "recycled_fuses": {
        "group": "recycled",
        "sortBy": "recycled_fuse",
        "label": "Fuses Recycled",
    },
    "recycled_sheet_metal": {
        "group": "recycled",
        "sortBy": "recycled_sheetmetal",
        "label": "Sheet Metal Recycled",
    },
    "recycled_rope": {
        "group": "recycled",
        "sortBy": "recycled_rope",
        "label": "Rope Recycled",
    },
    "recycled_tarp": {
        "group": "recycled",
        "sortBy": "recycled_tarp",
        "label": "Tarp Recycled",
    },
    "recycled_sewing_kits": {
        "group": "recycled",
        "sortBy": "recycled_sewingkit",
        "label": "Sewing Kits Recycled",
    },
    "recycled_roadsigns": {
        "group": "recycled",
        "sortBy": "recycled_roadsigns",
        "label": "Road Signs Recycled",
    },
    "recycled_metal_springs": {
        "group": "recycled",
        "sortBy": "recycled_metalspring",
        "label": "Metal Springs Recycled",
    },
    "recycled_semi_bodies": {
        "group": "recycled",
        "sortBy": "recycled_semibody",
        "label": "Semi Bodies Recycled",
    },
    "recycled_rifle_bodies": {
        "group": "recycled",
        "sortBy": "recycled_riflebody",
        "label": "Rifle Bodies Recycled",
    },
    "recycled_metal_pipes": {
        "group": "recycled",
        "sortBy": "recycled_metalpipe",
        "label": "Metal Pipes Recycled",
    },
    "recycled_gears": {
        "group": "recycled",
        "sortBy": "recycled_gears",
        "label": "Gears Recycled",
    },
    # --- Resources gathered (group: gathered) ---
    "gathered_metal_ore": {
        "group": "gathered",
        "sortBy": "gathered_metal.ore",
        "label": "Metal Ore Gathered",
    },
    "gathered_cactus_flesh": {
        "group": "gathered",
        "sortBy": "gathered_cactusflesh",
        "label": "Cactus Flesh Gathered",
    },
    "gathered_cloth": {
        "group": "gathered",
        "sortBy": "gathered_cloth",
        "label": "Cloth Gathered",
    },
    "gathered_sulfur_ore": {
        "group": "gathered",
        "sortBy": "gathered_sulfur.ore",
        "label": "Sulfur Ore Gathered",
    },
    "gathered_hqm_ore": {
        "group": "gathered",
        "sortBy": "gathered_hq.metal.ore",
        "label": "HQM Ore Gathered",
    },
    "gathered_animal_fat": {
        "group": "gathered",
        "sortBy": "gathered_fat.animal",
        "label": "Animal Fat Gathered",
    },
    "gathered_leather": {
        "group": "gathered",
        "sortBy": "gathered_leather",
        "label": "Leather Gathered",
    },
    "gathered_wood": {
        "group": "gathered",
        "sortBy": "gathered_wood",
        "label": "Wood Gathered",
    },
    "gathered_stone": {
        "group": "gathered",
        "sortBy": "gathered_stones",
        "label": "Stone Gathered",
    },
    # --- Boom / explosives (group: boom) ---
    "boom_rocket_hv": {
        "group": "boom",
        "sortBy": "shot_ammo.rocket.hv",
        "label": "HV Rockets Fired",
    },
    "boom_rocket_fire": {
        "group": "boom",
        "sortBy": "shot_ammo.rocket.fire",
        "label": "Fire Rockets Fired",
    },
    "boom_rocket_basic": {
        "group": "boom",
        "sortBy": "shot_ammo.rocket.basic",
        "label": "Rockets Fired",
    },
    "boom_beancan": {
        "group": "boom",
        "sortBy": "thrown_grenade.beancan",
        "label": "Beancan Grenades Thrown",
    },
    "boom_f1": {
        "group": "boom",
        "sortBy": "thrown_grenade.f1",
        "label": "F1 Grenades Thrown",
    },
    "boom_flashbang": {
        "group": "boom",
        "sortBy": "thrown_grenade.flashbang",
        "label": "Flashbangs Thrown",
    },
    "boom_molotov": {
        "group": "boom",
        "sortBy": "thrown_grenade.molotov",
        "label": "Molotovs Thrown",
    },
    "boom_satchel": {
        "group": "boom",
        "sortBy": "thrown_explosive.satchel",
        "label": "Satchels Thrown",
    },
    "boom_smoke_grenade": {
        "group": "boom",
        "sortBy": "thrown_grenade.smoke",
        "label": "Smoke Grenades Thrown",
    },
    "boom_catapult_incendiary": {
        "group": "boom",
        "sortBy": "explode_catapult.ammo.incendiary",
        "label": "Catapult Incendiary Ammo",
    },
    "boom_catapult_boulder": {
        "group": "boom",
        "sortBy": "explode_catapult.ammo.boulder",
        "label": "Catapult Boulder Ammo",
    },
    "boom_catapult_explosive": {
        "group": "boom",
        "sortBy": "explode_catapult.ammo.explosive",
        "label": "Catapult Explosive Ammo",
    },
    "boom_c4": {
        "group": "boom",
        "sortBy": "thrown_explosive.timed",
        "label": "Timed Explosives Thrown",
    },
    "boom_gl_he": {
        "group": "boom",
        "sortBy": "shot_ammo.grenadelauncher.he",
        "label": "GL HE Rounds Fired",
    },
    "boom_gl_smoke": {
        "group": "boom",
        "sortBy": "shot_ammo.grenadelauncher.smoke",
        "label": "GL Smoke Rounds Fired",
    },
    "boom_explosive_rifle": {
        "group": "boom",
        "sortBy": "shot_ammo.rifle.explosive",
        "label": "Explosive Rifle Rounds Fired",
    },
}


# ---------------------------------------------------------------------------
# Helper functions for building and executing requests
# ---------------------------------------------------------------------------


def _build_common_params(limit: int) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "limit": limit,
        "offset": 0,
        "sortDir": "desc",
        "serverId": settings.server_id,
        "serverWipeId": settings.server_wipe_id,
    }
    if settings.org_id is not None:
        params["orgId"] = settings.org_id
    return params


def fetch_leaderboard_for_metric(metric_key: str, limit: int = 50) -> Dict[str, Any]:
    """Fetch clan leaderboard data for a given metric key.

    Uses METRICS to map `metric_key` to the correct Rustinated
    group/sortBy parameters.
    """
    if metric_key not in METRICS:
        raise KeyError(f"Unknown metric key: {metric_key}")

    cfg = METRICS[metric_key]
    params = _build_common_params(limit)
    params.update(
        {
            "type": "clan",
            "group": cfg["group"],
            "sortBy": cfg["sortBy"],
        }
    )

    try:
        logger.debug("Requesting clan leaderboard: %s", params)
        resp = requests.get(BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.error("Error fetching leaderboard for %s: %s", metric_key, exc)
        return {"success": False, "error": str(exc), "data": {}}
    except ValueError as exc:
        logger.error("Failed to decode JSON for %s: %s", metric_key, exc)
        return {"success": False, "error": "invalid_json", "data": {}}

    return data


def fetch_player_leaderboard(
    group: str,
    sort_by: str,
    limit: int = 50,
) -> Dict[str, Any]:
    """Fetch a player leaderboard for a specific group/sortBy combination.

    This is used by commands like /me (per-player stats).
    """
    params = _build_common_params(limit)
    params.update(
        {
            "type": "player",
            "group": group,
            "sortBy": sort_by,
        }
    )

    try:
        logger.debug("Requesting player leaderboard: %s", params)
        resp = requests.get(BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.error(
            "Error fetching player leaderboard for group=%s sortBy=%s: %s",
            group,
            sort_by,
            exc,
        )
        return {"success": False, "error": str(exc), "data": {}}
    except ValueError as exc:
        logger.error("Failed to decode player leaderboard JSON: %s", exc)
        return {"success": False, "error": "invalid_json", "data": {}}

    return data


def parse_leaderboard_rows(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract the entry rows from a leaderboard response.

    Expected shape:
      { "success": true, "data": { ..., "entries": [ ... ] } }

    Returns an empty list if the format is unexpected.
    """
    try:
        return list(data["data"]["entries"])
    except (KeyError, TypeError):
        logger.warning("Unexpected leaderboard format: %r", data)
        return []


# ---------------------------------------------------------------------------
# Utility helpers for working with rows
# ---------------------------------------------------------------------------


def find_clan_in_rows(
    rows: List[Dict[str, Any]],
    clan_name: str,
) -> Optional[Dict[str, Any]]:
    """Find a clan entry in rows by name (case-insensitive).

    The API usually returns a `name` field for each row (clan tag or name).
    """
    target = clan_name.lower()
    for row in rows:
        name = str(row.get("name", "")).lower()
        if name == target:
            return row
    return None


def get_clan_and_next(
    rows: List[Dict[str, Any]],
    clan_name: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Return (this_clan_row, next_clan_row) for a given clan name.

    - If the clan is not found, returns (None, None)
    - If the clan is last in the list, next_clan_row will be None.
    """
    target = clan_name.lower()
    for idx, row in enumerate(rows):
        name = str(row.get("name", "")).lower()
        if name == target:
            next_row = rows[idx + 1] if idx + 1 < len(rows) else None
            return row, next_row
    return None, None

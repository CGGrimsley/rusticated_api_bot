import discord

from rustinity_bot.commands import _is_valid_steam_id, _build_player_stats_embed


def test_is_valid_steam_id_accepts_17_digit_numeric():
    steam_id = "76561198000000000"  # 17 digits

    assert _is_valid_steam_id(steam_id) is True


def test_is_valid_steam_id_strips_whitespace():
    steam_id = "   76561198000000000  "

    assert _is_valid_steam_id(steam_id) is True


def test_is_valid_steam_id_rejects_non_numeric():
    steam_id = "76561198O00000000"  # letter O instead of zero

    assert _is_valid_steam_id(steam_id) is False


def test_is_valid_steam_id_rejects_wrong_length():
    too_short = "1234567890123456"
    too_long = "123456789012345678"

    assert _is_valid_steam_id(too_short) is False
    assert _is_valid_steam_id(too_long) is False


def test_build_player_stats_embed_basic_fields():
    username = "TestUser"
    steam_id = "76561198000000000"
    row = {
        "rank": 5,
        "stats": {
            "kill_player": "10",
            "death_player": "2",
            "kdr": "5.0",
            "playtime": 3 * 3600 + 15 * 60,  # 3h 15m
        },
    }

    embed: discord.Embed = _build_player_stats_embed(username, steam_id, row)

    # Title / description
    assert embed.title == f"Stats for {username}"
    assert steam_id in embed.description

    # You currently have 5 fields: rank, kills, deaths, kdr, playtime
    assert len(embed.fields) == 5

    rank_field = embed.fields[0]
    kills_field = embed.fields[1]
    deaths_field = embed.fields[2]
    kdr_field = embed.fields[3]
    playtime_field = embed.fields[4]

    assert rank_field.name.startswith("Leaderboard Rank")
    assert rank_field.value == "5"

    assert kills_field.name == "Kills"
    assert kills_field.value == "10"

    assert deaths_field.name == "Deaths"
    assert deaths_field.value == "2"

    assert kdr_field.name == "K/D Ratio"
    assert kdr_field.value == "5.00"

    assert playtime_field.name.startswith("Playtime")
    assert playtime_field.value == "3h 15m"


def test_build_player_stats_embed_handles_bad_values():
    username = "BrokenUser"
    steam_id = "76561198000000000"
    row = {
        # No rank, stats are non-numeric strings
        "stats": {
            "kill_player": "not-a-number",
            "death_player": None,
            "kdr": "NaN",
            "playtime": "oops",
        },
    }

    embed: discord.Embed = _build_player_stats_embed(username, steam_id, row)

    # 5 fields again: rank, kills, deaths, kdr, playtime
    assert len(embed.fields) == 5

    rank_field = embed.fields[0]
    kills_field = embed.fields[1]
    deaths_field = embed.fields[2]
    kdr_field = embed.fields[3]
    playtime_field = embed.fields[4]

    # Rank defaults to "?"
    assert rank_field.value == "?"

    # Bad numeric values should fall back to 0
    assert kills_field.value == "0"
    assert deaths_field.value == "0"
    assert kdr_field.value == "0.00"

    # Bad playtime → 0h 0m
    assert playtime_field.value == "0h 0m"

import pytest

# Module under test
from rustinity_bot.rustinity_client import (
    parse_leaderboard_rows,
    find_clan_in_rows,
    get_clan_and_next,
)


def test_parse_leaderboard_rows_happy_path():
    data = {
        "success": True,
        "data": {
            "entries": [
                {"name": "ClanA", "rank": 1},
                {"name": "ClanB", "rank": 2},
            ]
        },
    }

    rows = parse_leaderboard_rows(data)

    assert isinstance(rows, list)
    assert len(rows) == 2
    assert rows[0]["name"] == "ClanA"
    assert rows[1]["rank"] == 2


def test_parse_leaderboard_rows_missing_entries_returns_empty_list():
    # No "entries" at all
    data = {"success": True, "data": {}}

    rows = parse_leaderboard_rows(data)

    assert rows == []


def test_parse_leaderboard_rows_invalid_shape_returns_empty_list():
    # Completely wrong shape
    data = {"foo": "bar"}

    rows = parse_leaderboard_rows(data)

    assert rows == []


def test_find_clan_in_rows_finds_case_insensitive():
    rows = [
        {"name": "walobots"},
        {"name": "OtherClan"},
    ]

    result = find_clan_in_rows(rows, "WALOBOTS")

    assert result is not None
    assert result["name"] == "walobots"


def test_find_clan_in_rows_returns_none_if_not_found():
    rows = [
        {"name": "Alpha"},
        {"name": "Bravo"},
    ]

    result = find_clan_in_rows(rows, "Charlie")

    assert result is None


def test_get_clan_and_next_middle_of_list():
    rows = [
        {"name": "ClanA", "rank": 1},
        {"name": "ClanB", "rank": 2},
        {"name": "ClanC", "rank": 3},
    ]

    clan, nxt = get_clan_and_next(rows, "ClanB")

    assert clan is not None
    assert clan["name"] == "ClanB"
    assert nxt is not None
    assert nxt["name"] == "ClanC"


def test_get_clan_and_next_last_item_has_no_next():
    rows = [
        {"name": "ClanA", "rank": 1},
        {"name": "ClanB", "rank": 2},
    ]

    clan, nxt = get_clan_and_next(rows, "ClanB")

    assert clan is not None
    assert clan["name"] == "ClanB"
    assert nxt is None


def test_get_clan_and_next_not_found():
    rows = [{"name": "ClanA"}, {"name": "ClanB"}]

    clan, nxt = get_clan_and_next(rows, "ClanX")

    assert clan is None
    assert nxt is None

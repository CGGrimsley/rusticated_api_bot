import discord

from rustinity_bot.embeds import build_help_embed, build_status_embed


def test_build_help_embed_contains_core_commands():
    embed: discord.Embed = build_help_embed()

    # Basic sanity checks
    assert embed.title
    assert "Rustinity Bot Commands" in embed.title

    field_names = [f.name for f in embed.fields]

    # Make sure key commands are documented
    assert "/help" in field_names
    assert "/link `<steamId64>`" in field_names
    assert "/me" in field_names
    assert "/status" in field_names
    assert "/toggle" in field_names
    assert "/track `<clan>`" in field_names
    assert "/untrack `<clan>`" in field_names
    assert "/trackplayer `<steamId64>`" in field_names
    assert "/untrackplayer `<steamId64>`" in field_names


def test_build_status_embed_when_tracking_off_and_no_clans():
    embed: discord.Embed = build_status_embed(
        tracking_enabled=False,
        watched_clans=[],
    )

    assert embed.title == "📊 Bot Tracking Status"
    assert "Current tracking state" in (embed.description or "")

    tracking_field = next(f for f in embed.fields if f.name == "Tracking")
    watched_field = next(f for f in embed.fields if f.name == "Watched Clans")
    total_field = next(f for f in embed.fields if f.name == "Total Watched")

    assert "🔴 OFF" in tracking_field.value
    assert "No clans are currently monitored" in watched_field.value
    assert total_field.value == "0"


def test_build_status_embed_when_tracking_on_with_clans():
    embed: discord.Embed = build_status_embed(
        tracking_enabled=True,
        watched_clans=["Walobots", "OtherClan"],
    )

    tracking_field = next(f for f in embed.fields if f.name == "Tracking")
    watched_field = next(f for f in embed.fields if f.name == "Watched Clans")
    total_field = next(f for f in embed.fields if f.name == "Total Watched")

    assert "🟢 ON" in tracking_field.value

    # Watched list should show both clan names
    assert "Walobots" in watched_field.value
    assert "OtherClan" in watched_field.value

    # Deduplicated length should be 2
    assert total_field.value == "2"

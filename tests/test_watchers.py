from rustinity_bot.watchers import is_tracking_enabled, set_tracking_enabled


def test_tracking_enabled_default_is_false():
    # Tests assume no prior state, so run this before anything else toggles.
    assert is_tracking_enabled() is False


def test_set_tracking_enabled_turns_on_and_off():
    set_tracking_enabled(True)
    assert is_tracking_enabled() is True

    set_tracking_enabled(False)
    assert is_tracking_enabled() is False

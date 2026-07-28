"""Lawn-local calendar helpers.

The bug these guard: flooring a raw UTC timedelta reads an evening application
as "today" the next morning, because it is less than 24 hours old.
"""

from datetime import UTC, datetime

from lawn_api.services.localtime import CENTRAL, local_days_between, local_today


def test_evening_application_is_one_day_ago_next_morning() -> None:
    applied = datetime(2026, 7, 27, 19, 30, tzinfo=CENTRAL)
    now = datetime(2026, 7, 28, 9, 0, tzinfo=CENTRAL)
    assert (now - applied).days == 0  # the raw-timedelta trap this replaces
    assert local_days_between(applied, now) == 1


def test_utc_instant_maps_to_central_date() -> None:
    # 2026-07-28 02:00 UTC is still July 27 in Topeka.
    late_utc = datetime(2026, 7, 28, 2, 0, tzinfo=UTC)
    assert local_today(late_utc).isoformat() == "2026-07-27"


def test_same_local_day_is_zero_days() -> None:
    morning = datetime(2026, 7, 28, 6, 0, tzinfo=CENTRAL)
    night = datetime(2026, 7, 28, 22, 0, tzinfo=CENTRAL)
    assert local_days_between(morning, night) == 0

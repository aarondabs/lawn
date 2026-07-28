"""Lawn-local calendar helpers.

Single-location app: the lawn is in Topeka, KS, so America/Chicago is the one
local zone. Instants are stored tz-aware (UTC); anything calendar-shaped --
"today", "days since", daily buckets -- must be computed on Central dates.
Flooring a raw UTC timedelta is not the same thing: a treatment applied
yesterday evening is less than 24 hours old the next morning, so `.days` calls
it "today".
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

CENTRAL = ZoneInfo("America/Chicago")


def local_today(now: datetime) -> date:
    """The lawn-local calendar date of an aware instant."""
    return now.astimezone(CENTRAL).date()


def local_days_between(earlier: datetime, later: datetime) -> int:
    """Calendar days between two aware instants, counted on lawn-local dates."""
    return (local_today(later) - local_today(earlier)).days

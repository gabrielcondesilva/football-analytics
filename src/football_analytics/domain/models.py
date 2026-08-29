"""Domain records for the Player Analytics MVP.

Vocabulary follows CONTEXT.md: Team, Position, Position Group, Player,
Statistic, Snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Team:
    fotmob_id: int
    name: str


@dataclass(frozen=True)
class Position:
    code: str
    """FotMob position code, e.g. "CB", "RW", "GK"."""

    group: str
    """Position Group this code belongs to: "Goalkeeper", "Defender", "Midfielder", or "Forward"."""


@dataclass(frozen=True)
class Statistic:
    key: str
    """Canonical stat key, taken from FotMob's localizedTitleId (e.g. "goals")."""

    label: str
    """Human-readable title, as shown by FotMob (e.g. "Goals")."""

    value: float

    format: str = "number"
    """FotMob's statFormat for this value (e.g. "number", "fraction",
    "percent"). Governs whether a Metric derived from this Statistic may
    be scaled per-90 (percent values may not)."""


@dataclass(frozen=True)
class Player:
    fotmob_id: int
    name: str
    team: Team
    positions: tuple[Position, ...]
    statistics: tuple[Statistic, ...]

    league: str | None = None
    """Name of the League this Player's Team currently plays in (ADR-0004) —
    always their most recently ingested roster, independent of which League
    actually produced the Statistics below. None until the Team's League has
    been backfilled."""

    statistics_league: str | None = None
    """Name of the League whose Season produced the Statistics above (via
    their latest Snapshot). None when no Statistic exists yet. May differ
    from `league` for a recently-transferred Player, whose shown Statistics
    still come from their previous League until they have some in the new
    one (ADR-0004, `find_known_league_entry`)."""

    age: int | None = None
    nationality: str | None = None
    preferred_foot: str | None = None
    photo_url: str | None = None
    """Biographical attributes, sourced from FotMob's playerData. None until
    ingestion extracts them."""


@dataclass(frozen=True)
class Snapshot:
    league: str
    season: str
    scraped_at: datetime
    players: tuple[Player, ...]

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
    "percentage"). Governs whether a Metric derived from this Statistic may
    be scaled per-90 (percentage values may not)."""


@dataclass(frozen=True)
class Player:
    fotmob_id: int
    name: str
    team: Team
    positions: tuple[Position, ...]
    statistics: tuple[Statistic, ...]


@dataclass(frozen=True)
class Snapshot:
    league: str
    season: str
    scraped_at: datetime
    players: tuple[Player, ...]

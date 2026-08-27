"""Seam B: domain records + selected Metrics + filters -> analysis output.

Pure functions only: no network, no database, no Streamlit. Every function
here operates on Players already normalized from a single Snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from football_analytics.domain.models import Player

MINUTES_PLAYED_KEY = "minutes_played"

MetricKind = Literal["raw", "per_90", "percentile"]


@dataclass(frozen=True)
class MetricSpec:
    key: str
    """The underlying Statistic key this Metric is derived from."""

    label: str
    kind: MetricKind


def statistic_value(player: Player, key: str) -> float | None:
    return next((s.value for s in player.statistics if s.key == key), None)


def position_group(player: Player) -> str | None:
    return player.positions[0].group if player.positions else None


def filter_by_position_group(players: list[Player], group: str) -> list[Player]:
    return [p for p in players if position_group(p) == group]


def apply_minutes_floor(players: list[Player], minutes_floor: float) -> list[Player]:
    return [p for p in players if (statistic_value(p, MINUTES_PLAYED_KEY) or 0) >= minutes_floor]


def per_90(player: Player, key: str) -> float | None:
    value = statistic_value(player, key)
    minutes = statistic_value(player, MINUTES_PLAYED_KEY)
    if value is None or not minutes:
        return None
    return value * 90 / minutes


def percentile(players: list[Player], player: Player, key: str) -> float | None:
    """Percentile of `player`'s raw Statistic `key` among the given peers.

    `players` is the reference population (typically the Player's Position
    Group within the Season) and is the caller's responsibility to scope —
    this function only ranks within whatever population it is given.
    """
    target = statistic_value(player, key)
    if target is None:
        return None
    peer_values = [v for p in players if (v := statistic_value(p, key)) is not None]
    if not peer_values:
        return None
    return 100 * sum(1 for v in peer_values if v <= target) / len(peer_values)


def compute_metric(players: list[Player], player: Player, spec: MetricSpec) -> float | None:
    """Compute a single Metric's value for `player`.

    `players` is the reference population used for `percentile` (ignored for
    `raw` and `per_90`, which only depend on `player`).
    """
    if spec.kind == "raw":
        return statistic_value(player, spec.key)
    if spec.kind == "per_90":
        return per_90(player, spec.key)
    return percentile(players, player, spec.key)

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
InsightKind = Literal["strength", "weakness"]


@dataclass(frozen=True)
class MetricSpec:
    key: str
    """The underlying Statistic key this Metric is derived from."""

    label: str
    kind: MetricKind


@dataclass(frozen=True)
class Insight:
    key: str
    label: str
    percentile: float
    kind: InsightKind


def statistic_value(player: Player, key: str) -> float | None:
    return next((s.value for s in player.statistics if s.key == key), None)


def position_group(player: Player) -> str | None:
    return player.positions[0].group if player.positions else None


def filter_by_position_group(players: list[Player], group: str) -> list[Player]:
    return [p for p in players if position_group(p) == group]


def apply_minutes_floor(players: list[Player], minutes_floor: float) -> list[Player]:
    return [p for p in players if (statistic_value(p, MINUTES_PLAYED_KEY) or 0) >= minutes_floor]


def per_90(player: Player, key: str) -> float | None:
    """Scale a Statistic to a per-90-minutes rate.

    Statistics already expressed as a percentage (`format == "percentage"`)
    are returned as-is: scaling a rate by minutes played would produce a
    meaningless number, not a fairer comparison.
    """
    stat = next((s for s in player.statistics if s.key == key), None)
    if stat is None:
        return None
    if stat.format == "percentage":
        return stat.value
    minutes = statistic_value(player, MINUTES_PLAYED_KEY)
    if not minutes:
        return None
    return stat.value * 90 / minutes


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


def top_metric_leaderboard(
    players: list[Player], key: str, *, size: int = 10
) -> list[tuple[Player, float, float]]:
    """Top `size` Players ranked by a Metric's per-90 value (as-is, unscaled,
    for a percentage-format Statistic), with each Player's percentile
    computed against that same per-90 value across `players`.

    `players` is both the ranking population and the percentile reference
    population — there is no separate reference population here, unlike
    `compute_metric`/`percentile`. Players the Metric can't be computed for
    (missing Statistic, or missing/zero minutes for a non-percentage one)
    are excluded entirely.

    Returns (player, value, percentile) tuples, highest value first.
    """
    scored = [(p, v) for p in players if (v := per_90(p, key)) is not None]
    if not scored:
        return []
    all_values = [v for _, v in scored]
    ranked = sorted(scored, key=lambda pv: pv[1], reverse=True)
    return [
        (player, value, 100 * sum(1 for v in all_values if v <= value) / len(all_values))
        for player, value in ranked[:size]
    ]


def scout_comparison(
    players: list[Player],
    reference: Player,
    specs: list[MetricSpec],
    *,
    restrict_to_position_group: bool = True,
) -> list[tuple[Player, float]]:
    """Rank `players` by similarity to `reference` across `specs`, weighted
    equally, excluding `reference` itself.

    Each Metric is z-score normalized across the candidate pool (plus the
    reference) before combining, so Metrics on different scales contribute
    equally to the resulting distance. `players` should already reflect the
    current Minutes Floor - this function only handles the Position Group
    restriction and the ranking itself.

    Returns (player, distance) pairs sorted ascending by distance (most
    similar first).
    """
    pool = [p for p in players if p.fotmob_id != reference.fotmob_id]
    if restrict_to_position_group:
        ref_group = position_group(reference)
        pool = [p for p in pool if position_group(p) == ref_group]
    if not pool or not specs:
        return []

    all_players = [reference, *pool]
    normalized: dict[int, list[float]] = {p.fotmob_id: [] for p in all_players}

    for spec in specs:
        raw_values = {p.fotmob_id: compute_metric(all_players, p, spec) for p in all_players}
        known = [v for v in raw_values.values() if v is not None]
        mean = sum(known) / len(known) if known else 0.0
        variance = sum((v - mean) ** 2 for v in known) / len(known) if known else 0.0
        std = variance**0.5
        for p in all_players:
            value = raw_values[p.fotmob_id]
            z = 0.0 if value is None or std == 0 else (value - mean) / std
            normalized[p.fotmob_id].append(z)

    ref_vector = normalized[reference.fotmob_id]
    ranked = [
        (p, sum((a - b) ** 2 for a, b in zip(ref_vector, normalized[p.fotmob_id])) ** 0.5)
        for p in pool
    ]
    ranked.sort(key=lambda pair: pair[1])
    return ranked


def generate_insights(
    players: list[Player],
    player: Player,
    *,
    high_threshold: float = 90.0,
    low_threshold: float = 10.0,
) -> list[Insight]:
    """Percentile-based Insights for every Statistic `player` has, relative
    to `players` (typically the Player's Position Group within the Season).

    Rule-based only, no LLM involved: a Statistic at or above
    `high_threshold` percentile is a "strength", at or below `low_threshold`
    a "weakness". Sorted with the most extreme strengths first, then the
    most extreme weaknesses.
    """
    insights = []
    for stat in player.statistics:
        pct = percentile(players, player, stat.key)
        if pct is None:
            continue
        if pct >= high_threshold:
            insights.append(Insight(key=stat.key, label=stat.label, percentile=pct, kind="strength"))
        elif pct <= low_threshold:
            insights.append(Insight(key=stat.key, label=stat.label, percentile=pct, kind="weakness"))

    insights.sort(key=lambda i: -i.percentile if i.kind == "strength" else i.percentile)
    return insights

"""Pure UI-helper functions shared by more than one dashboard page."""

from __future__ import annotations

from football_analytics.domain.models import Player


def metric_label_options(players: list[Player]) -> dict[str, str]:
    """Map each available Statistic's label to its key, first label wins."""
    options: dict[str, str] = {}
    for p in players:
        for s in p.statistics:
            options.setdefault(s.label, s.key)
    return options

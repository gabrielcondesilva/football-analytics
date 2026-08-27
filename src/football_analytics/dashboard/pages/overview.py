"""Overview page: Top 10 Players per selected Metric.

Empty until a Metric is picked; each Metric selected in either the Per-90
or Per Season multiselect adds its own Top 10 table (Name, Team, Positions,
value), laid out two per row — Per-90 selections first, then Per Season, in
each multiselect's own selection order. Picking the same Metric in both
shows both: they're independent selections, not a single toggle, so e.g.
xA Per-90 and xA Per Season can sit side by side. A Statistic already
expressed as a percent is shown as-is in both cases, see `per_90()`.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from football_analytics.analysis.metrics import (
    MetricKind,
    apply_minutes_floor,
    filter_by_position_group,
    position_group,
    top_metric_leaderboard,
)
from football_analytics.dashboard.data import get_players
from football_analytics.dashboard.shared import metric_label_options, position_codes
from football_analytics.domain.models import Player

TABLE_SIZE = 10
GRID_COLUMNS = 2

KIND_DISPLAY_LABEL: dict[MetricKind, str] = {
    "per_90": "Per-90",
    "raw": "Per Season",
}


def leaderboard_dataframe(
    players: list[Player], key: str, label: str, kind: MetricKind
) -> pd.DataFrame:
    entries = top_metric_leaderboard(players, key, kind=kind, size=TABLE_SIZE)
    return pd.DataFrame(
        [
            {
                "Name": player.name,
                "Team": player.team.name,
                "Positions": position_codes(player),
                label: value,
            }
            for player, value in entries
        ]
    )


def main() -> None:
    st.title("Overview")

    players = get_players()
    if not players:
        st.warning("No players found. Has the ingestion pipeline been run yet?")
        return

    team_names = sorted({p.team.name for p in players})
    position_code_options = sorted({pos.code for p in players for pos in p.positions})
    position_groups = sorted({g for p in players if (g := position_group(p)) is not None})
    league_names = sorted({p.league for p in players if p.league})
    label_options = metric_label_options(players)

    with st.sidebar:
        st.header("Filters")
        selected_teams = st.multiselect("Team", team_names)
        selected_positions = st.multiselect("Position", position_code_options)
        selected_group = st.selectbox("Position Group", ["All", *position_groups])
        selected_leagues = st.multiselect("League", league_names)
        minutes_floor = st.number_input("Minutes Floor", min_value=0, value=0, step=90)
        st.multiselect(
            "Age",
            [],
            disabled=True,
            help="Em breve — depende de dados de idade ainda não ingeridos.",
        )
        st.multiselect(
            "Nationality",
            [],
            disabled=True,
            help="Em breve — depende de dados de nacionalidade ainda não ingeridos.",
        )

        st.header("Metrics")
        per90_labels = st.multiselect("Metrics (Per-90)", sorted(label_options))
        season_labels = st.multiselect("Metrics (Per Season)", sorted(label_options))

    view_players = players
    if selected_teams:
        view_players = [p for p in view_players if p.team.name in selected_teams]
    if selected_positions:
        view_players = [
            p for p in view_players if any(pos.code in selected_positions for pos in p.positions)
        ]
    if selected_group != "All":
        view_players = filter_by_position_group(view_players, selected_group)
    if selected_leagues:
        view_players = [p for p in view_players if p.league in selected_leagues]
    view_players = apply_minutes_floor(view_players, minutes_floor)

    selections: list[tuple[str, MetricKind]] = [(label, "per_90") for label in per90_labels] + [
        (label, "raw") for label in season_labels
    ]

    if not selections:
        st.info("Selecione uma métrica de desempenho")
        return

    for row_start in range(0, len(selections), GRID_COLUMNS):
        row = selections[row_start : row_start + GRID_COLUMNS]
        columns = st.columns(GRID_COLUMNS)
        for column, (label, kind) in zip(columns, row, strict=False):
            with column:
                key = label_options[label]
                st.subheader(f"{label} ({KIND_DISPLAY_LABEL[kind]})")
                df = leaderboard_dataframe(view_players, key, label, kind)
                if df.empty:
                    st.info("No players have this Metric under the current filters.")
                else:
                    st.dataframe(df, width="stretch", hide_index=True)


main()

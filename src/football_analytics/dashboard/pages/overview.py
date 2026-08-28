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
    "per_90": "Por 90 min",
    "raw": "Por Temporada",
}

ALL_POSITION_GROUPS = "Todos"


def leaderboard_dataframe(
    players: list[Player], key: str, label: str, kind: MetricKind
) -> pd.DataFrame:
    entries = top_metric_leaderboard(players, key, kind=kind, size=TABLE_SIZE)
    return pd.DataFrame(
        [
            {
                "Nome": player.name,
                "Time": player.team.name,
                "Posições": position_codes(player),
                label: value,
            }
            for player, value in entries
        ]
    )


def value_column_config(df: pd.DataFrame, label: str, kind: MetricKind) -> dict:
    """`st.dataframe` column_config for a leaderboard's value column.

    Per-90 values are rates (minutes-scaled, or a Statistic already
    expressed as a percent per `per_90()`), so they always render with two
    decimal places. Per Season values are season totals and are typically
    whole numbers (goals, tackles, ...) that already read fine unformatted;
    only format them when the underlying data is itself fractional (e.g. a
    percent-format Statistic shown as a season figure), so genuine counts
    keep reading as plain integers.
    """
    if kind == "per_90" or (df[label] % 1 != 0).any():
        return {label: st.column_config.NumberColumn(format="%.2f")}
    return {}


def main() -> None:
    st.title("Visão Geral")

    players = get_players()
    if not players:
        st.warning("Nenhum jogador encontrado. O pipeline de ingestão já foi executado?")
        return

    team_names = sorted({p.team.name for p in players})
    position_code_options = sorted({pos.code for p in players for pos in p.positions})
    position_groups = sorted({g for p in players if (g := position_group(p)) is not None})
    league_names = sorted({p.league for p in players if p.league})
    label_options = metric_label_options(players)

    with st.sidebar:
        st.header("Filtros")
        per90_labels = st.multiselect("Métricas (Por 90 min)", sorted(label_options))
        season_labels = st.multiselect("Métricas (Por Temporada)", sorted(label_options))
        selected_teams = st.multiselect("Time", team_names)
        selected_positions = st.multiselect("Posição", position_code_options)
        selected_group = st.selectbox("Grupo de Posição", [ALL_POSITION_GROUPS, *position_groups])
        selected_leagues = st.multiselect("Liga", league_names)
        minutes_floor = st.number_input("Minutos Mínimos", min_value=0, value=0, step=90)
        st.multiselect(
            "Idade",
            [],
            disabled=True,
            help="Em breve — depende de dados de idade ainda não ingeridos.",
        )
        st.multiselect(
            "Nacionalidade",
            [],
            disabled=True,
            help="Em breve — depende de dados de nacionalidade ainda não ingeridos.",
        )

    view_players = players
    if selected_teams:
        view_players = [p for p in view_players if p.team.name in selected_teams]
    if selected_positions:
        view_players = [
            p for p in view_players if any(pos.code in selected_positions for pos in p.positions)
        ]
    if selected_group != ALL_POSITION_GROUPS:
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
                    st.info("Nenhum jogador possui essa métrica com os filtros atuais.")
                else:
                    st.dataframe(
                        df,
                        width="stretch",
                        hide_index=True,
                        column_config=value_column_config(df, label, kind),
                    )


main()

"""Player Analysis page (Análise de Jogadores): search a single Player, scope
a Comparison Population by Position Group + Minutes Floor, show that
Player's biographical card, and compare selected Metrics against the
Comparison Population as either a Tercil-colored matrix or a percentile
radar.

Full rebuild per .scratch/player-analysis-page/spec.md, tickets 03-05: shell/
search/filters/card, Metrics multiselect + Por Temporada/Por 90 toggle +
Tercil matrix, and the Matriz<->Radar toggle. The page's previous content
(general leaderboard, Insights, Scout Comparison, PDF export) was removed
per ADR 0003 — see docs/adr/0003-drop-scout-comparison-on-workspace-rebuild.md.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st
from plotly.graph_objects import Figure

from football_analytics.analysis.metrics import (
    MetricKind,
    MetricSpec,
    TercileBand,
    apply_minutes_floor,
    compute_metric,
    filter_by_position_group,
    position_group,
    tercile_band,
)
from football_analytics.dashboard.data import get_players
from football_analytics.dashboard.shared import metric_label_options, position_codes
from football_analytics.domain.models import Player

ALL_POSITION_GROUPS = "Todos"
NO_PLAYER_SELECTED = "Selecione um jogador…"

LAST_PLAYER_KEY = "workspace_last_player_id"
POSITION_GROUP_KEY = "workspace_position_group"

_UNSET: object = object()
"""Sentinel distinguishing "never synced" from "synced to no Player
selected" (`None`) in `st.session_state`."""

AVATAR_HEIGHT = 88

VALUE_KIND_BY_LABEL: dict[str, MetricKind] = {"Por Temporada": "raw", "Por 90 min": "per_90"}
VIEW_OPTIONS = ("Matriz", "Radar")

SEQUENTIAL_BLUE = "#2a78d6"
"""Default sequential hue from the project's dataviz skill (references/
palette.md) — same tone used elsewhere in the app (Overview's leaderboards,
before their removal). The radar is a single Player's own profile, not a
good/bad status, so it stays on this one brand hue rather than the matrix's
Tercil red/amber/green."""

# Fixed, mode-invariant status colors from the project's dataviz skill
# (references/palette.md) — never themed, so a tercile band reads the same
# regardless of the app's light/dark mode. Text color is chosen per swatch
# for contrast against that swatch itself (white on the two saturated/dark
# hues, near-black on the lighter amber), not against the page surface.
TERCILE_CELL_STYLE: dict[TercileBand, str] = {
    "top": "background-color: #0ca30c; color: #ffffff;",
    "middle": "background-color: #fab219; color: #0b0b0b;",
    "bottom": "background-color: #d03b3b; color: #ffffff;",
}


def player_search_options(players: list[Player]) -> dict[str, Player]:
    """Map "Name (Team)" display label to Player, sorted by name — the
    embedded filter/options for the search selectbox."""
    return {f"{p.name} ({p.team.name})": p for p in sorted(players, key=lambda p: p.name)}


def bio_field(value: int | str | None) -> str:
    """Display value for an optional biographical field: "-" until the
    field is ingested (all of age/nationality/preferred_foot today)."""
    return str(value) if value is not None else "-"


def sync_position_group_with_player(
    selected_player: Player | None, position_groups: list[str]
) -> None:
    """Auto-fill the Position Group filter with the selected Player's group,
    every time the *selected Player* changes — not on every rerun, so a
    manual override of Position Group survives reruns but resets the next
    time the Player changes.

    Must run before the Position Group `st.selectbox` below is instantiated:
    Streamlit only respects a `st.session_state[key]` write for a widget's
    `key` when it happens earlier in the same script run.
    """
    current_player_id = selected_player.fotmob_id if selected_player else None
    if st.session_state.get(LAST_PLAYER_KEY, _UNSET) == current_player_id:
        return
    st.session_state[LAST_PLAYER_KEY] = current_player_id
    group = position_group(selected_player) if selected_player else None
    st.session_state[POSITION_GROUP_KEY] = group if group in position_groups else ALL_POSITION_GROUPS


def metric_matrix_dataframe(
    comparison_population: list[Player], player: Player, specs: list[MetricSpec]
) -> pd.DataFrame:
    """One row per selected Metric: its Value (per `spec.kind`) and its
    Percentile within `comparison_population`. Percentile is always computed
    regardless of `spec.kind` — the Percentual column never switches type
    with the Por Temporada/Por 90 min toggle, only Valor does.

    A Metric missing for this Player (or for the whole population) keeps its
    row with a blank Valor/Percentual rather than being dropped, so every
    Metric the user picked stays visible in the matrix.
    """
    rows = []
    for spec in specs:
        percentile_spec = MetricSpec(key=spec.key, label=spec.label, kind="percentile")
        rows.append(
            {
                "Métrica": spec.label,
                "Valor": compute_metric(comparison_population, player, spec),
                "Percentual": compute_metric(comparison_population, player, percentile_spec),
            }
        )
    return pd.DataFrame(rows, columns=["Métrica", "Valor", "Percentual"])


def style_percentile_cell(value: float | None) -> str:
    """Pandas Styler cell function: Tercil-band background/text color for
    one Percentual cell, no style for a missing value."""
    if value is None or pd.isna(value):
        return ""
    return TERCILE_CELL_STYLE[tercile_band(value)]


def matrix_column_config(df: pd.DataFrame, kind: MetricKind) -> dict:
    """`st.dataframe` column_config for the matrix's Valor/Percentual
    columns. Valor follows the same convention as the Overview leaderboards
    (`leaderboard_dataframe`'s sibling `value_column_config`): Per-90 rates
    always show two decimals; Por Temporada totals stay whole unless the
    underlying data is itself fractional. Percentual is always a whole
    percentage, independent of the toggle.
    """
    config: dict = {"Percentual": st.column_config.NumberColumn(format="%.0f%%")}
    if kind == "per_90" or (df["Valor"].dropna() % 1 != 0).any():
        config["Valor"] = st.column_config.NumberColumn(format="%.2f")
    return config


def metric_radar_chart(matrix_df: pd.DataFrame) -> Figure:
    """Percentile radar for the same rows already computed by
    `metric_matrix_dataframe` — one axis per Metric, r = Percentual, always
    the percentile regardless of the matrix's Por Temporada/Por 90 toggle
    (that toggle only ever changes the matrix's Valor column). Single brand
    hue with a soft fill, no Tercil red/amber/green — that scheme is
    reserved for the matrix's cell-level status color, not a Player's own
    shape here. A Metric missing its Percentual (statistic not available for
    this Player) plots as 0 rather than breaking the polygon.
    """
    radar_df = matrix_df[["Métrica", "Percentual"]].fillna(0)
    fig = px.line_polar(radar_df, r="Percentual", theta="Métrica", line_close=True, range_r=[0, 100])
    fig.update_traces(
        line_color=SEQUENTIAL_BLUE,
        fill="toself",
        fillcolor="rgba(42, 120, 214, 0.25)",
        hovertemplate="%{theta}: %{r:.0f}%<extra></extra>",
    )
    return fig


def render_player_card(player: Player) -> None:
    """Player identity card: avatar placeholder, name, positions, Team, and
    the (currently always empty) biographical fields."""
    with st.container(border=True):
        avatar_col, info_col = st.columns([1, 4], vertical_alignment="center")
        with (
            avatar_col,
            st.container(
                border=True,
                height=AVATAR_HEIGHT,
                horizontal_alignment="center",
                vertical_alignment="center",
            ),
        ):
            st.markdown(":material/person:", text_alignment="center")
        with info_col:
            st.subheader(player.name)
            st.caption(f"{position_codes(player) or 'Sem posição registrada'} · {player.team.name}")

        bio_cols = st.columns(3)
        with bio_cols[0]:
            st.metric("Idade", bio_field(player.age))
        with bio_cols[1]:
            st.metric("Nacionalidade", bio_field(player.nationality))
        with bio_cols[2]:
            st.metric("Pé preferido", bio_field(player.preferred_foot))


def render_metrics_section(
    players: list[Player], comparison_population: list[Player], player: Player
) -> None:
    """Metrics multiselect + Por Temporada/Por 90 toggle, then either the
    Tercil-colored matrix or a percentile radar for the same selected
    Metrics (Matriz<->Radar toggle) — or an instruction message while
    nothing is selected yet. Lives in the column beside `render_player_card`,
    per Q11 of the grill that originated this spec — card and Metrics side
    by side, not stacked. Switching Matriz<->Radar, like switching Por
    Temporada/Por 90, never resets the Metrics multiselect: each widget's
    Streamlit-managed state is independent of the others, so no explicit
    `st.session_state` bookkeeping is needed here (unlike Position Group in
    `sync_position_group_with_player`, which has to survive Player changes).
    """
    st.subheader("Métricas")
    label_options = metric_label_options(players)
    metric_col, toggle_col = st.columns([3, 1])
    with metric_col:
        selected_metric_labels = st.multiselect("Métricas", sorted(label_options))
    with toggle_col:
        value_kind_label = st.radio("Tipo de Valor", list(VALUE_KIND_BY_LABEL), horizontal=True)

    if not selected_metric_labels:
        st.info("Selecione ao menos uma Métrica para ver a matriz ou o radar de comparação.")
        return

    view = st.radio("Visualização", VIEW_OPTIONS, horizontal=True)

    value_kind = VALUE_KIND_BY_LABEL[value_kind_label]
    specs = [
        MetricSpec(key=label_options[label], label=label, kind=value_kind)
        for label in selected_metric_labels
    ]
    matrix_df = metric_matrix_dataframe(comparison_population, player, specs)

    if view == "Radar":
        st.plotly_chart(metric_radar_chart(matrix_df), width="stretch")
    else:
        styled_matrix = matrix_df.style.map(style_percentile_cell, subset=["Percentual"])
        st.dataframe(
            styled_matrix,
            width="stretch",
            hide_index=True,
            column_config=matrix_column_config(matrix_df, value_kind),
        )


def main() -> None:
    st.title("Análise de Jogadores")

    players = get_players()
    if not players:
        st.warning("Nenhum jogador encontrado. O pipeline de ingestão já foi executado?")
        return

    position_groups = sorted({g for p in players if (g := position_group(p)) is not None})
    search_options = player_search_options(players)

    with st.sidebar:
        st.header("Filtros")
        search_label = st.selectbox(
            "Buscar Jogador",
            [NO_PLAYER_SELECTED, *search_options],
            key="workspace_player_search",
        )
        selected_player = search_options.get(search_label)

        sync_position_group_with_player(selected_player, position_groups)
        selected_group = st.selectbox(
            "Grupo de Posição",
            [ALL_POSITION_GROUPS, *position_groups],
            key=POSITION_GROUP_KEY,
        )
        minutes_floor = st.number_input("Minutos Mínimos", min_value=0, value=0, step=90)

    if selected_player is None:
        st.info("Busque um jogador na barra lateral para começar a análise.")
        return

    comparison_population = (
        players if selected_group == ALL_POSITION_GROUPS else filter_by_position_group(players, selected_group)
    )
    comparison_population = apply_minutes_floor(comparison_population, minutes_floor)

    card_col, metrics_col = st.columns([1, 2])
    with card_col:
        render_player_card(selected_player)
        st.caption(
            f"População de comparação: {len(comparison_population)} jogador(es) · "
            f"Grupo de Posição: {selected_group} · Minutos mínimos: {int(minutes_floor)}"
        )
    with metrics_col:
        render_metrics_section(players, comparison_population, selected_player)


main()

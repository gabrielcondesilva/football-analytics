"""Player Analysis page (Análise de Jogadores): search a single Player, scope
a Comparison Population by exact Position (union match against the Player's
own codes) + Minutes Floor, show that Player's biographical card, and
compare selected Metrics against the Comparison Population as either a
Tercil-colored matrix or a percentile radar.

Full rebuild per .scratch/player-analysis-page/spec.md, tickets 03-05: shell/
search/filters/card, Metrics multiselect + Por Temporada/Por 90 toggle +
Tercil matrix, and the Matriz<->Radar toggle. The page's previous content
(general leaderboard, Insights, Scout Comparison, PDF export) was removed
per ADR 0003 — see docs/adr/0003-drop-scout-comparison-on-workspace-rebuild.md.
"""

from __future__ import annotations

from typing import Literal, cast

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
    filter_by_shared_position,
    percentile,
    tercile_band,
)
from football_analytics.dashboard.data import get_players
from football_analytics.dashboard.shared import (
    metric_label_options,
    nationality_label,
    position_codes,
    preferred_foot_label,
)
from football_analytics.domain.models import Player

NO_PLAYER_SELECTED = "Selecione um jogador…"

AVATAR_HEIGHT = 160

VALUE_KIND_BY_LABEL: dict[str, MetricKind] = {"Por Temporada": "raw", "Por 90 min": "per_90"}
VIEW_OPTIONS = ("Matriz", "Radar")

# Default sequential hue from the project's dataviz skill (references/
# palette.md) — same tone used elsewhere in the app (Overview's leaderboards,
# before their removal). The radar is a single Player's own profile, not a
# good/bad status, so it stays on this one brand hue rather than the matrix's
# Tercil red/amber/green.
SEQUENTIAL_BLUE = "#2a78d6"

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


def metric_matrix_dataframe(
    comparison_population: list[Player], player: Player, specs: list[MetricSpec]
) -> pd.DataFrame:
    """One row per selected Metric: its Value (per `spec.kind`) and its
    Percentile within `comparison_population`. Percentile is ranked on the
    same basis as Valor — raw season totals under Por Temporada, per-90 rate
    under Por 90 min — so a bench player's near-zero raw total doesn't skew
    the Por 90 min percentile of a Player who plays every minute, and vice
    versa. `spec.kind` is always "raw" or "per_90" here, never "percentile"
    itself (that's `metric_radar_chart`/this function's own concern, not a
    caller-supplied MetricSpec).

    A Metric missing for this Player (or for the whole population) keeps its
    row with a blank Valor/Percentual rather than being dropped, so every
    Metric the user picked stays visible in the matrix.
    """
    rows = []
    for spec in specs:
        rows.append(
            {
                "Métrica": spec.label,
                "Valor": compute_metric(comparison_population, player, spec),
                "Percentual": percentile(
                    comparison_population, player, spec.key, kind=cast(Literal["raw", "per_90"], spec.kind)
                ),
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
    underlying data is itself fractional. Percentual always shows one
    decimal, independent of the toggle.
    """
    config: dict = {"Percentual": st.column_config.NumberColumn(format="%.1f%%")}
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
    """Player identity card: photo (or a placeholder icon while the Player's
    `photo_url` hasn't been backfilled) stacked above name/positions/Team,
    then the biographical fields as a stacked label/value list.

    This card lives in a narrow sidebar-width column (`card_col`, see
    `main()`), so the photo is stacked above the name — rather than beside
    it in a slim avatar column — to give it real visual presence at that
    width. The bio fields (Idade/Nacionalidade/Pé preferido) are plain text
    rows instead of `st.metric`: a long value like "República Dominicana"
    needs to wrap onto a second line at this width, and `st.metric`'s large
    bold value doesn't wrap cleanly and reads as a different type scale than
    the name/caption above it. Plain rows wrap like normal text and share
    the body font, so photo + name + bio read as one coherent unit. "-"
    until FotMob has that field for this Player, or until the Player was
    ingested after bio fields existed — via `bio_field`."""
    with st.container(border=True):
        with st.container(horizontal_alignment="center"):
            with st.container(
                border=True,
                width=AVATAR_HEIGHT,
                height=AVATAR_HEIGHT,
                horizontal_alignment="center",
                vertical_alignment="center",
            ):
                if player.photo_url:
                    st.image(player.photo_url, width=AVATAR_HEIGHT - 24)
                else:
                    st.markdown(":material/person:", text_alignment="center")
            st.subheader(player.name, text_alignment="center")
            st.caption(
                f"{position_codes(player) or 'Sem posição registrada'} · {player.team.name}",
                text_alignment="center",
            )

        st.divider()

        for label, value in (
            ("Idade", bio_field(player.age)),
            ("Nacionalidade", bio_field(nationality_label(player.nationality))),
            ("Pé preferido", bio_field(preferred_foot_label(player.preferred_foot))),
        ):
            st.write(f"**{label}:** {value}")


def render_metrics_content(
    comparison_population: list[Player],
    player: Player,
    label_options: dict[str, str],
    selected_metric_labels: list[str],
    value_kind_label: str,
    view: str,
) -> None:
    """Tercil-colored matrix or percentile radar for the Metrics chosen by
    the sidebar's Métricas multiselect + Tipo de Valor/Visualização toggles
    (below Buscar Jogador) — or an instruction message while nothing is
    selected yet. Lives in the column beside `render_player_card`, per Q11 of
    the grill that originated this spec — card and Metrics side by side, not
    stacked.
    """
    st.subheader("Métricas")
    if not selected_metric_labels:
        st.info("Selecione ao menos uma Métrica na barra lateral para ver a matriz ou o radar de comparação.")
        return

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

    search_options = player_search_options(players)

    with st.sidebar:
        st.header("Filtros")
        search_label = st.selectbox(
            "Buscar Jogador",
            [NO_PLAYER_SELECTED, *search_options],
            key="workspace_player_search",
        )
        selected_player = search_options.get(search_label)

        st.subheader("Métricas")
        label_options = metric_label_options(players)
        selected_metric_labels = st.multiselect(
            "Métricas", sorted(label_options), placeholder="Selecione as métricas…"
        )
        value_kind_label = st.radio("Tipo de Valor", list(VALUE_KIND_BY_LABEL), horizontal=True)
        view = st.radio("Visualização", VIEW_OPTIONS, horizontal=True)

        minutes_floor = st.number_input("Minutos Mínimos", min_value=0, value=900, step=90)

    if selected_player is None:
        st.info("Busque um jogador na barra lateral para começar a análise.")
        return

    comparison_population = filter_by_shared_position(players, selected_player)
    comparison_population = apply_minutes_floor(comparison_population, minutes_floor)

    card_col, metrics_col = st.columns([1, 2])
    with card_col:
        st.subheader("Perfil do Jogador")
        render_player_card(selected_player)
        st.caption(
            f"População de comparação: {len(comparison_population)} jogador(es) · "
            f"Posições: {position_codes(selected_player)} · Minutos mínimos: {int(minutes_floor)}"
        )
    with metrics_col:
        render_metrics_content(
            comparison_population,
            selected_player,
            label_options,
            selected_metric_labels,
            value_kind_label,
            view,
        )


main()

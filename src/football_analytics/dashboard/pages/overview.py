"""Overview page: Top 10 Players per selected Metric.

Empty until a Metric is picked; each Metric selected in either the Per-90
or Per Season multiselect adds its own Top 10 table (Photo, Name, Team,
Positions, value), laid out two per row — Per-90 selections first, then Per Season, in
each multiselect's own selection order. Picking the same Metric in both
shows both: they're independent selections, not a single toggle, so e.g.
xA Per-90 and xA Per Season can sit side by side. A Statistic already
expressed as a percent is shown as-is in both cases, see `per_90()`.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape as html_escape

import streamlit as st

from football_analytics.analysis.metrics import (
    MetricKind,
    apply_minutes_floor,
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

# Injected once per page render (see main()), not per table, so the markup
# for each individual leaderboard can stay a plain <table> without repeating
# a <style> block per card. Colors are theme-aware (Streamlit's CSS custom
# properties) rather than fixed hex values, so the table reads correctly in
# both light and dark theme.
LEADERBOARD_TABLE_CSS = """
<style>
.lb-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.lb-table th {
    text-align: left;
    padding: 0.4rem 0.6rem;
    border-bottom: 1px solid var(--secondary-background-color, rgba(128, 128, 128, 0.4));
    color: var(--text-color);
    opacity: 0.7;
    font-weight: 600;
}
.lb-table td {
    padding: 0.35rem 0.6rem;
    border-bottom: 1px solid var(--secondary-background-color, rgba(128, 128, 128, 0.25));
    color: var(--text-color);
    vertical-align: middle;
}
.lb-table tr:last-child td { border-bottom: none; }
.lb-player { display: flex; align-items: center; gap: 0.5rem; }
.lb-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
    background: var(--secondary-background-color, rgba(128, 128, 128, 0.25));
}
.lb-avatar--placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-color);
    opacity: 0.6;
}
.lb-name { font-weight: 500; }
.lb-value { text-align: right; font-variant-numeric: tabular-nums; }
</style>
"""


@dataclass(frozen=True)
class LeaderboardRow:
    """One ranked Player, ready to render as a leaderboard table row."""

    photo_url: str | None
    name: str
    team: str
    positions: str
    value: float


def leaderboard_rows(players: list[Player], key: str, kind: MetricKind) -> list[LeaderboardRow]:
    entries = top_metric_leaderboard(players, key, kind=kind, size=TABLE_SIZE)
    return [
        LeaderboardRow(
            photo_url=player.photo_url,
            name=player.name,
            team=player.team.name,
            positions=position_codes(player),
            value=value,
        )
        for player, value in entries
    ]


def _player_cell_html(row: LeaderboardRow) -> str:
    """Photo + name rendered as one inline unit ("Jogador" cell).

    `st.dataframe`'s `column_config` can't merge an image and text into a
    single cell: `ImageColumn` only renders an image (no accompanying text),
    and `MarkdownColumn` — the only column type that supports Markdown image
    syntax — renders that Markdown inside a click-to-open overlay, not in
    the cell itself. Hand-rendering this leaderboard as HTML trades away
    `st.dataframe`'s built-in sort/selection for a real inline photo+name
    cell. A Player missing `photo_url` gets a neutral initial-letter avatar
    instead of a broken-image icon.
    """
    name = html_escape(row.name)
    if row.photo_url:
        avatar = f'<img class="lb-avatar" src="{html_escape(row.photo_url)}" alt="" />'
    else:
        initial = html_escape(row.name[:1].upper()) if row.name else "?"
        avatar = f'<span class="lb-avatar lb-avatar--placeholder">{initial}</span>'
    return f'<span class="lb-player">{avatar}<span class="lb-name">{name}</span></span>'


def leaderboard_table_html(rows: list[LeaderboardRow], label: str, kind: MetricKind) -> str:
    """Render leaderboard rows as an HTML table (Jogador, Time, Posições,
    value), assuming `LEADERBOARD_TABLE_CSS` was already injected on the
    page.

    Per-90 values are rates (minutes-scaled, or a Statistic already
    expressed as a percent per `per_90()`), so they always render with two
    decimal places. Per Season values are season totals and are typically
    whole numbers (goals, tackles, ...) that already read fine unformatted;
    only format them when the underlying data is itself fractional (e.g. a
    percent-format Statistic shown as a season figure), so genuine counts
    keep reading as plain integers. All Player-controlled fields (name,
    team, positions, photo URL) are HTML-escaped since they're interpolated
    into raw markup.
    """
    use_decimals = kind == "per_90" or any(row.value % 1 != 0 for row in rows)

    def format_value(value: float) -> str:
        return f"{value:.2f}" if use_decimals else f"{value:.0f}"

    body_rows = "".join(
        "<tr>"
        f"<td>{_player_cell_html(row)}</td>"
        f"<td>{html_escape(row.team)}</td>"
        f"<td>{html_escape(row.positions)}</td>"
        f'<td class="lb-value">{format_value(row.value)}</td>'
        "</tr>"
        for row in rows
    )
    return (
        '<table class="lb-table"><thead><tr>'
        "<th>Jogador</th><th>Time</th><th>Posições</th>"
        f'<th class="lb-value">{html_escape(label)}</th>'
        f"</tr></thead><tbody>{body_rows}</tbody></table>"
    )


def main() -> None:
    st.title("Visão Geral")

    players = get_players()
    if not players:
        st.warning("Nenhum jogador encontrado. O pipeline de ingestão já foi executado?")
        return

    team_names = sorted({p.team.name for p in players})
    position_code_options = sorted({pos.code for p in players for pos in p.positions})
    league_names = sorted({p.league for p in players if p.league})
    label_options = metric_label_options(players)

    with st.sidebar:
        st.header("Filtros")
        per90_labels = st.multiselect(
            "Métricas (Por 90 min)", sorted(label_options), placeholder="Selecione as métricas…"
        )
        season_labels = st.multiselect(
            "Métricas (Por Temporada)", sorted(label_options), placeholder="Selecione as métricas…"
        )
        selected_teams = st.multiselect("Time", team_names, placeholder="Selecione os times…")
        selected_positions = st.multiselect(
            "Posição", position_code_options, placeholder="Selecione as posições…"
        )
        selected_leagues = st.multiselect("Liga", league_names, placeholder="Selecione as ligas…")
        minutes_floor = st.number_input("Minutos Mínimos", min_value=0, value=900, step=90)
        st.multiselect(
            "Idade",
            [],
            disabled=True,
            placeholder="Sem dados disponíveis",
            help="Em breve — depende de dados de idade ainda não ingeridos.",
        )
        st.multiselect(
            "Nacionalidade",
            [],
            disabled=True,
            placeholder="Sem dados disponíveis",
            help="Em breve — depende de dados de nacionalidade ainda não ingeridos.",
        )

    view_players = players
    if selected_teams:
        view_players = [p for p in view_players if p.team.name in selected_teams]
    if selected_positions:
        view_players = [
            p for p in view_players if any(pos.code in selected_positions for pos in p.positions)
        ]
    if selected_leagues:
        view_players = [p for p in view_players if p.league in selected_leagues]
    view_players = apply_minutes_floor(view_players, minutes_floor)

    selections: list[tuple[str, MetricKind]] = [(label, "per_90") for label in per90_labels] + [
        (label, "raw") for label in season_labels
    ]

    if not selections:
        st.info("Selecione uma métrica de desempenho")
        return

    st.markdown(LEADERBOARD_TABLE_CSS, unsafe_allow_html=True)
    for row_start in range(0, len(selections), GRID_COLUMNS):
        row = selections[row_start : row_start + GRID_COLUMNS]
        columns = st.columns(GRID_COLUMNS)
        for column, (label, kind) in zip(columns, row, strict=False):
            with column:
                key = label_options[label]
                st.subheader(f"{label} ({KIND_DISPLAY_LABEL[kind]})")
                rows = leaderboard_rows(view_players, key, kind)
                if not rows:
                    st.info("Nenhum jogador possui essa métrica com os filtros atuais.")
                else:
                    st.markdown(
                        leaderboard_table_html(rows, label, kind), unsafe_allow_html=True
                    )


main()

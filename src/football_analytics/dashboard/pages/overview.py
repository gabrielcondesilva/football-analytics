"""Overview page: Top 10 Players per selected Metric.

Empty until a Metric is picked; each Metric selected in either the Per-90
or Per Season multiselect adds its own Top 10 leaderboard card (Rank+Photo+
Name, Age, Crest+Team, Positions, value — one row per Player, no table
columns/header), laid out two per row — Per-90 selections first, then Per
Season, in each multiselect's own selection order. Picking the same Metric
in both shows both: they're independent selections, not a single toggle, so
e.g. xA Per-90 and xA Per Season can sit side by side. A Statistic already
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
from football_analytics.dashboard.shared import (
    bio_field,
    metric_label_options,
    position_codes,
    team_logo_url,
)
from football_analytics.domain.models import Player

TABLE_SIZE = 10
GRID_COLUMNS = 2

KIND_DISPLAY_LABEL: dict[MetricKind, str] = {
    "per_90": "Por 90 min",
    "raw": "Por Temporada",
}

# Injected once per page render (see main()), not per card, so each
# leaderboard's row-list markup doesn't repeat a <style> block. Colors are
# theme-aware (Streamlit's CSS custom properties), so the list reads
# correctly in both light and dark theme; `.lb-value` matches `.lb-name`'s
# color/weight rather than a status hue — this is a Top 10 by raw/per-90
# value, not a Player ranked against a Comparison Population, so neither a
# single brand accent nor the Tercil red/amber/green (reserved for that
# different concept, see CONTEXT.md) is the right read here.
#
# `.lb-list` is ONE CSS Grid shared by every Player row (5 cells per row:
# Rank+Photo+Name, Idade, Escudo+Time, Posições, Valor — `leaderboard_rows_
# html` emits them as flat grid children, not wrapped in a per-row div), so
# each column's width is computed once across all rows, the same way a real
# `<table>` aligns its columns. Per-row `display:flex` cells computed their
# own width independently and drifted out of alignment (e.g. Valor landing
# at a different x per row depending on that row's Team-name/Posições
# length) — this is what the shared grid fixes. `.lb-identity` and
# `.lb-team` still get `minmax(0, ...)` + ellipsis so a long name/team
# truncates instead of pushing Posições/Valor out of the card.
LEADERBOARD_CARD_CSS = """
<style>
.lb-list {
    display: grid;
    grid-template-columns: minmax(0, 1.4fr) auto minmax(0, 1fr) auto auto;
    column-gap: 1rem;
}
.lb-cell {
    display: flex;
    align-items: center;
    min-width: 0;
    padding: 0.55rem 0;
    border-bottom: 1px solid var(--secondary-background-color, rgba(128, 128, 128, 0.25));
}
/* Exactly 5 cells per Player row, so the grid's last 5 children are always
   the last row's — this is what drops the divider after the final row,
   now that no `.lb-row` wraps each row as its own element. */
.lb-list > *:nth-last-child(-n+5) { border-bottom: none; }

.lb-identity { gap: 0.6rem; }
.lb-rank {
    flex-shrink: 0;
    width: 1.3rem;
    text-align: right;
    font-weight: 600;
    font-size: 0.8rem;
    color: var(--text-color);
    opacity: 0.5;
    font-variant-numeric: tabular-nums;
}
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
.lb-name {
    font-weight: 600;
    font-size: 0.82rem;
    color: var(--text-color);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.lb-age {
    justify-content: center;
    font-size: 0.8rem;
    color: var(--text-color);
    opacity: 0.7;
    font-variant-numeric: tabular-nums;
}

.lb-team { gap: 0.45rem; }
.lb-crest { width: 20px; height: 20px; object-fit: contain; flex-shrink: 0; }
.lb-crest--hidden { display: none; }
.lb-team-name {
    color: var(--text-color);
    opacity: 0.75;
    font-size: 0.72rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.lb-position { justify-content: center; }
.lb-position-badge {
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    background: var(--secondary-background-color, rgba(128, 128, 128, 0.18));
    color: var(--text-color);
    opacity: 0.8;
    font-size: 0.62rem;
    font-weight: 600;
    white-space: nowrap;
}

.lb-value {
    justify-content: flex-end;
    gap: 0.35rem;
    font-weight: 700;
    font-size: 0.92rem;
    color: var(--text-color);
    font-variant-numeric: tabular-nums;
}
/* Rare-case mismatch indicator (Player transferred, Statistics still from
   their previous League — see `_league_flag_html`). Reserves no space when
   absent; when present, a small circular "i" rather than a text pill so it
   doesn't compete with the value's own weight/size for attention. Native
   `title` attribute supplies the hover tooltip, no JS needed. */
.lb-league-flag {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--secondary-background-color, rgba(128, 128, 128, 0.25));
    color: var(--text-color);
    opacity: 0.65;
    font-size: 0.6rem;
    font-weight: 700;
    font-style: italic;
    font-family: serif;
    cursor: help;
}

.lb-title {
    font-weight: 700;
    font-size: 1.05rem;
    color: var(--text-color);
    margin: 0 0 0.5rem 0;
}
</style>
"""


@dataclass(frozen=True)
class LeaderboardRow:
    """One ranked Player, ready to render as a leaderboard row."""

    rank: int
    photo_url: str | None
    name: str
    age: int | None
    team_name: str
    team_fotmob_id: int
    positions: str
    value: float

    league: str | None = None
    statistics_league: str | None = None
    """The Player's current League (via their Team) and the League whose
    Season actually produced `value` (via their latest Snapshot) — see
    `Player.league`/`Player.statistics_league` (ADR-0004). These differ for
    a recently-transferred Player, whose shown value still comes from their
    previous League. `None`/`None` for a Player predating the League-
    backfill or with no Statistics Season resolved."""


def leaderboard_rows(players: list[Player], key: str, kind: MetricKind) -> list[LeaderboardRow]:
    entries = top_metric_leaderboard(players, key, kind=kind, size=TABLE_SIZE)
    return [
        LeaderboardRow(
            rank=rank,
            photo_url=player.photo_url,
            name=player.name,
            age=player.age,
            team_name=player.team.name,
            team_fotmob_id=player.team.fotmob_id,
            positions=position_codes(player),
            value=value,
            league=player.league,
            statistics_league=player.statistics_league,
        )
        for rank, (player, value) in enumerate(entries, start=1)
    ]


def _identity_cell_html(row: LeaderboardRow) -> str:
    """Rank + photo + name rendered as one tightly-grouped inline unit.

    `st.dataframe`'s `column_config` can't merge an image and text into a
    single cell: `ImageColumn` only renders an image (no accompanying text),
    and `MarkdownColumn` — the only column type that supports Markdown image
    syntax — renders that Markdown inside a click-to-open overlay, not in
    the cell itself. Hand-rendering this leaderboard as HTML trades away
    `st.dataframe`'s built-in sort/selection for a real inline rank+photo+
    name cell. A Player missing `photo_url` gets a neutral initial-letter
    avatar instead of a broken-image icon.
    """
    name = html_escape(row.name)
    if row.photo_url:
        avatar = f'<img class="lb-avatar" src="{html_escape(row.photo_url)}" alt="" />'
    else:
        initial = html_escape(row.name[:1].upper()) if row.name else "?"
        avatar = f'<span class="lb-avatar lb-avatar--placeholder">{initial}</span>'
    return (
        '<div class="lb-cell lb-identity">'
        f'<span class="lb-rank">{row.rank}</span>'
        f"{avatar}"
        f'<span class="lb-name" title="{name}">{name}</span>'
        "</div>"
    )


def _team_cell_html(row: LeaderboardRow) -> str:
    """Crest + Team name as one tightly-grouped inline unit, mirroring
    `_identity_cell_html`. The crest URL is FotMob's deterministic team-logo
    CDN path (`team_logo_url`, keyed on `Team.fotmob_id`) — like Player's own
    `photo_url`, no extra ingestion is needed to populate it.

    Not every Team has a crest at that URL (lower-profile/newly-promoted
    clubs) — `onerror` swaps a failed request for `lb-crest--hidden` instead
    of leaving the browser's broken-image icon on screen, so the row
    degrades to Team name alone rather than showing a visibly broken asset.
    `this.onerror = null` guards against a retry loop should the fallback
    class itself somehow fail to suppress the image.
    """
    team_name = html_escape(row.team_name)
    crest = (
        '<img class="lb-crest" src="'
        f"{html_escape(team_logo_url(row.team_fotmob_id))}"
        '" alt="" loading="lazy" '
        "onerror=\"this.onerror=null;this.classList.add('lb-crest--hidden');\" />"
    )
    return (
        '<div class="lb-cell lb-team">'
        f"{crest}"
        f'<span class="lb-team-name" title="{team_name}">{team_name}</span>'
        "</div>"
    )


def _league_flag_html(row: LeaderboardRow) -> str:
    """A discreet mismatch indicator for a Player whose shown `value` was
    produced in a different League than the one they currently play in —
    e.g. right after a transfer, before they've logged minutes in the new
    League (see `LeaderboardRow.league`/`statistics_league`, ADR-0004).

    Returns "" (no markup at all, not just a hidden element) when
    `league`/`statistics_league` are equal or either is `None`, so the
    common case — today, effectively every row — reserves no layout space
    and adds no visual weight. When they do differ, a small icon with a
    native `title` tooltip communicates "these numbers are from
    {statistics_league}, not {league}" without competing with the value
    itself for attention.
    """
    if (
        row.statistics_league is None
        or row.league is None
        or row.statistics_league == row.league
    ):
        return ""
    tooltip = f"Valores de {row.statistics_league}, não {row.league}"
    return f'<span class="lb-league-flag" title="{html_escape(tooltip)}">i</span>'


def leaderboard_rows_html(rows: list[LeaderboardRow], kind: MetricKind) -> str:
    """Render leaderboard rows as a card row-list — one line per Player
    (Rank+Photo+Name, Idade, Escudo+Time, Posições, Valor), no table
    columns/header — assuming `LEADERBOARD_CARD_CSS` was already injected on
    the page. The card's own border lives in the caller's
    `st.container(border=True)`; the `.lb-title` heading is rendered by the
    caller too (a plain `st.subheader` reads too large next to this list's
    now-smaller type scale), not in this markup.

    Each Player contributes 5 flat `.lb-cell` children to the shared
    `.lb-list` grid (not a wrapping per-row div — see `LEADERBOARD_CARD_CSS`)
    so every row's Rank+Photo+Name/Idade/Escudo+Time/Posições/Valor line up
    in the same columns regardless of how long any one row's name/team/
    positions are.

    Per-90 values are rates (minutes-scaled, or a Statistic already
    expressed as a percent per `per_90()`), so they always render with two
    decimal places. Per Season values are season totals and are typically
    whole numbers (goals, tackles, ...) that already read fine unformatted;
    only format them when the underlying data is itself fractional (e.g. a
    percent-format Statistic shown as a season figure), so genuine counts
    keep reading as plain integers. Idade falls back to "-" via `bio_field`
    until FotMob's bio fields are backfilled for every Player (today, only
    some rows have it). All Player-controlled fields are HTML-escaped since
    they're interpolated into raw markup.
    """
    use_decimals = kind == "per_90" or any(row.value % 1 != 0 for row in rows)

    def format_value(value: float) -> str:
        return f"{value:.2f}" if use_decimals else f"{value:.0f}"

    cells = "".join(
        f"{_identity_cell_html(row)}"
        f'<div class="lb-cell lb-age">{html_escape(bio_field(row.age))}</div>'
        f"{_team_cell_html(row)}"
        '<div class="lb-cell lb-position">'
        f'<span class="lb-position-badge">{html_escape(row.positions or "-")}</span>'
        "</div>"
        f'<div class="lb-cell lb-value">{_league_flag_html(row)}{format_value(row.value)}</div>'
        for row in rows
    )
    return f'<div class="lb-list">{cells}</div>'


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

    st.markdown(LEADERBOARD_CARD_CSS, unsafe_allow_html=True)
    for row_start in range(0, len(selections), GRID_COLUMNS):
        row = selections[row_start : row_start + GRID_COLUMNS]
        columns = st.columns(GRID_COLUMNS)
        for column, (label, kind) in zip(columns, row, strict=False):
            with column, st.container(border=True):
                key = label_options[label]
                title = f"{html_escape(label)} ({html_escape(KIND_DISPLAY_LABEL[kind])})"
                st.markdown(
                    f'<div class="lb-title">{title}</div>', unsafe_allow_html=True
                )
                rows = leaderboard_rows(view_players, key, kind)
                if not rows:
                    st.info("Nenhum jogador possui essa métrica com os filtros atuais.")
                else:
                    st.markdown(leaderboard_rows_html(rows, kind), unsafe_allow_html=True)


main()

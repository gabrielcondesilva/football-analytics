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

from html import escape as html_escape
from typing import Literal, cast

import pandas as pd
import plotly.express as px
import streamlit as st
from plotly.graph_objects import Figure

from football_analytics.analysis.metrics import (
    MINUTES_PLAYED_KEY,
    MetricKind,
    MetricSpec,
    TercileBand,
    apply_minutes_floor,
    compute_metric,
    filter_by_shared_position,
    percentile,
    statistic_value,
    tercile_band,
)
from football_analytics.dashboard.data import get_players
from football_analytics.dashboard.shared import (
    SEQUENTIAL_BLUE,
    bio_field,
    metric_label_options,
    nationality_flag_url,
    nationality_label,
    position_codes,
    preferred_foot_label,
    team_logo_url,
)
from football_analytics.domain.models import Player

NO_PLAYER_SELECTED = "Selecione um jogador…"

VALUE_KIND_BY_LABEL: dict[str, MetricKind] = {"Por 90 min": "per_90", "Por Temporada": "raw"}
VIEW_OPTIONS = ("Matriz", "Radar")

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


# Injected once per render inside `render_player_card` — this page shows
# exactly one Player Card at a time, so there's no risk of the <style> block
# appearing more than once the way `overview.py`'s repeated per-row
# leaderboard markup would. Hand-rendered as one HTML/CSS block rather than
# stacked native Streamlit widgets, same rationale as before this redesign
# (each native widget carries its own default margin Streamlit gives no way
# to collapse). Colors are theme-aware via Streamlit's CSS custom properties
# (`--text-color`, `--secondary-background-color`), same convention as
# `overview.py`'s `LEADERBOARD_CARD_CSS`, so the card reads correctly in
# both light and dark theme.
#
# Second-iteration layout, replacing the header-row version (crest+flag left,
# photo right, name beside it): the photo is now the vertically-centered
# focal point of the card, with Team name and Player name stacked directly
# beneath it — the actual ask from user feedback ("a imagem dele tem que
# ficar centralizado e o nome abaixo da foto"). Team crest and nationality
# still both appear, just relocated to a thin top row that flanks the photo
# (crest top-left corner, flag+country top-right corner) instead of sitting
# beside it, so they read as card "chrome" framing the portrait rather than
# competing with it for the centerline. The avatar itself is enlarged
# (76px -> 128px) and given a themed ring so it reads as a portrait medallion
# — the "player card" feel the user asked for — rather than a small profile
# thumbnail.
#
# Third-iteration tweak, per direct user feedback: the divider (`.pc-divider`,
# now removed) between the Player name and the stat fields is gone, and the
# four stat fields (`.pc-stats`) no longer sit in a centered 2x2 grid — they
# stack as a single left-aligned column (Idade, Posição, Pé preferido,
# Minutos Jogados, in that order), with a slightly smaller font than before.
# This is an intentional break from the rest of the card's centered
# alignment, not a bug: the photo/name block above stays centered while only
# the stats block below it goes left-aligned, per the user's explicit ask.
#
# Fourth-iteration tweak, per direct user feedback ("vamos colocar o titulo
# ao lado do valor, por exemplo, Idade: 22, Posição: ..."): each stat's label
# and value now sit on the same line ("Idade: 22") instead of label-above-
# value on two lines. The four rows (`.pc-stat-row`) still stack vertically,
# still left-aligned, still in the same order — only the label/value pairing
# within a row changed from stacked to inline.
#
# Fifth-iteration tweak, per direct user feedback ("deixar mais estreito o
# card com o escudo do time alinhado com essas palavras... Pode colocar
# também o [flag] em baixo do escudo do time e sem o nome do pais"): `.pc-card`
# now carries its own `max-width` (matching `.pc-stats`'s), so the whole card
# — crest+flag, avatar, names, stats — shares one narrow column instead of
# the crest/flag row spanning the full bordered container width while only
# the stats/avatar below it stayed narrow (that mismatch was the source of
# the "muito espaço em branco na lateral" complaint). The old full-width
# `.pc-top-row` (crest left corner, flag+country name right corner) is gone;
# `.pc-crest-flag` replaces it as a small vertical stack (crest on top, flag
# directly below, image only — `.pc-nationality-name`'s country-name text is
# dropped entirely) pinned to the card's left edge via `align-self:
# flex-start`, so it lines up flush with the stat rows beneath it. The photo
# and Team/Player name block keep their own centered alignment (`align-items:
# center` on `.pc-card` still applies to every other child) — this is a
# deliberate one card, two alignments split: crest+flag+stats flush left,
# everything else centered, per the user's explicit call-out that only the
# crest/flag column needed to move.
#
# Sixth-iteration tweaks, per direct user feedback ("um pequeno espaçamento
# entre o Minutos Jogados a linha de borda inferior, a mesma que tem da
# superior pro escudo do time... aumentar um pouco o escudo e o pais e vamos
# voltar o pais com o nome do pais e pro outro lado do card"), four changes:
# (1) `.pc-card` gains its own `padding-bottom` — nothing in this stylesheet
# had ever added space below the last stat row (the flex `gap` on
# `.pc-stats` only inserts space *between* rows, not after the final one), so
# the bottom of the card sat flush against the bordered container's own
# inset while the top read with a visible gap above the crest. We can't
# re-measure the live container padding in a browser (project convention),
# so rather than guess a pixel value to literally match it, `.pc-card`
# reuses this file's existing "small gap" unit (0.75rem, the same value
# `.pc-top-row` below uses for its own margin-bottom) so the bottom finally
# gets *some* deliberate breathing room instead of none, in the same small
# spirit the user asked for ("um pequeno espaçamento"). (2) `.pc-crest` and
# `.pc-flag` are both scaled up ~20% (30px->36px; 20x14px->24x17px, keeping
# the same aspect ratio) — a modest bump, not a redesign, so the two still
# read as a matched pair. (3) `.pc-nationality-name` returns: the flag is no
# longer image-only, it once again carries the country name as text next to
# it. (4) The crest and the flag+country pairing split apart again: `.pc-
# crest-flag`'s single vertical stack is gone, replaced by `.pc-top-row` — a
# full-width flex row, crest on the left (still flush with `.pc-stats`'s left
# edge underneath it, since both are direct, unpadded, 100%-width children of
# `.pc-card`) and `.pc-nationality` (flag + name) pushed to the opposite,
# right-hand edge via `justify-content: space-between`. This is the second-
# iteration's original left/right flanking idea, revived now that the card's
# own `max-width` (from the fifth iteration) keeps that full-width row
# exactly as narrow as the stats column beneath it — the fifth iteration's
# fix for the alignment problem, without the fifth iteration's now-reversed
# "stack them together, no text" layout choice.
#
# Seventh-iteration tweak, per direct user feedback ("vamos estreitar um
# pouco mais o cartao, acho que tem bastante espaço em branco dos lados"):
# after the fifth iteration's fix, the crest/flag row and the stats column
# no longer *mismatch* each other's width, but the card as a whole still
# reads as narrower than its surrounding whitespace. Two independent
# contributors, both addressed here:
#   1. `card_col` in `main()` is a *ratio* of the page's wide-layout content
#      width, not a pixel value. At `[1, 3]` (fifth iteration), card_col is
#      25% of that row — comfortably wider than a ~220px card plus
#      `st.container(border=True)`'s own internal padding on typical wide-
#      layout viewport widths, leaving a visible margin inside the column
#      before the border is even reached. Narrowed further to `[1, 4]` (20%
#      of the row) so the column itself tracks the card's actual footprint
#      more closely; the width freed up goes to `metrics_col`, which is
#      chart content that benefits from it anyway.
#   2. `.pc-card`'s own `max-width` is trimmed from 220px to 200px — a modest
#      further reduction, not a redesign. Checked against the tightest
#      content row before picking this number: `.pc-stat-row` is
#      `white-space: nowrap`, and its longest row ("Minutos Jogados: 12.345
#      min") needs roughly 190px at this font size, so 200px keeps that row
#      from wrapping or clipping while still shrinking the card's footprint.
#      128px avatar and `.pc-top-row` (crest + flag + country name, which
#      already truncates via `text-overflow: ellipsis`) both fit comfortably
#      inside 200px too.
# Deliberately NOT touched: `st.container(border=True)`'s own internal
# padding. Streamlit doesn't expose a supported parameter for it, and
# nothing else in this dashboard (`overview.py` included) overrides a
# Streamlit-internal padding via its private emotion-cache class names — that
# would be a version-fragile hack with no precedent here, not a "reuse an
# established approach" move. If side whitespace is still visible after this
# change, that container padding (plus whatever margin remains between 200px
# and card_col's actual rendered width, which depends on the viewer's window
# size and can't be pinned exactly via ratio-based `st.columns`) is the
# remaining, unaddressed source — flagged here rather than guessed at.
PLAYER_CARD_CSS = """
<style>
.pc-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    width: 100%;
    max-width: 200px;
    margin: 0 auto;
    padding-bottom: 0.75rem;
}
.pc-top-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
}
.pc-crest { width: 36px; height: 36px; object-fit: contain; flex-shrink: 0; }
.pc-crest--hidden { display: none; }
.pc-nationality {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    min-width: 0;
}
.pc-flag {
    width: 24px;
    height: 17px;
    object-fit: cover;
    border-radius: 2px;
    flex-shrink: 0;
}
.pc-flag--hidden { display: none; }
.pc-nationality-name {
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--text-color);
    opacity: 0.65;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.pc-avatar, .pc-avatar-placeholder {
    width: 128px;
    height: 128px;
    border-radius: 50%;
    flex-shrink: 0;
    background: var(--secondary-background-color, rgba(128, 128, 128, 0.25));
    border: 3px solid var(--secondary-background-color, rgba(128, 128, 128, 0.35));
}
.pc-avatar { object-fit: cover; }
.pc-avatar-placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-color);
    opacity: 0.45;
}
.pc-team-name {
    margin-top: 0.85rem;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--text-color);
    opacity: 0.6;
}
.pc-name {
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--text-color);
    line-height: 1.25;
    margin: 0.15rem 0 0 0;
}
.pc-stats {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    text-align: left;
    gap: 0.55rem;
    width: 100%;
    margin-top: 1rem;
}
.pc-stat-row {
    white-space: nowrap;
}
.pc-stat-label {
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.01em;
    color: var(--text-color);
    opacity: 0.6;
    margin-right: 0.3rem;
}
.pc-stat-value {
    font-size: 0.85rem;
    font-weight: 700;
    color: var(--text-color);
}
</style>
"""

# Generic person silhouette shown in place of a photo when `Player.photo_url`
# hasn't been backfilled — inline SVG rather than an emoji/icon-font
# shortcode, so it renders identically regardless of the OS's emoji set and
# takes its color from `.pc-avatar-placeholder`'s `currentColor` (theme-
# aware, matches the rest of the card's ink). Scaled up from the previous
# 34px to keep the same proportion (~45% of the circle's diameter) inside
# the now-larger 128px avatar.
_PLACEHOLDER_AVATAR_SVG = (
    '<svg viewBox="0 0 24 24" width="56" height="56" fill="currentColor" aria-hidden="true">'
    '<path d="M12 12c2.7 0 4.9-2.2 4.9-4.9S14.7 2.2 12 2.2 7.1 4.4 7.1 7.1 9.3 12 12 12zm0 2.4'
    'c-3.3 0-9.8 1.6-9.8 4.9v2.4h19.6v-2.4c0-3.3-6.5-4.9-9.8-4.9z"/></svg>'
)


def minutes_played_display(player: Player) -> str:
    """"Minutos Jogados" stat-grid value: a whole number with a "."
    thousands separator (e.g. "2.847 min"), matching the reference card's
    own grouping convention. "-" until the Statistic exists for this
    Player, same convention as `bio_field`."""
    minutes = statistic_value(player, MINUTES_PLAYED_KEY)
    if minutes is None:
        return "-"
    return f"{int(minutes):,}".replace(",", ".") + " min"


def player_card_html(player: Player) -> str:
    """Player identity card body markup, paired with `PLAYER_CARD_CSS`.

    Second-iteration layout, per direct user feedback on the first redesign
    ("quero que fique mais com cara de card do jogador, a imagem dele tem
    que ficar centralizado e o nome abaixo da foto"): the photo is the
    centered focal point, with Team name then Player name stacked directly
    below it — deliberately a bigger departure from `exemplo/card.png`'s own
    side-by-side header than the previous iteration was, since the
    reference itself doesn't center its photo either. Team crest and the
    Player's nationality (flag + name) still both appear — moved to a thin
    top row flanking the photo (crest top-left corner, flag+country
    top-right corner) rather than stacked beside it, so they read as framing
    for the portrait instead of competing with it. The four bio fields — Idade,
    Posição, Pé preferido, Minutos Jogados, in that order — render as a single
    left-aligned column stacked directly below the Player name (third
    iteration: no more divider, no more centered 2x2 grid — direct user
    feedback asked for the stats to read left-aligned, one on top of the
    other). Each row renders as "Label: value" on one line (fourth iteration:
    label and value used to stack on two lines within a row; user asked for
    them side by side instead). No "Ativo" badge: this project's domain model
    has no active/injured status to back one.

    Fifth iteration: the crest+nationality "top row" is gone. The crest and
    the nationality flag now stack vertically as `.pc-crest-flag` — crest on
    top, flag directly below, image only, no country-name text — pinned to
    the card's left edge so they line up flush with the stat rows underneath
    (both now sit inside the same narrowed `.pc-card` column). The photo and
    Team/Player name block are unaffected and stay centered.

    Sixth iteration: the crest and the nationality flag split apart again.
    `.pc-top-row` replaces `.pc-crest-flag` as a full-width flex row — crest
    on the left (still flush with `.pc-stats`'s left edge below it) and
    `.pc-nationality` (flag image + country name, the name text is back)
    pushed to the opposite right edge of the card. Photo/name block and the
    stats column are otherwise unchanged.

    Kept as a pure function separate from `render_player_card`, per this
    module's convention (`metric_matrix_dataframe`, `metric_radar_chart`),
    so the markup is checkable without a running Streamlit session.
    """
    name = html_escape(player.name)
    team_name = html_escape(player.team.name)

    crest_url = html_escape(team_logo_url(player.team.fotmob_id))
    crest_html = (
        f'<img class="pc-crest" src="{crest_url}" alt="" loading="lazy" '
        "onerror=\"this.onerror=null;this.classList.add('pc-crest--hidden');\" />"
    )

    flag_url = nationality_flag_url(player.nationality)
    flag_html = (
        (
            f'<img class="pc-flag" src="{html_escape(flag_url)}" alt="" loading="lazy" '
            "onerror=\"this.onerror=null;this.classList.add('pc-flag--hidden');\" />"
        )
        if flag_url
        else ""
    )
    country_name = nationality_label(player.nationality)
    country_name_html = (
        f'<span class="pc-nationality-name">{html_escape(country_name)}</span>' if country_name else ""
    )
    nationality_html = (
        f'<div class="pc-nationality">{flag_html}{country_name_html}</div>'
        if flag_html or country_name_html
        else ""
    )

    if player.photo_url:
        avatar_html = f'<img class="pc-avatar" src="{html_escape(player.photo_url)}" alt="" />'
    else:
        avatar_html = f'<div class="pc-avatar-placeholder">{_PLACEHOLDER_AVATAR_SVG}</div>'

    stats = (
        ("Idade", bio_field(player.age)),
        ("Posição", position_codes(player) or "-"),
        ("Pé preferido", bio_field(preferred_foot_label(player.preferred_foot))),
        ("Minutos Jogados", minutes_played_display(player)),
    )
    stats_html = "".join(
        f'<div class="pc-stat-row">'
        f'<span class="pc-stat-label">{html_escape(label)}:</span>'
        f'<span class="pc-stat-value">{html_escape(str(value))}</span></div>'
        for label, value in stats
    )

    return (
        '<div class="pc-card">'
        f'<div class="pc-top-row">{crest_html}{nationality_html}</div>'
        f"{avatar_html}"
        f'<div class="pc-team-name">{team_name}</div>'
        f'<div class="pc-name">{name}</div>'
        f'<div class="pc-stats">{stats_html}</div>'
        "</div>"
    )


def render_player_card(player: Player) -> None:
    """Player identity card. See `player_card_html` for the layout
    rationale — this function just wraps that markup in the app's standard
    bordered container and injects `PLAYER_CARD_CSS`."""
    with st.container(border=True):
        st.markdown(PLAYER_CARD_CSS + player_card_html(player), unsafe_allow_html=True)


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

    # [1, 4] (seventh iteration, down from [1, 3]): the card's own content is
    # capped at 200px (`.pc-card`'s `max-width`), so a wider card_col just
    # left it floating in extra whitespace on both sides — narrowing the
    # column itself closes most of that gap. Metrics/matrix content gets the
    # freed-up width instead. See the seventh-iteration comment above
    # `PLAYER_CARD_CSS` for what this does and doesn't fix.
    card_col, metrics_col = st.columns([1, 4])
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

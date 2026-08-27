"""Player Workspace page: browse/filter Players, inspect a single Player's
profile and Insights, and run a Scout Comparison — with PDF export for both.

Relocated from the dashboard's former single-page `app.py` as part of
introducing multipage navigation; no functional changes.

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the environment (see
.env.example). Works with whatever Statistic categories have been ingested
so far, since Team and Position(s) are current-state attributes.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st
from plotly.graph_objects import Figure

from football_analytics.analysis.metrics import (
    Insight,
    MetricKind,
    MetricSpec,
    apply_minutes_floor,
    compute_metric,
    filter_by_position_group,
    generate_insights,
    position_group,
    scout_comparison,
)
from football_analytics.dashboard.data import get_players
from football_analytics.domain.models import Player
from football_analytics.reports.player_report import build_player_report_pdf
from football_analytics.reports.scout_comparison_report import (
    build_scout_comparison_report_pdf,
)

METRIC_KIND_BY_LABEL: dict[str, MetricKind] = {
    "Raw": "raw",
    "Per-90": "per_90",
    "Percentile": "percentile",
}

LEADERBOARD_SIZE = 20

# Palette from the project's dataviz skill (references/palette.md), validated
# for colorblind-safety and light/dark contrast — see comments below for why
# each slot is used where it is.
SEQUENTIAL_BLUE = "#2a78d6"  # categorical slot 1 / default sequential hue
STATUS_GOOD = "#0ca30c"  # fixed status color, mode-invariant
STATUS_CRITICAL = "#d03b3b"  # fixed status color, mode-invariant
MUTED_INK = "#898781"  # axis/label role, mode-invariant
GRIDLINE_COLOR = "rgba(137, 135, 129, 0.35)"  # muted ink, hairline opacity


def to_dataframe(players: list[Player]) -> pd.DataFrame:
    df = pd.DataFrame(
        [
            {
                "Name": p.name,
                "Team": p.team.name,
                "Positions": ", ".join(pos.code for pos in p.positions),
            }
            for p in players
        ]
    )
    return df.sort_values("Name", ignore_index=True)


def _format_metric_value(value: float, kind: MetricKind) -> str:
    """Human-friendly label for a Metric value: whole numbers stay whole,
    Percentiles never show decimals, everything else gets 2 decimals."""
    if kind == "percentile" or float(value).is_integer():
        return f"{value:.0f}"
    return f"{value:.2f}"


def _bar_chart_height(n_rows: int) -> int:
    """Enough height for `n_rows` horizontal bars to stay <=24px thick with
    breathing room, without the chart card growing unbounded."""
    return max(220, min(40 * n_rows + 80, 900))


def metric_label_options(players: list[Player]) -> dict[str, str]:
    """Map each available Statistic's label to its key, first label wins."""
    options: dict[str, str] = {}
    for p in players:
        for s in p.statistics:
            options.setdefault(s.label, s.key)
    return options


def leaderboard_dataframe(
    reference_players: list[Player], view_players: list[Player], spec: MetricSpec
) -> pd.DataFrame:
    rows = []
    for p in view_players:
        value = compute_metric(reference_players, p, spec)
        if value is not None:
            rows.append(
                {
                    "Name": p.name,
                    "Team": p.team.name,
                    "Player": f"{p.name} · {p.team.name}",
                    spec.label: value,
                }
            )
    df = pd.DataFrame(rows).sort_values(spec.label, ascending=False).head(LEADERBOARD_SIZE)
    return df


def leaderboard_chart(df: pd.DataFrame, spec: MetricSpec, metric_kind: MetricKind) -> Figure:
    """Top-N horizontal bar chart for one Metric.

    Deliberately a single sequential hue rather than `color="Team"`: with the
    default (unfiltered) view, a Top 20 leaderboard routinely spans well over
    the palette's 8-color categorical ceiling (~20 Premier League teams), so
    coloring by Team would mean cycling generated hues — the dataviz skill's
    #1 flagged anti-pattern, and no longer colorblind-safe. The ranking is a
    magnitude comparison (the chart's actual job), so Team identity is
    preserved as a direct label on the y-axis and in the hover instead of
    burning the color channel on an unsafe encoding.
    """
    value_col = spec.label
    text = [_format_metric_value(v, metric_kind) for v in df[value_col]]
    fig = px.bar(
        df,
        x=value_col,
        y="Player",
        orientation="h",
        color_discrete_sequence=[SEQUENTIAL_BLUE],
        text=text,
    )
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        marker_line_width=0,
        hovertemplate=f"%{{y}}<br>{value_col}: %{{text}}<extra></extra>",
    )
    fig.update_layout(
        yaxis={"categoryorder": "total ascending", "title": None},
        xaxis={"gridcolor": GRIDLINE_COLOR, "title": value_col},
        bargap=0.35,
        height=_bar_chart_height(len(df)),
        margin={"l": 10, "r": 60, "t": 10, "b": 10},
    )
    if metric_kind == "percentile":
        fig.update_xaxes(range=[0, 100])
    return fig


def scout_comparison_dataframe(
    results: list[tuple[Player, float]],
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Name": p.name,
                "Team": p.team.name,
                "Positions": ", ".join(pos.code for pos in p.positions),
                "Distance": distance,
            }
            for p, distance in results
        ]
    )


def scout_comparison_chart(df: pd.DataFrame) -> Figure:
    """Horizontal bar of Distance-to-reference for the ranked candidates.

    Same sequential blue and "value at the tip" treatment as the Metric
    leaderboards, for a consistent visual system. Distance is lower-is-better
    (closer match), the opposite of every other ranked chart in this app, so
    this is the one place that orders bars with "total descending" — that is
    what puts the best match at the top here, matching every other
    leaderboard's "best result on top" convention rather than breaking it.
    """
    chart_df = df.assign(Player=df["Name"] + " · " + df["Team"])
    text = [f"{v:.2f}" for v in chart_df["Distance"]]
    fig = px.bar(
        chart_df,
        x="Distance",
        y="Player",
        orientation="h",
        color_discrete_sequence=[SEQUENTIAL_BLUE],
        text=text,
    )
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        marker_line_width=0,
        hovertemplate="%{y}<br>Distance: %{text}<extra></extra>",
    )
    fig.update_layout(
        yaxis={"categoryorder": "total descending", "title": None},
        xaxis={"gridcolor": GRIDLINE_COLOR, "title": "Distance (lower = more similar)"},
        bargap=0.35,
        height=_bar_chart_height(len(chart_df)),
        margin={"l": 10, "r": 60, "t": 10, "b": 10},
    )
    return fig


def render_insight(insight: Insight) -> None:
    icon = "🔼" if insight.kind == "strength" else "🔽"
    st.write(f"{icon} **{insight.label}** — {insight.percentile:.0f}th percentile")


def insights_chart(insights: list[Insight]) -> Figure:
    df = pd.DataFrame(
        [
            {"Statistic": i.label, "Percentile": i.percentile, "Kind": i.kind.capitalize()}
            for i in insights
        ]
    )
    text = [f"{v:.0f}" for v in df["Percentile"]]
    fig = px.bar(
        df,
        x="Percentile",
        y="Statistic",
        orientation="h",
        color="Kind",
        # Strength/Weakness is a good/bad status, not a generic identity —
        # use the dataviz skill's fixed, mode-invariant status colors rather
        # than the old unvalidated green/red.
        color_discrete_map={"Strength": STATUS_GOOD, "Weakness": STATUS_CRITICAL},
        range_x=[0, 100],
        text=text,
    )
    fig.update_traces(textposition="outside", cliponaxis=False, marker_line_width=0)
    # 50th percentile is the neutral reference every bar is measured against —
    # a dashed threshold line earns its place here (unlike a plain gridline).
    fig.add_vline(
        x=50,
        line_width=1,
        line_dash="dash",
        line_color=MUTED_INK,
        annotation_text="Median",
        annotation_position="top",
        annotation_font_color=MUTED_INK,
    )
    fig.update_layout(
        yaxis={"categoryorder": "total ascending", "title": None},
        xaxis={"gridcolor": GRIDLINE_COLOR, "title": "Percentile"},
        bargap=0.35,
        height=_bar_chart_height(len(df)),
        legend_title_text="",
        margin={"l": 10, "r": 60, "t": 30, "b": 10},
    )
    return fig


def main() -> None:
    st.title("Premier League 2025/26 — Players")

    players = get_players()
    if not players:
        st.warning("No players found. Has the ingestion pipeline been run yet?")
        return

    team_names = sorted({p.team.name for p in players})
    position_codes = sorted({pos.code for p in players for pos in p.positions})
    position_groups = sorted({g for p in players if (g := position_group(p)) is not None})
    label_options = metric_label_options(players)

    with st.sidebar:
        st.header("Filters")
        selected_teams = st.multiselect("Team", team_names)
        selected_positions = st.multiselect("Position", position_codes)
        selected_group = st.selectbox("Position Group", ["All", *position_groups])
        minutes_floor = st.number_input("Minutes Floor", min_value=0, value=0, step=90)

        st.header("Metrics")
        metric_kind_label = st.radio("Metric type", list(METRIC_KIND_BY_LABEL), horizontal=True)
        selected_metric_labels = st.multiselect("Metrics", sorted(label_options))

    reference_players = players if selected_group == "All" else filter_by_position_group(
        players, selected_group
    )

    view_players = players
    if selected_teams:
        view_players = [p for p in view_players if p.team.name in selected_teams]
    if selected_positions:
        view_players = [
            p for p in view_players if any(pos.code in selected_positions for pos in p.positions)
        ]
    if selected_group != "All":
        view_players = filter_by_position_group(view_players, selected_group)
    view_players = apply_minutes_floor(view_players, minutes_floor)

    st.caption(f"{len(view_players)} of {len(players)} players")
    st.dataframe(to_dataframe(view_players), width="stretch", hide_index=True)

    metric_kind = METRIC_KIND_BY_LABEL[metric_kind_label]
    specs = [
        MetricSpec(key=label_options[label], label=label, kind=metric_kind)
        for label in selected_metric_labels
    ]

    for spec in specs:
        df = leaderboard_dataframe(reference_players, view_players, spec)
        st.subheader(f"{spec.label} ({metric_kind_label})")
        if df.empty:
            st.info("No players have this Metric under the current filters.")
            continue
        leader = df.iloc[0]
        leader_value = _format_metric_value(leader[spec.label], metric_kind)
        st.caption(f"Leads: **{leader['Name']}** ({leader['Team']}) — {leader_value}")
        fig = leaderboard_chart(df, spec, metric_kind)
        st.plotly_chart(fig, width="stretch")

    st.header("Player Profile")
    player_labels = {f"{p.name} ({p.team.name})": p for p in sorted(players, key=lambda p: p.name)}
    reference_label = st.selectbox("Player", list(player_labels))
    reference = player_labels[reference_label]

    group = position_group(reference)
    st.subheader(f"{reference.name} — {reference.team.name}")
    st.caption(", ".join(pos.code for pos in reference.positions) or "No Position data")

    insight_population = players if group is None else filter_by_position_group(players, group)
    insights = generate_insights(insight_population, reference)
    chart_png = None
    if not insights:
        st.info("No notable Insights for this Player yet.")
    else:
        for insight in insights:
            render_insight(insight)
        fig = insights_chart(insights)
        st.plotly_chart(fig, width="stretch")
        chart_png = fig.to_image(format="png")

    pdf_bytes = build_player_report_pdf(reference, insights, chart_png)
    st.download_button(
        "Download Player Report (PDF)",
        data=pdf_bytes,
        file_name=f"{reference.name.replace(' ', '_')}_report.pdf",
        mime="application/pdf",
    )

    st.header("Scout Comparison")
    restrict_group = st.checkbox("Restrict to reference Player's Position Group", value=True)

    if not specs:
        st.info("Select at least one Metric above to run a Scout Comparison.")
    else:
        candidates = apply_minutes_floor(players, minutes_floor)
        if not any(p.fotmob_id == reference.fotmob_id for p in candidates):
            candidates = [reference, *candidates]

        results = scout_comparison(
            candidates, reference, specs, restrict_to_position_group=restrict_group
        )
        if not results:
            st.info("No comparable Players found under the current filters.")
        else:
            top_results = results[:LEADERBOARD_SIZE]
            comparison_df = scout_comparison_dataframe(top_results)
            closest = comparison_df.iloc[0]
            st.caption(
                f"Closest match: **{closest['Name']}** ({closest['Team']}) — "
                f"distance {closest['Distance']:.2f} across {len(specs)} "
                f"metric{'s' if len(specs) != 1 else ''}"
            )
            st.plotly_chart(scout_comparison_chart(comparison_df), width="stretch")
            st.dataframe(
                comparison_df,
                width="stretch",
                hide_index=True,
            )
            scout_pdf_bytes = build_scout_comparison_report_pdf(
                reference, top_results, specs, candidates
            )
            st.download_button(
                "Download Scout Comparison Report (PDF)",
                data=scout_pdf_bytes,
                file_name=f"{reference.name.replace(' ', '_')}_scout_comparison.pdf",
                mime="application/pdf",
            )


main()

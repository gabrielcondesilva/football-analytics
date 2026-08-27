"""Dashboard shell: browse and filter Premier League 2025/26 Players.

Usage: `uv run streamlit run src/football_analytics/dashboard/app.py`

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the environment (see
.env.example). Works with whatever Statistic categories have been ingested
so far, since Team and Position(s) are current-state attributes.
"""

from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

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
from football_analytics.domain.models import Player
from football_analytics.persistence.player_queries import list_players

METRIC_KIND_BY_LABEL: dict[str, MetricKind] = {
    "Raw": "raw",
    "Per-90": "per_90",
    "Percentile": "percentile",
}

LEADERBOARD_SIZE = 20


@st.cache_resource
def get_client() -> Client:
    load_dotenv()
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])


@st.cache_data(ttl=300)
def get_players() -> list[Player]:
    return list_players(get_client())


def to_dataframe(players: list[Player]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Name": p.name,
                "Team": p.team.name,
                "Positions": ", ".join(pos.code for pos in p.positions),
            }
            for p in players
        ]
    )


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
            rows.append({"Name": p.name, "Team": p.team.name, spec.label: value})
    df = pd.DataFrame(rows).sort_values(spec.label, ascending=False).head(LEADERBOARD_SIZE)
    return df


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


def render_insight(insight: Insight) -> None:
    icon = "🔼" if insight.kind == "strength" else "🔽"
    st.write(f"{icon} **{insight.label}** — {insight.percentile:.0f}th percentile")


def main() -> None:
    st.set_page_config(page_title="Player Analytics", layout="wide")
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
        fig = px.bar(df, x=spec.label, y="Name", orientation="h", color="Team")
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
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
    if not insights:
        st.info("No notable Insights for this Player yet.")
    else:
        for insight in insights:
            render_insight(insight)

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
            st.dataframe(
                scout_comparison_dataframe(results[:LEADERBOARD_SIZE]),
                width="stretch",
                hide_index=True,
            )


main()

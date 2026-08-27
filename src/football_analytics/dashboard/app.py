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
    MetricKind,
    MetricSpec,
    apply_minutes_floor,
    compute_metric,
    filter_by_position_group,
    position_group,
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
    for metric_label in selected_metric_labels:
        spec = MetricSpec(key=label_options[metric_label], label=metric_label, kind=metric_kind)
        df = leaderboard_dataframe(reference_players, view_players, spec)
        st.subheader(f"{metric_label} ({metric_kind_label})")
        if df.empty:
            st.info("No players have this Metric under the current filters.")
            continue
        fig = px.bar(df, x=metric_label, y="Name", orientation="h", color="Team")
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, width="stretch")


main()

"""Dashboard shell: browse and filter Premier League 2025/26 Players.

Usage: `uv run streamlit run src/football_analytics/dashboard/app.py`

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the environment (see
.env.example). Works with whatever Statistic categories have been ingested
so far, since Team and Position(s) are current-state attributes.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

from football_analytics.domain.models import Player
from football_analytics.persistence.player_queries import list_players


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


def main() -> None:
    st.set_page_config(page_title="Player Analytics", layout="wide")
    st.title("Premier League 2025/26 — Players")

    players = get_players()
    if not players:
        st.warning("No players found. Has the ingestion pipeline been run yet?")
        return

    team_names = sorted({p.team.name for p in players})
    position_codes = sorted({pos.code for p in players for pos in p.positions})

    with st.sidebar:
        st.header("Filters")
        selected_teams = st.multiselect("Team", team_names)
        selected_positions = st.multiselect("Position", position_codes)

    filtered = players
    if selected_teams:
        filtered = [p for p in filtered if p.team.name in selected_teams]
    if selected_positions:
        filtered = [
            p for p in filtered if any(pos.code in selected_positions for pos in p.positions)
        ]

    st.caption(f"{len(filtered)} of {len(players)} players")
    st.dataframe(to_dataframe(filtered), width="stretch", hide_index=True)


main()

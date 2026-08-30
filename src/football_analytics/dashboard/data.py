"""Shared data access for every dashboard page: a single cached Supabase
client and Player list, so Overview and the Player Workspace page read the
same data without each re-querying Supabase independently.
"""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

from football_analytics.domain.models import Player
from football_analytics.persistence.player_queries import (
    get_touch_map_coordinates,
    list_players,
)


@st.cache_resource
def get_client() -> Client:
    load_dotenv()
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])


@st.cache_data(ttl=300)
def get_players() -> list[Player]:
    return list_players(get_client())


@st.cache_data(ttl=300)
def get_touch_map(fotmob_id: int) -> list[tuple[float, float]]:
    """Raw touch coordinates for one Player — see `get_touch_map_coordinates`.
    Cached (and fetched) independently of `get_players()`, one Player at a
    time, since only the Análise de Jogadores page ever needs this."""
    return get_touch_map_coordinates(get_client(), fotmob_id)

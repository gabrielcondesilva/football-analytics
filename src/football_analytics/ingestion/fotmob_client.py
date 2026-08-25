"""Thin HTTP client for FotMob's unofficial data API.

No test coverage here by design (see the spec's Testing Decisions): this is
the I/O layer, kept thin enough that Seam A (normalize.py) carries the real
logic and is what gets tested.
"""

from __future__ import annotations

import time

import requests

_BASE_URL = "https://www.fotmob.com/api/data"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


class FotMobClient:
    def __init__(self, request_delay_seconds: float = 1.0) -> None:
        self._session = requests.Session()
        self._session.headers["User-Agent"] = _USER_AGENT
        self._request_delay_seconds = request_delay_seconds

    def _get(self, path: str, **params: str | int) -> dict:
        response = self._session.get(f"{_BASE_URL}/{path}", params=params)
        response.raise_for_status()
        time.sleep(self._request_delay_seconds)
        return response.json()

    def get_league_table(self, league_id: int, season: str) -> dict:
        return self._get("leagues", id=league_id, season=season, tab="table")

    def get_team(self, team_id: int, season: str) -> dict:
        return self._get("teams", id=team_id, season=season)

    def get_player_data(self, player_id: int) -> dict:
        return self._get("playerData", id=player_id)

    def get_player_stats(self, player_id: int, entry_id: str) -> dict:
        return self._get("playerStats", playerId=player_id, seasonId=entry_id)

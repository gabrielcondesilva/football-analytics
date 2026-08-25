"""Writes normalized domain records to Supabase, one call at a time so a
Snapshot's rows land incrementally instead of only at the very end of a run.

No test coverage here by design (see the spec's Testing Decisions): this is
the persistence I/O layer, kept as a thin translation from domain records to
upserts against the schema in schema.sql.
"""

from __future__ import annotations

from datetime import datetime
from typing import cast

from supabase import Client

from football_analytics.domain.models import Player, Team


class SupabaseRepo:
    def __init__(self, client: Client) -> None:
        self._client = client

    def get_or_create_league(self, fotmob_id: int, name: str) -> int:
        return self._upsert_and_get_id("leagues", {"fotmob_id": fotmob_id, "name": name}, "fotmob_id")

    def get_or_create_season(self, league_id: int, name: str) -> int:
        return self._upsert_and_get_id(
            "seasons", {"league_id": league_id, "name": name}, "league_id,name"
        )

    def create_snapshot(self, season_id: int, scraped_at: datetime) -> int:
        return self._upsert_and_get_id(
            "snapshots",
            {"season_id": season_id, "scraped_at": scraped_at.isoformat()},
            "season_id,scraped_at",
        )

    def save_team(self, team: Team) -> int:
        return self._upsert_and_get_id(
            "teams", {"fotmob_id": team.fotmob_id, "name": team.name}, "fotmob_id"
        )

    def save_player(self, snapshot_id: int, team_id: int, player: Player) -> int:
        player_id = self._upsert_and_get_id(
            "players",
            {"fotmob_id": player.fotmob_id, "name": player.name, "team_id": team_id},
            "fotmob_id",
        )

        self._client.table("player_positions").delete().eq("player_id", player_id).execute()
        if player.positions:
            self._client.table("player_positions").insert(
                [
                    {"player_id": player_id, "code": p.code, "position_group": p.group}
                    for p in player.positions
                ]
            ).execute()

        if player.statistics:
            self._client.table("statistics").upsert(
                [
                    {
                        "snapshot_id": snapshot_id,
                        "player_id": player_id,
                        "key": s.key,
                        "label": s.label,
                        "value": s.value,
                    }
                    for s in player.statistics
                ],
                on_conflict="snapshot_id,player_id,key",
            ).execute()

        return player_id

    def _upsert_and_get_id(self, table: str, row: dict, on_conflict: str) -> int:
        result = self._client.table(table).upsert(row, on_conflict=on_conflict).execute()
        first_row = cast(dict, result.data[0])
        return int(first_row["id"])

"""Writes normalized domain records to Supabase, one call at a time so a
Snapshot's rows land incrementally instead of only at the very end of a run.

No test coverage here by design (see the spec's Testing Decisions): this is
the persistence I/O layer, kept as a thin translation from domain records to
upserts against the schema in schema.sql.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from supabase import Client

from football_analytics.domain.models import Player, Team


class SupabaseRepo:
    def __init__(self, client: Client) -> None:
        self._client = client

    def get_or_create_league(self, fotmob_id: int, name: str) -> int:
        return self._upsert_and_get_id("leagues", {"fotmob_id": fotmob_id, "name": name}, "fotmob_id")

    def list_leagues(self) -> list[tuple[int, int, str]]:
        """Every League currently tracked, as `(id, fotmob_id, name)` triples
        — used by the ingestion orchestrator to know which Leagues are safe
        fallback targets for a Player's cross-League Statistics (ADR-0004,
        `find_known_league_entry`)."""
        result = self._client.table("leagues").select("id, fotmob_id, name").execute()
        return [
            (int(row["id"]), int(row["fotmob_id"]), row["name"]) for row in cast(list[dict], result.data)
        ]

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

    def get_or_create_latest_snapshot(self, season_id: int) -> int:
        """The most recent existing Snapshot for `season_id`, or a new one if
        none exists yet — for attaching a Player's cross-League fallback
        Statistics (ADR-0004) to the League/Season they actually came from,
        without creating a redundant one-off Snapshot just for one Player.
        The League actively being ingested this run always gets its own
        fresh Snapshot via `create_snapshot` instead, never this method."""
        result = (
            self._client.table("snapshots")
            .select("id")
            .eq("season_id", season_id)
            .order("scraped_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return int(cast(dict, result.data[0])["id"])
        return self.create_snapshot(season_id, datetime.now(UTC))

    def save_team(self, team: Team, league_id: int) -> int:
        """`league_id` is the Team's current League (ADR-0004) — always the
        League being ingested right now, never derived from a Player's
        Statistics. Overwritten on every ingestion run, same as `name`."""
        return self._upsert_and_get_id(
            "teams",
            {"fotmob_id": team.fotmob_id, "name": team.name, "league_id": league_id},
            "fotmob_id",
        )

    def save_player(self, snapshot_id: int, team_id: int, player: Player) -> int:
        player_id = self._upsert_and_get_id(
            "players",
            {
                "fotmob_id": player.fotmob_id,
                "name": player.name,
                "team_id": team_id,
                "age": player.age,
                "nationality": player.nationality,
                "preferred_foot": player.preferred_foot,
                "photo_url": player.photo_url,
            },
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
                        "format": s.format,
                    }
                    for s in player.statistics
                ],
                on_conflict="snapshot_id,player_id,key",
            ).execute()

        return player_id

    def save_touch_map(self, player_id: int, coordinates: list[tuple[float, float]]) -> None:
        """Replace the Player's Mapa de Toques in full — current-state,
        never accumulated per Snapshot like `statistics` (ADR-0005). An
        empty `coordinates` deletes any previously stored row instead of
        leaving it stale (e.g. this run's entry has Statistics but no
        `heatmap`, or no entry at all) — same delete-then-insert handling
        `save_player` above already uses for `player_positions`, and the
        same "no data" convention as a Player with no Statistics."""
        if not coordinates:
            self._client.table("player_touch_maps").delete().eq("player_id", player_id).execute()
            return
        self._client.table("player_touch_maps").upsert(
            {
                "player_id": player_id,
                "coordinates": [{"x": x, "y": y} for x, y in coordinates],
            },
            on_conflict="player_id",
        ).execute()

    def _upsert_and_get_id(self, table: str, row: dict, on_conflict: str) -> int:
        result = self._client.table(table).upsert(row, on_conflict=on_conflict).execute()
        first_row = cast(dict, result.data[0])
        return int(first_row["id"])

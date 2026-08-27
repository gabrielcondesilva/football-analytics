"""Read-side Supabase queries for the dashboard.

No test coverage here by design (see the spec's Testing Decisions): this is
the persistence I/O layer, kept as a thin translation from Supabase rows to
domain records.
"""

from __future__ import annotations

from typing import cast

from supabase import Client

from football_analytics.domain.models import Player, Position, Team


def list_players(client: Client) -> list[Player]:
    """Every Player currently in the database, with their Team and Position(s).

    Team and Position(s) are current-state attributes (not Snapshot-scoped),
    so this works regardless of which Statistic categories, if any, have
    been ingested for a given Player.
    """
    result = (
        client.table("players")
        .select("id, fotmob_id, name, teams(fotmob_id, name), player_positions(code, position_group)")
        .execute()
    )

    players = []
    for row in cast(list[dict], result.data):
        team_row = cast(dict, row["teams"])
        team = Team(fotmob_id=team_row["fotmob_id"], name=team_row["name"])
        positions = tuple(
            Position(code=p["code"], group=p["position_group"]) for p in row["player_positions"]
        )
        players.append(
            Player(
                fotmob_id=row["fotmob_id"],
                name=row["name"],
                team=team,
                positions=positions,
                statistics=(),
            )
        )
    return players

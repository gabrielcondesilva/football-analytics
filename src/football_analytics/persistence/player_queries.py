"""Read-side Supabase queries for the dashboard.

No test coverage here by design (see the spec's Testing Decisions): this is
the persistence I/O layer, kept as a thin translation from Supabase rows to
domain records.
"""

from __future__ import annotations

from typing import cast

from supabase import Client

from football_analytics.domain.models import Player, Position, Statistic, Team


def get_latest_snapshot(client: Client) -> tuple[int, str | None] | None:
    """The id and League name (via Season -> League) of the most recent
    Snapshot, or None if no Snapshot exists yet. A single query rather than
    one for the id and a second for the League, since both live on the same
    `snapshots` row.
    """
    result = (
        client.table("snapshots")
        .select("id, seasons(leagues(name))")
        .order("scraped_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict], result.data)
    if not rows:
        return None
    row = rows[0]
    season = cast(dict | None, row["seasons"])
    league = cast(dict | None, season["leagues"]) if season is not None else None
    return int(row["id"]), (league["name"] if league is not None else None)


def list_players(client: Client) -> list[Player]:
    """Every Player currently in the database, with their Team, Position(s),
    Statistics, and League (all from the latest Snapshot; empty/None if no
    Snapshot exists yet).

    Team and Position(s) are current-state attributes (not Snapshot-scoped),
    so this works regardless of which Statistic categories, if any, have
    been ingested for a given Player.
    """
    latest = get_latest_snapshot(client)
    snapshot_id, league_name = latest if latest is not None else (None, None)

    query = client.table("players").select(
        "id, fotmob_id, name, teams(fotmob_id, name), "
        "player_positions(code, position_group), statistics(key, label, value, format)"
    )
    if snapshot_id is not None:
        query = query.eq("statistics.snapshot_id", snapshot_id)
    result = query.execute()

    players = []
    for row in cast(list[dict], result.data):
        team_row = cast(dict, row["teams"])
        team = Team(fotmob_id=team_row["fotmob_id"], name=team_row["name"])
        positions = tuple(
            Position(code=p["code"], group=p["position_group"]) for p in row["player_positions"]
        )
        statistics = tuple(
            Statistic(key=s["key"], label=s["label"], value=s["value"], format=s["format"])
            for s in row["statistics"]
        )
        players.append(
            Player(
                fotmob_id=row["fotmob_id"],
                name=row["name"],
                team=team,
                positions=positions,
                statistics=statistics,
                league=league_name,
            )
        )
    return players

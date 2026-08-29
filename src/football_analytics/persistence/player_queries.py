"""Read-side Supabase queries for the dashboard.

No test coverage here by design (see the spec's Testing Decisions): this is
the persistence I/O layer, kept as a thin translation from Supabase rows to
domain records.
"""

from __future__ import annotations

from typing import cast

from supabase import Client

from football_analytics.domain.models import Player, Position, Statistic, Team


def get_latest_snapshots(client: Client) -> dict[int, str | None]:
    """The id and League name (via Season -> League) of the most recent
    Snapshot *per League*, not a single global latest: each League is
    ingested independently (and may be re-ingested at different times), so
    "latest" must be scoped per League or a newly-ingested League's Snapshot
    would shadow every other League's Players entirely.

    Returns `{snapshot_id: league_name}`. Empty if no Snapshot exists yet.
    """
    result = (
        client.table("snapshots")
        .select("id, scraped_at, seasons(leagues(name))")
        .order("scraped_at", desc=True)
        .execute()
    )
    rows = cast(list[dict], result.data)

    latest_snapshot_id_by_league: dict[str | None, int] = {}
    for row in rows:
        season = cast(dict | None, row["seasons"])
        league = cast(dict | None, season["leagues"]) if season is not None else None
        league_name = league["name"] if league is not None else None
        # Rows are ordered by scraped_at desc, so the first one seen for a
        # given League is that League's latest Snapshot.
        latest_snapshot_id_by_league.setdefault(league_name, int(row["id"]))

    return {snapshot_id: league_name for league_name, snapshot_id in latest_snapshot_id_by_league.items()}


def list_players(client: Client) -> list[Player]:
    """Every Player currently in the database, with their Team, Position(s),
    Statistics, and League (from that Player's own League's latest Snapshot;
    empty/None if no Snapshot exists yet for their League).

    Team and Position(s) are current-state attributes (not Snapshot-scoped),
    so this works regardless of which Statistic categories, if any, have
    been ingested for a given Player.
    """
    league_by_snapshot_id = get_latest_snapshots(client)

    query = client.table("players").select(
        "id, fotmob_id, name, age, nationality, preferred_foot, photo_url, teams(fotmob_id, name), "
        "player_positions(code, position_group), statistics(key, label, value, format, snapshot_id)"
    )
    if league_by_snapshot_id:
        query = query.in_("statistics.snapshot_id", list(league_by_snapshot_id))
    result = query.execute()

    players = []
    for row in cast(list[dict], result.data):
        team_row = cast(dict, row["teams"])
        team = Team(fotmob_id=team_row["fotmob_id"], name=team_row["name"])
        positions = tuple(
            Position(code=p["code"], group=p["position_group"]) for p in row["player_positions"]
        )
        raw_statistics = cast(list[dict], row["statistics"])
        statistics = tuple(
            Statistic(key=s["key"], label=s["label"], value=s["value"], format=s["format"])
            for s in raw_statistics
        )
        # A Player's Statistics all share one Snapshot (they were all
        # ingested together), so any row's snapshot_id identifies their
        # League.
        league_name = (
            league_by_snapshot_id.get(raw_statistics[0]["snapshot_id"]) if raw_statistics else None
        )
        players.append(
            Player(
                fotmob_id=row["fotmob_id"],
                name=row["name"],
                team=team,
                positions=positions,
                statistics=statistics,
                league=league_name,
                age=row.get("age"),
                nationality=row.get("nationality"),
                preferred_foot=row.get("preferred_foot"),
                photo_url=row.get("photo_url"),
            )
        )
    return players

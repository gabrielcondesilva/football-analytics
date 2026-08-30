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


_PLAYERS_SELECT = (
    "id, fotmob_id, name, age, nationality, preferred_foot, photo_url, "
    "teams(fotmob_id, name, leagues(name)), "
    "player_positions(code, position_group), statistics(key, label, value, format, snapshot_id)"
)
_PAGE_SIZE = 1000


def _fetch_all_player_rows(client: Client, league_by_snapshot_id: dict[int, str | None]) -> list[dict]:
    """Every row of the `players` query, paginated past PostgREST's default
    1000-row response cap via `.range()`. A single un-paginated `.execute()`
    silently truncated the League with the highest `players.id`s once the
    database passed 1000 total Players across every League combined (hit
    live once Ligue 1 was ingested on top of Premier League + La Liga) —
    `.order("id")` keeps page boundaries stable across the repeated queries
    this loop issues."""
    rows: list[dict] = []
    start = 0
    while True:
        query = client.table("players").select(_PLAYERS_SELECT).order("id")
        if league_by_snapshot_id:
            query = query.in_("statistics.snapshot_id", list(league_by_snapshot_id))
        page = cast(list[dict], query.range(start, start + _PAGE_SIZE - 1).execute().data)
        rows.extend(page)
        if len(page) < _PAGE_SIZE:
            return rows
        start += _PAGE_SIZE


def get_touch_map_coordinates(client: Client, fotmob_id: int) -> list[tuple[float, float]]:
    """Raw touch coordinates (Mapa de Toques, CONTEXT.md) for a single
    Player, keyed by their `fotmob_id` — independent of `list_players()`,
    fetched only for the one Player the Análise de Jogadores page has
    selected at a time. Deliberately not part of the shared, cached Player
    list every dashboard page reads: `player_touch_maps` holds a much
    bigger blob per Player than anything else on `Player`, and only this
    one page ever needs it (ADR-0005).

    Empty list if the Player has no Mapa de Toques yet — not backfilled, or
    no Statistics for it to be sourced from (same "no data" convention as
    an absent Statistic) — or if no Player with this `fotmob_id` exists at
    all.
    """
    result = (
        client.table("players")
        .select("player_touch_maps(coordinates)")
        .eq("fotmob_id", fotmob_id)
        .execute()
    )
    rows = cast(list[dict], result.data)
    if not rows:
        return []
    touch_map = cast(dict | None, rows[0]["player_touch_maps"])
    if touch_map is None:
        return []
    coordinates = cast(list[dict], touch_map["coordinates"])
    return [(float(c["x"]), float(c["y"])) for c in coordinates]


def list_players(client: Client) -> list[Player]:
    """Every Player currently in the database, with their Team, Position(s),
    Statistics, current League, and Statistics League.

    `league` is the Player's own Team's current League (ADR-0004 — always
    their most recently ingested roster; None until the Team's League has
    been backfilled). `statistics_league` is the League whose Season
    actually produced the Statistics below (via their latest Snapshot;
    None if no Statistic exists yet) — these two can differ for a
    recently-transferred Player, whose shown Statistics still come from
    their previous League until they have some in the new one (see
    `find_known_league_entry`).

    Team and Position(s) are current-state attributes (not Snapshot-scoped),
    so this works regardless of which Statistic categories, if any, have
    been ingested for a given Player.
    """
    league_by_snapshot_id = get_latest_snapshots(client)

    players = []
    for row in _fetch_all_player_rows(client, league_by_snapshot_id):
        team_row = cast(dict, row["teams"])
        team = Team(fotmob_id=team_row["fotmob_id"], name=team_row["name"])
        team_league = cast(dict | None, team_row.get("leagues"))
        league_name = team_league["name"] if team_league is not None else None
        positions = tuple(
            Position(code=p["code"], group=p["position_group"]) for p in row["player_positions"]
        )
        raw_statistics = cast(list[dict], row["statistics"])
        statistics = tuple(
            Statistic(key=s["key"], label=s["label"], value=s["value"], format=s["format"])
            for s in raw_statistics
        )
        # A Player's Statistics all share one Snapshot (they were all
        # ingested together), so any row's snapshot_id identifies the
        # League that produced them.
        statistics_league_name = (
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
                statistics_league=statistics_league_name,
                age=row.get("age"),
                nationality=row.get("nationality"),
                preferred_foot=row.get("preferred_foot"),
                photo_url=row.get("photo_url"),
            )
        )
    return players

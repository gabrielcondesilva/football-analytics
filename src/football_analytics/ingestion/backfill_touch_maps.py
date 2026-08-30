"""One-off backfill: populate the Mapa de Toques for every Player already in
Supabase from before this feature existed, without re-running a full League
ingestion (see .scratch/player-touch-map/spec.md, ADR-0005).

Reuses exactly the League/Season that already backs each Player's current
Statistics and calls `find_entry_id` directly against that known
tournament/season, never re-running the cross-League fallback search from
scratch (ADR-0004's fallback already ran once, at ingestion time, to
produce the Statistics this script starts from).

A Player's `statistics` rows can span more than one Snapshot -- a League
re-ingested more than once never deletes the older run's rows, it only
stops being "latest" -- so which Snapshot backs a Player's *current*
Statistics has to be resolved the same way `player_queries.list_players`
does: via `get_latest_snapshots` (latest Snapshot id *per League*), then
restricting each Player's embedded `statistics` to just those ids before
picking one. Skipping that filter risks reading a stale League/Season from
a superseded Snapshot instead of the one the dashboard actually shows.

Usage: `uv run python -m football_analytics.ingestion.backfill_touch_maps`
A run covering every Player currently in the database takes a while (two
FotMob requests per Player with Statistics, at the client's default 1s
delay each) -- for a run too long to finish in one sitting, `--offset N
--limit N` processes only that slice of Players, ordered by id (the same
chunking convention `ingestion.run` uses for --team-offset/--team-limit).
Safe to re-run any chunk, or the whole thing, any number of times:
`SupabaseRepo.save_touch_map` always replaces a Player's row in full.

A Player with no Statistics at all is skipped (logged, not an error) --
there's no League/Season to source a Mapa de Toques from.

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the environment (see
.env.example).
"""

from __future__ import annotations

import argparse
import os
from typing import cast

from dotenv import load_dotenv
from supabase import Client, create_client

from football_analytics.ingestion.fotmob_client import FotMobClient
from football_analytics.ingestion.normalize import (
    find_entry_id,
    parse_touch_coordinates,
)
from football_analytics.persistence.player_queries import get_latest_snapshots
from football_analytics.persistence.supabase_repo import SupabaseRepo

_PLAYERS_SELECT = (
    "id, fotmob_id, name, statistics(snapshot_id, snapshots(seasons(name, leagues(fotmob_id))))"
)
_PAGE_SIZE = 1000


def _fetch_players(
    supabase: Client, latest_snapshot_ids: list[int], *, offset: int, limit: int | None
) -> list[dict]:
    """Every Player (or the requested `--offset`/`--limit` slice), each with
    at most one embedded `statistics` row -- enough to know which League/
    Season backs their current Statistics without pulling every one of
    their (often dozens of) Statistic rows over the wire for nothing.

    `latest_snapshot_ids` restricts the embedded `statistics` to rows from
    a League's current latest Snapshot (from `get_latest_snapshots`) before
    `.limit(1, foreign_table="statistics")` picks one -- without it, a
    Player whose `statistics` span more than one Snapshot (any re-ingested
    League) could just as easily get a superseded row back.

    Paginates past PostgREST's default 1000-row response cap when no
    `--limit` was given, same reasoning and `.order("id")` stability as
    `player_queries._fetch_all_player_rows`.
    """

    def query():
        q = supabase.table("players").select(_PLAYERS_SELECT).order("id")
        if latest_snapshot_ids:
            q = q.in_("statistics.snapshot_id", latest_snapshot_ids)
        return q.limit(1, foreign_table="statistics")

    if limit is not None:
        return cast(list[dict], query().range(offset, offset + limit - 1).execute().data)

    rows: list[dict] = []
    start = offset
    while True:
        page = cast(list[dict], query().range(start, start + _PAGE_SIZE - 1).execute().data)
        rows.extend(page)
        if len(page) < _PAGE_SIZE:
            return rows
        start += _PAGE_SIZE


def backfill(*, offset: int = 0, limit: int | None = None) -> None:
    load_dotenv()
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

    fotmob = FotMobClient()
    supabase = create_client(supabase_url, supabase_key)
    repo = SupabaseRepo(supabase)

    latest_snapshot_ids = list(get_latest_snapshots(supabase))
    rows = _fetch_players(supabase, latest_snapshot_ids, offset=offset, limit=limit)
    print(f"Backfilling Mapa de Toques for {len(rows)} players (offset={offset})")

    updated = 0
    no_statistics = 0
    for row in rows:
        raw_statistics = cast(list[dict], row["statistics"])
        if not raw_statistics:
            no_statistics += 1
            print(f"  {row['name']}: no Statistics, skipping")
            continue

        season = cast(dict, cast(dict, raw_statistics[0]["snapshots"])["seasons"])
        tournament_id = cast(dict, season["leagues"])["fotmob_id"]
        season_name = season["name"]

        try:
            player_data = fotmob.get_player_data(row["fotmob_id"])
            entry_id = find_entry_id(player_data, season_name=season_name, tournament_id=tournament_id)
            if entry_id is None:
                # Clears any Mapa de Toques a prior run left behind for this
                # Player, same "no data" convention as an empty coordinates
                # list from a fresh ingestion (save_touch_map deletes rather
                # than leaving a now-untraceable row stale).
                repo.save_touch_map(row["id"], [])
                print(f"  {row['name']}: no {season_name} entry for League {tournament_id} anymore, skipping")
                continue

            player_stats = fotmob.get_player_stats(row["fotmob_id"], entry_id)
            touch_coordinates = parse_touch_coordinates(player_stats)
            repo.save_touch_map(row["id"], touch_coordinates)
            updated += 1
        except Exception as exc:  # noqa: BLE001 - one player's failure must not abort the run
            print(f"  skipping {row['name']}: {exc!r}")
            continue

    print(f"Updated {updated}/{len(rows)} players ({no_statistics} had no Statistics)")


def run() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offset", type=int, default=0, help="Skip this many Players, ordered by id")
    parser.add_argument(
        "--limit", type=int, default=None, help="Process at most this many Players this invocation"
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be a positive integer")
    backfill(offset=args.offset, limit=args.limit)


if __name__ == "__main__":
    run()

"""One-off backfill: populate `teams.league_id` for every Team ingested
before that column existed (ADR-0004: a Team's current League is its own
fact, independent of which League produced any Player's Statistics).

Cheap compared to re-running `ingestion.run`: one `leagues` table fetch per
League, no Player/Statistic scraping at all.

Usage: `uv run python -m football_analytics.ingestion.backfill_team_league`

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the environment (see
.env.example). Safe to re-run: it only overwrites `teams.league_id`, same as
a normal ingestion run keeps it current via `SupabaseRepo.save_team`.
"""

from __future__ import annotations

import os
from typing import cast

from dotenv import load_dotenv
from supabase import create_client

from football_analytics.ingestion.fotmob_client import FotMobClient
from football_analytics.ingestion.normalize import parse_teams
from football_analytics.ingestion.run import SEASON_NAME


def run() -> None:
    load_dotenv()
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

    client = FotMobClient()
    supabase = create_client(supabase_url, supabase_key)

    leagues = cast(list[dict], supabase.table("leagues").select("id, fotmob_id, name").execute().data)
    print(f"Backfilling team league_id for {len(leagues)} leagues")

    updated = 0
    for league in leagues:
        try:
            league_table = client.get_league_table(league["fotmob_id"], SEASON_NAME)
            teams = parse_teams(league_table)
        except Exception as exc:  # noqa: BLE001 - one League's failure must not abort the run
            print(f"  skipping {league['name']}: {exc!r}")
            continue

        for team in teams:
            supabase.table("teams").update({"league_id": league["id"]}).eq(
                "fotmob_id", team.fotmob_id
            ).execute()
            updated += 1
        print(f"  {league['name']}: {len(teams)} teams")

    print(f"Updated league_id for {updated} teams")


if __name__ == "__main__":
    run()

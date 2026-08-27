"""Ingest the Premier League 2025/2026 roster and full Statistic profile
(Top Stats plus every category, including the goalkeeper-specific ones)
into Supabase.

Usage: `uv run python -m football_analytics.ingestion.run`

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the environment (see
.env.example).

Persists incrementally (team by team, player by player) rather than
buffering the whole league in memory: a failure partway through a
1000+ request run still leaves everything scraped so far saved under the
Snapshot, instead of losing it all.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

from dotenv import load_dotenv
from supabase import create_client

from football_analytics.ingestion.fotmob_client import FotMobClient
from football_analytics.ingestion.normalize import (
    find_entry_id,
    parse_all_stats,
    parse_squad,
    parse_teams,
    with_statistics,
)
from football_analytics.persistence.supabase_repo import SupabaseRepo

LEAGUE_FOTMOB_ID = 47
LEAGUE_NAME = "Premier League"
SEASON_NAME = "2025/2026"


def run() -> None:
    load_dotenv()
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

    client = FotMobClient()
    repo = SupabaseRepo(create_client(supabase_url, supabase_key))

    league_id = repo.get_or_create_league(LEAGUE_FOTMOB_ID, LEAGUE_NAME)
    season_id = repo.get_or_create_season(league_id, SEASON_NAME)
    snapshot_id = repo.create_snapshot(season_id, datetime.now(UTC))

    league_table = client.get_league_table(LEAGUE_FOTMOB_ID, SEASON_NAME)
    teams = parse_teams(league_table)
    print(f"Found {len(teams)} teams for {LEAGUE_NAME} {SEASON_NAME}")

    saved_count = 0
    for team in teams:
        try:
            team_id = repo.save_team(team)
            squad_payload = client.get_team(team.fotmob_id, SEASON_NAME)
            roster = parse_squad(squad_payload, team)
        except Exception as exc:  # noqa: BLE001 - one team's failure must not abort the run
            print(f"  skipping {team.name}: {exc!r}")
            continue
        print(f"  {team.name}: {len(roster)} players")

        for roster_player in roster:
            try:
                player_data = client.get_player_data(roster_player.fotmob_id)
                entry_id = find_entry_id(
                    player_data, season_name=SEASON_NAME, tournament_id=LEAGUE_FOTMOB_ID
                )
                if entry_id is None:
                    print(f"    skipping {roster_player.name}: no {SEASON_NAME} entry")
                    continue

                player_stats = client.get_player_stats(roster_player.fotmob_id, entry_id)
                statistics = parse_all_stats(player_stats)
                player = with_statistics(roster_player, statistics)

                repo.save_player(snapshot_id, team_id, player)
                saved_count += 1
            except Exception as exc:  # noqa: BLE001 - one player's failure must not abort the run
                print(f"    skipping {roster_player.name}: {exc!r}")
                continue

    print(f"Saved snapshot {snapshot_id} with {saved_count} players")


if __name__ == "__main__":
    run()

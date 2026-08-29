"""Ingest a League's roster and full Statistic profile (Top Stats plus every
category, including the goalkeeper-specific ones) into Supabase, for a
single Season.

Usage: `uv run python -m football_analytics.ingestion.run` (defaults to the
Premier League 2025/2026). For another League/Season:
`uv run python -m football_analytics.ingestion.run --league-id 87
--league-name "La Liga" --season 2025/2026`

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the environment (see
.env.example).

Persists incrementally (team by team, player by player) rather than
buffering the whole league in memory: a failure partway through a
1000+ request run still leaves everything scraped so far saved under the
Snapshot, instead of losing it all.
"""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime

from dotenv import load_dotenv
from supabase import create_client

from football_analytics.ingestion.fotmob_client import FotMobClient
from football_analytics.ingestion.normalize import (
    find_entry_id,
    find_known_league_entry,
    parse_all_stats,
    parse_squad,
    parse_teams,
    with_bio,
    with_statistics,
)
from football_analytics.persistence.supabase_repo import SupabaseRepo

LEAGUE_FOTMOB_ID = 47
LEAGUE_NAME = "Premier League"
SEASON_NAME = "2025/2026"


def ingest_league(league_fotmob_id: int, league_name: str, season_name: str) -> None:
    load_dotenv()
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

    client = FotMobClient()
    repo = SupabaseRepo(create_client(supabase_url, supabase_key))

    league_id = repo.get_or_create_league(league_fotmob_id, league_name)
    season_id = repo.get_or_create_season(league_id, season_name)
    snapshot_id = repo.create_snapshot(season_id, datetime.now(UTC))

    # Leagues already tracked (this one included) are the only safe fallback
    # targets for a Player whose Statistics for `season_name` belong to a
    # different League than the one being ingested right now — e.g. a
    # recently-transferred Player (ADR-0004). Fetched once per run, not
    # per-Player: cheap, and "known" shouldn't drift mid-run.
    known_leagues = {fotmob_id: (id_, name) for id_, fotmob_id, name in repo.list_leagues()}
    known_league_tournament_ids = set(known_leagues)

    league_table = client.get_league_table(league_fotmob_id, season_name)
    teams = parse_teams(league_table)
    print(f"Found {len(teams)} teams for {league_name} {season_name}")

    saved_count = 0
    fallback_count = 0
    no_statistics_count = 0
    for team in teams:
        try:
            team_id = repo.save_team(team, league_id)
            squad_payload = client.get_team(team.fotmob_id, season_name)
            roster = parse_squad(squad_payload, team)
        except Exception as exc:  # noqa: BLE001 - one team's failure must not abort the run
            print(f"  skipping {team.name}: {exc!r}")
            continue
        print(f"  {team.name}: {len(roster)} players")

        for roster_player in roster:
            try:
                player_data = client.get_player_data(roster_player.fotmob_id)
                entry_id = find_entry_id(
                    player_data, season_name=season_name, tournament_id=league_fotmob_id
                )
                target_snapshot_id = snapshot_id

                if entry_id is None:
                    fallback = find_known_league_entry(
                        player_data,
                        season_name=season_name,
                        known_league_tournament_ids=known_league_tournament_ids,
                    )
                    if fallback is not None:
                        fallback_tournament_id, entry_id = fallback
                        fallback_league_id, fallback_league_name = known_leagues[fallback_tournament_id]
                        fallback_season_id = repo.get_or_create_season(fallback_league_id, season_name)
                        target_snapshot_id = repo.get_or_create_latest_snapshot(fallback_season_id)
                        fallback_count += 1
                        print(
                            f"    {roster_player.name}: no {league_name} entry, "
                            f"using {fallback_league_name} Statistics instead"
                        )

                if entry_id is not None:
                    player_stats = client.get_player_stats(roster_player.fotmob_id, entry_id)
                    statistics = parse_all_stats(player_stats)
                else:
                    statistics = []
                    no_statistics_count += 1
                    print(f"    {roster_player.name}: saved with no Statistics ({season_name})")

                player = with_bio(with_statistics(roster_player, statistics), player_data)
                repo.save_player(target_snapshot_id, team_id, player)
                saved_count += 1
            except Exception as exc:  # noqa: BLE001 - one player's failure must not abort the run
                print(f"    skipping {roster_player.name}: {exc!r}")
                continue

    print(
        f"Saved snapshot {snapshot_id} with {saved_count} players "
        f"({fallback_count} with fallback Statistics, {no_statistics_count} with none)"
    )


def run() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league-id", type=int, default=LEAGUE_FOTMOB_ID, help="FotMob League id")
    parser.add_argument("--league-name", default=LEAGUE_NAME, help="League display name")
    parser.add_argument("--season", default=SEASON_NAME, help='Season name, e.g. "2025/2026"')
    args = parser.parse_args()
    ingest_league(args.league_id, args.league_name, args.season)


if __name__ == "__main__":
    run()

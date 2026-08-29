"""One-off backfill: populate age/nationality/preferred_foot/photo_url for
every Player already in Supabase from before these bio columns existed,
without re-scraping Statistics or touching Snapshots.

Usage: `uv run python -m football_analytics.ingestion.backfill_bio`

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the environment (see
.env.example). Safe to re-run: it only overwrites the same bio columns a
normal `ingestion.run` already keeps current via `with_bio`.
"""

from __future__ import annotations

import os
from typing import cast

from dotenv import load_dotenv
from supabase import create_client

from football_analytics.domain.models import Player, Team
from football_analytics.ingestion.fotmob_client import FotMobClient
from football_analytics.ingestion.normalize import with_bio


def run() -> None:
    load_dotenv()
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

    client = FotMobClient()
    supabase = create_client(supabase_url, supabase_key)

    rows = cast(list[dict], supabase.table("players").select("id, fotmob_id, name").execute().data)
    print(f"Backfilling bio for {len(rows)} players")

    updated = 0
    for row in rows:
        try:
            player_data = client.get_player_data(row["fotmob_id"])
            placeholder = Player(
                fotmob_id=row["fotmob_id"],
                name=row["name"],
                team=Team(fotmob_id=0, name=""),
                positions=(),
                statistics=(),
            )
            bio_player = with_bio(placeholder, player_data)
            supabase.table("players").update(
                {
                    "age": bio_player.age,
                    "nationality": bio_player.nationality,
                    "preferred_foot": bio_player.preferred_foot,
                    "photo_url": bio_player.photo_url,
                }
            ).eq("id", row["id"]).execute()
            updated += 1
        except Exception as exc:  # noqa: BLE001 - one player's failure must not abort the run
            print(f"  skipping {row['name']}: {exc!r}")
            continue

    print(f"Updated {updated}/{len(rows)} players")


if __name__ == "__main__":
    run()

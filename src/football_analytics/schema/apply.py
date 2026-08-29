"""Apply schema.sql directly to the database via SUPABASE_DB_URL.

Usage: `uv run python -m football_analytics.schema.apply`

Requires SUPABASE_DB_URL in the environment (see .env.example) — a direct
Postgres connection string from Supabase's Project Settings > Database,
distinct from SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY (the REST API
credentials the rest of the app uses).

Idempotent: schema.sql is written entirely with `create table if not
exists` / `add column if not exists`, so re-running after a schema change
only applies what's new.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def run() -> None:
    load_dotenv()
    db_url = os.environ["SUPABASE_DB_URL"]
    sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(sql)
        conn.commit()
    print("Schema applied.")


if __name__ == "__main__":
    run()

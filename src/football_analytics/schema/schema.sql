-- Player Analytics MVP schema (see CONTEXT.md for the vocabulary, ADR-0002
-- for why Statistics are grouped under a timestamped Snapshot instead of
-- being overwritten in place).

create table if not exists leagues (
    id bigint generated always as identity primary key,
    fotmob_id integer not null unique,
    name text not null
);

create table if not exists seasons (
    id bigint generated always as identity primary key,
    league_id bigint not null references leagues (id),
    name text not null, -- e.g. "2025/2026"
    unique (league_id, name)
);

create table if not exists teams (
    id bigint generated always as identity primary key,
    fotmob_id integer not null unique,
    name text not null
);

-- age/nationality/preferred_foot/photo_url are current-state attributes
-- (like player_positions below), not scoped to a Snapshot: refreshed on
-- every ingestion run. Nullable because FotMob doesn't always have every
-- field for every Player.
create table if not exists players (
    id bigint generated always as identity primary key,
    fotmob_id integer not null unique,
    name text not null,
    team_id bigint not null references teams (id),
    age integer,
    nationality text,
    preferred_foot text,
    photo_url text
);

-- A Player's Positions (Position Group included) are current-state
-- attributes, not scoped to a Snapshot: refreshed on every ingestion run.
create table if not exists player_positions (
    player_id bigint not null references players (id) on delete cascade,
    code text not null, -- FotMob position code, e.g. "CB", "RW"
    position_group text not null, -- Goalkeeper | Defender | Midfielder | Forward
    primary key (player_id, code)
);

-- One Snapshot per ingestion run for a given Season.
create table if not exists snapshots (
    id bigint generated always as identity primary key,
    season_id bigint not null references seasons (id),
    scraped_at timestamptz not null,
    unique (season_id, scraped_at)
);

-- A Player's Statistics as captured in a given Snapshot.
create table if not exists statistics (
    id bigint generated always as identity primary key,
    snapshot_id bigint not null references snapshots (id) on delete cascade,
    player_id bigint not null references players (id),
    key text not null, -- canonical stat key, e.g. "goals"
    label text not null, -- human-readable title, e.g. "Goals"
    value double precision not null,
    format text not null default 'number', -- FotMob's statFormat, e.g. "number", "fraction", "percent"
    unique (snapshot_id, player_id, key)
);

-- Idempotent for databases created before `format` existed.
alter table statistics add column if not exists format text not null default 'number';

-- Idempotent for databases created before these bio columns existed.
alter table players add column if not exists age integer;
alter table players add column if not exists nationality text;
alter table players add column if not exists preferred_foot text;
alter table players add column if not exists photo_url text;

-- The League a Team currently plays in — a current-state fact of the Team
-- itself (always the most recently ingested roster), independent of which
-- League/Season produced any given Player's Statistics (ADR-0004). Nullable
-- because it's backfilled after the fact for Teams ingested before this
-- column existed.
alter table teams add column if not exists league_id bigint references leagues (id);

-- A Player's Mapa de Toques: raw touch coordinates from FotMob, one row per
-- Player. Current-state, not Snapshot-scoped like `statistics` (ADR-0005) —
-- every ingestion/backfill run replaces the row in full via upsert, never
-- accumulates history. Kept out of `players` itself so the broad read used
-- by every dashboard page (list_players) doesn't pay for a blob only the
-- Análise de Jogadores page needs, one Player at a time.
create table if not exists player_touch_maps (
    player_id bigint primary key references players (id) on delete cascade,
    coordinates jsonb not null
);

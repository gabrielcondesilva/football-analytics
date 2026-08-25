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

create table if not exists players (
    id bigint generated always as identity primary key,
    fotmob_id integer not null unique,
    name text not null,
    team_id bigint not null references teams (id)
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
    unique (snapshot_id, player_id, key)
);

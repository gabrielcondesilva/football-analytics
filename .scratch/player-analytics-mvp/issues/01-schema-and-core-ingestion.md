# 01: Schema + core ingestion pipeline (roster + one Statistic category)

**What to build:** The Supabase schema for the domain (League, Season, Team, Player, Position, Snapshot, Statistic), plus a FotMob ingestion pipeline that fetches the full Premier League 2025/26 roster (with each Player's Team and Position(s)) and normalizes/persists one representative Statistic category as the first Snapshot.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Supabase schema exists for League, Season, Team, Player, Position, Snapshot, Statistic
- [ ] Ingestion fetches the full Premier League 2025/26 roster from FotMob's internal API, including each Player's Team and Position(s)
- [ ] A representative Statistic category (e.g. Top Stats: goals, assists, xG, minutes played) is normalized and persisted for every Player as a new Snapshot
- [ ] Seam A (raw FotMob JSON → normalized domain records) has fixture-based tests covering the roster and this Statistic category, with no live network calls
- [ ] Querying Supabase shows every PL 2025/26 Player with Team, Position(s), and this category's Statistics populated

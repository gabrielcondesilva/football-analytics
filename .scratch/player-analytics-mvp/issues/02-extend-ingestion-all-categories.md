# 02: Extend ingestion to all remaining Statistic categories (incl. goalkeeper)

**What to build:** Extend the ingestion pipeline from ticket 01 to cover every remaining FotMob Statistic category for every Player — Attack, Team Play, Defence, Passes for outfield Players, and the goalkeeper-specific category for goalkeepers — written into the same Snapshot mechanism.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Attack, Team Play, Defence, and Passes Statistic categories are normalized and persisted for every outfield Player
- [ ] The goalkeeper-specific Statistic category is normalized and persisted for every goalkeeper Player
- [ ] All categories are written into the same Snapshot mechanism established in ticket 01, with no schema migration needed
- [ ] Seam A tests extended with fixtures for each new category, including the goalkeeper-specific shape
- [ ] Querying any outfield Player and any goalkeeper Player in Supabase shows their complete FotMob stat profile

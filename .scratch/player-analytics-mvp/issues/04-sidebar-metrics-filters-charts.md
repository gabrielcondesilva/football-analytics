# 04: Sidebar Metric selection with per-90/percentile, Position Group + Minutes Floor filters, and charts

**What to build:** The sidebar Metric picker (raw Statistics or derived per-90/percentile), a Position Group filter, an adjustable Minutes Floor filter, and Plotly charts/leaderboards that reflect the current selection.

**Blocked by:** 02, 03

**Status:** ready-for-agent

- [ ] Sidebar lets the user pick one or more Metrics, either raw Statistics or derived per-90/percentile values
- [ ] Per-90 values are computed correctly using each Player's minutes-played Statistic
- [ ] Percentile values are computed correctly relative to the Player's Position Group within the Season
- [ ] Sidebar includes a Position Group filter
- [ ] Sidebar includes an adjustable Minutes Floor filter, and Players below the floor are excluded from the view
- [ ] Selected Metrics render in a Plotly chart/leaderboard that updates as filters change
- [ ] Seam B (domain records + selected Metrics + filters → analysis output) has tests covering Metric derivation, Minutes Floor exclusion, and Position Group filtering, independent of Streamlit and Supabase

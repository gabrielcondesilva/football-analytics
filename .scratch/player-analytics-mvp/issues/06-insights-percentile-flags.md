# 06: Insights — automatic percentile-based flags on a Player profile

**What to build:** A Player profile view that surfaces automatically generated Insights, derived from percentile thresholds on the Player's Metrics — no LLM involved.

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] Player profile view shows a list of automatically generated Insights
- [ ] Each Insight is derived from a percentile threshold rule on the Player's Metrics (e.g. "top 10% of the league in finishing"), with no LLM call involved
- [ ] Seam B tests cover Insight generation for Players both above and below the relevant thresholds

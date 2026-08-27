## Agent skills

### Issue tracker

Issues and specs live as local markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default triage labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Dashboard charts

Any new or edited chart/visual section in the Streamlit dashboard (`src/football_analytics/dashboard/app.py` and friends) goes through the `streamlit-dashboard-designer` subagent, not freehand in the main thread. Trust its design judgment (storytelling checklist + `dataviz` skill, see `.claude/agents/streamlit-dashboard-designer.md`) — no need to re-confirm chart choices with the user each time before delegating.

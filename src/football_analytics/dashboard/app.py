"""Dashboard entry point: multipage navigation between Overview and the
Player Workspace.

Usage: `uv run streamlit run src/football_analytics/dashboard/app.py`

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the environment (see
.env.example).
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Análise de Jogadores", layout="wide")

overview_page = st.Page("pages/overview.py", title="Visão Geral", icon="📊", default=True)
workspace_page = st.Page("pages/workspace.py", title="Análise de Jogadores", icon="👤")

navigation = st.navigation([overview_page, workspace_page])
navigation.run()

"""Report module: single-Player profile as a downloadable PDF.

No test coverage here by design (see the spec's Testing Decisions): this is
the I/O layer (PDF generation), verified manually. Reuses the same domain
records and Insights shown on the dashboard's Player Profile view; the
chart is expected to be exported from the same Plotly figure shown there
(as a static PNG, via kaleido) so the PDF matches what the user sees.
"""

from __future__ import annotations

import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer

from football_analytics.analysis.metrics import Insight
from football_analytics.domain.models import Player


def build_player_report_pdf(
    player: Player, insights: list[Insight], chart_png: bytes | None
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    positions = ", ".join(pos.code for pos in player.positions) or "No Position data"
    story = [
        Paragraph(player.name, styles["Title"]),
        Paragraph(f"{player.team.name} — {positions}", styles["Normal"]),
        Spacer(1, 12),
    ]

    if chart_png is not None:
        story.append(Image(io.BytesIO(chart_png), width=16 * cm, height=10 * cm))
        story.append(Spacer(1, 12))

    story.append(Paragraph("Insights", styles["Heading2"]))
    if insights:
        for insight in insights:
            marker = "Strength" if insight.kind == "strength" else "Weakness"
            story.append(
                Paragraph(
                    f"{marker}: {insight.label} — {insight.percentile:.0f}th percentile",
                    styles["Normal"],
                )
            )
    else:
        story.append(Paragraph("No notable Insights for this Player yet.", styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()

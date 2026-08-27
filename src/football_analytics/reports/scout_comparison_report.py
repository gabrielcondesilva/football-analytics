"""Report module: Scout Comparison result as a downloadable PDF.

No test coverage here by design (see the spec's Testing Decisions): this is
the I/O layer (PDF generation), verified manually. Reuses the shared PDF
pipeline (reports/pdf.py) first built for the single-Player Report
(ticket 07): same page setup and stylesheet, a comparison Table in place
of that report's chart + Insights list.
"""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from football_analytics.analysis.metrics import MetricSpec, compute_metric
from football_analytics.domain.models import Player
from football_analytics.reports.pdf import get_styles, render_pdf


def build_scout_comparison_report_pdf(
    reference: Player,
    results: list[tuple[Player, float]],
    specs: list[MetricSpec],
    metric_population: list[Player],
) -> bytes:
    styles = get_styles()

    positions = ", ".join(pos.code for pos in reference.positions) or "No Position data"
    story = [
        Paragraph(f"Scout Comparison — {reference.name}", styles["Title"]),
        Paragraph(f"Reference: {reference.name} ({reference.team.name}) — {positions}", styles["Normal"]),
        Spacer(1, 12),
    ]

    header = ["Player", "Team", "Positions", *(spec.label for spec in specs), "Distance"]
    rows = [header, _row(reference, "-", specs, metric_population)]
    rows.extend(
        _row(player, f"{distance:.3f}", specs, metric_population) for player, distance in results
    )

    table = Table(rows, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#e8f0fe")),
            ]
        )
    )
    story.append(table)

    return render_pdf(story)


def _row(
    player: Player, distance_label: str, specs: list[MetricSpec], metric_population: list[Player]
) -> list[str]:
    metric_cells = []
    for spec in specs:
        value = compute_metric(metric_population, player, spec)
        metric_cells.append("-" if value is None else f"{value:.2f}")
    player_positions = ", ".join(pos.code for pos in player.positions)
    return [player.name, player.team.name, player_positions, *metric_cells, distance_label]

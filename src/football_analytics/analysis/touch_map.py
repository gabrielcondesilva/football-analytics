"""Seam B: raw touch coordinates -> Mapa de Toques grid.

Pure function only: no network, no database, no Streamlit. Distinct from
`metrics.py` — a Mapa de Toques is a Player's own raw positional
distribution (CONTEXT.md), not a Metric compared against a Comparison
Population.
"""

from __future__ import annotations

GRID_ROWS = 6
"""3 rows covering the defensive half (x 0-50), 3 covering the attacking
half (x 50-100), each half split into 3 equal bands."""

GRID_COLS = 4
"""4 equal lanes covering the full width of the pitch (y 0-100)."""


def touch_map_grid(coordinates: list[tuple[float, float]]) -> list[list[float]] | None:
    """Percentage of `coordinates` (FotMob's 0-100 x/y touch scale, x=0 is a
    Player's own goal per the Mapa de Toques definition in CONTEXT.md)
    falling into each cell of the fixed `GRID_ROWS` x `GRID_COLS` grid.

    Returns `None` for an empty `coordinates` list ("sem dados") rather than
    an all-zero grid, so a caller can tell "no data" apart from "0%
    everywhere". Otherwise returns `GRID_ROWS` lists of `GRID_COLS`
    percentages each (row-major, row 0 the most defensive band, column 0 the
    y=0 edge), summing to 100.0 across the whole grid (floating-point
    rounding aside).

    Cell boundaries are half-open (`[start, end)`): a point exactly on a
    boundary belongs to the cell it's the *low* edge of, e.g. x=50.0 (the
    defensive/attacking half boundary) lands in the first attacking-half row,
    not the last defensive one. The one exception is the maximum coordinate
    value itself (100.0 on either axis), which the half-open rule would
    otherwise push one cell past the grid entirely — clamped into the last
    row/column instead.
    """
    if not coordinates:
        return None

    grid = [[0] * GRID_COLS for _ in range(GRID_ROWS)]
    for x, y in coordinates:
        row = min(max(int(x / 100 * GRID_ROWS), 0), GRID_ROWS - 1)
        col = min(max(int(y / 100 * GRID_COLS), 0), GRID_COLS - 1)
        grid[row][col] += 1

    total = len(coordinates)
    return [[count / total * 100 for count in row] for row in grid]

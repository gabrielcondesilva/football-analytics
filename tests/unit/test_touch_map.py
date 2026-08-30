import pytest

from football_analytics.analysis.touch_map import GRID_COLS, GRID_ROWS, touch_map_grid


def test_touch_map_grid_returns_none_for_no_coordinates():
    assert touch_map_grid([]) is None


def test_touch_map_grid_percentages_sum_to_100():
    coordinates = [(3.0, 5.0), (20.0, 90.0), (55.0, 40.0), (99.0, 1.0), (70.0, 70.0)]

    grid = touch_map_grid(coordinates)

    assert grid is not None
    total = sum(cell for row in grid for cell in row)
    assert total == pytest.approx(100.0)


def test_touch_map_grid_has_the_expected_shape():
    grid = touch_map_grid([(0.0, 0.0)])

    assert grid is not None
    assert len(grid) == GRID_ROWS
    assert all(len(row) == GRID_COLS for row in grid)


def test_touch_map_grid_puts_every_point_in_its_own_cell_when_all_share_one():
    coordinates = [(10.0, 10.0)] * 4 + [(90.0, 90.0)] * 6

    grid = touch_map_grid(coordinates)

    assert grid is not None
    assert grid[0][0] == pytest.approx(40.0)
    assert grid[GRID_ROWS - 1][GRID_COLS - 1] == pytest.approx(60.0)
    other_cells = [
        grid[row][col]
        for row in range(GRID_ROWS)
        for col in range(GRID_COLS)
        if (row, col) not in {(0, 0), (GRID_ROWS - 1, GRID_COLS - 1)}
    ]
    assert all(cell == 0.0 for cell in other_cells)


def test_touch_map_grid_assigns_a_row_boundary_point_to_the_higher_row():
    """x=50 sits exactly on the defensive/attacking half boundary (each row
    spans 100/6 ≈ 16.67 in x) — the documented rule is the cell starting at
    that boundary wins (half-open `[start, end)` cells), so x=50 lands in
    row 3 (the first attacking-half row: rows 0-2 are defensive, 3-5 are
    attacking), not row 2."""
    grid = touch_map_grid([(50.0, 10.0)])

    assert grid is not None
    assert grid[3][0] == pytest.approx(100.0)
    assert grid[2][0] == 0.0


def test_touch_map_grid_assigns_a_column_boundary_point_to_the_higher_column():
    """Same half-open rule on the y axis: y=50 (exact boundary between
    column 1 and 2 of 4 equal columns) lands in column 2."""
    grid = touch_map_grid([(10.0, 50.0)])

    assert grid is not None
    assert grid[0][2] == pytest.approx(100.0)
    assert grid[0][1] == 0.0


def test_touch_map_grid_clamps_the_maximum_coordinate_into_the_last_cell():
    """x=100.0/y=100.0 is the documented edge case: the half-open rule would
    otherwise push it one cell past the grid entirely."""
    grid = touch_map_grid([(100.0, 100.0)])

    assert grid is not None
    assert grid[GRID_ROWS - 1][GRID_COLS - 1] == pytest.approx(100.0)

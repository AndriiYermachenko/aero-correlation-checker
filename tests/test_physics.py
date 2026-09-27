"""Tests for correlation/physics.py: turning forces into coefficients."""

import pandas as pd
import pytest

from correlation import physics


def one_run(downforce_n: float, drag_n: float) -> pd.DataFrame:
    """Build a single tunnel run at 50 m/s on the 0.54 m2 model."""
    return pd.DataFrame({
        "speed_ms": [50.0],
        "ref_area_m2": [0.54],
        "downforce_n": [downforce_n],
        "drag_n": [drag_n],
    })


def test_worked_example_gives_cl_of_three():
    """Proves the two formulas: q is 0.5 * 1.225 * 50 * 50, and CL is force / (q * area)."""
    result = physics.add_coefficients(one_run(downforce_n=2480.6, drag_n=826.9))
    assert physics.dynamic_pressure(50.0) == pytest.approx(1531.25)
    assert result["cl"].iloc[0] == pytest.approx(3.00, abs=0.01)


def test_efficiency_is_cl_divided_by_cd():
    """Proves efficiency = CL / CD: a CL of 3.00 over a CD of 1.50 is 2.00."""
    result = physics.add_coefficients(one_run(downforce_n=2480.6, drag_n=1240.3))
    assert result["cd"].iloc[0] == pytest.approx(1.50, abs=0.01)
    assert result["efficiency"].iloc[0] == pytest.approx(2.00, abs=0.01)


def test_average_by_height_gives_one_row_per_height():
    """Proves repeats are averaged: three runs at 20 mm become one row with their mean."""
    runs = pd.DataFrame({
        "ride_height_mm": [30, 20, 20, 20],
        "cl": [3.0, 3.1, 3.2, 3.6],
        "cd": [0.9, 1.0, 1.0, 1.15],
    })
    result = physics.average_by_height(runs)
    assert list(result["ride_height_mm"]) == [20, 30]
    assert list(result["cl_mean"]) == pytest.approx([3.3, 3.0])
    assert list(result["cd_mean"]) == pytest.approx([1.05, 0.9])


def test_single_run_at_a_height_has_zero_spread():
    """Proves one run on its own reports a spread of 0, not an empty value."""
    runs = pd.DataFrame({"ride_height_mm": [20], "cl": [3.2], "cd": [1.0]})
    result = physics.average_by_height(runs)
    assert result["cl_std"].iloc[0] == 0.0
    assert result["cd_std"].iloc[0] == 0.0

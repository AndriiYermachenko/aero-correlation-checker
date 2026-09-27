"""Tests for correlation/compare.py: lining two sources up by ride height."""

import pandas as pd
import pytest

from correlation import compare


def averages(heights: list[int], cl_mean: list[float], cd_mean: list[float]) -> pd.DataFrame:
    """Build a small table shaped like the output of average_by_height."""
    return pd.DataFrame({
        "ride_height_mm": heights,
        "cl_mean": cl_mean,
        "cl_std": [0.0] * len(heights),
        "cd_mean": cd_mean,
        "cd_std": [0.0] * len(heights),
    })


# The reference has three heights. The other source has no 40 mm data.
REFERENCE = averages([20, 30, 40], cl_mean=[3.30, 3.00, 2.78], cd_mean=[1.00, 0.80, 0.98])
OTHER = averages([30, 20], cl_mean=[2.94, 3.63], cd_mean=[0.76, 1.06])


def test_differences_are_signed_percentages_of_the_reference():
    """Proves diff = (other - reference) / reference * 100, keeping the sign."""
    result = compare.compare(REFERENCE, OTHER, "cfd")
    at_20 = result.iloc[0]
    at_30 = result.iloc[1]
    assert at_20["cl_diff_pct"] == pytest.approx(10.0, abs=0.01)   # 3.63 against 3.30
    assert at_20["cd_diff_pct"] == pytest.approx(6.0, abs=0.01)    # 1.06 against 1.00
    assert at_30["cl_diff_pct"] == pytest.approx(-2.0, abs=0.01)   # 2.94 against 3.00
    assert at_30["cd_diff_pct"] == pytest.approx(-5.0, abs=0.01)   # 0.76 against 0.80


def test_height_missing_from_one_side_is_kept_without_data():
    """Proves a height only the reference has still gets a row, marked as no data."""
    result = compare.compare(REFERENCE, OTHER, "cfd")
    assert list(result["ride_height_mm"]) == [20, 30, 40]
    assert list(result["has_data"]) == [True, True, False]
    assert pd.isna(result["cl_diff_pct"].iloc[2])
    assert pd.isna(result["cd_diff_pct"].iloc[2])

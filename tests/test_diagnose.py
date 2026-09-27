"""Tests for correlation/diagnose.py: one hand-made pattern of gaps per verdict."""

import numpy as np
import pandas as pd

from correlation import diagnose

HEIGHTS = pd.Series([20, 25, 30, 35, 40])


def test_small_gaps_agree_with_the_tunnel() -> None:
    """Proves gaps of 3% or less in either direction count as agreement."""
    gaps = pd.Series([0.8, -1.1, 0.3, 3.0, -3.0])
    assert diagnose.diagnose(gaps, HEIGHTS) == "agrees with the tunnel (all within 3%)"


def test_same_gap_at_every_height_is_a_constant_offset() -> None:
    """Proves a steady gap is blamed on the setup, and reports its real size."""
    gaps = pd.Series([6.1, 5.9, 6.0, 6.2, 5.8])
    verdict = diagnose.diagnose(gaps, HEIGHTS)
    assert verdict.startswith("constant offset of about +6.0% at every ride height")
    assert "check the simulation setup" in verdict


def test_gap_that_grows_near_the_ground_is_ground_effect() -> None:
    """Proves a gap that widens as ride height falls is blamed on the underbody."""
    gaps = pd.Series([7.0, 4.0, 2.0, 1.0, 0.0])
    verdict = diagnose.diagnose(gaps, HEIGHTS)
    assert verdict.startswith("gap grows as the car gets closer to the ground")


def test_single_point_out_names_its_ride_height() -> None:
    """Proves one bad point is reported with the height where it happened."""
    gaps = pd.Series([0.5, -0.4, 8.0, 0.3, -0.2])
    assert diagnose.diagnose(gaps, HEIGHTS) == "one point out at 30 mm: check that run"


def test_two_valid_points_are_not_enough_to_judge() -> None:
    """Proves empty gaps are ignored, and that two real points give no verdict."""
    gaps = pd.Series([5.0, np.nan, np.nan, 4.0, np.nan])
    assert diagnose.diagnose(gaps, HEIGHTS) == "not enough points to judge"


def test_a_wider_tolerance_accepts_bigger_gaps() -> None:
    """Proves the tolerance can be changed: 4% gaps agree once 5% is allowed."""
    gaps = pd.Series([4.0, -4.0, 1.0, 2.0, 5.0])
    verdict = diagnose.diagnose(gaps, HEIGHTS, tolerance_pct=5.0)
    assert verdict == "agrees with the tunnel (all within 5%)"


def test_scattered_large_gaps_are_a_mixed_picture() -> None:
    """Proves gaps with no pattern fall through to the catch-all verdict."""
    gaps = pd.Series([5.0, -4.0, 0.5, 6.0, -5.0])
    assert diagnose.diagnose(gaps, HEIGHTS) == "mixed picture: investigate point by point"

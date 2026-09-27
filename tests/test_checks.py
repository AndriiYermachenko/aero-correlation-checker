"""Tests for correlation/checks.py: finding bad data and removing it."""

import numpy as np
import pandas as pd

from correlation import checks

# On the 0.54 m2 model at 50 m/s, 2480.6 N of downforce is a CL of 3.00.
GOOD_DOWNFORCE = 2480.6
GOOD_DRAG = 826.9


def make_runs(downforce_n: list[float], drag_n: list[float]) -> pd.DataFrame:
    """Build repeat tunnel runs at 30 mm and 50 m/s with the given forces."""
    count = len(downforce_n)
    return pd.DataFrame({
        "run_id": range(1, count + 1),
        "ride_height_mm": [30] * count,
        "speed_ms": [50.0] * count,
        "ref_area_m2": [0.54] * count,
        "downforce_n": downforce_n,
        "drag_n": drag_n,
    })


def flagged(issues: list[checks.Issue]) -> list[tuple[int, str]]:
    """Reduce each issue to (run_id, kind) so a test can compare them easily."""
    return [(issue.run_id, issue.kind) for issue in issues]


def test_nan_downforce_is_reported_as_missing():
    """Proves an empty downforce value is caught and blamed on the right run."""
    runs = make_runs([GOOD_DOWNFORCE, np.nan], [GOOD_DRAG, GOOD_DRAG])
    assert flagged(checks.find_issues(runs, "tunnel")) == [(2, "missing")]


def test_negative_drag_is_reported_as_out_of_range():
    """Proves an impossible value is caught: drag always pushes backwards, never forwards."""
    runs = make_runs([GOOD_DOWNFORCE, GOOD_DOWNFORCE], [GOOD_DRAG, -GOOD_DRAG])
    assert flagged(checks.find_issues(runs, "tunnel")) == [(2, "out_of_range")]


def test_run_with_cl_25_percent_high_is_not_repeatable():
    """Proves that out of three repeats, only the one that disagrees is flagged."""
    runs = make_runs([GOOD_DOWNFORCE, GOOD_DOWNFORCE * 1.25, GOOD_DOWNFORCE], [GOOD_DRAG] * 3)
    assert flagged(checks.find_issues(runs, "tunnel")) == [(2, "not_repeatable")]


def test_bad_row_does_not_distort_the_median():
    """Proves a row that is already flagged is left out of the repeatability check.

    Runs 1 and 2 are 3.3% apart, so each is under 2% from their shared median.
    If run 3 were counted, the median would move to run 1 and run 2 would be flagged.
    """
    runs = make_runs([GOOD_DOWNFORCE, GOOD_DOWNFORCE * 1.033, 100.0], [GOOD_DRAG, GOOD_DRAG, -5.0])
    assert flagged(checks.find_issues(runs, "tunnel")) == [(3, "out_of_range")]


def test_drop_flagged_removes_exactly_the_flagged_rows():
    """Proves flagged runs are removed and every other run is kept."""
    runs = make_runs([GOOD_DOWNFORCE] * 4, [GOOD_DRAG] * 4)
    issues = [
        checks.Issue("tunnel", 2, "missing", "missing drag_n"),
        checks.Issue("tunnel", 4, "out_of_range", "out of range"),
    ]
    assert list(checks.drop_flagged(runs, issues)["run_id"]) == [1, 3]

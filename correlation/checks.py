"""Find bad data before it is analysed, so one bad row cannot spoil an average.

There are three checks: values that are missing, values that cannot be real,
and repeat runs that disagree with each other. A row that fails is "flagged".
"""

from dataclasses import dataclass

import pandas as pd

from correlation.physics import add_coefficients

# Every one of these must hold a value before a row can be used.
NEEDED_COLUMNS = ["downforce_n", "drag_n", "speed_ms", "ref_area_m2", "ride_height_mm"]


@dataclass
class Issue:
    """One problem found in one row of one source."""

    source: str
    run_id: int
    kind: str      # "missing", "out_of_range" or "not_repeatable"
    message: str


def find_missing(df: pd.DataFrame, name: str) -> list[Issue]:
    """Flag every row where a value we need is empty (NaN)."""
    issues = []
    for _, row in df.iterrows():
        empty = [column for column in NEEDED_COLUMNS if pd.isna(row[column])]
        if empty:
            message = "missing " + ", ".join(empty)
            issues.append(Issue(name, int(row["run_id"]), "missing", message))
    return issues


def find_out_of_range(df: pd.DataFrame, name: str) -> list[Issue]:
    """Flag every row holding a value that cannot be real, such as negative drag."""
    issues = []
    for _, row in df.iterrows():
        problems = []
        if row["downforce_n"] <= 0:
            problems.append("downforce_n is not above zero")
        if row["drag_n"] <= 0:
            problems.append("drag_n is not above zero")
        if not 10 <= row["speed_ms"] <= 120:
            problems.append("speed_ms is outside 10 to 120 m/s")
        if not 5 <= row["ride_height_mm"] <= 100:
            problems.append("ride_height_mm is outside 5 to 100 mm")
        if problems:
            message = "out of range, " + ", ".join(problems)
            issues.append(Issue(name, int(row["run_id"]), "out_of_range", message))
    return issues


def find_not_repeatable(df: pd.DataFrame, name: str, tolerance: float) -> list[Issue]:
    """Flag repeat runs whose CL is too far from the median CL at their ride height."""
    issues = []
    for height, group in add_coefficients(df).groupby("ride_height_mm"):
        if len(group) < 2:
            continue   # a single run has nothing to be compared with
        # The median is used because, unlike the mean, one bad run cannot drag it away.
        median = group["cl"].median()
        for _, row in group.iterrows():
            gap = abs(row["cl"] - median) / median
            if gap > tolerance:
                message = f"not repeatable, CL {gap * 100:.1f}% from the median at {int(height)} mm"
                issues.append(Issue(name, int(row["run_id"]), "not_repeatable", message))
    return issues


def drop_flagged(df: pd.DataFrame, issues: list[Issue]) -> pd.DataFrame:
    """Return only the rows that no issue points at."""
    flagged_ids = [issue.run_id for issue in issues]
    return df[~df["run_id"].isin(flagged_ids)]


def find_issues(df: pd.DataFrame, name: str, tolerance: float = 0.03) -> list[Issue]:
    """Run the three checks in order. Each check skips rows that are already flagged."""
    issues = find_missing(df, name)
    issues += find_out_of_range(drop_flagged(df, issues), name)
    issues += find_not_repeatable(drop_flagged(df, issues), name, tolerance)
    return issues

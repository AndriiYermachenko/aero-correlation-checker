"""Build the plain-text summary that is printed and saved as summary.txt.

It lives in its own file only to keep analyse.py short.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

from correlation.checks import Issue

TITLES = {"cfd": "CFD vs tunnel", "track": "Track vs tunnel"}


def quality_line(name: str, df: pd.DataFrame, issues: list[Issue], all_heights: set[int]) -> str:
    """Describe one source: its rows, what was dropped and which heights it lacks."""
    dropped = {issue.run_id for issue in issues}   # a set, so each run is counted once
    label = name + ":"
    # "<7" pads the label with spaces to 7 characters, which lines the numbers up.
    line = f"  {label:<7} {len(df)} rows, {len(dropped)} dropped"
    if issues:
        reasons = [f"run {issue.run_id}: {issue.message}" for issue in issues]
        line += " (" + "; ".join(reasons) + ")"
    absent = sorted(all_heights - set(df["ride_height_mm"]))
    if absent:
        line += "   [no data at " + ", ".join(f"{int(height)} mm" for height in absent) + "]"
    return line


def comparison_lines(table: pd.DataFrame, verdicts: dict[str, str]) -> list[str]:
    """Return the block of lines for one source compared with the tunnel."""
    source = table["source"].iloc[0]
    lines = ["", TITLES[source], f"  {'ride height':<14}{'CL diff':<10}CD diff"]
    for _, row in table.iterrows():
        height = f"{int(row['ride_height_mm'])} mm"
        if row["has_data"]:
            cl = f"{row['cl_diff_pct']:+.1f}%"   # "+" shows the sign even when positive
            cd = f"{row['cd_diff_pct']:+.1f}%"
        else:
            cl = cd = "no data"
        lines.append(f"  {height:<14}{cl:<10}{cd}")
    lines.append(f"  CL: {verdicts[source + '_cl']}")
    lines.append(f"  CD: {verdicts[source + '_cd']}")
    return lines


def build_summary(now: datetime, sources: dict[str, pd.DataFrame],
                  issues: dict[str, list[Issue]], comparisons: list[pd.DataFrame],
                  verdicts: dict[str, str], chart_paths: list[Path]) -> str:
    """Return the whole summary as one piece of text."""
    # Collect every ride height any source has, to spot a source that lacks one.
    all_heights = set()
    for df in sources.values():
        all_heights.update(df["ride_height_mm"].dropna())
    lines = ["Aero correlation check  " + now.strftime("%Y-%m-%d %H:%M"), "", "Data quality"]
    for name, df in sources.items():
        lines.append(quality_line(name, df, issues[name], all_heights))
    for table in comparisons:
        lines += comparison_lines(table, verdicts)
    lines += ["", "Charts: " + ", ".join(str(path) for path in chart_paths)]
    return "\n".join(lines) + "\n"

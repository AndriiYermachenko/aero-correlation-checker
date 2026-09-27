"""Line two sources up by ride height and measure the gap between them.

The tunnel is always the reference. That is a design choice, not a law: the
tunnel is the measurement the team trusts most day to day, so the other
sources are described by how far they sit from it.
"""

import pandas as pd

OUTPUT_COLUMNS = [
    "ride_height_mm", "source", "cl_ref", "cl_other", "cl_diff_pct",
    "cd_ref", "cd_other", "cd_diff_pct", "has_data",
]


def compare(reference: pd.DataFrame, other: pd.DataFrame, other_name: str) -> pd.DataFrame:
    """Return the gap in CL and CD, as a percentage of the reference, at each ride height."""
    ref = reference.rename(columns={"cl_mean": "cl_ref", "cd_mean": "cd_ref"})
    oth = other.rename(columns={"cl_mean": "cl_other", "cd_mean": "cd_other"})
    # An outer merge keeps every ride height, even one that only one side has.
    # The side without that height gets NaN, which means "no value".
    merged = pd.merge(
        ref[["ride_height_mm", "cl_ref", "cd_ref"]],
        oth[["ride_height_mm", "cl_other", "cd_other"]],
        on="ride_height_mm",
        how="outer",
    )
    merged["source"] = other_name
    merged["cl_diff_pct"] = (merged["cl_other"] - merged["cl_ref"]) / merged["cl_ref"] * 100
    merged["cd_diff_pct"] = (merged["cd_other"] - merged["cd_ref"]) / merged["cd_ref"] * 100
    # Any sum that involves NaN is NaN, so a gap only exists where both sides have data.
    merged["has_data"] = merged["cl_diff_pct"].notna() & merged["cd_diff_pct"].notna()
    merged = merged.sort_values("ride_height_mm").reset_index(drop=True)
    return merged[OUTPUT_COLUMNS]

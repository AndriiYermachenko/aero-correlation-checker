"""Turn a pattern of gaps into a hint about the likely cause.

Different faults leave different fingerprints. A wrong setup value shifts
every point by the same amount. Weak ground-effect modelling gets worse the
lower the car runs. One bad run moves a single point.
"""

import pandas as pd

TOLERANCE_PCT = 3.0         # a gap this small or smaller counts as agreement
CONSTANT_SPREAD_PCT = 1.0   # gaps that vary by less than this are "the same everywhere"
TREND_CORRELATION = -0.8    # below this, the gap clearly grows as ride height falls


# These are hints that point an engineer where to look first, not conclusions.
def diagnose(diff_pct: pd.Series, ride_height_mm: pd.Series,
             tolerance_pct: float = TOLERANCE_PCT) -> str:
    """Return a one-line hint describing the pattern in the gaps to the tunnel."""
    # Keep only the ride heights where both the gap and the height hold a value.
    valid = diff_pct.notna() & ride_height_mm.notna()
    diff = diff_pct[valid]
    height = ride_height_mm[valid]

    if len(diff) < 3:
        return "not enough points to judge"
    if (diff.abs() <= tolerance_pct).all():
        # ":g" prints 3.0 as "3", so the text reads "within 3%".
        return f"agrees with the tunnel (all within {tolerance_pct:g}%)"
    if diff.std() < CONSTANT_SPREAD_PCT and abs(diff.mean()) > tolerance_pct:
        return (f"constant offset of about {diff.mean():+.1f}% at every ride height: "
                "check the simulation setup (reference area, speed, air density)")
    # A correlation near -1 means: the lower the ride height, the bigger the gap.
    if diff.corr(height) < TREND_CORRELATION and diff.abs().max() > tolerance_pct:
        return ("gap grows as the car gets closer to the ground: "
                "ground-effect region, check floor and underbody modelling")
    over = diff.abs() > tolerance_pct   # True for each point outside the tolerance
    if over.sum() == 1:
        return f"one point out at {int(height[over].iloc[0])} mm: check that run"
    return "mixed picture: investigate point by point"

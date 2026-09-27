"""The physics: the constants and the two formulas behind every comparison.

Raw forces depend on how big the car is and how fast the air is moving, so
they cannot be compared between the tunnel, CFD and the track. Dividing by
the dynamic pressure and the reference area gives coefficients, which can.
"""

import pandas as pd

AIR_DENSITY = 1.225    # kg/m3, air at sea level
FULL_CAR_AREA = 1.5    # m2, reference area of the full-size car
MODEL_SCALE = 0.6      # the tunnel model is 60% size
MODEL_AREA = FULL_CAR_AREA * MODEL_SCALE ** 2   # = 0.54 m2 (area scales with size squared)


def dynamic_pressure(speed_ms: float) -> float:
    """Return the dynamic pressure q in pascals: the push of air moving at this speed."""
    return 0.5 * AIR_DENSITY * speed_ms ** 2


def add_coefficients(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with the columns cl, cd and efficiency added."""
    result = df.copy()
    # Every row has its own speed and area, so q is worked out row by row.
    q = result["speed_ms"].apply(dynamic_pressure)
    result["cl"] = result["downforce_n"] / (q * result["ref_area_m2"])
    result["cd"] = result["drag_n"] / (q * result["ref_area_m2"])
    result["efficiency"] = result["cl"] / result["cd"]
    return result


def average_by_height(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per ride height: the mean and the spread (std) of cl and cd."""
    # Each line reads: new column = (column to summarise, how to summarise it).
    # groupby also sorts the result by ride height.
    averages = df.groupby("ride_height_mm").agg(
        cl_mean=("cl", "mean"),
        cl_std=("cl", "std"),
        cd_mean=("cd", "mean"),
        cd_std=("cd", "std"),
    )
    # A single run has no spread to measure, which pandas reports as NaN. Call it 0.
    averages[["cl_std", "cd_std"]] = averages[["cl_std", "cd_std"]].fillna(0.0)
    # reset_index turns ride height back from a row label into a normal column.
    return averages.reset_index()

"""Write the three fake data files: tunnel.csv, cfd.csv and track.csv.

Every source is built from the same "true" car, then four faults are planted
so the analysis has something to find. The random seed is fixed, so every run
writes exactly the same files.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from correlation.physics import FULL_CAR_AREA, MODEL_AREA, dynamic_pressure

HEIGHTS = [20, 25, 30, 35, 40]   # ride heights in mm

# The "true" car: its real coefficients at each ride height.
TRUE_CL = {20: 3.30, 25: 3.15, 30: 3.00, 35: 2.88, 40: 2.78}
TRUE_CD = {20: 1.03, 25: 1.01, 30: 1.00, 35: 0.99, 40: 0.98}

# Fault 3: the extra downforce CFD wrongly predicts, growing as the car gets lower.
CFD_EXTRA_DOWNFORCE = {20: 0.07, 25: 0.04, 30: 0.02, 35: 0.01, 40: 0.00}


def true_runs(heights: list[int], speeds: np.ndarray, area: float) -> pd.DataFrame:
    """Return one row per run, holding the forces the true car would produce."""
    df = pd.DataFrame({
        "run_id": range(1, len(heights) + 1),
        "ride_height_mm": heights,
        "speed_ms": speeds.round(2),   # a real sensor reports about this many digits
        "ref_area_m2": area,
    })
    # force = q * area * coefficient: the coefficient formula turned around.
    q = df["speed_ms"].apply(dynamic_pressure)
    df["downforce_n"] = q * area * df["ride_height_mm"].map(TRUE_CL)
    df["drag_n"] = q * area * df["ride_height_mm"].map(TRUE_CD)
    return df


def make_tunnel(rng: np.random.Generator) -> pd.DataFrame:
    """Three repeats per ride height on the 60% model, with small random noise."""
    heights = sorted(HEIGHTS * 3)   # 20, 20, 20, 25, 25, 25 and so on
    df = true_runs(heights, 50 + rng.normal(0, 0.2, size=15), MODEL_AREA)
    df["downforce_n"] *= 1 + rng.normal(0, 0.005, size=15)
    df["drag_n"] *= 1 + rng.normal(0, 0.005, size=15)
    # Fault 1, a bad reading: run 8 (a 30 mm run) reads 25% too much downforce.
    df.loc[df["run_id"] == 8, "downforce_n"] *= 1.25
    return df


def make_cfd() -> pd.DataFrame:
    """One simulation per ride height. No noise: a simulation always repeats itself."""
    df = true_runs(HEIGHTS, np.full(5, 60.0), FULL_CAR_AREA)
    # Fault 3, weak ground-effect modelling: too much downforce, worse when lower.
    df["downforce_n"] *= 1 + df["ride_height_mm"].map(CFD_EXTRA_DOWNFORCE)
    # Fault 2, a setup mistake: every drag value is 6% too high.
    df["drag_n"] *= 1.06
    return df


def make_track(rng: np.random.Generator) -> pd.DataFrame:
    """One averaged reading per ride height from the real car, with random noise."""
    df = true_runs(HEIGHTS, 70 + rng.normal(0, 1.5, size=5), FULL_CAR_AREA)
    df["downforce_n"] *= 1 + rng.normal(0, 0.01, size=5)
    df["drag_n"] *= 1 + rng.normal(0, 0.01, size=5)
    # Fault 4, missing data: the team never got a clean reading at 35 mm...
    df = df[df["ride_height_mm"] != 35].reset_index(drop=True)
    df["run_id"] = range(1, len(df) + 1)
    # ...and the downforce reading at 40 mm was lost.
    df.loc[df["ride_height_mm"] == 40, "downforce_n"] = np.nan
    return df


def main(data_dir: Path = Path("data")) -> None:
    """Build the three sources and write each one to a CSV file in data_dir."""
    rng = np.random.default_rng(seed=42)   # fixed seed: the same "random" numbers every run
    data_dir.mkdir(parents=True, exist_ok=True)
    sources = {"tunnel": make_tunnel(rng), "cfd": make_cfd(), "track": make_track(rng)}
    for name, df in sources.items():
        df["downforce_n"] = df["downforce_n"].round(1)
        df["drag_n"] = df["drag_n"].round(1)
        path = data_dir / f"{name}.csv"
        df.to_csv(path, index=False)
        print(f"Wrote {path} ({len(df)} rows)")


if __name__ == "__main__":
    main()

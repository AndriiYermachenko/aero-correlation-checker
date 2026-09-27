"""Read the three CSV data files and check they have the columns we need."""

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    "run_id",
    "ride_height_mm",
    "speed_ms",
    "ref_area_m2",
    "downforce_n",
    "drag_n",
]

# The name of each source and the file it is kept in.
FILE_NAMES = {"tunnel": "tunnel.csv", "cfd": "cfd.csv", "track": "track.csv"}


def load_source(path: Path, name: str) -> pd.DataFrame:
    """Read one CSV file and label every row with the name of its source."""
    if not path.exists():
        raise FileNotFoundError(f"data file not found: {path}")
    df = pd.read_csv(path)
    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            raise ValueError(f"{path} is missing the column '{column}'")
    df["source"] = name
    return df


def load_all(data_dir: Path) -> dict[str, pd.DataFrame]:
    """Read tunnel.csv, cfd.csv and track.csv from data_dir, keyed by source name."""
    sources = {}
    for name, file_name in FILE_NAMES.items():
        sources[name] = load_source(data_dir / file_name, name)
    return sources

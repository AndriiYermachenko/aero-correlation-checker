"""Save each analysis to a small SQLite database, so repeated runs build a history.

SQLite keeps a whole database inside one ordinary file, and Python can read
and write it with the sqlite3 module from the standard library.
"""

import sqlite3
from pathlib import Path

import pandas as pd

CREATE_COMPARISONS = """
    CREATE TABLE IF NOT EXISTS comparisons (
        analysed_at TEXT, source TEXT, ride_height_mm INTEGER,
        cl_ref REAL, cl_other REAL, cl_diff_pct REAL,
        cd_ref REAL, cd_other REAL, cd_diff_pct REAL
    )"""

CREATE_VERDICTS = """
    CREATE TABLE IF NOT EXISTS verdicts (
        analysed_at TEXT, source TEXT, quantity TEXT, verdict TEXT
    )"""

# The columns of a comparison table that hold decimal numbers.
NUMBER_COLUMNS = ["cl_ref", "cl_other", "cl_diff_pct", "cd_ref", "cd_other", "cd_diff_pct"]


def save_results(db_path: Path, analysed_at: str, comparisons: list[pd.DataFrame],
                 verdicts: dict[str, str]) -> None:
    """Append the comparison rows and the verdicts of one run to the database."""
    connection = sqlite3.connect(db_path)
    connection.execute(CREATE_COMPARISONS)
    connection.execute(CREATE_VERDICTS)
    for table in comparisons:
        for _, row in table.iterrows():
            # sqlite3 only knows Python's own int and float, not the numpy kinds.
            # A NaN (no data) is saved as NULL, the database's word for "empty".
            values = [analysed_at, row["source"], int(row["ride_height_mm"])]
            values += [float(row[column]) for column in NUMBER_COLUMNS]
            # Each ? is replaced by the matching value from the list.
            connection.execute("INSERT INTO comparisons VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", values)
    for key, verdict in verdicts.items():
        source, quantity = key.split("_")   # "cfd_cl" becomes "cfd" and "cl"
        connection.execute("INSERT INTO verdicts VALUES (?, ?, ?, ?)",
                           (analysed_at, source, quantity, verdict))
    connection.commit()   # nothing reaches the file until the commit
    connection.close()


def history(db_path: Path) -> list[tuple]:
    """Return analysed_at, source, quantity and verdict for every past run, newest first."""
    connection = sqlite3.connect(db_path)
    # rowid is SQLite's own row counter: it keeps one run's verdicts in the order saved.
    rows = connection.execute(
        "SELECT analysed_at, source, quantity, verdict FROM verdicts "
        "ORDER BY analysed_at DESC, rowid"
    ).fetchall()
    connection.close()
    return rows

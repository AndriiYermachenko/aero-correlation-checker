"""Command-line entry point: check whether the tunnel, CFD and the track agree.

Run it with:
    .venv/bin/python analyse.py [--data data] [--out output] [--tolerance 3.0]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from correlation import charts, checks, compare, diagnose, loading, physics, storage, summary


def run(data_dir: Path, out_dir: Path, tolerance: float) -> None:
    """Run every step of the analysis in order, printing a short line for each."""
    now = datetime.now()

    print("1. Loading the three sources")
    sources = loading.load_all(data_dir)

    print("2. Checking the data")
    issues = {}
    clean = {}
    for name, df in sources.items():
        # The checks take the tolerance as a fraction, so 3.0% becomes 0.03.
        issues[name] = checks.find_issues(df, name, tolerance / 100)
        for issue in issues[name]:
            print(f"   {issue.source} run {issue.run_id}: {issue.message}")
        clean[name] = checks.drop_flagged(df, issues[name])

    print("3. Converting forces to coefficients and averaging by ride height")
    averages = {}
    for name, df in clean.items():
        averages[name] = physics.average_by_height(physics.add_coefficients(df))

    print("4. Comparing CFD and the track against the tunnel")
    comparisons = []
    for name in ["cfd", "track"]:
        comparisons.append(compare.compare(averages["tunnel"], averages[name], name))

    print("5. Diagnosing the gaps")
    verdicts = {}
    for table in comparisons:
        source = table["source"].iloc[0]
        for quantity in ["cl", "cd"]:
            gaps = table[quantity + "_diff_pct"]
            verdict = diagnose.diagnose(gaps, table["ride_height_mm"], tolerance)
            verdicts[source + "_" + quantity] = verdict   # the key looks like "cfd_cl"

    print("6. Drawing the charts")
    out_dir.mkdir(parents=True, exist_ok=True)
    chart_paths = [out_dir / "coefficients.png", out_dir / "differences.png"]
    charts.plot_coefficients(averages, chart_paths[0])
    charts.plot_differences(comparisons, tolerance, chart_paths[1])

    print("7. Saving the results. History, newest first:")
    db_path = out_dir / "results.db"
    storage.save_results(db_path, now.strftime("%Y-%m-%d %H:%M:%S"), comparisons, verdicts)
    for analysed_at, source, quantity, verdict in storage.history(db_path):
        print(f"   {analysed_at}  {source} {quantity.upper()}: {verdict}")

    print("8. Writing the summary")
    text = summary.build_summary(now, sources, issues, comparisons, verdicts, chart_paths)
    (out_dir / "summary.txt").write_text(text)
    print()
    print(text)


def main() -> int:
    """Read the command-line options, run the analysis and return the exit code."""
    parser = argparse.ArgumentParser(description="Check whether tunnel, CFD and track data agree.")
    parser.add_argument("--data", type=Path, default=Path("data"),
                        help="folder holding the three CSV files")
    parser.add_argument("--out", type=Path, default=Path("output"),
                        help="folder for the charts, the summary and the database")
    parser.add_argument("--tolerance", type=float, default=3.0,
                        help="largest gap, in percent, that still counts as agreement")
    args = parser.parse_args()
    try:
        run(args.data, args.out, args.tolerance)
    except FileNotFoundError as error:
        print(f"Error: {error}")
        return 1   # any exit code other than 0 tells the shell that something failed
    return 0


if __name__ == "__main__":
    sys.exit(main())

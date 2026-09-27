"""Draw the two charts: the coefficients themselves, and the gaps to the tunnel."""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.use("Agg")   # draw straight into a file, so no window is ever opened


def plot_coefficients(averages: dict[str, pd.DataFrame], out_path: Path) -> None:
    """Plot CL against ride height, one line per source, and save it as a PNG."""
    fig, ax = plt.subplots()
    for name, df in averages.items():
        # The error bars show the spread (std) between repeat runs at each height.
        ax.errorbar(df["ride_height_mm"], df["cl_mean"], yerr=df["cl_std"],
                    marker="o", capsize=3, label=name)
    ax.set_xlabel("Ride height (mm)")
    ax.set_ylabel("Downforce coefficient CL (no units)")
    ax.set_title("Downforce coefficient vs ride height")
    ax.legend()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)   # free the memory the figure was using


def plot_differences(comparisons: list[pd.DataFrame], tolerance_pct: float,
                     out_path: Path) -> None:
    """Plot the CL and CD gaps to the tunnel side by side, and save them as a PNG."""
    fig, (cl_ax, cd_ax) = plt.subplots(1, 2, figsize=(12, 5))
    panels = [
        (cl_ax, "cl_diff_pct", "CL difference vs tunnel (%)"),
        (cd_ax, "cd_diff_pct", "CD difference vs tunnel (%)"),
    ]
    for ax, column, title in panels:
        # Any point inside the grey band counts as agreeing with the tunnel.
        ax.axhspan(-tolerance_pct, tolerance_pct, color="grey", alpha=0.2,
                   label=f"within {tolerance_pct:g}%")
        ax.axhline(0, color="black", linestyle="--")
        for df in comparisons:
            # A height with no data holds NaN, which leaves a gap in the line.
            ax.plot(df["ride_height_mm"], df[column], marker="o", label=df["source"].iloc[0])
        ax.set_xlabel("Ride height (mm)")
        ax.set_ylabel("Difference (%)")
        ax.set_title(title)
        ax.legend()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)

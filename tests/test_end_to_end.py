"""End-to-end test: make the fake data, run the whole analysis, check what comes out."""

from pathlib import Path

import analyse
import make_data


def test_full_run_finds_the_planted_faults(tmp_path: Path) -> None:
    """Proves every step works together, from the CSV files to the written summary."""
    data_dir = tmp_path / "data"
    out_dir = tmp_path / "output"
    make_data.main(data_dir)

    analyse.run(data_dir, out_dir, 3.0)

    for file_name in ["coefficients.png", "differences.png", "summary.txt", "results.db"]:
        assert (out_dir / file_name).exists()
    summary = (out_dir / "summary.txt").read_text()
    assert "constant offset" in summary          # CFD drag: the setup mistake
    assert "closer to the ground" in summary     # CFD downforce: weak ground effect
    assert "agrees with the tunnel" in summary   # the track matches the tunnel

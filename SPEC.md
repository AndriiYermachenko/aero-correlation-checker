# Aero Correlation Checker: build specification

## 0. What this is and the rules for building it

A small command-line tool that checks whether three sources of aerodynamic data agree with each other: the wind tunnel, CFD (computer simulation of airflow) and the real car on track. It converts all three to comparable numbers, lines them up, flags where they disagree, and suggests the likely reason.

It is a weekend demo project. The author, a second-year Computer Science student, must be able to explain every line of it in a job interview. So:

- **Simple beats clever.** Plain functions, short files, obvious names. No abstractions that exist only to look professional.
- **Comment the "why", in plain English.** A reader who knows Python but nothing about aerodynamics must be able to follow it. Every file starts with a short docstring saying what the file is for. Every function has a one- or two-line docstring.
- **Small files.** No file over about 90 lines. Split further if it grows.
- **Only these libraries:** `pandas`, `numpy`, `matplotlib`, `pytest`, plus the Python standard library (`argparse`, `pathlib`, `sqlite3`, `dataclasses`, `datetime`). They are already installed. Do not add anything else. If something seems to need another library, stop and ask.
- **Use the project's own Python environment, not the system one.** It already exists at `.venv/` in the project root. Run everything with `.venv/bin/python ...` and `.venv/bin/python -m pytest ...`. Never call plain `python3`, never `pip install` outside the `.venv`, never touch the `.venv` folder itself.
- **Do not build:** a web app, a GUI, a notebook, machine learning, threading, async, plotting styles beyond the defaults, or a plugin system.
- **Reproducible:** the fake data uses a fixed random seed, so every run produces the same files and the tests always see the same data.
- **British spelling** in comments and text output ("analyse", "colour").
- Type hints on function signatures. `if __name__ == "__main__":` guards on runnable scripts.
- Do not modify `.gitignore` except to add the `output/` line described below. Do not modify `requirements.txt`.

## 1. Project layout

The project folder already contains `.venv/`, `.git/`, `.gitignore` and `requirements.txt`. Create the rest:

```
aero-correlation-checker/
  README.md
  make_data.py              # writes the three fake data files
  analyse.py                # the command-line entry point
  correlation/              # the tool's code, one small module per step
    __init__.py             # empty
    physics.py              # constants and the two formulas
    loading.py              # read the CSV files
    checks.py               # find bad data
    compare.py              # line the sources up and measure the gaps
    diagnose.py             # turn a pattern of gaps into a likely cause
    charts.py               # draw the two charts
    storage.py              # save results to a small SQLite database
  tests/
    __init__.py             # empty
    test_physics.py
    test_checks.py
    test_compare.py
    test_diagnose.py
    test_end_to_end.py
  data/                     # created by make_data.py (committed to git)
    tunnel.csv
    cfd.csv
    track.csv
  output/                   # created by analyse.py (not committed)
    coefficients.png
    differences.png
    summary.txt
    results.db
```

Add `output/` to `.gitignore`. The `data/` folder is committed so a reader can see the input without running anything.

## 2. The physics, kept to two formulas

All three sources measure the same two forces on the car:

- **downforce** (newtons): the air pushing the car down onto the track. More downforce means more grip in corners.
- **drag** (newtons): the air holding the car back on the straights.

Raw forces cannot be compared between sources because the wind tunnel uses a 60% scale model at 50 m/s, CFD simulates a full-size car at 60 m/s, and the track car is full size at about 70 m/s. So the tool converts forces into **coefficients**, which do not depend on size or speed:

```
dynamic_pressure q = 0.5 * AIR_DENSITY * speed^2        (pascals)
CL = downforce / (q * ref_area)                         (downforce coefficient)
CD = drag      / (q * ref_area)                         (drag coefficient)
efficiency = CL / CD
```

Constants (in `correlation/physics.py`):

```
AIR_DENSITY   = 1.225   # kg/m3, air at sea level
FULL_CAR_AREA = 1.5     # m2, reference area of the full-size car
MODEL_SCALE   = 0.6     # the tunnel model is 60% size
MODEL_AREA    = FULL_CAR_AREA * MODEL_SCALE ** 2   # = 0.54 m2 (area scales with size squared)
```

Worked example that must hold: downforce 2480.6 N at 50 m/s with area 0.54 m2 gives q = 1531.25 Pa and CL = 3.00.

**Ride height** (mm) is how high the car's floor sits above the ground. Lower ride height gives more downforce, up to a point ("ground effect"). Every row in every file is at one ride height, and ride height is the key the tool uses to line the sources up.

## 3. The data files

All three files have exactly the same columns, in this order:

| column | type | meaning |
|---|---|---|
| `run_id` | int | row number within the file, starting at 1 |
| `ride_height_mm` | int | ride height, one of 20, 25, 30, 35, 40 |
| `speed_ms` | float | air speed in m/s |
| `ref_area_m2` | float | reference area used for the coefficients |
| `downforce_n` | float | downforce in newtons |
| `drag_n` | float | drag in newtons |

One row means:

- `tunnel.csv`: one wind tunnel run of the 60% model at one ride height. Three repeats per ride height, so 15 rows. Small random noise.
- `cfd.csv`: one simulation of the full-size car at one ride height. One row per height, 5 rows. No noise (a simulation gives the same answer every time).
- `track.csv`: one averaged measurement from the real car at one ride height. One row per height, but one height is missing, so 4 rows. Small random noise.

## 4. `make_data.py`: generating the fake data

Writes the three CSV files into `data/` (create the folder if needed). Fixed seed: `numpy.random.default_rng(seed=42)`.

**The "true" car**, used to generate every source:

| ride height mm | true CL | true CD |
|---|---|---|
| 20 | 3.30 | 1.03 |
| 25 | 3.15 | 1.01 |
| 30 | 3.00 | 1.00 |
| 35 | 2.88 | 0.99 |
| 40 | 2.78 | 0.98 |

Force for any row = `q * ref_area * coefficient`, then rounded to 1 decimal place.

**Tunnel** (`speed 50 m/s`, `ref_area 0.54`): 3 repeats per height. Speed for each run is `50 + normal(0, 0.2)`. Each force gets multiplicative noise `1 + normal(0, 0.005)`. Rows ordered by ride height then repeat, run_id 1 to 15.

**CFD** (`speed 60 m/s`, `ref_area 1.5`): one row per height, no noise, run_id 1 to 5.

**Track** (`speed 70 + normal(0, 1.5)` per row, `ref_area 1.5`): one row per height, noise `1 + normal(0, 0.01)` on each force. Then the 35 mm row is deleted entirely (the team never got a clean reading at that height), so run_id 1 to 4.

**Planted faults**, so the tool has something to find. These are the four kinds of thing that go wrong in real correlation work:

1. **Tunnel, bad reading:** run_id 8 (a 30 mm run) has `downforce_n` multiplied by 1.25. The repeatability check must flag it.
2. **CFD, setup mistake:** every CFD `drag_n` is multiplied by 1.06. A constant 6% offset at every height, the signature of a wrong reference value in the simulation setup.
3. **CFD, ground-effect modelling weakness:** CFD `downforce_n` is multiplied by `1 + extra`, where extra is 0.00 at 40 mm, 0.01 at 35, 0.02 at 30, 0.04 at 25, 0.07 at 20. The gap grows as the car gets closer to the ground.
4. **Track, missing data:** the 35 mm row is absent (above), and the 40 mm row has `downforce_n` set to empty (NaN).

Apply fault 3 before fault 2 does not matter; they affect different columns. Print one line per file: `Wrote data/tunnel.csv (15 rows)`.

## 5. Modules

Each module is small, with functions only. Two tiny `dataclass`es are allowed where noted. No other classes.

### `correlation/physics.py`
- The constants above.
- `dynamic_pressure(speed_ms: float) -> float`
- `add_coefficients(df: pd.DataFrame) -> pd.DataFrame`: returns a copy with new columns `cl`, `cd`, `efficiency`, computed row by row from the formulas.
- `average_by_height(df) -> pd.DataFrame`: groups by `ride_height_mm` and returns mean and standard deviation of `cl` and `cd` (columns `cl_mean, cl_std, cd_mean, cd_std`, ride height as a normal column, sorted by height). For sources with one row per height the std is 0 or NaN; treat NaN std as 0.

### `correlation/loading.py`
- `REQUIRED_COLUMNS` list, exactly the six columns in section 3.
- `load_source(path: Path, name: str) -> pd.DataFrame`: reads the CSV, checks every required column is present (raise `ValueError` with a clear message naming the file and the missing column), and adds a `source` column set to `name`.
- `load_all(data_dir: Path) -> dict[str, pd.DataFrame]`: returns `{"tunnel": ..., "cfd": ..., "track": ...}` from the three fixed file names.

### `correlation/checks.py`
- `@dataclass Issue`: `source: str`, `run_id: int`, `kind: str`, `message: str`. `kind` is one of `"missing"`, `"out_of_range"`, `"not_repeatable"`.
- `find_issues(df, name, tolerance=0.03) -> list[Issue]`, running three checks:
  1. **Missing:** any NaN in `downforce_n`, `drag_n`, `speed_ms`, `ref_area_m2` or `ride_height_mm`.
  2. **Out of range:** downforce or drag not strictly positive; speed outside 10 to 120 m/s; ride height outside 5 to 100 mm. Rows already flagged as missing are skipped here.
  3. **Not repeatable:** only meaningful when a ride height has 2 or more rows. Compute `cl` for each row (use `add_coefficients`), then for each ride height compare every row's `cl` to the median `cl` of that height. Flag rows more than `tolerance` (a fraction, 0.03 = 3%) away from the median. Rows flagged by checks 1 or 2 are excluded before computing the median.
- `drop_flagged(df, issues) -> pd.DataFrame`: returns the rows whose `run_id` is not in any issue.

### `correlation/compare.py`
- `compare(reference: pd.DataFrame, other: pd.DataFrame, other_name: str) -> pd.DataFrame`. Both inputs are the output of `average_by_height`. Outer-merge on `ride_height_mm` so a height missing from one side still appears. Output columns: `ride_height_mm, source, cl_ref, cl_other, cl_diff_pct, cd_ref, cd_other, cd_diff_pct, has_data`, sorted by height. `cl_diff_pct = (cl_other - cl_ref) / cl_ref * 100` (a percentage, signed). `has_data` is False where either side is missing; the diff columns are NaN there.
- The tunnel is always the reference. This is a design choice, not a law: the tunnel is the measurement the team trusts most day to day, and the comment in the code should say so.

### `correlation/diagnose.py`
- `TOLERANCE_PCT = 3.0` (percent), `CONSTANT_SPREAD_PCT = 1.0`, `TREND_CORRELATION = -0.8`. Each with a one-line comment.
- `diagnose(diff_pct: pd.Series, ride_height_mm: pd.Series) -> str`. Drop NaN pairs first. Then, in this order:
  1. Fewer than 3 valid points: `"not enough points to judge"`.
  2. All `abs(diff) <= TOLERANCE_PCT`: `"agrees with the tunnel (all within 3%)"`.
  3. Standard deviation of diff < `CONSTANT_SPREAD_PCT` and `abs(mean) > TOLERANCE_PCT`: `"constant offset of about +6.0% at every ride height: check the simulation setup (reference area, speed, air density)"` with the real mean substituted.
  4. Correlation between diff and ride height < `TREND_CORRELATION` and `max(abs(diff)) > TOLERANCE_PCT`: `"gap grows as the car gets closer to the ground: ground-effect region, check floor and underbody modelling"`.
  5. Exactly one point over tolerance: `"one point out at 30 mm: check that run"` with the real height.
  6. Otherwise: `"mixed picture: investigate point by point"`.
- Comment above the function: these are hints that point an engineer where to look first, not conclusions.

### `correlation/charts.py`
- `plot_coefficients(averages: dict[str, pd.DataFrame], out_path: Path)`: one figure, CL on the y axis, ride height on the x axis, one line with markers per source (tunnel, cfd, track), error bars from `cl_std`, legend, axis labels with units, title "Downforce coefficient vs ride height". Save at 150 dpi. Never call `plt.show()`. Close the figure after saving.
- `plot_differences(comparisons: list[pd.DataFrame], tolerance_pct: float, out_path: Path)`: one figure with two subplots side by side, "CL difference vs tunnel (%)" and "CD difference vs tunnel (%)". One line per non-tunnel source. A horizontal shaded band from `-tolerance` to `+tolerance` and a dashed line at 0. Heights with no data are simply gaps in the line. Same saving rules.

### `correlation/storage.py`
- Uses `sqlite3` from the standard library only.
- `save_results(db_path: Path, analysed_at: str, comparisons: list[pd.DataFrame], verdicts: dict[str, str])`: creates two tables if they do not exist and appends rows.
  - `comparisons(analysed_at TEXT, source TEXT, ride_height_mm INTEGER, cl_ref REAL, cl_other REAL, cl_diff_pct REAL, cd_ref REAL, cd_other REAL, cd_diff_pct REAL)`
  - `verdicts(analysed_at TEXT, source TEXT, quantity TEXT, verdict TEXT)` where quantity is `"cl"` or `"cd"`
- `history(db_path: Path) -> list[tuple]`: returns `analysed_at, source, quantity, verdict` for every past run, newest first. Printed by `analyse.py` so repeated runs build a visible history.

### `analyse.py`
Command-line entry point using `argparse`:

```
.venv/bin/python analyse.py [--data data] [--out output] [--tolerance 3.0]
```

Steps, each printed as a short line so the user can follow along:

1. Load the three sources (`loading.load_all`).
2. Run `checks.find_issues` on each. Print each issue on one line: `tunnel run 8: not repeatable, CL 25.1% from the median at 30 mm`. Drop flagged rows.
3. Add coefficients and average by height for each source.
4. Compare cfd and track against the tunnel.
5. Diagnose CL and CD for each comparison.
6. Draw the two charts into `--out`.
7. Save to `output/results.db` and print the history.
8. Write `output/summary.txt` and print the same text to the console.

`summary.txt` format (values are illustrative; the real numbers come from the data):

```
Aero correlation check  2026-09-27 15:42

Data quality
  tunnel: 15 rows, 1 dropped (run 8: not repeatable, CL 25.1% from median at 30 mm)
  cfd:    5 rows, 0 dropped
  track:  4 rows, 1 dropped (run 4: missing downforce_n)   [no data at 35 mm]

CFD vs tunnel
  ride height   CL diff   CD diff
  20 mm         +7.1%     +6.0%
  25 mm         +4.0%     +6.1%
  30 mm         +2.0%     +5.9%
  35 mm         +1.0%     +6.0%
  40 mm         +0.1%     +6.0%
  CL: gap grows as the car gets closer to the ground: ground-effect region, check floor and underbody modelling
  CD: constant offset of about +6.0% at every ride height: check the simulation setup (reference area, speed, air density)

Track vs tunnel
  ride height   CL diff   CD diff
  20 mm         +0.8%     -0.4%
  25 mm         -1.1%     +0.6%
  30 mm         +0.3%     -0.9%
  35 mm         no data   no data
  40 mm         no data   no data
  CL: agrees with the tunnel (all within 3%)
  CD: agrees with the tunnel (all within 3%)

Charts: output/coefficients.png, output/differences.png
```

Exit code 0 on success. If a data file is missing, print a one-line error naming the file and exit with code 1.

## 6. Tests (`pytest`)

Run with `.venv/bin/python -m pytest -q`. All tests must pass. Keep each test short, with a comment saying what it proves.

- `test_physics.py`: the worked example (2480.6 N, 50 m/s, 0.54 m2 gives CL 3.00 within 0.01); efficiency = cl / cd; `average_by_height` returns one row per height with the right mean.
- `test_checks.py`: a NaN downforce is reported as `missing`; a negative drag as `out_of_range`; in a group of three runs where one CL is 25% high, exactly that run is `not_repeatable`; `drop_flagged` removes exactly the flagged rows.
- `test_compare.py`: two tiny frames with heights 20, 30, 40 on the reference and 20, 30 on the other: diff percentages are correct to 0.01, the 40 mm row exists with `has_data` False.
- `test_diagnose.py`: five hand-made series, one per verdict: agrees; constant offset; growing gap; single outlier; not enough points.
- `test_end_to_end.py`: in a temporary directory, run `make_data.main()` then the main function of `analyse.py` (structure `analyse.py` so its steps are in a `run(data_dir, out_dir, tolerance)` function that the test can call). Assert the four output files exist and that `summary.txt` contains "constant offset", "closer to the ground" and "agrees with the tunnel".

## 7. README.md

Short, plain English, in this order:

1. One paragraph: what the tool does and why raw forces cannot be compared directly (size and speed), so it converts to coefficients.
2. How to run, three commands: activate the environment, `make_data.py`, `analyse.py`. Then how to run the tests.
3. What the input files are (the table from section 3, and one line on what a row means for each source).
4. What the outputs are, with the two chart images embedded.
5. The four planted faults and which check catches each one.
6. "What I would add next": counting runs against the aerodynamic testing limit, and reading real telemetry instead of a CSV.
7. One line: all data is synthetic; this is a learning project.

## 8. Definition of done

- `.venv/bin/python make_data.py` writes three files with 15, 5 and 4 rows.
- `.venv/bin/python analyse.py` runs in under 10 seconds, prints the summary, and produces the four files in `output/`.
- The tunnel run 8 is flagged as not repeatable; the track 40 mm row is flagged as missing; the summary shows "no data" for track at 35 mm and 40 mm.
- CFD CL verdict contains "closer to the ground"; CFD CD verdict contains "constant offset"; both track verdicts contain "agrees".
- `.venv/bin/python -m pytest -q` passes.
- Every file has a module docstring, every function a docstring, and no file is longer than about 90 lines.
- No library outside the allowed list is imported anywhere.
- `git status` shows `output/` ignored and `data/` included. Make one commit per completed step with a clear message.

## 9. When the build is finished

Stop and explain each file to the author in plain English, one file at a time, in the order: physics, loading, checks, compare, diagnose, charts, storage, analyse, make_data, tests. Wait for questions after each file before moving to the next.

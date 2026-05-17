"""Clean Florida crash data and load it into DuckDB.

Reads every ``crashes_*.json`` file in ``data/raw/``, applies the
12-step cleaning plan documented at the bottom of
``notebooks/01_eda.ipynb``, and writes the cleaned frame to a local
``crashes.duckdb`` file as a single table called ``crashes``.

The mapping from EDA-plan step number to code is preserved in the
step comments below — if anything here surprises you, the "why" lives
in the notebook's "Cleaning plan" markdown cell, not here.

Step 6 (Step 6 in ``PROJECT_PLAN.md``) will extend this script to also
run the ``sql/*.sql`` aggregations and export per-view CSVs to
``data/processed/``. For now, ``clean.py`` stops after the DuckDB load.
"""

import json
import sys
from pathlib import Path

import duckdb
import pandas as pd

# --- Paths ----------------------------------------------------------

PROJECT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT / "data" / "raw"
SQL_DIR = PROJECT / "sql"
PROCESSED_DIR = PROJECT / "data" / "processed"
DB_PATH = PROJECT / "crashes.duckdb"

# --- Constants derived from EDA -------------------------------------

# Florida bounding box (lat/lon). EDA showed all valid geocodes already
# fall inside this box, so the bbox doubles as a sanity filter against
# corrupted future pulls rather than a tight constraint on this one.
FL_LAT_RANGE = (24.0, 31.5)
FL_LON_RANGE = (-88.0, -79.5)

# INJSEVER -> human label. See docs/api_notes.md for the full code map.
SEVERITY_LABELS = {
    "4": "Serious injury",
    "5": "Fatal",
}

# Year to drop entirely: EDA found only 1,763 rows in 2019 (~10% of a
# normal year), so the dashboard will be framed as 2011–2018.
DROP_YEAR_THRESHOLD = 2019  # rows with CALENDAR_YEAR >= this are dropped


# --- Pipeline -------------------------------------------------------

def load_raw(raw_dir: Path) -> pd.DataFrame:
    """Concatenate every ``crashes_*.json`` file in ``raw_dir``.

    Step 1 of the cleaning plan. Reading all files (not just the
    latest) means re-running ``ingest.py`` with a wider range, or
    later swapping in a second source, just works — the dedupe
    step that follows collapses any cross-pull overlap by ``XID``.
    """
    paths = sorted(raw_dir.glob("crashes_*.json"))
    if not paths:
        raise FileNotFoundError(f"no crashes_*.json files found in {raw_dir}")

    frames = []
    for p in paths:
        with p.open() as f:
            blob = json.load(f)
        frames.append(pd.DataFrame([feat["attributes"] for feat in blob["features"]]))
        print(f"  loaded {p.name}: {len(frames[-1]):,} rows")

    return pd.concat(frames, ignore_index=True)


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Apply cleaning steps 2-11 from the EDA plan. Returns (frame, counts)."""
    counts: dict[str, int] = {"initial": len(df)}

    # Step 2 — dedupe on XID. Every duplicate pair is row-identical
    # (verified in EDA), so plain drop_duplicates is sufficient.
    df = df.drop_duplicates(subset="XID").reset_index(drop=True)
    counts["after_dedupe"] = len(df)

    # Step 3 — parse CRASH_DATE (epoch milliseconds -> datetime).
    df["crash_dt"] = pd.to_datetime(df["CRASH_DATE"], unit="ms")

    # Step 4 — split the HHMM CRASH_TIME string into numeric hour/min.
    # errors='coerce' silently turns malformed values into NaN; EDA
    # confirmed 0 malformed in the current pull, but keep the guard.
    df["hour"] = pd.to_numeric(df["CRASH_TIME"].str[:2], errors="coerce")
    df["minute"] = pd.to_numeric(df["CRASH_TIME"].str[2:], errors="coerce")

    # Step 5 — flag '0000' rows as ambiguous. EDA showed hour=0 volume
    # is 1.92x its neighbors, meaning '0000' is a mix of genuine
    # midnight crashes and "time unknown" sentinels. We don't impute
    # or drop — we let the dashboard decide whether to filter them.
    df["hour_is_ambiguous"] = df["CRASH_TIME"].eq("0000")

    # Step 6 — derive time dimensions used by the dashboard sheets.
    df["year"] = df["crash_dt"].dt.year
    df["month"] = df["crash_dt"].dt.month
    df["day_of_week"] = df["crash_dt"].dt.day_name()
    df["is_weekend"] = df["day_of_week"].isin(["Saturday", "Sunday"])

    # Step 7 — normalize COUNTY_TXT for display.
    # pandas .str.title() splits on hyphens, so 'MIAMI-DADE' -> 'Miami-Dade'.
    df["county"] = df["COUNTY_TXT"].str.strip().str.title()

    # Step 8 — human-readable severity label.
    df["severity"] = df["INJSEVER"].map(SEVERITY_LABELS)

    # Step 9 — geometry filter. Drop rows with missing/zero coords
    # and (defensively) anything outside the FL bbox. EDA showed
    # only ~16 rows fail this in the current pull.
    valid_geo = (
        df["SAFETYLAT"].notna()
        & df["SAFETYLON"].notna()
        & df["SAFETYLAT"].ne(0)
        & df["SAFETYLON"].ne(0)
        & df["SAFETYLAT"].between(*FL_LAT_RANGE)
        & df["SAFETYLON"].between(*FL_LON_RANGE)
    )
    df = df[valid_geo].reset_index(drop=True)
    counts["after_geo"] = len(df)

    # Step 10 — drop 2019 (partial year).
    df = df[df["CALENDAR_YEAR"] < DROP_YEAR_THRESHOLD].reset_index(drop=True)
    counts["after_2019_drop"] = len(df)

    # Step 11 — sparse fields stay nullable. SPEED_LIMIT (41.7% null)
    # and FUNCLASS (36.1% null) are kept as-is, no imputation.

    # Project to the final dashboard-friendly schema with snake_case
    # column names. This is the contract Step 6 SQL files write against.
    out = df[[
        "XID",
        "year", "month", "crash_dt", "hour", "minute", "hour_is_ambiguous",
        "day_of_week", "is_weekend",
        "county", "DHSMV_CTY_CD", "SAFETYLAT", "SAFETYLON",
        "severity", "INJSEVER", "SPEED_LIMIT", "IN_TOWN_FLAG", "FUNCLASS",
    ]].rename(columns={
        "XID": "crash_id",
        "DHSMV_CTY_CD": "dhsmv_city_code",
        "SAFETYLAT": "lat",
        "SAFETYLON": "lon",
        "INJSEVER": "severity_code",
        "SPEED_LIMIT": "speed_limit",
        "IN_TOWN_FLAG": "in_town_flag",
        "FUNCLASS": "func_class",
    })

    counts["final"] = len(out)
    return out, counts


def write_duckdb(df: pd.DataFrame, db_path: Path) -> None:
    """Step 12 — write the cleaned frame to DuckDB as table ``crashes``."""
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    # DuckDB's Python integration auto-registers `df` as a view; no
    # explicit register call needed.
    con.execute("CREATE TABLE crashes AS SELECT * FROM df")
    con.close()


def export_aggregations(db_path: Path, sql_dir: Path, out_dir: Path) -> list[tuple[str, int]]:
    """Run every ``sql/*.sql`` file against the DuckDB table and write each
    result to ``data/processed/<basename>.csv`` (Step 6 in PROJECT_PLAN.md).

    Returns a list of (csv_name, row_count) for the summary print.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    sql_files = sorted(sql_dir.glob("*.sql"))
    if not sql_files:
        raise FileNotFoundError(f"no *.sql files found in {sql_dir}")

    con = duckdb.connect(str(db_path), read_only=True)
    results: list[tuple[str, int]] = []
    try:
        for sql_path in sql_files:
            query = sql_path.read_text()
            # Each SQL file is a single SELECT; .df() materializes it
            # into pandas so we can write CSV with consistent quoting.
            result = con.execute(query).df()
            csv_path = out_dir / f"{sql_path.stem}.csv"
            result.to_csv(csv_path, index=False)
            results.append((csv_path.name, len(result)))
    finally:
        con.close()
    return results


def main() -> int:
    print(f"Reading from {RAW_DIR.relative_to(PROJECT)}/ ...")
    df_raw = load_raw(RAW_DIR)
    print(f"  total raw rows: {len(df_raw):,}")

    df_clean, counts = clean(df_raw)

    initial = counts["initial"]
    print("\n--- cleaning step row counts ---")
    print(f"  initial            : {counts['initial']:>9,}")
    print(f"  after XID dedupe   : {counts['after_dedupe']:>9,}  "
          f"(-{initial - counts['after_dedupe']:,})")
    print(f"  after geo filter   : {counts['after_geo']:>9,}  "
          f"(-{counts['after_dedupe'] - counts['after_geo']:,})")
    print(f"  after 2019 drop    : {counts['after_2019_drop']:>9,}  "
          f"(-{counts['after_geo'] - counts['after_2019_drop']:,})")
    print(f"  final              : {counts['final']:>9,}  "
          f"({100 * counts['final'] / initial:.1f}% of raw)")

    print(f"\nWriting DuckDB -> {DB_PATH.relative_to(PROJECT)}")
    write_duckdb(df_clean, DB_PATH)

    # Verify the saved table.
    con = duckdb.connect(str(DB_PATH))
    n = con.execute("SELECT COUNT(*) FROM crashes").fetchone()[0]
    n_fatal = con.execute(
        "SELECT COUNT(*) FROM crashes WHERE severity = 'Fatal'"
    ).fetchone()[0]
    n_serious = con.execute(
        "SELECT COUNT(*) FROM crashes WHERE severity = 'Serious injury'"
    ).fetchone()[0]
    cols = con.execute("PRAGMA table_info(crashes)").fetchall()
    con.close()

    print(f"  table 'crashes': {n:,} rows, {len(cols)} columns")
    print(f"    - severity=Fatal          : {n_fatal:,}")
    print(f"    - severity=Serious injury : {n_serious:,}")

    # Step 6 — run sql/*.sql aggregations and export per-view CSVs.
    print(f"\nRunning aggregations from {SQL_DIR.relative_to(PROJECT)}/ "
          f"-> {PROCESSED_DIR.relative_to(PROJECT)}/")
    exports = export_aggregations(DB_PATH, SQL_DIR, PROCESSED_DIR)
    for name, rows in exports:
        print(f"  {name:<40} {rows:>7,} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())

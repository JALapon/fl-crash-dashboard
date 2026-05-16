# Florida Crash Dashboard

> One-line hook: TODO — e.g. "Where and when are Florida traffic crashes most likely, and what can a city do about it?"

## The question this project answers

TODO — state the analytical question (e.g. *Which Florida counties saw the
largest year-over-year change in crash severity, and what hour-of-day /
day-of-week patterns drive that change?*).

## Data source

Florida Department of Transportation (FDOT) / Signal Four Analytics public
crash data API.

TODO — link to the specific endpoint(s), document the date range pulled,
and note any access caveats (rate limits, registration, etc.).

## Pipeline

```
  FDOT / Signal Four Analytics API
                │
                ▼
       src/ingest.py  ──►  data/raw/      (immutable JSON / CSV pulls)
                                │
                                ▼
                       src/clean.py
                       (pandas: clean, type, dedupe)
                                │
                                ▼
                       DuckDB (*.duckdb)
                       sql/ aggregation queries
                                │
                                ▼
                       data/processed/    (per-view CSVs)
                                │
                                ▼
                       Tableau Public dashboard
```

## Key findings

TODO — fill in once analysis is complete (3–5 bullet points, each tied to a
chart in the dashboard).

## Live Tableau dashboard

TODO — Tableau Public URL.

## How to reproduce

```bash
# 1. Clone
git clone <repo-url> fl-crash-dashboard
cd fl-crash-dashboard

# 2. Create and activate the virtual environment
python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Pull raw crash data → data/raw/
python src/ingest.py

# 5. Clean, load into DuckDB, export aggregated CSVs → data/processed/
python src/clean.py

# 6. Open the dashboard
# Tableau Public link: TODO
```

## Tech stack

Python · pandas · DuckDB · SQL · Tableau Public

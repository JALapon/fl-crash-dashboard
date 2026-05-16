# Florida Crash Dashboard

> Where and when do Florida's most dangerous crashes happen — and what does that pattern reveal about which counties, times, and conditions warrant attention?

## The question this project answers

**Primary question:** *Where and when do Florida's **fatal and serious-injury**
crashes concentrate?*

By filtering to fatal and serious-injury crashes (instead of all crashes),
the dashboard surfaces places that are genuinely dangerous rather than
just busy — a total-crash map of Florida looks essentially like a map of
where people live, which isn't useful.

**Supporting sub-questions:**
- *Where:* Which counties, cities, and road segments hold the largest
  share of fatal/serious-injury crashes?
- *When:* What are the dominant time-of-day, day-of-week, and seasonal
  patterns for those crashes?
- *Trend:* How has the where/when pattern shifted year over year
  (subject to the date range available from the API)?

## Data source

**FDOT State Safety Office** — public ArcGIS REST FeatureServer:
[`https://gis.fdot.gov/arcgis/rest/services/Crashes_All/FeatureServer`](https://gis.fdot.gov/arcgis/rest/services/Crashes_All/FeatureServer)

- **Coverage:** 2011 – 2019 (~3.3M total crashes statewide).
- **Analytical slice:** fatal + serious-injury crashes only
  (`INJSEVER IN ('4','5')`), ≈ **161,000 records** — the dashboard is
  scoped to genuinely dangerous outcomes, not all fender-benders.
- **Access:** open, no API key, no registration required.
- **Why not Signal Four Analytics:** the recent end of FL crash data
  lives there, but S4A is gated behind agency accounts and not
  accessible for a public portfolio project.

See [`docs/api_notes.md`](docs/api_notes.md) for the full layer / field
breakdown, severity-code mapping, pagination scheme, and a working
`curl` example.

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

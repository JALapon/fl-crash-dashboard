# Project Plan — Florida Crash Dashboard

A step-by-step runbook for taking this project from empty scaffold to a
published Tableau Public dashboard + LinkedIn writeup. Tackle one step at
a time; each section lists what the step covers and what "done" looks
like.

---

## Step 1 — Pin down the analytical question

**Goal:** decide the single, sharp question the dashboard answers. Without
this, every later decision (which fields to pull, which aggregations to
write, which charts to build) is unanchored.

**What it involves:**
- Write 2–3 candidate questions. Examples:
  - *Where and when are fatal/serious-injury crashes in Florida most
    concentrated, and has the pattern shifted in the last 5 years?*
  - *Which Florida counties have the worst rush-hour crash rates per
    capita, and which factors (weather, road type, time of day)
    correlate with severity?*
- Pick **one** primary question + at most two supporting sub-questions.
- Update the **"The question this project answers"** section of `README.md`.

**Done when:** `README.md` has a real question (not TODO), and you can
describe in one sentence why a hiring manager would care.

---

## Step 2 — Investigate the FDOT / Signal Four Analytics API

**Goal:** understand exactly what data is available, how to pull it, and
what the response looks like — *before* writing any pull code.

**What it involves:**
- Find the public endpoint(s) for crash records.
- Check whether registration / an API key is required. If so, register
  and put the key in a local `.env` (already gitignored).
- Document:
  - base URL and example request
  - query parameters (date range, county, severity filter, etc.)
  - pagination scheme (offset/limit, cursor, page tokens)
  - rate limits
  - response shape (JSON keys, CSV columns)
- Identify the **minimum field set** you actually need for the question
  from Step 1 (location, datetime, severity, county, road type, etc.).
  Pulling fewer fields = smaller raw files, faster iteration.

**Done when:** you can paste a working `curl` example into the terminal
and get back a small page of records.

---

## Step 3 — Implement `src/ingest.py`

**Goal:** a reproducible script that pulls raw crash data and lands it,
untouched, in `data/raw/`.

**Features this step adds:**
- Read API key (if any) from `.env` via `python-dotenv`.
- Accept simple CLI args or constants for date range and any filters
  (start date, end date, counties). Keep it simple — no `argparse`
  config-system gymnastics.
- Hit the API with `requests`, with a `tqdm` progress bar across pages.
- Paginate until exhausted, accumulating records in memory (or streaming
  to disk if the result is huge).
- Save the raw response **untouched** to
  `data/raw/crashes_<YYYYMMDD>_<from>_<to>.json` (or `.csv`).
- Print a one-line summary at the end: how many records pulled, how
  many pages, total bytes on disk.
- Fail loudly on HTTP errors — no silent retries that mask real problems.

**Done when:** `python src/ingest.py` produces a fresh, dated file in
`data/raw/` and prints a sensible summary line.

---

## Step 4 — Exploratory data analysis in `notebooks/01_eda.ipynb`

**Goal:** learn the data so the cleaning script isn't guessing.

**What it involves:**
- Load the raw file from `data/raw/` with `pandas.read_json` /
  `read_csv`.
- Check: row count, column list, dtypes, null counts per column,
  duplicate `crash_id`s, date range coverage.
- Inspect categorical fields: how many distinct counties, severity
  codes, weather codes? Any unexpected values (`"Unknown"`, `-1`,
  whitespace)?
- Plot quick distributions with `matplotlib` — crashes per year, per
  hour, per day of week — to sanity-check coverage.
- Write a short markdown cell at the top of the notebook listing the
  cleaning decisions you'll make in Step 5 (which columns to drop, how
  to handle nulls, which categoricals to normalize).

**Done when:** the notebook ends with a clear, written-down list of
cleaning steps + a draft list of the aggregations the dashboard needs.

---

## Step 5 — Implement `src/clean.py` (cleaning portion)

**Goal:** turn raw pulls into one clean, typed, deduped DataFrame
loaded into DuckDB.

**Features this step adds:**
- Read **all** files in `data/raw/` (so re-running ingest with a wider
  date range "just works").
- Concatenate into a single DataFrame.
- Cast types: datetimes via `pd.to_datetime`, numerics, categoricals.
- Drop / impute nulls per Step 4's decisions.
- Dedupe on `crash_id` (keep the latest record if there are revisions).
- Standardize categoricals: trim whitespace, normalize case, map raw
  severity codes to readable labels.
- Derive useful columns: `year`, `month`, `hour`, `day_of_week`, plus
  any flags the dashboard needs (e.g., `is_rush_hour`, `is_fatal`).
- Load the final DataFrame into a local DuckDB file (e.g.,
  `crashes.duckdb`, already gitignored) as a table named `crashes`.
- Print a summary: row count in, row count out, % dropped, table name.

**Done when:** running `python src/clean.py` produces a `.duckdb` file
with a `crashes` table whose row count and dtypes match expectations.

---

## Step 6 — Write SQL aggregations in `sql/` + wire them into `clean.py`

**Goal:** one CSV per dashboard view, generated from SQL (not pandas) so
the aggregation logic is reviewable on its own.

**Features this step adds:**
- One `.sql` file per dashboard view, named after the question it
  answers. Suggested starting set (adjust to your Step 1 question):
  - `sql/crashes_by_county_year.sql`
  - `sql/crashes_by_hour_dow.sql`
  - `sql/severity_breakdown_by_county.sql`
  - `sql/top10_intersections.sql` (if location-detailed)
- Each `.sql` is a single `SELECT` against `crashes`. Comment the
  intent at the top — these are the artifacts an interviewer will read.
- In `clean.py`, after the DuckDB load:
  - Glob `sql/*.sql`
  - For each file, run the query and `COPY` / write the result to
    `data/processed/<sql_basename>.csv` with a header row.
- Verify each CSV opens cleanly in a text editor and has the expected
  shape.

**Done when:** `data/processed/` contains one CSV per `.sql` file and
they all have non-zero rows.

---

## Step 7 — Build the Tableau Public dashboard

**Goal:** turn the CSVs into a polished, public-facing dashboard.

**What it involves:**
- Install **Tableau Public Desktop** (free).
- Connect to the CSVs in `data/processed/` (Tableau Public can only
  read local files, not databases — that's why we exported CSVs).
- Build one **sheet per question/sub-question** from Step 1. Keep each
  sheet focused — one chart, one idea.
- Compose sheets into a single **dashboard** with:
  - A clear title that restates the question.
  - 3–5 sheets max — resist the urge to add everything.
  - Filters where they help (year, county, severity).
  - Tooltips that explain numbers, not just repeat them.
- Publish to Tableau Public (`Server → Tableau Public → Save to Tableau
  Public`).

**Done when:** you have a public URL anyone can open without a Tableau
account.

---

## Step 8 — Finish the README

**Goal:** turn `README.md` from a scaffold into a finished portfolio
artifact.

**What it involves:**
- Fill in **Key findings** with 3–5 bullets, each tied to a sheet on
  the dashboard. Lead with the number, then the interpretation.
  - Bad: *"Hour-of-day was an interesting variable."*
  - Good: *"42% of fatal crashes occur between 6pm–midnight, despite
    that window holding only 25% of total crash volume."*
- Paste the Tableau Public URL into the **Live Tableau dashboard**
  section.
- Add a screenshot or short GIF of the dashboard at the top of the
  README — most reviewers scroll for 8 seconds before deciding to read.
  Commit the image to the repo (e.g., `docs/dashboard.png`).

**Done when:** a friend who has never seen the project can read the
README in 2 minutes and answer: what's the question, what's the
answer, and how do I run it.

---

## Step 9 — LinkedIn writeup

**Goal:** drive traffic to the GitHub repo and the dashboard.

**What it involves:**
- Lead with the question and a single surprising finding.
- 3–4 short paragraphs, *not* a bulleted résumé blob:
  1. What you set out to learn and why
  2. How you built it (Python → pandas → DuckDB → Tableau, ~1 line)
  3. The 2–3 most interesting findings, with concrete numbers
  4. Links: GitHub repo + Tableau Public dashboard
- Attach the dashboard screenshot.
- Tag it `#dataanalytics #tableau #python #duckdb` (no more than 4–5).

**Done when:** posted, and the GitHub repo and Tableau dashboard both
have inbound traffic from the post.

---

## Optional polish (only after Steps 1–9 are done)

These add credibility but aren't blockers. Do them only if you have
time before submitting applications.

- **`Makefile` / `run.sh`:** one command (`make all`) that runs ingest
  then clean. Shows you think about reproducibility.
- **Data dictionary** (`docs/data_dictionary.md`): one row per column
  in the cleaned table, with type and definition. Interviewers love
  this.
- **Tests:** a couple of `pytest` cases asserting row counts / dtype
  invariants on a tiny fixture file. Demonstrates you can write a test
  even on an analysis project.
- **`v1.0` git tag** on the commit that matches the published
  dashboard, so the repo state and dashboard state are pinned together.

---

## Step-completion log

Tick these off as you go so we both know where we are.

- [x] Step 1 — Question pinned in README
- [x] Step 2 — API documented (curl example works)
- [x] Step 3 — `ingest.py` produces raw files
- [x] Step 4 — EDA notebook + cleaning plan written
- [x] Step 5 — `clean.py` loads cleaned data into DuckDB
- [x] Step 6 — SQL aggregations exported as CSVs in `data/processed/`
- [ ] Step 7 — Tableau Public dashboard published
- [ ] Step 8 — README finalized (findings, link, screenshot)
- [ ] Step 9 — LinkedIn post live

"""Clean and aggregate Florida crash data for the Tableau dashboard.

Reads raw pulls from ``data/raw/``, cleans them with pandas (types,
nulls, geometry, dedupe), loads the cleaned frame into a local DuckDB
file, runs the aggregation queries in ``sql/`` against it, and writes
the resulting per-view CSVs to ``data/processed/`` for Tableau Public.

TODO: implement read/clean/load/aggregate/export steps.
"""

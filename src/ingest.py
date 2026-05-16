"""Ingest Florida crash data from the FDOT / Signal Four Analytics public API.

This script pulls raw crash records and writes them, untouched, to
``data/raw/`` (as JSON and/or CSV). Keeping the raw pulls immutable means
``clean.py`` can be re-run against the same snapshot without re-hitting
the API, and makes the pipeline reproducible.

TODO: implement API request, pagination, and on-disk save.
"""

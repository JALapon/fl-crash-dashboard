"""Ingest Florida crash data from the FDOT public ArcGIS REST FeatureServer.

Pulls fatal + serious-injury crashes (``INJSEVER IN ('4','5')``) for
2011-2019 from the FDOT State Safety Office's public Crashes_All layer,
and writes the raw response to ``data/raw/crashes_<YYYYMMDD>_2011_2019.json``.

The pulled file is treated as immutable: ``clean.py`` reads from it but
nothing in this project rewrites it. Re-running this script always
creates a new dated file rather than overwriting an old one.

See ``docs/api_notes.md`` for the full source documentation
(layers, field schema, severity-code mapping, pagination scheme).
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import requests
from tqdm import tqdm

# --- Source configuration (see docs/api_notes.md) ---------------------

# FDOT State Safety Office, public ArcGIS REST FeatureServer, layer 0
# ("All Crashes"). No auth required.
QUERY_URL = (
    "https://gis.fdot.gov/arcgis/rest/services/"
    "Crashes_All/FeatureServer/0/query"
)

# Server-side severity filter: only fatal (INJSEVER='5') and
# incapacitating / serious-injury (INJSEVER='4') crashes. This is the
# analytical slice the dashboard scopes to.
WHERE_CLAUSE = "INJSEVER IN ('4','5')"

# Slim field shortlist used by clean.py. Pulled in the order they're
# used downstream (id -> when -> where -> severity -> context).
OUT_FIELDS = ",".join([
    "XID",              # unique crash id (dedupe key)
    "CALENDAR_YEAR",
    "CRASH_DATE",
    "CRASH_TIME",
    "WEEKDAY_TXT",
    "COUNTY_TXT",
    "DHSMV_CTY_CD",
    "SAFETYLAT",        # WGS84 lat, attribute (not geometry)
    "SAFETYLON",        # WGS84 lon, attribute (not geometry)
    "INJSEVER",
    "SPEED_LIMIT",
    "IN_TOWN_FLAG",
    "FUNCLASS",
])

# Server caps a single response at 1000 rows; this matches that cap.
PAGE_SIZE = 1000

# Year range hard-coded into the output filename. The FDOT public feed
# only exposes 2011-2019 — see docs/api_notes.md "Coverage".
YEAR_RANGE = "2011_2019"

# Network timeouts. Generous because some pages run slow under load,
# but bounded so a stuck request fails loudly rather than hanging.
COUNT_TIMEOUT_S = 30
PAGE_TIMEOUT_S = 120


def get_total_count(session: requests.Session) -> int:
    """Ask the server how many rows our WHERE matches, for the progress bar."""
    r = session.get(
        QUERY_URL,
        params={
            "where": WHERE_CLAUSE,
            "returnCountOnly": "true",
            "f": "json",
        },
        timeout=COUNT_TIMEOUT_S,
    )
    r.raise_for_status()
    payload = r.json()
    if "error" in payload:
        raise RuntimeError(f"count query returned API error: {payload['error']}")
    return int(payload["count"])


def fetch_page(session: requests.Session, offset: int) -> dict:
    """Fetch a single page of features starting at ``offset``.

    Ordering by ``XID`` is important: ArcGIS REST pagination is only
    stable when an explicit order is set, otherwise rows can shift
    between calls and you get duplicates or gaps.
    """
    r = session.get(
        QUERY_URL,
        params={
            "where": WHERE_CLAUSE,
            "outFields": OUT_FIELDS,
            "returnGeometry": "false",      # SAFETYLAT/LON are in attributes
            "orderByFields": "XID",         # stable pagination
            "resultOffset": offset,
            "resultRecordCount": PAGE_SIZE,
            "f": "json",
        },
        timeout=PAGE_TIMEOUT_S,
    )
    r.raise_for_status()
    payload = r.json()
    if "error" in payload:
        raise RuntimeError(
            f"API error at offset {offset}: {payload['error']}"
        )
    return payload


def main() -> int:
    out_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    total = get_total_count(session)

    metadata: dict | None = None
    features: list[dict] = []
    n_pages = 0

    with tqdm(total=total, unit="rec", desc="Pulling FDOT crashes") as pbar:
        offset = 0
        while offset < total:
            page = fetch_page(session, offset)

            # Keep the response metadata from the first page (field
            # schema, spatial reference, etc.) so the saved file is
            # self-describing without us inventing a wrapper format.
            if metadata is None:
                metadata = {k: v for k, v in page.items() if k != "features"}

            page_features = page.get("features", [])
            if not page_features:
                # Server returned an empty page before we expected the
                # end. Bail loudly rather than silently truncating.
                raise RuntimeError(
                    f"empty page at offset {offset} but expected more rows "
                    f"(have {len(features)}/{total})"
                )

            features.extend(page_features)
            n_pages += 1
            pbar.update(len(page_features))
            offset += PAGE_SIZE

    pull_date = datetime.now().strftime("%Y%m%d")
    out_path = out_dir / f"crashes_{pull_date}_{YEAR_RANGE}.json"

    # Atomic write: dump to .tmp then rename, so a crash mid-write
    # can't leave a half-valid JSON file in data/raw/.
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    with tmp_path.open("w") as f:
        json.dump({"metadata": metadata, "features": features}, f)
    tmp_path.replace(out_path)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(
        f"\nPulled {len(features):,} records across {n_pages} pages "
        f"-> {out_path.name} ({size_mb:.1f} MB)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

# FDOT Crash Data API — Notes

Working notes from Step 2. The cheat sheet `src/ingest.py` (Step 3) is
built from.

## Source

**FDOT State Safety Office, public ArcGIS REST FeatureServer**

```
https://gis.fdot.gov/arcgis/rest/services/Crashes_All/FeatureServer
```

- **No authentication.** No key, no signup, no rate-limit headers
  encountered in testing.
- Service description: *"Map & Feature service of statewide crash data
  from the FDOT State Safety Office. This data is downloaded each week
  from DB2."* (Note: the historic dataset is what's exposed publicly —
  see *Coverage* below.)
- Contact listed on the service: Daniel Teaf, 850-410-5468.

## Coverage

- **Years available: 2011 – 2019.** Confirmed by
  `MIN(CALENDAR_YEAR)` / `MAX(CALENDAR_YEAR)` over Layer 0.
- **Total records (Layer 0 — All Crashes): 3,332,000.**
- The recent end of FL crash data lives in **Signal Four Analytics**,
  which is gated behind agency accounts and not usable for this project.

## Layers we care about

| Layer ID | Name | Row count | Relevance |
|---:|---|---:|---|
| 0 | All Crashes | 3,332,000 | Full table — use this with our own severity filter |
| 3 | Fatalities | 22,690 | Pre-filtered to `INJSEVER='5'` |
| 4 | Injuries and Fatalities | 1,336,622 | Includes minor injuries too — too broad for our question |

We use **Layer 0** with a server-side `INJSEVER IN ('4','5')` filter to
get exactly fatal + serious-injury crashes.

The full layer list (for reference) also includes pedestrian, bicyclist,
motorcycle, work-zone, dark-conditions, wet-weather, aggressive-driving,
red-light, speeding, alcohol/drug, and seat-belt-not-used layers. We
don't use them here but they could power follow-up dashboards.

## Severity codes (`INJSEVER`)

Resolved by grouping Layer 0 by `INJSEVER` and counting, then
cross-checking against Layer 3 ("Fatalities") which matched code `'5'`
exactly.

| `INJSEVER` | Meaning (FL KABCO) | Count | In our filter? |
|---:|---|---:|:---:|
| `'1'` | No injury / property damage only (O) | 1,994,031 | — |
| `'2'` | Possible injury (C) | 691,454 | — |
| `'3'` | Non-incapacitating injury (B) | 419,058 | — |
| `'4'` | **Incapacitating / serious injury (A)** | **138,467** | ✓ |
| `'5'` | **Fatal (K)** | **22,690** | ✓ |
| `'6'` | Non-traffic fatality | 1,347 | — (medical event, not crash impact) |
| `'0'` | Unknown / missing | 64,953 | — |

**Total in our filter: 161,157 crashes over 2011–2019.**

## Pagination

Standard ArcGIS REST:

- Server caps each response at **1,000 records** (`maxRecordCount`).
- Page using `resultOffset` and `resultRecordCount`.
- Layer's `advancedQueryCapabilities.supportsPagination = true`.

Loop pattern (pseudocode for Step 3):

```python
offset = 0
while True:
    r = requests.get(QUERY_URL, params={
        "where": "INJSEVER IN ('4','5')",
        "outFields": "*",
        "outSR": 4326,                  # WGS84 lat/lon, not UTM
        "resultOffset": offset,
        "resultRecordCount": 1000,
        "f": "json",
    })
    features = r.json()["features"]
    if not features:
        break
    yield features
    offset += 1000
```

## Geometry / coordinates

- The native `geometry` field is in **`wkid 26917`** (UTM Zone 17N,
  NAD83). Don't use this directly in Tableau.
- The attributes also carry **`SAFETYLAT`** and **`SAFETYLON`** in plain
  WGS84 — these are what we feed Tableau.
- Alternative: pass `outSR=4326` to the query and the returned geometry
  will already be lon/lat in WGS84. Either works; we prefer
  `SAFETYLAT/SAFETYLON` because it's an attribute (survives a CSV
  flatten without needing geometry handling).

## Fields we actually need

The full record has 60+ fields. For the where/when hotspot question we
only need:

| Field | Purpose |
|---|---|
| `XID` | Unique crash id (for dedupe) |
| `CALENDAR_YEAR` | `year` dimension |
| `CRASH_DATE` | `date` (parsed to datetime) |
| `CRASH_TIME` | `hour` of day |
| `WEEKDAY_TXT` | `day_of_week` |
| `COUNTY_TXT` | `county` (where) |
| `DHSMV_CTY_CD` / city fields | city-level rollups |
| `SAFETYLAT`, `SAFETYLON` | map points |
| `INJSEVER` | severity filter (already applied server-side) |
| `SPEED_LIMIT` | secondary breakdown |
| `IN_TOWN_FLAG` | urban vs rural cut |
| `FUNCLASS` | road type |

That's ~12 columns out of 60+ — sharply cuts payload size on the wire.

## Working `curl` example (Step 2 acceptance criterion)

Returns 5 fatal/serious-injury crashes from 2019 in Miami-Dade, with
the slim field set, as JSON:

```bash
curl -s "https://gis.fdot.gov/arcgis/rest/services/Crashes_All/FeatureServer/0/query" \
  --data-urlencode "where=INJSEVER IN ('4','5') AND CALENDAR_YEAR=2019 AND COUNTY_TXT='MIAMI-DADE'" \
  --data-urlencode "outFields=XID,CALENDAR_YEAR,CRASH_DATE,CRASH_TIME,COUNTY_TXT,INJSEVER,SAFETYLAT,SAFETYLON,SPEED_LIMIT,WEEKDAY_TXT" \
  --data-urlencode "resultRecordCount=5" \
  --data-urlencode "f=json" \
  -G
```

Verified to return 5 features. Step 2 acceptance criterion met.

## Caveats / known limitations

- **Data ends in 2019** — frame the dashboard accordingly ("Florida
  fatal & serious-injury crash patterns, 2011–2019").
- `INJSEVER` is reported by the officer at the scene — under-reporting
  of serious injuries that turn fatal later in the hospital is a known
  issue in any KABCO-coded dataset.
- A handful of rows have `SAFETYLAT/LON` missing or zero — drop those
  in `clean.py` rather than trying to backfill from the UTM geometry.
- `COUNTY_TXT` is uppercase and includes hyphenated names (e.g.
  `'MIAMI-DADE'`) — normalize to title-case for display in Tableau.

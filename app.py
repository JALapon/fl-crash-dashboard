"""Streamlit dashboard for Florida fatal & serious-injury crashes (2011-2018).

Reads the five pre-aggregated CSVs in ``data/processed/`` (committed to
git so the deployed Streamlit Community Cloud app has data on startup —
the cloud runner doesn't execute our pipeline). One section per Step 1
sub-question from PROJECT_PLAN.md.

Run locally:
    streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# --- Constants ------------------------------------------------------

PROJECT = Path(__file__).resolve().parent
PROCESSED = PROJECT / "data" / "processed"

DOW_ORDER = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]

# Severity color palette — used in every chart so colors stay
# consistent across the dashboard.
FATAL_COLOR = "#c2362a"     # crimson
SERIOUS_COLOR = "#4a6fa5"   # steel blue


# --- Page config ----------------------------------------------------

st.set_page_config(
    page_title="FL Fatal & Serious-Injury Crashes (2011–2018)",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- Data loaders ---------------------------------------------------

@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    """Read one pre-aggregated CSV from data/processed/."""
    return pd.read_csv(PROCESSED / f"{name}.csv")


county_year = load_csv("crashes_by_county_year")
hour_dow = load_csv("crashes_by_hour_dow")
yearly = load_csv("crashes_yearly_trend")
sev_by_county = load_csv("severity_breakdown_by_county")
points = load_csv("top_points")


# --- Hero -----------------------------------------------------------

total_crashes = int(yearly["total"].sum())
total_fatal = int(yearly["fatal"].sum())
total_serious = int(yearly["serious_injury"].sum())

st.title("🚦 Florida fatal & serious-injury crashes")
st.markdown(
    f"**Where and when do Florida's most dangerous crashes concentrate?** "
    f"An analysis of **{total_crashes:,} fatal and serious-injury crashes** "
    f"({total_fatal:,} fatal · {total_serious:,} serious) across Florida from "
    f"2011 through 2018. Data sourced from the "
    f"[FDOT State Safety Office]"
    f"(https://gis.fdot.gov/arcgis/rest/services/Crashes_All/FeatureServer) "
    f"public ArcGIS REST FeatureServer."
)


# --- Sidebar filters ------------------------------------------------

with st.sidebar:
    st.header("Filters")

    year_lo, year_hi = int(yearly["year"].min()), int(yearly["year"].max())
    yr_range = st.slider(
        "Year range",
        min_value=year_lo,
        max_value=year_hi,
        value=(year_lo, year_hi),
    )
    st.caption(
        "Applies to: fatal-point map, yearly trend, county trend lines. "
        "The hour × day-of-week heatmap and the top-counties stacked bar "
        "are cross-year aggregates and ignore this filter."
    )

    all_counties = sorted(points["county"].unique())
    chosen_counties = st.multiselect(
        "Counties — filters the fatal point map only",
        options=all_counties,
        default=[],
        help="Empty selection = show every county.",
    )


def filter_yr(df: pd.DataFrame, col: str = "year") -> pd.DataFrame:
    """Slice ``df`` to the sidebar year range."""
    return df[(df[col] >= yr_range[0]) & (df[col] <= yr_range[1])]


# --- Row 1: Where ---------------------------------------------------

st.header("Where")
col_map, col_bar = st.columns([1.2, 1])

with col_map:
    st.subheader("Fatal crashes — point map")

    points_f = filter_yr(points)
    if chosen_counties:
        points_f = points_f[points_f["county"].isin(chosen_counties)]

    fig = px.scatter_map(
        points_f,
        lat="lat",
        lon="lon",
        hover_data={
            "year": True, "county": True, "day_of_week": True,
            "hour": True, "lat": False, "lon": False,
        },
        color_discrete_sequence=[FATAL_COLOR],
        zoom=5.6,
        height=520,
        map_style="carto-positron",
    )
    fig.update_traces(marker=dict(size=4, opacity=0.55))
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, width="stretch")
    st.caption(
        f"Showing **{len(points_f):,}** fatal crashes. Serious-injury "
        f"crashes are not plotted — at 115,600 points they'd be too "
        f"dense to read individually."
    )

with col_bar:
    st.subheader("Top 15 counties — fatal vs serious-injury")

    top15 = sev_by_county.head(15)
    melted = top15.melt(
        id_vars="county",
        value_vars=["fatal", "serious_injury"],
        var_name="severity",
        value_name="count",
    )
    melted["severity"] = melted["severity"].map({
        "fatal": "Fatal",
        "serious_injury": "Serious injury",
    })

    fig = px.bar(
        melted,
        x="count",
        y="county",
        color="severity",
        orientation="h",
        color_discrete_map={"Fatal": FATAL_COLOR, "Serious injury": SERIOUS_COLOR},
        height=520,
    )
    fig.update_layout(
        yaxis=dict(categoryorder="total ascending", title=""),
        xaxis=dict(title="crashes 2011–2018"),
        legend=dict(orientation="h", y=-0.08, title=""),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Cross-year aggregate (does not respect year filter). "
        "Counties are sorted by combined volume; the **fatal-share** "
        "ratio is a separate question worth exploring per row."
    )


# --- Row 2: When ----------------------------------------------------

st.header("When")
col_heat, col_line = st.columns([1, 1])

with col_heat:
    st.subheader("Hour of day × day of week")

    pivot = (
        hour_dow.pivot(index="day_of_week", columns="hour", values="total")
                .reindex(DOW_ORDER)
    )

    fig = px.imshow(
        pivot,
        labels=dict(x="hour", y="", color="crashes"),
        color_continuous_scale="Reds",
        aspect="auto",
        height=420,
    )
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    fig.update_xaxes(tickmode="linear", tick0=0, dtick=2)
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Rows where `CRASH_TIME='0000'` are excluded — the EDA found "
        "those are a mix of genuine midnight crashes and 'time unknown' "
        "sentinels (hour=0 ran 1.92× the volume of hours 1–4). "
        "Cross-year aggregate."
    )

with col_line:
    st.subheader("Yearly trend")

    yearly_f = filter_yr(yearly)
    yearly_melted = yearly_f.melt(
        id_vars="year",
        value_vars=["fatal", "serious_injury"],
        var_name="severity",
        value_name="count",
    )
    yearly_melted["severity"] = yearly_melted["severity"].map({
        "fatal": "Fatal",
        "serious_injury": "Serious injury",
    })

    fig = px.line(
        yearly_melted,
        x="year",
        y="count",
        color="severity",
        markers=True,
        color_discrete_map={"Fatal": FATAL_COLOR, "Serious injury": SERIOUS_COLOR},
        height=420,
    )
    fig.update_layout(
        legend=dict(orientation="h", y=-0.15, title=""),
        margin=dict(l=0, r=0, t=20, b=0),
        xaxis=dict(tickmode="linear", tick0=2011, dtick=1, title=""),
        yaxis=dict(title="crashes"),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        f"Years {yr_range[0]}–{yr_range[1]}. 2019 is excluded entirely "
        "(only 1,763 records — ~10% of a normal year)."
    )


# --- Row 3: Where × When --------------------------------------------

st.header("Where × when — county trends over time")

default_counties = sev_by_county.head(5)["county"].tolist()
trend_counties = st.multiselect(
    "Compare counties (top 5 by volume shown by default):",
    options=sorted(county_year["county"].unique()),
    default=default_counties,
)

if trend_counties:
    county_year_f = filter_yr(
        county_year[county_year["county"].isin(trend_counties)]
    )

    fig = px.line(
        county_year_f,
        x="year",
        y="total",
        color="county",
        markers=True,
        height=420,
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(tickmode="linear", tick0=2011, dtick=1, title=""),
        yaxis=dict(title="crashes per year"),
        legend=dict(title=""),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Each point is total fatal + serious-injury crashes in that "
        "county-year. Add or remove counties above to compare any pair."
    )
else:
    st.info("Pick at least one county above to render the chart.")


# --- Footer ---------------------------------------------------------

st.markdown("---")
st.caption(
    "**Code:** [github.com/JALapon/fl-crash-dashboard]"
    "(https://github.com/JALapon/fl-crash-dashboard)  ·  "
    "**Source notes:** [docs/api_notes.md]"
    "(https://github.com/JALapon/fl-crash-dashboard/blob/main/docs/api_notes.md)  ·  "
    "**EDA notebook:** [notebooks/01_eda.ipynb]"
    "(https://github.com/JALapon/fl-crash-dashboard/blob/main/notebooks/01_eda.ipynb)"
)

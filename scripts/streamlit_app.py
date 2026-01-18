from __future__ import annotations
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from shapely import wkt
from sxm_mobility.config import settings

st.set_page_config(page_title="SXM Mobility Graph Lab", layout="wide")

APP_DIR = Path(__file__).resolve().parent          
REPO_DIR = APP_DIR.parent                         
PROCESSED_DIR = REPO_DIR / "data" / "processed"

EDGES_PATH = PROCESSED_DIR / "edges.parquet"
BOTTLENECKS_PATH = PROCESSED_DIR / "baseline_bottlenecks.parquet"
KPI_PATH = PROCESSED_DIR / "results_baseline.parquet"
SCEN_PATH = PROCESSED_DIR / "results_scenarios.parquet"

st.title("SXM Mobility Graph Lab — Network Map (Plotly + OpenStreetMap)")
st.caption("Prototype dashboard scaffold. Add maps + scenario runners here.")

with st.expander("Debug: paths & files", expanded=False):
    st.write("CWD:", str(Path.cwd()))
    st.write("Repo dir:", str(REPO_DIR))
    st.write("Processed dir exists?:", PROCESSED_DIR.exists())
    if PROCESSED_DIR.exists():
        st.write("Processed parquet files:", [p.name for p in PROCESSED_DIR.glob("*.parquet")])
    st.write("EDGES_PATH:", str(EDGES_PATH))
    st.write("EDGES exists?:", EDGES_PATH.exists())

st.subheader("Inputs")
st.write(
    {
        "place_query": settings.place_query,
        "network_type": settings.network_type,
        "msa_iters": settings.msa_iters,
        "bpr_alpha": settings.bpr_alpha,
        "bpr_beta": settings.bpr_beta,
    }
)

st.subheader("Baseline outputs")
try:
    kpi = pd.read_parquet(KPI_PATH)
    st.write("KPI summary")
    st.dataframe(kpi, use_container_width=True)

    df = pd.read_parquet(BOTTLENECKS_PATH)
    st.write("Top bottlenecks")
    st.dataframe(df, use_container_width=True)
except FileNotFoundError:
    st.info("Baseline outputs not found. Run scripts/run_baseline.py to generate them.")
except Exception as e:
    st.warning(f"Baseline outputs error: {e}")


st.subheader("Scenario outputs")
try:
    scen = pd.read_parquet(SCEN_PATH)
    st.dataframe(scen, use_container_width=True)
except FileNotFoundError:
    st.info("Scenario outputs not found. Run scripts/run_scenarios.py to generate them.")
except Exception as e:
    st.warning(f"Scenario outputs error: {e}")


def linestring_to_lonlat_lists(wkt_str: str) -> tuple[list[float], list[float]]:
    """Parse a WKT LineString and return longitude/latitude coordinate lists.

    Assumes the geometry is a LineString (or LineString-like) and that coordinates
    are in (lon, lat) order, as commonly stored in OSM/Geo data.

    :param wkt_str: WKT string representing a LineString geometry.
    :type wkt_str: str
    :raises Exception: If the WKT cannot be parsed or is not a LineString-like geometry.
    :return: A tuple of (lons, lats) lists extracted from the geometry.
    :rtype: tuple[list[float], list[float]]
    """
    geom = wkt.loads(wkt_str)
    xs, ys = geom.xy  # xs=lon, ys=lat
    return list(xs), list(ys)


def build_network_trace(edges_df: pd.DataFrame, max_edges: int | None = None) -> "go.Scattermapbox":
    """Build a single Plotly Mapbox trace representing many network edges.

    Efficiently draws many line segments by concatenating all coordinates into one
    `Scattermapbox` trace, using `None` separators between segments (Plotly treats
    `None` as a line break).

    Expects `edges_df` to contain a `geometry_wkt` column with WKT LineString values.

    :param edges_df: Edge table containing a `geometry_wkt` column.
    :type edges_df: pd.DataFrame
    :param max_edges: Optional cap on the number of edges to render (uses `.head()`),
        defaults to None.
    :type max_edges: int | None, optional
    :raises KeyError: If `geometry_wkt` column is missing.
    :return: A Plotly Scattermapbox trace suitable for adding to a Figure.
    :rtype: go.Scattermapbox
    """
    if max_edges is not None:
        edges_df = edges_df.head(max_edges)

    lons_all, lats_all = [], []
    for w in edges_df["geometry_wkt"].dropna():
        lons, lats = linestring_to_lonlat_lists(w)
        lons_all.extend(lons + [None])
        lats_all.extend(lats + [None])

    return go.Scattermapbox(
        lon=lons_all,
        lat=lats_all,
        mode="lines",
        line=dict(width=2),
        hoverinfo="skip",
        name="Road network",
    )


def compute_center(edges_df: pd.DataFrame) -> tuple[float, float]:
    """Compute an approximate map center (lat, lon) from edge geometries.

    Uses a small sample of up to the first 200 non-null `geometry_wkt` rows, parses
    each geometry, and averages all coordinates to estimate the center.

    If no coordinates are available, falls back to a hard-coded center
    (approximately Sint Maarten).

    :param edges_df: Edge table containing a `geometry_wkt` column.
    :type edges_df: pd.DataFrame
    :raises KeyError: If `geometry_wkt` column is missing.
    :return: A `(lat, lon)` tuple representing the center point.
    :rtype: tuple[float, float]
    """
    # quick-and-good center: take first N geometries and average coords
    sample = edges_df["geometry_wkt"].dropna().head(200)
    lons_sum, lats_sum, n = 0.0, 0.0, 0
    for w in sample:
        xs, ys = linestring_to_lonlat_lists(w)
        lons_sum += sum(xs)
        lats_sum += sum(ys)
        n += len(xs)
    if n == 0:
        return 18.0, -63.1  # fallback (SXM-ish)
    return (lats_sum / n), (lons_sum / n)

st.subheader("St. Maarten Road Network Map")
st.sidebar.header("Render options") 
max_edges = st.sidebar.slider("Max edges to draw (performance)", 500, 20000, 8000, step=500)

if not EDGES_PATH.exists():
    st.error(f"Missing edges file: {EDGES_PATH}")
    st.info(
        "Ensure data/processed/edges.parquet exists in the deployed repo (committed) "
        "or download/generate it during app startup."
    )
    st.stop()

edges = pd.read_parquet(EDGES_PATH)
base_trace = build_network_trace(edges, max_edges=max_edges)
center_lat, center_lon = compute_center(edges)

fig = go.Figure()
fig.add_trace(base_trace)

show_bottlenecks = st.sidebar.checkbox("Overlay bottlenecks (if available)", value=True)
top_n = st.sidebar.slider("Top N bottlenecks", 10, 300, 50, step=10)

if show_bottlenecks:
    try:
        b = pd.read_parquet(BOTTLENECKS_PATH)
        merged = b.merge(edges, on=["u", "v", "key"], how="left")
        metric_col = "delay" if "delay" in merged.columns else None
        merged = merged.dropna(subset=["geometry_wkt"])
        if metric_col:
            merged = merged.sort_values(metric_col, ascending=False)

        merged = merged.head(top_n)

        lons_all, lats_all = [], []
        for w in merged["geometry_wkt"]:
            lons, lats = linestring_to_lonlat_lists(w)
            lons_all.extend(lons + [None])
            lats_all.extend(lats + [None])

        fig.add_trace(
            go.Scattermapbox(
                lon=lons_all,
                lat=lats_all,
                mode="lines",
                line=dict(width=5),
                name="Top bottlenecks",
                hoverinfo="skip",
            )
        )

    except FileNotFoundError:
        st.info("No baseline_bottlenecks.parquet found yet. Run scripts/run_baseline.py first.")
    except Exception as e:
        st.warning(f"Could not overlay bottlenecks: {e}")

fig.update_layout(
    mapbox=dict(
        style="open-street-map",
        center=dict(lat=center_lat, lon=center_lon),
        zoom=12,
    ),
    margin=dict(l=0, r=0, t=0, b=0),
    height=750,
    showlegend=True,
)

st.plotly_chart(fig, use_container_width=True)

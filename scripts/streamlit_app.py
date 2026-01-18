from __future__ import annotations

import pandas as pd
import streamlit as st

from sxm_mobility.config import settings

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from shapely import wkt

EDGES_PATH = "data/processed/edges.parquet"
BOTTLENECKS_PATH = "data/processed/baseline_bottlenecks.parquet" 

st.title("SXM Mobility Graph Lab")
st.caption("Prototype dashboard scaffold. Add maps + scenario runners here.")

st.subheader("Inputs")
st.write({
    "place_query": settings.place_query,
    "network_type": settings.network_type,
    "msa_iters": settings.msa_iters,
    "bpr_alpha": settings.bpr_alpha,
    "bpr_beta": settings.bpr_beta,
})

st.subheader("Baseline outputs")
try:
    kpi = pd.read_parquet("data/processed/results_baseline.parquet")
    st.write("KPI summary")
    st.dataframe(kpi, use_container_width=True)

    df = pd.read_parquet("data/processed/baseline_bottlenecks.parquet")
    st.write("Top bottlenecks")
    st.dataframe(df, use_container_width=True)
except Exception:
    st.info("Run scripts/run_baseline.py to generate baseline outputs.")

st.subheader("Scenario outputs")
try:
    scen = pd.read_parquet("data/processed/results_scenarios.parquet")
    st.dataframe(scen, use_container_width=True)
except Exception:
    st.info("Run scripts/run_scenarios.py to generate scenario outputs.")


def linestring_to_lonlat_lists(wkt_str: str):
    geom = wkt.loads(wkt_str)
    xs, ys = geom.xy  # xs=lon, ys=lat
    return list(xs), list(ys)


def build_network_trace(edges_df: pd.DataFrame, max_edges: int | None = None):
    """
    Efficiently draw many line segments by concatenating them into one trace,
    using None separators between segments.
    """
    if max_edges is not None:
        edges_df = edges_df.head(max_edges)

    lons_all, lats_all = [], []
    for w in edges_df["geometry_wkt"].dropna():
        lons, lats = linestring_to_lonlat_lists(w)
        lons_all.extend(lons + [None])
        lats_all.extend(lats + [None])

    trace = go.Scattermapbox(
        lon=lons_all,
        lat=lats_all,
        mode="lines",
        line=dict(width=2),
        hoverinfo="skip",
        name="Road network",
    )
    return trace


def compute_center(edges_df: pd.DataFrame):
    # quick-and-good center: take first N geometries and average coords
    sample = edges_df["geometry_wkt"].dropna().head(200)
    lons, lats, n = 0.0, 0.0, 0
    for w in sample:
        xs, ys = linestring_to_lonlat_lists(w)
        lons += sum(xs)
        lats += sum(ys)
        n += len(xs)
    if n == 0:
        return 18.0, -63.1  # fallback
    return (lats / n), (lons / n)


st.set_page_config(layout="wide")
st.title("SXM Mobility Graph Lab — Network Map (Plotly + OpenStreetMap)")

edges = pd.read_parquet(EDGES_PATH)

# Optional: performance controls
st.sidebar.header("Render options")
max_edges = st.sidebar.slider("Max edges to draw (performance)", 500, 20000, 8000, step=500)

# Build base network trace
base_trace = build_network_trace(edges, max_edges=max_edges)

# Center map
center_lat, center_lon = compute_center(edges)

fig = go.Figure()
fig.add_trace(base_trace)

# Optional bottleneck overlay (if file exists & has non-zero flows later)
show_bottlenecks = st.sidebar.checkbox("Overlay bottlenecks (if available)", value=True)
top_n = st.sidebar.slider("Top N bottlenecks", 10, 300, 50, step=10)

if show_bottlenecks:
    try:
        b = pd.read_parquet(BOTTLENECKS_PATH)
        # Expect b has columns: u, v, key, delay (or v_c)
        # Join on u,v,key to recover geometry from edges table
        # Note: edges.parquet likely has u,v,key columns from reset_index()
        merged = b.merge(edges, on=["u", "v", "key"], how="left")
        merged = merged.dropna(subset=["geometry_wkt"]).sort_values("delay", ascending=False).head(top_n)

        bottleneck_trace = go.Scattermapbox(
            lon=[],
            lat=[],
            mode="lines",
            line=dict(width=5),  # thicker overlay
            name="Top bottlenecks",
        )

        # Build overlay coords
        lons_all, lats_all = [], []
        for w in merged["geometry_wkt"]:
            lons, lats = linestring_to_lonlat_lists(w)
            lons_all.extend(lons + [None])
            lats_all.extend(lats + [None])

        bottleneck_trace.lon = lons_all
        bottleneck_trace.lat = lats_all
        fig.add_trace(bottleneck_trace)

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


# st.set_page_config(page_title="SXM Mobility Graph Lab", layout="wide")
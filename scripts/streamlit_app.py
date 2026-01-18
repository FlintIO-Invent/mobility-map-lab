from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from shapely import wkt

from sxm_mobility.config import settings


# MUST be the first Streamlit call
st.set_page_config(page_title="SXM Mobility Graph Lab", layout="wide")


# --- Paths (repo-relative, Streamlit Cloud safe) ---
APP_DIR = Path(__file__).resolve().parent          # .../mobility-map-lab/scripts
REPO_DIR = APP_DIR.parent                          # .../mobility-map-lab
PROCESSED_DIR = REPO_DIR / "data" / "processed"

EDGES_PATH = PROCESSED_DIR / "edges.parquet"
BOTTLENECKS_PATH = PROCESSED_DIR / "baseline_bottlenecks.parquet"
KPI_PATH = PROCESSED_DIR / "results_baseline.parquet"
SCEN_PATH = PROCESSED_DIR / "results_scenarios.parquet"


# --- UI header ---
st.title("SXM Mobility Graph Lab — Network Map (Plotly + OpenStreetMap)")
st.caption("Prototype dashboard scaffold. Add maps + scenario runners here.")


# --- Debug panel (helps on Streamlit Cloud) ---
with st.expander("Debug: paths & files", expanded=False):
    st.write("CWD:", str(Path.cwd()))
    st.write("Repo dir:", str(REPO_DIR))
    st.write("Processed dir exists?:", PROCESSED_DIR.exists())
    if PROCESSED_DIR.exists():
        st.write("Processed parquet files:", [p.name for p in PROCESSED_DIR.glob("*.parquet")])
    st.write("EDGES_PATH:", str(EDGES_PATH))
    st.write("EDGES exists?:", EDGES_PATH.exists())


# --- Inputs ---
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


# --- Baseline outputs ---
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


# --- Scenario outputs ---
st.subheader("Scenario outputs")
try:
    scen = pd.read_parquet(SCEN_PATH)
    st.dataframe(scen, use_container_width=True)
except FileNotFoundError:
    st.info("Scenario outputs not found. Run scripts/run_scenarios.py to generate them.")
except Exception as e:
    st.warning(f"Scenario outputs error: {e}")


# --- Helper functions ---
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

    return go.Scattermapbox(
        lon=lons_all,
        lat=lats_all,
        mode="lines",
        line=dict(width=2),
        hoverinfo="skip",
        name="Road network",
    )


def compute_center(edges_df: pd.DataFrame):
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


# --- Map rendering ---
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

# Optional bottleneck overlay
show_bottlenecks = st.sidebar.checkbox("Overlay bottlenecks (if available)", value=True)
top_n = st.sidebar.slider("Top N bottlenecks", 10, 300, 50, step=10)

if show_bottlenecks:
    try:
        b = pd.read_parquet(BOTTLENECKS_PATH)

        # Join to recover geometry for bottlenecks
        merged = b.merge(edges, on=["u", "v", "key"], how="left")

        # If your bottleneck metric isn't "delay", this will still work with a fallback
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

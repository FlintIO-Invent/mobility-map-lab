from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import pickle
import networkx as nx
import osmnx as ox
import pandas as pd






def download_osm_graph(place_query: str, network_type: str = "drive") -> nx.MultiDiGraph:
    """Download a road network using OSMnx.

    Requires optional dependency group: `geo`.

    Notes
    -----
    - Node ids from OSMnx are integers.
    - Edge attributes can contain lists/dicts and shapely geometries.
    """

    try:
        import osmnx as ox
    except ImportError as e:
        raise ImportError("Install geo extras: `uv sync --extra geo`") from e

    ox.settings.use_cache = True
    ox.settings.log_console = False

    G = ox.graph_from_place(place_query, network_type=network_type, simplify=True)
    return nx.MultiDiGraph(G)


def _graphml_safe_value(v: Any) -> Any:
    """Convert common non-GraphML types to GraphML-safe scalars."""

    if v is None:
        return ""

    if isinstance(v, (str, int, float, bool)):
        return v

    # Shapely geometry -> WKT string (LineString/Point/etc.)
    wkt = getattr(v, "wkt", None)
    if wkt is not None:
        return wkt

    # list/tuple/set/dict -> JSON string
    if isinstance(v, (list, tuple, set)):
        return json.dumps(list(v), ensure_ascii=False)

    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)

    # fallback
    return str(v)


def make_graph_graphml_safe(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Return a copy of G where all attrs are GraphML-safe types."""

    H = G.copy()

    # Graph-level attrs
    H.graph = {k: _graphml_safe_value(v) for k, v in H.graph.items()}

    # Node attrs
    for _, data in H.nodes(data=True):
        for k, v in list(data.items()):
            data[k] = _graphml_safe_value(v)

    # Edge attrs (MultiDiGraph)
    for _, _, _, data in H.edges(keys=True, data=True):
        for k, v in list(data.items()):
            data[k] = _graphml_safe_value(v)

    return H


def save_graphml(G: nx.MultiDiGraph, path: Path) -> None:
    """Save a GraphML artifact for sharing (Gephi/yEd/etc.).

    GraphML does not support lists/dicts/geometry objects, so we sanitize to strings.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    H = make_graph_graphml_safe(G)
    nx.write_graphml(H, path)


def load_graphml(path: Path) -> nx.MultiDiGraph:
    """Load GraphML back into NetworkX.

    Warning: GraphML loads node ids and attribute values as strings.
    Prefer gpickle for internal computation.
    """

    return nx.read_graphml(path)  # type: ignore[return-value]


def save_gpickle(G: nx.Graph, path: str | Path) -> None:
    """Save graph in a fast, full-fidelity Python format (engine artifact)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)


def load_gpickle(path: str | Path) -> nx.Graph:
    """Load graph saved by save_gpickle()."""
    path = Path(path)
    with path.open("rb") as f:
        return pickle.load(f)


def graph_basic_stats(G: nx.MultiDiGraph) -> dict[str, Any]:
    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "is_directed": G.is_directed(),
    }


def _to_json_string(v: Any) -> str:
    """Make values safe + consistent for Parquet/Arrow."""
    if v is None:
        return ""
    # keep common scalars
    if isinstance(v, (str, int, float, bool)):
        return str(v)
    # lists/dicts/sets -> JSON
    if isinstance(v, (list, tuple, set, dict)):
        return json.dumps(v, ensure_ascii=False)
    # shapely -> WKT if present
    wkt = getattr(v, "wkt", None)
    if wkt is not None:
        return wkt
    return str(v)


# def export_nodes_edges_parquet(G, nodes_path: str | Path, edges_path: str | Path) -> None:
#     nodes_path = Path(nodes_path)
#     edges_path = Path(edges_path)
#     nodes_path.parent.mkdir(parents=True, exist_ok=True)
#     edges_path.parent.mkdir(parents=True, exist_ok=True)

#     gdf_nodes, gdf_edges = ox.graph_to_gdfs(
#         G, nodes=True, edges=True, fill_edge_geometry=True
#     )

#     # Make geometry portable across tools
#     gdf_nodes["geometry_wkt"] = gdf_nodes.geometry.to_wkt()
#     gdf_edges["geometry_wkt"] = gdf_edges.geometry.to_wkt()

#     # Drop shapely geometry columns (keeps Parquet simple + tool-agnostic)
#     gdf_nodes = gdf_nodes.drop(columns=["geometry"])
#     gdf_edges = gdf_edges.drop(columns=["geometry"])

#     # IMPORTANT: bring index into columns (especially edges: u,v,key)
#     nodes_df = gdf_nodes.reset_index()
#     edges_df = gdf_edges.reset_index()

#     # Normalize columns that commonly contain mixed types (OSMnx attributes)
#     for df in (nodes_df, edges_df):
#         if "osmid" in df.columns:
#             df["osmid"] = df["osmid"].map(_to_json_string)

#         protected = {"u", "v", "key", "node_id"}  

#         obj_cols = df.select_dtypes(include=["object"]).columns
#         for c in ["u", "v", "key"]:
#             if c in edges_df.columns:
#                 edges_df[c] = pd.to_numeric(edges_df[c], errors="coerce").astype("Int64")

#     nodes_df.to_parquet(nodes_path, index=False)
#     edges_df.to_parquet(edges_path, index=False)


def export_nodes_edges_parquet(G, nodes_path: str | Path, edges_path: str | Path) -> None:
    nodes_path = Path(nodes_path)
    edges_path = Path(edges_path)
    nodes_path.parent.mkdir(parents=True, exist_ok=True)
    edges_path.parent.mkdir(parents=True, exist_ok=True)

    gdf_nodes, gdf_edges = ox.graph_to_gdfs(G, nodes=True, edges=True, fill_edge_geometry=True)

    # geometry as portable WKT
    gdf_nodes["geometry_wkt"] = gdf_nodes.geometry.to_wkt()
    gdf_edges["geometry_wkt"] = gdf_edges.geometry.to_wkt()

    # drop shapely geometry columns
    gdf_nodes = gdf_nodes.drop(columns=["geometry"])
    gdf_edges = gdf_edges.drop(columns=["geometry"])

    # bring index into columns (nodes: node id; edges: u,v,key)
    nodes_df = gdf_nodes.reset_index()
    edges_df = gdf_edges.reset_index()

    # Keep join keys numeric
    if "osmid" in nodes_df.columns:
        nodes_df["node_id"] = pd.to_numeric(nodes_df["osmid"], errors="coerce").astype("Int64")

    for c in ["u", "v", "key"]:
        if c in edges_df.columns:
            edges_df[c] = pd.to_numeric(edges_df[c], errors="coerce").astype("Int64")

    protected = {"u", "v", "key", "node_id"}  # do NOT stringify these

    # Normalize: first handle known troublemakers explicitly
    for c in ["highway", "name", "maxspeed", "lanes", "access", "bridge", "junction", "ref", "service", "tunnel", "osmid"]:
        if c in edges_df.columns and c not in protected:
            edges_df[c] = edges_df[c].map(_to_json_string)

    # Now normalize all remaining object/string columns except protected
    for df in (nodes_df, edges_df):
        cols = df.select_dtypes(include=["object", "string"]).columns
        for c in cols:
            if c not in protected:
                df[c] = df[c].map(_to_json_string)

    # Final safety: if any column still contains list/dict/etc, force convert it
    def has_complex(series: pd.Series) -> bool:
        return series.map(lambda x: isinstance(x, (list, dict, tuple, set))).any()

    for df in (nodes_df, edges_df):
        for c in df.columns:
            if has_complex(df[c]):
                df[c] = df[c].map(_to_json_string)

    # drop rows missing join keys (rare but safe)
    edges_df = edges_df.dropna(subset=[c for c in ["u", "v", "key"] if c in edges_df.columns])

    nodes_df.to_parquet(nodes_path, index=False)
    edges_df.to_parquet(edges_path, index=False)

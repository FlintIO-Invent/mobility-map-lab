from __future__ import annotations

from pathlib import Path
import osmnx as ox
import networkx as nx



def build_graph(place_query: str, network_type: str = "drive") -> nx.MultiDiGraph:
    """
    Build and return an OSM road network graph (no saving here).
    Saving/exporting is handled by scripts/build_graph.py.
    """
    G = ox.graph_from_place(place_query, network_type=network_type, simplify=True)

    # Optional (recommended): keep largest strongly connected component for drive networks
    # (prevents weird disconnected islands from breaking assignment)
    try:
        G = ox.truncate.largest_component(G, strongly=True)
    except Exception:
        pass

    return G
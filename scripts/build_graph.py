from __future__ import annotations

from pathlib import Path
from loguru import logger

from sxm_mobility.config import settings
from sxm_mobility.network.build_graph import build_graph
from sxm_mobility.io.osm_ingest import (
    save_gpickle,
    save_graphml,
    export_nodes_edges_parquet,
)

def main() -> None:
    out_dir = Path(settings.data_dir) / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading + building graph for: {settings.place_query}")
    G = build_graph(settings.place_query, settings.network_type)

    # 1) Engine artifact
    gpickle_path = out_dir / "graph.gpickle"
    save_gpickle(G, gpickle_path)
    logger.info(f"Saved: {gpickle_path}")

    # 2) Shareable artifact
    graphml_path = out_dir / "graph.graphml"
    save_graphml(G, graphml_path)
    logger.info(f"Saved: {graphml_path}")

    # 3) Tables for dashboards/DB
    nodes_path = out_dir / "nodes.parquet"
    edges_path = out_dir / "edges.parquet"
    export_nodes_edges_parquet(G, nodes_path, edges_path)
    logger.info(f"Saved: {nodes_path}")
    logger.info(f"Saved: {edges_path}")


if __name__ == "__main__":
    main()

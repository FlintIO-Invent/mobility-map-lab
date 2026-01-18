from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger
import pandas as pd
from sxm_mobility.assignment.metrics import top_bottlenecks, total_delay, total_system_travel_time
from sxm_mobility.assignment.msa import msa_traffic_assignment
from sxm_mobility.config import settings
from sxm_mobility.demand.od_generation import random_od
from sxm_mobility.io.osm_ingest import load_gpickle


def main() -> None:
    out_dir = Path(settings.data_dir) / "processed"
    graph_path = out_dir / "graph.gpickle"
    if not graph_path.exists():
        raise FileNotFoundError(f"Graph not found: {graph_path}. Run scripts/build_graph.py first.")

    G = load_gpickle(graph_path)

    od = random_od(G, n_pairs=250)
    total_demand = sum(d for _, _, d in od)
    logger.info(f"OD pairs: {len(od)} | total_demand: {total_demand}")

    missing = sum(1 for o, d, _ in od if o not in G or d not in G)
    if missing:
        raise ValueError(f"OD nodes missing from graph: {missing}/{len(od)} — OD generator is using wrong node IDs.")

    logger.info("Running assignment (iters={})", settings.msa_iters)
    G = msa_traffic_assignment(G, od=od, iters=settings.msa_iters, alpha=settings.bpr_alpha, beta=settings.bpr_beta)

    # Detailed bottleneck table
    rows = top_bottlenecks(G, n=50)
    df_b = pd.DataFrame(rows)
    out_b_parquet = out_dir / "baseline_bottlenecks.parquet"
    out_b_csv = out_dir / "baseline_bottlenecks.csv"

    for c in ["u", "v", "key"]:
        if c in df_b.columns:
            df_b[c] = pd.to_numeric(df_b[c], errors="coerce").astype("Int64")

            df_b.to_parquet(out_b_parquet, index=False)
            df_b.to_csv(out_b_csv, index=False)
            logger.info("Saved bottlenecks to {}", out_b_parquet)

    # Summary KPI table (1 row) for dashboards/portals
    summary = {
        "place_query": settings.place_query,
        "network_type": settings.network_type,
        "msa_iters": settings.msa_iters,
        "bpr_alpha": settings.bpr_alpha,
        "bpr_beta": settings.bpr_beta,
        "od_pairs": len(od),
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "tstt": total_system_travel_time(G),
        "delay": total_delay(G),
    }
    df_s = pd.DataFrame([summary])
    out_summary = out_dir / "results_baseline.parquet"
    df_s.to_parquet(out_summary, index=False)
    logger.info("Saved baseline KPI summary to {}", out_summary)


if __name__ == "__main__":
    main()

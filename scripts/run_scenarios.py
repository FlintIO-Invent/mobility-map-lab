from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from loguru import logger

from sxm_mobility.assignment.msa import msa_traffic_assignment
from sxm_mobility.config import settings
from sxm_mobility.demand.od_generation import random_od
from sxm_mobility.io.osm_ingest import load_gpickle
from sxm_mobility.scenarios.catalog import AddConnector, Closure, IncreaseCapacity
from sxm_mobility.scenarios.runner import run_scenario


def _as_json(x: object) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True)


def main() -> None:
    out_dir = Path(settings.data_dir) / "processed"
    graph_path = out_dir / "graph.gpickle"
    if not graph_path.exists():
        raise FileNotFoundError(f"Graph not found: {graph_path}. Run scripts/build_graph.py first.")

    base_G = load_gpickle(graph_path)

    # Synthetic OD for prototyping (replace with zone/real OD later)
    od = random_od(base_G, n_pairs=200)

    # ---- Baseline (computed inside this script for scenario deltas)
    logger.info("Running baseline assignment (iters={})", settings.msa_iters)
    baseline_G = msa_traffic_assignment(
        base_G.copy(),
        od=od,
        iters=settings.msa_iters,
        alpha=settings.bpr_alpha,
        beta=settings.bpr_beta,
    )

    from sxm_mobility.scenarios.evaluator import score_graph

    baseline_scores = score_graph(baseline_G)

    # ---- Scenario catalog (prototype examples)
    # You can replace this with generated candidates later.
    edges = list(base_G.edges(keys=True))
    scenarios = []

    # 1) Increase capacity on a few early edges (proxy for widening/signal improvement)
    for i, (u, v, k) in enumerate(edges[:5]):
        scenarios.append(
            IncreaseCapacity(
                name=f"Increase capacity {i+1}",
                description="Prototype: increase capacity on a selected edge",
                u=str(u),
                v=str(v),
                key=int(k),
                pct=0.25,
            )
        )

    # 2) Closure test on one key edge (proxy for incident/roadworks)
    if edges:
        u, v, k = edges[0]
        scenarios.append(
            Closure(
                name="Closure test (first edge)",
                description="Prototype: remove one edge to test fragility",
                u=str(u),
                v=str(v),
                key=int(k),
            )
        )

    # 3) Add a connector between two random nodes (proxy for new link)
    nodes = list(base_G.nodes())
    if len(nodes) >= 2:
        u = str(nodes[0])
        v = str(nodes[-1])
        scenarios.append(
            AddConnector(
                name="Add connector (prototype)",
                description="Prototype: add a hypothetical connector edge",
                u=u,
                v=v,
                length_m=350.0,
                speed_kph=40.0,
                capacity_vph=900.0,
            )
        )

    logger.info("Running {} scenarios", len(scenarios))

    results_rows: list[dict] = []
    details_rows: list[dict] = []

    for s in scenarios:
        res = run_scenario(
            base_graph=base_G,
            od=od,
            scenario=s,
            iters=settings.msa_iters,
            alpha=settings.bpr_alpha,
            beta=settings.bpr_beta,
        )

        scores = res["scores"]
        scenario_dict = res["scenario"]

        row = {
            "scenario_name": scenario_dict.get("name"),
            "scenario_type": s.__class__.__name__,
            "tstt": float(scores.get("tstt", 0.0)),
            "delay": float(scores.get("delay", 0.0)),
            "delta_tstt": float(scores.get("tstt", 0.0)) - float(baseline_scores.get("tstt", 0.0)),
            "delta_delay": float(scores.get("delay", 0.0)) - float(baseline_scores.get("delay", 0.0)),
            "baseline_tstt": float(baseline_scores.get("tstt", 0.0)),
            "baseline_delay": float(baseline_scores.get("delay", 0.0)),
            "od_pairs": len(od),
            "msa_iters": settings.msa_iters,
            "bpr_alpha": settings.bpr_alpha,
            "bpr_beta": settings.bpr_beta,
        }

        # Convenience: positive means improvement (less delay)
        row["delay_improvement"] = -row["delta_delay"]

        results_rows.append(row)

        details_rows.append(
            {
                "scenario_name": scenario_dict.get("name"),
                "scenario_type": s.__class__.__name__,
                "description": scenario_dict.get("description"),
                "params_json": _as_json({k: v for k, v in scenario_dict.items() if k not in {"name", "description"}}),
            }
        )

    df_results = pd.DataFrame(results_rows)
    df_details = pd.DataFrame(details_rows)

    # Rank: biggest delay improvement first
    if not df_results.empty:
        df_results = df_results.sort_values(by=["delay_improvement"], ascending=False)

    out_results = out_dir / "results_scenarios.parquet"
    out_details = out_dir / "scenario_details.parquet"

    df_results.to_parquet(out_results, index=False)
    df_details.to_parquet(out_details, index=False)

    logger.info("Saved scenario summary results to {}", out_results)
    logger.info("Saved scenario details to {}", out_details)


if __name__ == "__main__":
    main()

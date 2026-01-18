from __future__ import annotations

from collections import defaultdict
from loguru import logger

import networkx as nx

from sxm_mobility.assignment.bpr import bpr_time


def update_edge_times(G: nx.MultiDiGraph, alpha: float, beta: float) -> None:
    for _, _, _, data in G.edges(keys=True, data=True):
        t0 = float(data.get("t0", 1.0))
        cap = float(data.get("capacity", 1.0))
        flow = float(data.get("flow", 0.0))
        data["time"] = bpr_time(t0=t0, flow=flow, capacity=cap, alpha=alpha, beta=beta)


def all_or_nothing_assignment(G: nx.MultiDiGraph, od: list[tuple[str, str, float]]) -> dict[tuple[str, str, int], float]:
    """Assign all OD demand to current shortest paths (by edge time)."""

    aux: dict[tuple[str, str, int], float] = defaultdict(float)

    for o, d, demand in od:
        if o not in G or d not in G:
            continue

        path = nx.shortest_path(G, o, d, weight="time")
        for u, v in zip(path[:-1], path[1:]):
            # choose best key among parallel edges
            best_key = min(G[u][v], key=lambda k: float(G[u][v][k].get("time", 1.0)))
            aux[(str(u), str(v), int(best_key))] += float(demand)


    return dict(aux)


def msa_traffic_assignment(
    G: nx.MultiDiGraph,
    od: list[tuple[str, str, float]],
    iters: int = 30,
    alpha: float = 0.15,
    beta: float = 4.0,
) -> nx.MultiDiGraph:
    """Method of Successive Averages (MSA) assignment.

    Returns G with updated edge attributes: flow, time.
    """

    failed = 0
    assigned = 0
    for o, d, demand in od:
        try:
            path = nx.shortest_path(G, o, d, weight="time")
            assigned += 1
            # add demand...
        except Exception:
            failed += 1

    logger.info(f"Assigned OD: {assigned}, Failed OD: {failed}")


    # initialize
    for _, _, _, data in G.edges(keys=True, data=True):
        data["flow"] = float(data.get("flow", 0.0))
        data["time"] = float(data.get("t0", data.get("time", 1.0)))

    for k in range(iters):
        update_edge_times(G, alpha=alpha, beta=beta)
        aux = all_or_nothing_assignment(G, od)

        

        step = 1.0 / (k + 1.0)

        for u, v, key, data in G.edges(keys=True, data=True):
            a = float(aux.get((str(u), str(v), int(key)), 0.0))
            f = float(data.get("flow", 0.0))
            data["flow"] = f + step * (a - f)

    update_edge_times(G, alpha=alpha, beta=beta)
    return G

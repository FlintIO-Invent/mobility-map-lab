from __future__ import annotations

import networkx as nx


def total_system_travel_time(G: nx.MultiDiGraph) -> float:
    return float(sum(float(d.get("flow", 0.0)) * float(d.get("time", 0.0)) for *_, d in G.edges(data=True, keys=True)))


def total_delay(G: nx.MultiDiGraph) -> float:
    return float(
        sum(
            float(d.get("flow", 0.0)) * (float(d.get("time", 0.0)) - float(d.get("t0", d.get("time", 0.0))))
            for *_, d in G.edges(data=True, keys=True)
        )
    )


def top_bottlenecks(G: nx.MultiDiGraph, n: int = 20) -> list[dict]:
    rows = []
    for u, v, k, d in G.edges(keys=True, data=True):
        flow = float(d.get("flow", 0.0))
        cap = float(d.get("capacity", 1.0))
        vc = flow / cap if cap > 0 else 0.0
        delay = flow * (float(d.get("time", 0.0)) - float(d.get("t0", 0.0)))
        rows.append({"u": str(u), "v": str(v), "key": int(k), "flow": flow, "capacity": cap, "v_c": vc, "delay": delay})

    rows.sort(key=lambda r: (r["delay"], r["v_c"]), reverse=True)
    return rows[:n]

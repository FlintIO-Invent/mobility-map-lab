from __future__ import annotations

import math

import networkx as nx


def _safe_float(x, default: float) -> float:
    try:
        return float(x)
    except Exception:
        return default


def add_freeflow_time_and_capacity(
    G: nx.MultiDiGraph,
    default_speed_kph: float = 40.0,
    default_capacity_vph: float = 900.0,
) -> nx.MultiDiGraph:
    """Add baseline edge attributes needed for assignment.

    Adds:
      - t0: free-flow travel time (seconds)
      - capacity: vehicles per hour

    Uses OSMnx edge attributes when available:
      - length (meters)
      - maxspeed (kph)
      - lanes

    Notes:
      - Capacity is a proxy in this prototype; refine with local counts later.
    """

    for _, _, _, data in G.edges(keys=True, data=True):
        length_m = _safe_float(data.get("length"), 50.0)

        # maxspeed can be list/str; try to parse
        maxspeed = data.get("maxspeed")
        if isinstance(maxspeed, list) and maxspeed:
            maxspeed = maxspeed[0]
        if isinstance(maxspeed, str):
            # keep digits
            digits = "".join(ch for ch in maxspeed if ch.isdigit() or ch == ".")
            speed_kph = _safe_float(digits, default_speed_kph)
        else:
            speed_kph = _safe_float(maxspeed, default_speed_kph)

        speed_kph = max(5.0, speed_kph)
        speed_mps = speed_kph * 1000.0 / 3600.0
        t0 = length_m / speed_mps

        lanes = data.get("lanes")
        if isinstance(lanes, list) and lanes:
            lanes = lanes[0]
        lanes_f = max(1.0, _safe_float(lanes, 1.0))

        # Very rough: capacity per lane per hour
        capacity = default_capacity_vph * lanes_f

        data["t0"] = float(t0)
        data["capacity"] = float(capacity)
        data.setdefault("flow", 0.0)
        data.setdefault("time", float(t0))

    return G

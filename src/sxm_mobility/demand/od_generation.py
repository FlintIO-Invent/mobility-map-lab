from __future__ import annotations
import random
from typing import Iterable
import networkx as nx
import random

def random_od(G, n_pairs=250, min_demand=50.0, max_demand=150.0, seed=42):
    rng = random.Random(seed)
    nodes = list(G.nodes)

    od = []
    for _ in range(n_pairs):
        o = rng.choice(nodes)
        d = rng.choice(nodes)
        while d == o:
            d = rng.choice(nodes)

        demand = rng.uniform(min_demand, max_demand)
        od.append((o, d, demand))

    return od

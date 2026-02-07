from __future__ import annotations
import random
from typing import Iterable
import networkx as nx
import random

def random_od(
    G: "nx.Graph",
    n_pairs: int = 250,
    min_demand: float = 50.0,
    max_demand: float = 150.0,
    seed: int = 42,
) -> list[tuple[Any, Any, float]]:
    """Generate random(Because you don’t yet have real travel demand data (mobile-phone OD matrices, traffic counts per zone, surveys, etc.)) 
    origin-destination (OD) demand pairs from a graph's nodes.

    Samples `n_pairs` (origin, destination) node pairs uniformly at random from `G.nodes`,
    ensuring origin != destination, and assigns each pair a random demand value drawn
    uniformly from [`min_demand`, `max_demand`].

    :param G: Input graph whose nodes are used to sample origins and destinations.
    :type G: nx.Graph
    :param n_pairs: Number of OD pairs to generate, defaults to 250.
    :type n_pairs: int, optional
    :param min_demand: Lower bound for the uniform demand draw, defaults to 50.0.
    :type min_demand: float, optional
    :param max_demand: Upper bound for the uniform demand draw, defaults to 150.0.
    :type max_demand: float, optional
    :param seed: Random seed for reproducible sampling, defaults to 42.
    :type seed: int, optional
    :raises ValueError: If `n_pairs` is negative.
    :raises ValueError: If `min_demand` is greater than `max_demand`.
    :raises ValueError: If `G` has fewer than 2 nodes.
    :return: A list of `(origin, destination, demand)` tuples.
    :rtype: list[tuple[Any, Any, float]]

    How you’ll upgrade it later (natural evolution)
        Replace “random OD” with:
        zone-based OD (Airport, Philipsburg, Simpson Bay, etc.)
        weighted by:
            population density
            hotel/POI density
            commuter patterns
            observed traffic counts
    """
    rng = random.Random(seed)
    nodes = list(G.nodes)

    if n_pairs < 0:
        raise ValueError("n_pairs must be >= 0")
    if min_demand > max_demand:
        raise ValueError("min_demand must be <= max_demand")
    if len(nodes) < 2:
        raise ValueError("G must contain at least 2 nodes to generate OD pairs")

    od = []
    for _ in range(n_pairs):
        o = rng.choice(nodes)
        d = rng.choice(nodes)
        while d == o:
            d = rng.choice(nodes)

        demand = rng.uniform(min_demand, max_demand)
        od.append((o, d, demand))

    return od

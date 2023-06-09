import copy
import random
import time
from concurrent.futures import ProcessPoolExecutor

import networkx as nx

from city_road_network.algo.utils import add_passes_count, build_paths, yeild_zone_pairs


def process_cell(args):
    o_zone, d_zone, g, trip_mat, weight, path_starts_ends = args
    count = trip_mat[o_zone, d_zone]
    paths = build_paths(g, o_zone, d_zone, count, weight, path_starts_ends)
    return o_zone, d_zone, paths


def run_naive_simulation(graph, trip_mat, weight, path_starts_ends=None, n=None):
    g = copy.deepcopy(graph)

    edge_attrs = next(iter(g.edges(data=True)))[2]
    if weight not in edge_attrs:
        raise ValueError(f"Weight '{weight}' not in edge attrs: {edge_attrs.keys()}")

    for s, e, edge_data in g.edges(data=True):
        edge_data["passes_count"] = 0
    if n is None:
        n = trip_mat.shape[0]

    mat = [[list() for _ in range(n)] for _ in range(n)]

    start = time.time()
    pairs = sorted(
        yeild_zone_pairs(n, g, trip_mat, weight, path_starts_ends), key=lambda x: x[3][x[0]][x[1]], reverse=True
    )
    with ProcessPoolExecutor() as executor:
        for result in executor.map(process_cell, pairs):
            o_zone, d_zone, paths = result
            mat[o_zone][d_zone] = paths

    print("finished in", time.time() - start)

    g = add_passes_count(g, mat)
    return mat, g

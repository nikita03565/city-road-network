import copy
import time
from concurrent.futures import ProcessPoolExecutor

from city_road_network.algo.common import (
    add_passes_count,
    build_paths,
    recalculate_flow_time,
    yield_zone_pairs,
)
from city_road_network.utils.utils import get_logger

logger = get_logger(__name__)


def process_cell(args):
    o_zone, d_zone, trip_mat, weight, path_starts_ends, g = args
    count = trip_mat[o_zone, d_zone]
    paths = build_paths(g, o_zone, d_zone, count, weight, path_starts_ends)
    return o_zone, d_zone, paths


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def run_smarter_simulation(graph, trip_mat, weight, path_starts_ends=None, n=None, n_chunks=20):
    g = copy.deepcopy(graph)
    edge_attrs = next(iter(g.edges(data=True)))[2]
    if weight not in edge_attrs:
        raise ValueError(f"Weight '{weight}' not in edge attrs: {edge_attrs.keys()}")
    for s, e, edge_data in g.edges(data=True):
        edge_data["passes_count"] = 0
    if n is None:
        n = trip_mat.shape[0]

    size = n * n
    chunk_size = size // n_chunks
    mat = [[list() for _ in range(n)] for _ in range(n)]

    # sort by trip_mat value
    pairs = sorted(
        yield_zone_pairs(n, trip_mat, weight, path_starts_ends), key=lambda x: x[2][x[0]][x[1]], reverse=True
    )
    start = time.time()
    with ProcessPoolExecutor() as executor:
        for chunk in chunks(pairs, chunk_size):
            ext_chunk = [(*c, g) for c in chunk]
            mat_iter = [[list() for _ in range(n)] for _ in range(n)]
            for result in executor.map(process_cell, ext_chunk):
                o_zone, d_zone, paths = result
                mat[o_zone][d_zone] = paths
                mat_iter[o_zone][d_zone] = paths
            g = recalculate_flow_time(add_passes_count(g, mat_iter))
            logger.info("Processed chunk...")
    print("finished in", time.time() - start)

    return mat, g

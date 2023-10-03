import copy
import os
import pickle
import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from itertools import islice

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.wkt import loads

from city_road_network.algo.common import (
    TimedPath,
    add_passes_count,
    recalculate_flow_time,
)
from city_road_network.algo.simulation import (
    NaiveSimulation,
    NaiveSimulationFixedNodes,
    SmarterSimulation,
    SmarterSimulationFixedNodes,
    yield_batches,
    yield_starts_ends,
)
from city_road_network.config import default_crs
from city_road_network.utils.io import read_graph
from city_road_network.utils.map import draw_trips_map
from city_road_network.utils.utils import get_data_subdir, get_html_subdir


def run_naive_simulation(graph, weight, trip_mat=None, old_paths=None, n=None, max_workers=None):
    if max_workers is None:
        max_workers = os.cpu_count()
    g = copy.deepcopy(graph)

    edge_attrs = next(iter(g.edges(data=True)))[2]
    if weight not in edge_attrs:
        raise ValueError(f"Weight '{weight}' not in edge attrs: {edge_attrs.keys()}")

    for s, e, edge_data in g.edges(data=True):
        edge_data["passes_count"] = 0
    if n is None:
        n = trip_mat.shape[0] if trip_mat else len(old_paths)
    else:
        trip_mat = trip_mat[:n, :n]
    mat = [[list() for _ in range(n)] for _ in range(n)]

    start = time.time()
    if trip_mat:
        pairs = yield_batches(trip_mat)
        sim = NaiveSimulation(g, weight)
    if old_paths:
        pairs = yield_starts_ends(old_paths)
        sim = NaiveSimulationFixedNodes(g, weight)

    c = 0
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for result in executor.map(sim.build_paths, pairs):
            c += 1
            print("processed batch", c)
            for built_paths in result:
                mat[built_paths.o_zone][built_paths.d_zone].extend(built_paths.paths)

    print("finished in", time.time() - start)

    g = add_passes_count(g, mat)
    return mat, g


def calc_total_paths(trip_mat: np.array = None, old_paths: list[list[list[TimedPath]]] = None) -> int:
    if trip_mat is not None:
        return trip_mat.sum()
    total_paths = 0
    for row in old_paths:
        for cell in row:
            total_paths += len(cell)
    return total_paths


def take(iterable, n):
    return list(islice(iterable, n))


def chunked(iterable, n):
    iterator = iter(partial(take, iter(iterable), n), [])
    return iterator


def run_smarter_simulation(graph, weight, trip_mat=None, old_paths=None, n=None, max_workers=None, n_recalc=20):
    if max_workers is None:
        max_workers = os.cpu_count()
    g = copy.deepcopy(graph)

    edge_attrs = next(iter(g.edges(data=True)))[2]
    if weight not in edge_attrs:
        raise ValueError(f"Weight '{weight}' not in edge attrs: {edge_attrs.keys()}")

    for s, e, edge_data in g.edges(data=True):
        edge_data["passes_count"] = 0
    if n is None:
        n = trip_mat.shape[0] if trip_mat is not None else len(old_paths)
    else:
        trip_mat = trip_mat[:n, :n]

    total_paths = calc_total_paths(trip_mat, old_paths)
    per_iteration = total_paths // n_recalc
    batch_size = per_iteration // max_workers
    print(total_paths, per_iteration, batch_size)

    mat = [[list() for _ in range(n)] for _ in range(n)]

    start = time.time()
    if trip_mat is not None:
        batches = yield_batches(trip_mat, batch_size=batch_size)
        sim = SmarterSimulation(g, weight)
    if old_paths is not None:
        batches = yield_starts_ends(old_paths, batch_size=batch_size)
        sim = SmarterSimulationFixedNodes(g, weight)
    chunks = chunked(batches, max_workers)

    # Recalculate travel time
    c = 0
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for chunk in chunks:
            mat_iter = [[list() for _ in range(n)] for _ in range(n)]
            for result in executor.map(sim.build_paths, chunk):
                c += 1
                print("processed batch", c)
                for built_paths in result:
                    mat[built_paths.o_zone][built_paths.d_zone].extend(built_paths.paths)
                    mat_iter[built_paths.o_zone][built_paths.d_zone].extend(built_paths.paths)
            g = recalculate_flow_time(add_passes_count(g, mat_iter))
            print("Processed chunk...")
    print("finished in", time.time() - start)
    return mat, g


if __name__ == "__main__":
    # loading data...
    city_name = "spb"
    data_dir = get_data_subdir(city_name)
    html_dir = get_html_subdir(city_name)
    G = read_graph(os.path.join(data_dir, "nodelist_upd.csv"), os.path.join(data_dir, "edgelist_upd.csv"))
    trip_mat = np.load(os.path.join(data_dir, "trip_mat.npy"))

    with open(os.path.join(data_dir, "paths_by_flow_time_s_1695987799.pkl"), "rb") as f:
        old_paths = pickle.load(f)

    zones_df = pd.read_csv(os.path.join(data_dir, "zones_upd.csv"), index_col=0)
    zones_df["geometry"] = zones_df["geometry"].apply(loads)
    zones_gdf = gpd.GeoDataFrame(zones_df, crs=default_crs)

    # running actual simulation
    weight = "flow_time (s)"  # or "length (m)"

    all_paths, new_graph = run_smarter_simulation(G, weight, trip_mat=None, old_paths=old_paths)
    # checking that all paths have been generated
    # for i in range(len(all_paths)):
    #     for j in range(len(all_paths)):
    #         assert len(all_paths[i][j]) == trip_mat[i, j]

    # saving map and paths
    ts = int(time.time())
    map = draw_trips_map(new_graph)
    clean_weight = weight.replace("(", "").replace(")", "").replace(" ", "_")
    filename = f"paths_by_{clean_weight}_{ts}"
    map.save(os.path.join(html_dir, f"{filename}.html"))
    with open(os.path.join(data_dir, f"{filename}.pkl"), "wb") as f:
        pickle.dump(all_paths, f)

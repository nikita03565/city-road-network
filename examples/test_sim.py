import copy
import math
import os
import pickle
import time
from concurrent.futures import ProcessPoolExecutor

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.wkt import loads

from city_road_network.algo.common import (
    add_passes_count,
    # build_paths,
    # yield_zone_pairs,
)
from city_road_network.algo.simulation import (
    BaseSimulation,
    yield_batches,
    # yield_starts_ends,
)
from city_road_network.config import default_crs
from city_road_network.utils.io import read_graph
from city_road_network.utils.map import draw_trips_map
from city_road_network.utils.utils import get_data_subdir, get_html_subdir


def run_naive_simulation(graph, trip_mat, weight, n=None, max_workers=None):
    if max_workers is None:
        max_workers = os.cpu_count()
    g = copy.deepcopy(graph)

    edge_attrs = next(iter(g.edges(data=True)))[2]
    if weight not in edge_attrs:
        raise ValueError(f"Weight '{weight}' not in edge attrs: {edge_attrs.keys()}")

    for s, e, edge_data in g.edges(data=True):
        edge_data["passes_count"] = 0
    if n is None:
        n = trip_mat.shape[0]
    else:
        trip_mat = trip_mat[:n, :n]
    mat = [[list() for _ in range(n)] for _ in range(n)]

    start = time.time()
    pairs = yield_batches(trip_mat)  # yield_zone_pairs(n, g, trip_mat, weight, path_starts_ends)
    estimated_batches = math.ceil(trip_mat.sum() / 1000)
    sim = BaseSimulation(g, weight)
    c = 0
    print(f"{estimated_batches=}")
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for result in executor.map(sim.build_paths, pairs):
            c += 1
            print("processed batch", c, "/", estimated_batches)
            for built_paths in result:
                mat[built_paths.o_zone][built_paths.d_zone].extend(built_paths.paths)

    print("finished in", time.time() - start)

    g = add_passes_count(g, mat)
    return mat, g


if __name__ == "__main__":
    # loading data...
    city_name = "spb"
    data_dir = get_data_subdir(city_name)
    html_dir = get_html_subdir(city_name)
    G = read_graph(os.path.join(data_dir, "nodelist_upd.csv"), os.path.join(data_dir, "edgelist_upd.csv"))
    trip_mat = np.load(os.path.join(data_dir, "trip_mat.npy"))

    zones_df = pd.read_csv(os.path.join(data_dir, "zones_upd.csv"), index_col=0)
    zones_df["geometry"] = zones_df["geometry"].apply(loads)
    zones_gdf = gpd.GeoDataFrame(zones_df, crs=default_crs)

    # running actual simulation
    weight = "flow_time (s)"  # or "length (m)"

    all_paths, new_graph = run_naive_simulation(G, trip_mat, weight=weight)
    # checking that all paths have been generated
    for i in range(len(all_paths)):
        for j in range(len(all_paths)):
            assert len(all_paths[i][j]) == trip_mat[i, j]

    # saving map and paths
    ts = int(time.time())
    map = draw_trips_map(new_graph)
    clean_weight = weight.replace("(", "").replace(")", "").replace(" ", "_")
    filename = f"paths_by_{clean_weight}_{ts}"
    map.save(os.path.join(html_dir, f"{filename}.html"))
    with open(os.path.join(data_dir, f"{filename}.pkl"), "wb") as f:
        pickle.dump(all_paths, f)

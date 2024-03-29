import os
import pickle
import time

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.wkt import loads

from city_road_network.algo.simulation import NaiveSimulation
from city_road_network.config import default_crs
from city_road_network.utils.io import read_graph
from city_road_network.utils.map import draw_trips_map
from city_road_network.utils.utils import get_data_subdir, get_html_subdir


def run_naive_simulation(graph, weight, trip_mat=None, old_paths=None, n=None, batch_size=1000, max_workers=None):
    sim = NaiveSimulation(graph, weight)
    res = sim.run(trip_mat, old_paths, n, max_workers, batch_size)
    return res


if __name__ == "__main__":
    # loading data...
    city_name = "spb"
    data_dir = get_data_subdir(city_name)
    html_dir = get_html_subdir(city_name)
    G = read_graph(os.path.join(data_dir, "nodelist_upd.csv"), os.path.join(data_dir, "edgelist_upd.csv"))
    trip_mat = np.load(os.path.join(data_dir, "trip_mat.npy"))

    # if you want you can load old paths like this:
    # with open(os.path.join(data_dir, "paths_by_flow_time_s_1696597874.pkl"), "rb") as f:
    #    old_paths = pickle.load(f)

    zones_df = pd.read_csv(os.path.join(data_dir, "zones_upd.csv"), index_col=0)
    zones_df["geometry"] = zones_df["geometry"].apply(loads)
    zones_gdf = gpd.GeoDataFrame(zones_df, crs=default_crs)

    # running actual simulation
    weight = "flow_time (s)"  # or "length (m)"
    all_paths, new_graph = run_naive_simulation(G, weight, trip_mat)

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

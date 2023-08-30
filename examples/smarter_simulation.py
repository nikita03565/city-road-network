import os
import pickle
import time

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.wkt import loads

from city_road_network.algo.smarter_sim import run_smarter_simulation
from city_road_network.config import default_crs
from city_road_network.utils.io import read_graph
from city_road_network.utils.map import draw_trips_map
from city_road_network.utils.utils import get_data_subdir, get_html_subdir

if __name__ == "__main__":
    # loading data...
    city_name = "moscow"
    data_dir = get_data_subdir(city_name)
    html_dir = get_html_subdir(city_name)

    G = read_graph(
        os.path.join(data_dir, "nodelist_upd.csv"),
        os.path.join(data_dir, "edgelist_upd.csv"),
    )
    trip_mat = np.load(os.path.join(data_dir, "trip_mat.npy"))

    zones_df = pd.read_csv(os.path.join(data_dir, "zones_upd.csv"), index_col=0)
    zones_df["geometry"] = zones_df["geometry"].apply(loads)
    zones_gdf = gpd.GeoDataFrame(zones_df, crs=default_crs)

    # running actual simulation
    weight = "flow_time (s)"  # or "length (m)"
    all_paths, new_graph = run_smarter_simulation(G, trip_mat, weight=weight)

    # checking that all paths have been generated
    for i in range(len(all_paths)):
        for j in range(len(all_paths)):
            assert len(all_paths[i][j]) == trip_mat[i, j]

    # saving map and paths
    ts = int(time.time())
    map = draw_trips_map(new_graph)
    clean_weight = weight.replace("(", "").replace(")", "").replace(" ", "")
    filename = f"smarter_paths_by_{clean_weight}_{ts}"
    map.save(os.path.join(html_dir, f"{filename}.html"))
    with open(os.path.join(data_dir, f"{filename}.pkl"), "wb") as f:
        pickle.dump(all_paths, f)

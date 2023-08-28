import os

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import wkt

from city_road_network.algo.gravity_model import (
    get_attr_error,
    get_prod_error,
    run_gravity_model,
)
from city_road_network.config import default_crs
from city_road_network.utils.utils import get_data_subdir

if __name__ == "__main__":
    city_name = "spb"
    data_dir = get_data_subdir(city_name)

    df_zones = pd.read_csv(os.path.join(data_dir, "zones_upd.csv"), index_col=0)
    df_zones["geometry"] = df_zones["geometry"].apply(wkt.loads)
    df_zones["centroid"] = df_zones["centroid"].apply(wkt.loads)

    df_zones.loc[df_zones["production"] == 0, "production"] = 1
    df_zones.loc[df_zones["poi_attraction"] == 0, "poi_attraction"] = 1

    zones_gdf = gpd.GeoDataFrame(df_zones, crs=default_crs)

    prod_array = np.array(zones_gdf["production"])
    attr_array = np.array(zones_gdf["poi_attraction"])

    trip_mat = run_gravity_model(zones_gdf)

    prod_error = get_prod_error(trip_mat, prod_array)
    attr_error = get_attr_error(trip_mat, attr_array)
    print(prod_error, attr_error)

    np.save(os.path.join(data_dir, "trip_mat"), trip_mat)

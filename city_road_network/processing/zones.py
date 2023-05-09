import os

import geopandas as gpd
import pandas as pd
from shapely import wkt

from city_road_network.config import (
    avg_daily_trips_per_veh,
    avg_household_size,
    avg_vehs_per_household,
    default_crs,
)
from city_road_network.utils.utils import calc_poi_attraction, get_data_subdir, get_logger
from city_road_network.writers.csv import save_dataframe

logger = get_logger(__name__)


def process_zones(city_name=None):
    data_dir = get_data_subdir(city_name)
    zones_df = pd.read_csv(os.path.join(data_dir, "zones.csv"), index_col=0)
    poi_df = pd.read_csv(os.path.join(data_dir, "poi.csv"), index_col=0)
    pop_df = pd.read_csv(os.path.join(data_dir, "population.csv"), dtype={"value": float}, index_col=0)
    nodes_df = pd.read_csv(os.path.join(data_dir, "nodelist.csv"), index_col=0)

    for df in [zones_df, poi_df, pop_df, nodes_df]:
        df["geometry"] = df["geometry"].apply(wkt.loads)

    zones_gdf = gpd.GeoDataFrame(zones_df, crs=default_crs)
    poi_gdf = gpd.GeoDataFrame(poi_df, crs=default_crs)
    pop_gdf = gpd.GeoDataFrame(pop_df, crs=default_crs)
    nodes_gdf = gpd.GeoDataFrame(nodes_df, crs=default_crs)

    nodes_gdf["zones"] = ""

    for idx, zone in zones_gdf.iterrows():
        nodes_gdf.loc[nodes_gdf.within(zone["geometry"]) | nodes_gdf.touches(zone["geometry"]), "zones"] += f"{idx},"

    nodes_gdf["zones"] = nodes_gdf["zones"].str.rstrip(",")

    zones_gdf["poi_count"] = 0
    zones_gdf["poi_attraction"] = 0
    for _, point in poi_gdf.iterrows():
        mask = zones_gdf.contains(point["geometry"]).astype(int)
        zones_gdf["poi_count"] += mask

        attr = calc_poi_attraction(point)
        zones_gdf["poi_attraction"] += mask * attr

    zones_gdf["pop"] = 0
    for _, point in pop_gdf.iterrows():
        zones_gdf["pop"] += zones_gdf.contains(point["geometry"]).astype(int) * point["value"]

    zones_gdf["households"] = zones_gdf["pop"] / avg_household_size
    zones_gdf["vehicles"] = zones_gdf["households"] * avg_vehs_per_household
    zones_gdf["production"] = zones_gdf["vehicles"] * avg_daily_trips_per_veh
    zones_gdf["production"] = zones_gdf["production"] / 16  # 16 hours = 24 full hours - 8 hours in the night

    logger.info("Total number of vehicles %s", zones_gdf["vehicles"].sum())
    logger.info("Total production before %s", zones_gdf["production"].sum())
    logger.info("Total attraction before %s", zones_gdf["poi_attraction"].sum())
    attr_prod_ratio = zones_gdf["poi_attraction"].sum() / zones_gdf["production"].sum()

    zones_gdf["poi_attraction"] = zones_gdf["poi_attraction"] / attr_prod_ratio

    logger.info("Total production after %s", zones_gdf["production"].sum())
    logger.info("Total attraction after %s", zones_gdf["poi_attraction"].sum())

    zones_gdf["centroid"] = zones_gdf.centroid

    for idx, point in nodes_gdf[nodes_gdf["zones"] == ""].iterrows():
        closest_zone = zones_gdf.exterior.distance(point["geometry"]).idxmin()
        nodes_gdf.loc[idx, "zones"] += str(closest_zone)
    assert nodes_gdf[nodes_gdf["zones"] == ""].empty
    nodes_gdf["zones"] = nodes_gdf["zones"].str.split(",")
    save_dataframe(nodes_gdf, "nodelist_upd.csv", city_name)
    save_dataframe(zones_gdf, "zones_upd.csv", city_name)
    return nodes_gdf, zones_gdf

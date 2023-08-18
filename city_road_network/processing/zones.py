import os


import geopandas as gpd
import pandas as pd
from shapely import wkt

from city_road_network.config import (
    default_avg_daily_trips_per_veh,
    default_avg_household_size,
    default_avg_vehs_per_household,
    default_crs,
)
from city_road_network.utils.utils import (
    calc_poi_attraction,
    get_data_subdir,
    get_logger,
)
from city_road_network.writers.csv import save_dataframe

logger = get_logger(__name__)


def process_zones(
    city_name: str | None = None,
    avg_hh_size: float | None = None,
    avg_vehs_per_hh: float | None = None,
    avg_trips_per_veh: float | None = None,
):
    """Distributes graph nodes, points of interest and population to zones. Estimates attraction and production for zones."""
    if avg_hh_size is None:
        avg_hh_size = default_avg_household_size
    if avg_vehs_per_hh is None:
        avg_vehs_per_hh = default_avg_vehs_per_household
    if avg_trips_per_veh is None:
        avg_trips_per_veh = default_avg_daily_trips_per_veh
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

    nodes_gdf["zone"] = None
    poi_gdf["zone"] = None

    for idx, zone in zones_gdf.iterrows():
        nodes_gdf.loc[nodes_gdf.within(zone["geometry"]) | nodes_gdf.touches(zone["geometry"]), "zone"] = idx
        poi_gdf.loc[poi_gdf.within(zone["geometry"]) | poi_gdf.touches(zone["geometry"]), "zone"] = idx

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

    zones_gdf["households"] = zones_gdf["pop"] / avg_hh_size
    zones_gdf["vehicles"] = zones_gdf["households"] * avg_vehs_per_hh
    zones_gdf["production"] = zones_gdf["vehicles"] * avg_trips_per_veh
    zones_gdf["production"] = zones_gdf["production"] / 24

    logger.info("Total number of vehicles %s", zones_gdf["vehicles"].sum())
    logger.info("Total production before %s", zones_gdf["production"].sum())
    logger.info("Total attraction before %s", zones_gdf["poi_attraction"].sum())
    attr_prod_ratio = zones_gdf["poi_attraction"].sum() / zones_gdf["production"].sum()

    zones_gdf["poi_attraction"] = zones_gdf["poi_attraction"] / attr_prod_ratio

    logger.info("Total production after %s", zones_gdf["production"].sum())
    logger.info("Total attraction after %s", zones_gdf["poi_attraction"].sum())

    zones_gdf["centroid"] = zones_gdf.centroid

    for idx, point in nodes_gdf[nodes_gdf["zone"].isna()].iterrows():
        closest_zone = zones_gdf.exterior.distance(point["geometry"]).idxmin()
        nodes_gdf.loc[idx, "zone"] = closest_zone
    assert nodes_gdf[nodes_gdf["zone"].isna()].empty

    save_dataframe(nodes_gdf, "nodelist_upd.csv", city_name)
    save_dataframe(zones_gdf, "zones_upd.csv", city_name)
    save_dataframe(poi_gdf, "poi_upd.csv", city_name)
    return nodes_gdf, zones_gdf

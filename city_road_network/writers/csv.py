import copy
import csv
import os

import geopandas as gpd
import networkx as nx
import pandas as pd
from shapely import Point

from city_road_network.downloaders.osm import OSMData
from city_road_network.utils.utils import get_data_subdir, get_logger

logger = get_logger(__name__)


def save_dataframe(df: pd.DataFrame | gpd.GeoDataFrame, filename: str, city_name: str | None = None):
    """Saves DataFrame to subdirecrory with name `city_name` and name `filename`"""
    dir_name = get_data_subdir(city_name)
    full_name = os.path.join(dir_name, filename)
    df.to_csv(full_name)
    logger.info("Saved dataframe to %s", os.path.abspath(full_name))


def save_graph(graph: nx.MultiDiGraph, city_name: str | None = None):
    """Saves Graph to csv files 'nodelist.csv' and 'edgelist.csv' in `city_name` subdirectory."""
    graph = copy.deepcopy(graph)
    edges_data_list = []

    for start_id, end_id, key, edge_data in graph.edges(data=True, keys=True):
        edges_data_list.append({"start_node": start_id, "end_node": end_id, "key": key, **edge_data})

    node_data_list = []

    for node_id, node_data in graph.nodes(data=True):
        node_data["geometry"] = Point(node_data["lon"], node_data["lat"])
        node_data_list.append({"id": node_id, **node_data})

    edges_df = pd.DataFrame(edges_data_list)
    nodes_df = pd.DataFrame(node_data_list)
    save_dataframe(edges_df, "edgelist.csv", city_name=city_name)
    save_dataframe(nodes_df, "nodelist.csv", city_name=city_name)


def save_osm_data(data: OSMData, city_name: str | None = None):
    """Wrapper function to save all OSM data"""
    save_graph(data.graph, city_name=city_name)
    save_dataframe(data.poi, "poi.csv", city_name=city_name)
    save_dataframe(data.zones, "zones.csv", city_name=city_name)

import colorsys
import json
import os
import time
from ast import literal_eval
from collections.abc import Callable

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd

from city_road_network.config import (
    default_crs,
    default_edge_export_keys,
    default_node_export_keys,
    highway_color_mapping,
    zones_color_map,
)
from city_road_network.utils.io import get_edgelist_from_graph, get_nodelist_from_graph
from city_road_network.utils.utils import get_geojson_subdir, get_logger

logger = get_logger(__name__)


def filter_empty(attrs: dict) -> dict:
    return {k: v for k, v in attrs.items() if v is not None}


def filter_keys(attrs: dict, allowed_keys: list[str]) -> dict:
    return {k: v for k, v in attrs.items() if k in allowed_keys}


def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % rgb


def get_pop_color(feature: dict, vmax: int = 600):
    value = feature["properties"]["value"]
    ratio = min(value / vmax, 1)
    b_g = int(255 * (1 - ratio))
    b_g = min(b_g, 200)
    return rgb_to_hex((255, b_g, b_g))


def get_mapping_color_getter(mapping: dict, key: str, default: str) -> Callable:
    def mapping_color_getter(feature, *args, **kwargs):
        value = feature[key]
        return mapping.get(value, default)

    return mapping_color_getter


def get_fixed_color_getter(color: str, *args, **kwargs) -> Callable:
    def fixed_color_getter(*args, **kwargs):
        return color

    return fixed_color_getter


def highway_color_getter(feature: dict) -> str:
    highway_raw = feature["properties"]["highway"]
    if isinstance(highway_raw, list):
        highway = highway_raw[0]
    else:
        highway = highway_raw if not highway_raw.startswith("[") else literal_eval(highway_raw)[0]
    color = highway_color_mapping.get(highway, "#B2BEB5")
    return color


def defloat(x):
    return tuple(int(255 * i) for i in x)


def _build_gradient(n: int = 1000):
    """Creates yellow to red gradient"""
    hsv = [(h, 1, 1) for h in np.linspace(0.29, 0.04, n)]
    rgb = [colorsys.hsv_to_rgb(*tup) for tup in hsv]

    # To draw gradient use this:
    # n = 100
    # rgb = np.array(_build_gradient(n=n))
    # rgb = rgb.reshape((1, n, 3))
    # rgb = np.tile(rgb, (n, 1, 1))
    # plt.imshow(rgb)
    # plt.show()
    return [defloat(x) for x in rgb]


def get_occupancy_color_getter(gradient: list | None = None, by_abs_value=False):
    if gradient is None:
        gradient = _build_gradient()

    def occupancy_color_getter(feature: dict) -> str:
        if by_abs_value:
            color_idx = min(feature["properties"]["passes_count"], len(gradient) - 1)
        else:  # by occupied percentage
            color_idx = min(int(feature["properties"]["capacity_occupied"] * len(gradient)), len(gradient) - 1)
        color_rgb = gradient[color_idx]
        return rgb_to_hex(color_rgb)

    return occupancy_color_getter


def _save_file(data, default_name_template, filename=None, city_name=None):
    name = filename
    if name is None:
        ts = int(time.time())
        name = default_name_template.format(ts=ts)
    json_dir = get_geojson_subdir(city_name)
    full_name = os.path.join(json_dir, name)
    with open(full_name, "w") as f:
        f.write(json.dumps(data))
    logger.info("Saved file %s", os.path.abspath(full_name))


def export_df(
    df: pd.DataFrame | gpd.GeoDataFrame,
    keys: list[str] | None = None,
    color_getter: Callable | None = None,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
    default_filename: str | None = None,
) -> dict:
    if not isinstance(df, gpd.GeoDataFrame):
        df["geometry"] = gpd.GeoSeries.from_wkt(df["geometry"])
        nodes_gdf = gpd.GeoDataFrame(df, crs=default_crs)
    else:
        nodes_gdf = df
    if "id" not in nodes_gdf.columns:
        nodes_gdf["id"] = nodes_gdf.index
    json_data_string = nodes_gdf.to_json()
    json_data = json.loads(json_data_string)

    for feature in json_data["features"]:
        if keys is not None:
            feature["properties"] = filter_empty(filter_keys(feature["properties"], keys))
        if color_getter is not None:
            feature["properties"]["display_color"] = color_getter(feature)

    if save:
        _save_file(json_data, default_name_template=default_filename, filename=filename, city_name=city_name)
    return json_data


def export_nodes(
    nodes_df: pd.DataFrame | gpd.GeoDataFrame,
    keys: list[str] | None = None,
    color_getter: Callable | None = None,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
) -> dict:
    if color_getter is None:
        color_getter = get_fixed_color_getter("blue")
    return export_df(
        df=nodes_df,
        keys=keys,
        color_getter=color_getter,
        save=save,
        filename=filename,
        city_name=city_name,
        default_filename="nodes_{ts}.json",
    )


def export_edges(
    edges_df: pd.DataFrame | gpd.GeoDataFrame,
    keys: list[str] | None = None,
    color_getter: Callable | None = None,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
) -> dict:
    if color_getter is None:
        color_getter = highway_color_getter
    return export_df(
        df=edges_df,
        keys=keys,
        color_getter=color_getter,
        save=save,
        filename=filename,
        city_name=city_name,
        default_filename="edges_{ts}.json",
    )


def export_zones(
    zones_df: pd.DataFrame | gpd.GeoDataFrame,
    keys: list[str] | None = None,
    color_getter: Callable | None = None,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
) -> dict:
    if color_getter is None:
        color_getter = get_mapping_color_getter(zones_color_map, "id", "#fc4503")
    return export_df(
        df=zones_df,
        keys=keys,
        color_getter=color_getter,
        save=save,
        filename=filename,
        city_name=city_name,
        default_filename="zones_{ts}.json",
    )


def export_population(
    pop_df: pd.DataFrame | gpd.GeoDataFrame,
    keys: list[str] | None = None,
    color_getter: Callable | None = None,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
) -> dict:
    if color_getter is None:
        color_getter = get_pop_color
    return export_df(
        df=pop_df,
        keys=keys,
        color_getter=color_getter,
        save=save,
        filename=filename,
        city_name=city_name,
        default_filename="pop_{ts}.json",
    )


def export_poi(
    poi_df: pd.DataFrame | gpd.GeoDataFrame,
    keys: list[str] | None = None,
    color_getter: Callable | None = None,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
) -> dict:
    if color_getter is None:
        color_getter = get_fixed_color_getter("#32a852")
    return export_df(
        df=poi_df,
        keys=keys,
        color_getter=color_getter,
        save=save,
        filename=filename,
        city_name=city_name,
        default_filename="poi_{ts}.json",
    )


def export_graph(
    graph: nx.DiGraph,
    node_export_keys: list[str] | None = None,
    edge_export_keys: list[str] | None = None,
    save: bool = False,
    nodes_filename: str | None = None,
    edges_filename: str | None = None,
    city_name: str | None = None,
):
    if node_export_keys is None:
        node_export_keys = default_node_export_keys
    if edge_export_keys is None:
        edge_export_keys = default_edge_export_keys

    nodes_df = get_nodelist_from_graph(graph)
    edges_df = get_edgelist_from_graph(graph)

    nodes_dict = export_nodes(
        nodes_df=nodes_df,
        keys=node_export_keys,
        save=save,
        city_name=city_name,
        filename=nodes_filename,
    )
    edges_dict = export_edges(
        edges_df=edges_df,
        keys=edge_export_keys,
        save=save,
        city_name=city_name,
        filename=edges_filename,
    )
    return nodes_dict, edges_dict

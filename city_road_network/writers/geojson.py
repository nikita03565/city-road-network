import json
import os
import time
from ast import literal_eval

import networkx as nx
import pandas as pd

from city_road_network.config import (
    default_edge_export_keys,
    default_node_export_keys,
    highway_color_mapping,
)
from city_road_network.utils.io import get_edgelist_from_graph, get_nodelist_from_graph
from city_road_network.utils.utils import get_geojson_subdir


def filter_empty(attrs: dict) -> dict:
    return {k: v for k, v in attrs.items() if v is not None}


def filter_keys(attrs: dict, allowed_keys: list[str]) -> dict:
    return {k: v for k, v in attrs.items() if k in allowed_keys}


def export_nodes(
    nodes_df: pd.DataFrame,
    keys: list[str],
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
) -> dict:
    nodes = {"type": "FeatureCollection", "features": []}

    for _, node in nodes_df.iterrows():
        all_attrs = node.to_dict()
        attrs = filter_empty(filter_keys(all_attrs, keys))
        nodes["features"].append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [node["lon"], node["lat"]]},
                "properties": {**attrs, "color": "blue"},
            }
        )

    if save:
        name = filename
        if name is None:
            ts = int(time.time())
            name = f"nodes_{ts}.json"
        json_dir = get_geojson_subdir(city_name)
        with open(os.path.join(json_dir, name), "w") as f:
            f.write(json.dumps(nodes))
    return nodes


def export_edges(
    edges_df: pd.DataFrame,
    nodes_df: pd.DataFrame,
    keys: list[str],
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
) -> dict:
    edges = {"type": "FeatureCollection", "features": []}

    for _, edge in edges_df.iterrows():
        all_attrs = edge.to_dict()
        attrs = filter_empty(filter_keys(all_attrs, keys))

        start_node = nodes_df[nodes_df["id"] == edge["start_node"]].iloc[0]
        end_node = nodes_df[nodes_df["id"] == edge["end_node"]].iloc[0]

        highway_raw = edge["highway"]
        if isinstance(highway_raw, list):
            highway = highway_raw[0]
        else:
            highway = highway_raw if not highway_raw.startswith("[") else literal_eval(highway_raw)[0]
        color = highway_color_mapping.get(highway, "#B2BEB5")
        edges["features"].append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [start_node["lon"], start_node["lat"]],
                        [end_node["lon"], end_node["lat"]],
                    ],
                },
                "properties": {**attrs, "color": color},
            }
        )

    if save:
        name = filename
        if name is None:
            ts = int(time.time())
            name = f"edges_{ts}.json"
        json_dir = get_geojson_subdir(city_name)
        with open(os.path.join(json_dir, name), "w") as f:
            f.write(json.dumps(edges))
    return edges


def export_zones(
    zones_df: pd.DataFrame,
    keys: list[str],
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
) -> dict:
    pass


def export_population(
    pop_df: pd.DataFrame, keys: list[str], save: bool = False, filename: str | None = None, city_name: str | None = None
) -> dict:
    pass


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
    # TODO BUILD NAME WITH SAME TS HERE??
    nodes_dict = export_nodes(nodes_df, node_export_keys, save=save, city_name=city_name, filename=nodes_filename)
    edges_dict = export_edges(
        edges_df, nodes_df, edge_export_keys, save=save, city_name=city_name, filename=edges_filename
    )
    return nodes_dict, edges_dict

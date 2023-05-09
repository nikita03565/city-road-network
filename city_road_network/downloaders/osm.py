from typing import NamedTuple

import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandas as pd
from osmnx import downloader, geometries_from_polygon, settings
from shapely import MultiPolygon, Polygon

from city_road_network.config import (
    amenity_rates,
    default_crs,
    default_osm_filter,
    landuse_rates,
    shop_rates,
    whitelist_node_attrs,
    whitelist_way_attrs,
)
from city_road_network.utils.utils import get_cache_subdir, get_first_coord

settings.use_cache = True
settings.useful_tags_node = list(set(settings.useful_tags_node) | whitelist_node_attrs)
settings.useful_tags_way = list(set(settings.useful_tags_way) | whitelist_way_attrs)
settings.cache_folder = get_cache_subdir()


class OSMData(NamedTuple):
    graph: nx.MultiDiGraph
    poi: gpd.GeoDataFrame
    zones: gpd.GeoDataFrame


def _get_poly_coord_str(poly: Polygon) -> str:
    strings = [" ".join(map(str, reversed(c))) for c in poly.exterior.coords]
    return " ".join(strings)


def _create_poly_from_response(members: dict) -> Polygon:
    G = nx.Graph(crs=default_crs)
    for member in members:
        if member["type"] != "way":
            continue
        geometry = member["geometry"]
        for node in geometry:
            G.add_node(f'{node["lat"]}_{node["lon"]}', lat=node["lat"], lon=node["lon"])
        for node_idx in range(len(geometry) - 1):
            u = geometry[node_idx]
            v = geometry[node_idx + 1]
            G.add_edge(f'{u["lat"]}_{u["lon"]}', f'{v["lat"]}_{v["lon"]}')
    if not nx.is_connected(G):
        cc = max(nx.connected_components(G), key=len)
        G = G.subgraph(cc).copy()
    cycles = nx.simple_cycles(G)
    out_polygon = Polygon()
    for cycle in cycles:
        sub = G.subgraph(cycle).copy()
        dfs_edges = list(nx.dfs_edges(sub))
        polygon_coords = []
        for s, e in dfs_edges:
            node = sub.nodes[s]
            polygon_coords.append(tuple([node["lon"], node["lat"]]))
        last_node = sub.nodes[e]
        polygon_coords.append(tuple([last_node["lon"], last_node["lat"]]))
        polygon = Polygon(polygon_coords)
        out_polygon = out_polygon.union(polygon)
    assert polygon.is_valid
    return out_polygon


def get_relation_poly(relation_id: int | str) -> Polygon:
    payload = {"data": f"[out:json][timeout:180];rel({relation_id});out geom;"}
    response = downloader.overpass_request(data=payload)
    poly = _create_poly_from_response(response["elements"][0]["members"])
    return poly


def get_admin_boundaries(poly: Polygon | MultiPolygon, admin_level: int | str = 8) -> gpd.GeoDataFrame:
    poly_str_list = []
    if isinstance(poly, MultiPolygon):
        for poly_part in poly.geoms:
            poly_str_list.append(_get_poly_coord_str(poly_part))
    else:
        poly_str_list.append(_get_poly_coord_str(poly))
    dfs = []
    for poly_str in poly_str_list:
        payload_relations = {
            "data": (
                f"[out:json]"
                f"[timeout:180];"
                f"rel[admin_level={admin_level}]"
                f"[type=boundary]"
                f"[boundary=administrative](poly:'{poly_str}');"
                f"out geom;"
            )
        }
        response = downloader.overpass_request(data=payload_relations)

        data_list = []
        for entry in response["elements"]:
            data_list.append({"name": entry["tags"]["name"], "geometry": _create_poly_from_response(entry["members"])})
        if data_list:
            dfs.append(gpd.GeoDataFrame(data_list, crs=default_crs))
    gdf = gpd.GeoDataFrame(pd.concat(dfs, ignore_index=True), crs=dfs[0].crs)
    return gdf


def _get_tags(tag_dict: dict) -> list:
    return [key for key in tag_dict if tag_dict[key]]


def get_poi(poly: Polygon) -> gpd.GeoDataFrame:
    payload = {
        "amenity": _get_tags(amenity_rates),
        "shop": _get_tags(shop_rates),
        "landuse": _get_tags(landuse_rates),
    }
    raw_df = geometries_from_polygon(poly, payload)
    desired_cols = ["geometry", "name", "amenity", "landuse", "shop"]
    df = raw_df[desired_cols].reset_index()

    df["geometry"] = df["geometry"].apply(get_first_coord)
    return df


def get_graph(poly: Polygon) -> nx.MultiDiGraph:
    graph = ox.graph_from_polygon(poly, custom_filter=default_osm_filter)
    for node_id, node_data in graph.nodes(data=True):
        if ("lat" not in node_data) or ("lon" not in node_data):
            node_data["lat"] = node_data["y"]
            node_data["lon"] = node_data["x"]
    return graph


def get_osm_data(poly: Polygon) -> OSMData:
    graph = get_graph(poly)
    poi = get_poi(poly)
    zones = get_admin_boundaries(poly)
    return OSMData(graph, poi, zones)

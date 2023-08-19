from typing import NamedTuple

import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandas as pd
from osmnx import features_from_polygon, settings
from osmnx._overpass import _overpass_request as overpass_request
from shapely import MultiPolygon, Polygon

from city_road_network.config import (
    amenity_rates,
    default_crs,
    landuse_rates,
    shop_rates,
    timeout,
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
    """Transforms shapely Polygon to coordinate string that Overpass API accepts

    :param poly: Polygon describing boundaries of an area of interest.
    :type poly: Polygon
    :return: Coordinate string ready to be used in Overpass API query.
    :rtype: str
    """
    strings = [" ".join(map(str, reversed(c))) for c in poly.exterior.coords]
    return " ".join(strings)


def _create_poly_from_response(members: dict) -> Polygon:
    """Creates shapely Polygon from Overpass API's response

    :param members: The main part of a response containing ways and nodes.
    :type members: dict
    :return: Polygon built from response.
    :rtype: Polygon
    """
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
    """Gets relation members (nodes and ways) from Overpass API for a given relation id, transforms result to shapely Polygon.

    :param relation_id: id for relation in OpenStreetMap.
    :type relation_id: int | str
    :return: Relation's representation in shapely Polygon.
    :rtype: Polygon
    """
    payload = {"data": f"[out:json][timeout:{timeout}];rel({relation_id});out geom;"}
    response = overpass_request(data=payload)
    poly = _create_poly_from_response(response["elements"][0]["members"])
    return poly


def get_admin_boundaries(poly: Polygon | MultiPolygon, admin_level: int | str = 8) -> gpd.GeoDataFrame:
    """Gets administrative boundaries inside of an area defined by `poly` with admin level == `admin_level`

    :param poly: Boundaries of an area of interest.
    :type poly: Polygon | MultiPolygon
    :param admin_level: Admin level as per OpenStreetMap docs, defaults to 8
    :type admin_level: int | str, optional
    :return: GeoDataFrame containing administrative boundaries relations with geometry.
    :rtype: gpd.GeoDataFrame
    """
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
                f"[timeout:{timeout}];"
                f"rel[admin_level={admin_level}]"
                f"[type=boundary]"
                f"[boundary=administrative](poly:'{poly_str}');"
                f"out geom;"
            )
        }
        response = overpass_request(data=payload_relations)

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
    """Gets Point of Interest according to values of tags 'amenity', 'shop', 'landuse' defined in config.py.

    :param poly: Boundaries of an area of interest.
    :type poly: Polygon
    :return: GeoDataFrame containing points of interest with geometry.
    :rtype: gpd.GeoDataFrame
    """
    payload = {
        "amenity": _get_tags(amenity_rates),
        "shop": _get_tags(shop_rates),
        "landuse": _get_tags(landuse_rates),
    }

    bbox = poly.bounds
    bbox_points = [(bbox[0], bbox[1]), (bbox[0], bbox[3]), (bbox[2], bbox[3]), (bbox[2], bbox[1])]
    bbox_poly = Polygon(bbox_points)

    raw_df = features_from_polygon(bbox_poly, payload)
    desired_cols = ["geometry", "name", "amenity", "landuse", "shop"]
    df = raw_df[desired_cols].reset_index()

    df["geometry"] = df["geometry"].apply(get_first_coord)
    return df


def get_graph(poly: Polygon, simplify: bool = True) -> nx.MultiDiGraph:
    graph = ox.graph_from_polygon(poly, simplify=simplify)
    for node_id, node_data in graph.nodes(data=True):
        if ("lat" not in node_data) or ("lon" not in node_data):
            node_data["lat"] = node_data["y"]
            node_data["lon"] = node_data["x"]
    return graph


def get_osm_data(poly: Polygon, admin_level: int | str = 8, simplify: bool = True) -> OSMData:
    """Wrapper function to get all OpenStreetMap data.

    :param poly: Boundaries of an area of interest.
    :type poly: Polygon
    :param admin_level: Admin level as per OpenStreetMap docs, defaults to 8
    :type admin_level: int | str, optional
    :return: Named Tuple containg graph, points of interest and admininstative boundaries data.
    :rtype: OSMData
    """
    graph = get_graph(poly, simplify=simplify)
    poi = get_poi(poly)
    zones = get_admin_boundaries(poly, admin_level=admin_level)
    return OSMData(graph, poi, zones)

import json
import os
import time

import geopandas as gpd
import jinja2
import networkx as nx
import pandas as pd
from shapely import MultiPolygon, Polygon, to_geojson

from city_road_network.config import highway_color_mapping, zones_color_map
from city_road_network.utils.io import get_edgelist_from_graph, get_nodelist_from_graph
from city_road_network.utils.utils import get_html_subdir, get_logger
from city_road_network.writers.color_helpers import get_occupancy_color_getter
from city_road_network.writers.geojson import (
    export_edges,
    export_graph,
    export_nodes,
    export_poi,
    export_population,
    export_zones,
)

logger = get_logger(__name__)

with open(os.path.join(os.path.dirname(__file__), "html_templates", "main.html")) as f:
    template = f.read()


def get_center(
    nodes_data: dict | None = None,
    edges_data: dict | None = None,
    zones_data: dict | None = None,
    pop_data: dict | None = None,
    poi_data: dict | None = None,
    bounds_data: dict | None = None,
):
    for data in [nodes_data, pop_data, poi_data]:
        if data is not None and data["features"]:
            feature = data["features"][0]
            return feature["geometry"]["coordinates"]
    if zones_data is not None and zones_data["features"]:
        feature = zones_data["features"][0]
        return feature["geometry"]["coordinates"][0][0]
    if edges_data is not None and edges_data["features"]:
        feature = edges_data["features"][0]
        return feature["geometry"]["coordinates"][0][0]
    if bounds_data is not None and bounds_data:
        return bounds_data["coordinates"][0][0]  # ...
    raise ValueError("No data to identify map center")


def generate_map(
    nodes_data: dict | None = None,
    edges_data: dict | None = None,
    zones_data: dict | None = None,
    pop_data: dict | None = None,
    poi_data: dict | None = None,
    bounds_data: dict | None = None,
    save=True,
    filename=None,
    city_name=None,
):
    e = jinja2.Environment()
    t = e.from_string(template)

    center = get_center(nodes_data, edges_data, zones_data, pop_data, poi_data, bounds_data)
    new_html = t.render(
        **{
            "center_lon": center[0],
            "center_lat": center[1],
            "nodes_data": json.dumps(nodes_data) if nodes_data is not None else "null",
            "edges_data": json.dumps(edges_data) if edges_data is not None else "null",
            "zones_data": json.dumps(zones_data) if zones_data is not None else "null",
            "bounds_data": json.dumps(bounds_data) if bounds_data is not None else "null",
            "pop_data": json.dumps(pop_data) if pop_data is not None else "null",
            "poi_data": json.dumps(poi_data) if poi_data is not None else "null",
        }
    )

    if save:
        html_dir = get_html_subdir(city_name=city_name)
        name = filename
        if name is None:
            ts = int(time.time())
            name = f"map_{ts}.html"
        full_name = os.path.join(html_dir, name)
        with open(full_name, "w") as f:
            f.write(new_html)
        print("Saved file %s" % os.path.abspath(full_name))
    return new_html


def _get_graph_legend_html() -> str:
    item_txt = """<br> &nbsp; {item} &nbsp; <i class="fa fa-minus fa-4" style="color:{col}"></i>"""

    item_txt_list = [item_txt.format(item=highway, col=color) for highway, color in highway_color_mapping.items()]
    html_itms = "\n".join(item_txt_list)

    legend_html = """
        <div style="
        position: fixed;
        bottom: 50px; left: 50px;;
        border:2px solid grey; z-index:9999;

        background-color:white;
        opacity: .85;

        font-size:14px;
        font-weight: bold;

        ">
        &nbsp; {title}

        {itm_txt}

        </div> """.format(
        title="Highway Types", itm_txt=html_itms
    )
    return legend_html


def draw_graph(
    graph: nx.DiGraph,
    node_popup_keys: list[str] | None = None,
    way_popup_keys: list[str] | None = None,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
):
    """Draws graph on map"""
    nodes_data, edges_data = export_graph(graph, node_export_keys=node_popup_keys, edge_export_keys=way_popup_keys)
    html = generate_map(nodes_data=nodes_data, edges_data=edges_data, save=save, filename=filename, city_name=city_name)
    return html


def draw_boundaries(
    poly: Polygon | MultiPolygon,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
):
    """Draws boundaries of an area of interest"""
    geojson_string = to_geojson(poly)
    geojson_data = json.loads(geojson_string)
    html = generate_map(bounds_data=geojson_data, save=save, filename=filename, city_name=city_name)
    return html


def draw_zones(
    zones_gdf: gpd.GeoDataFrame,
    popup_keys: list[str] | None = None,
    color_map: dict | None = None,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
):
    """Draws zones on map"""
    zones_data = export_zones(zones_gdf, keys=popup_keys)
    if color_map is None:
        color_map = zones_color_map
    html = generate_map(zones_data=zones_data, save=save, filename=filename, city_name=city_name)
    return html


def draw_trips_map(
    graph: nx.DiGraph,
    zones_gdf: gpd.GeoDataFrame | None = None,
    gradient: list[float] | None = None,
    by_abs_value: bool = False,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
):
    """Draws graph on map with edges color being gradient from green (low load) to red (high load)."""
    # TODO BIG TODO EXPORT GRAPH WITH COLOR GETTER
    # REMOVE EDGES THAT HAVE NO PASSES COUNTS!!!!
    # DONT FORGET TO INCLUDE ZONES?!??!?!
    color_getter = get_occupancy_color_getter(gradient=gradient, by_abs_value=by_abs_value)
    nodes_df = get_nodelist_from_graph(graph)
    edges_df = get_edgelist_from_graph(graph)

    edges_df = edges_df[edges_df["passes_count"] > 0]

    nodes_data = export_nodes(
        nodes_df=nodes_df,
        keys=None,
        save=False,
    )
    edges_data = export_edges(edges_df=edges_df, keys=None, save=False, color_getter=color_getter)
    kwargs = {"nodes_data": nodes_data, "edges_data": edges_data}
    if zones_gdf:
        zones_data = export_zones(zones_gdf)
        kwargs["zones_data"] = zones_data
    html = generate_map(**kwargs, save=save, filename=filename, city_name=city_name)
    return html


def draw_population(
    pop_df: pd.DataFrame,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
):
    pop_data = export_population(pop_df)
    """Draws population distribution on map"""
    html = generate_map(pop_data=pop_data, save=save, filename=filename, city_name=city_name)
    return html


def draw_poi(
    poi_df: pd.DataFrame,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
):
    """Draws population distribution on map"""
    poi_data = export_poi(poi_df)
    html = generate_map(poi_data=poi_data, save=save, filename=filename, city_name=city_name)
    return html

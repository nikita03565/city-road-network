import colorsys
import json
import os
from ast import literal_eval

import folium
import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
from pyproj import Geod
from shapely import MultiPolygon, Polygon

from city_road_network.config import highway_color_mapping, zones_color_map
from city_road_network.utils.utils import get_html_subdir, get_logger

logger = get_logger(__name__)
_geodesic = Geod(ellps="WGS84")


def _create_arrow(start_node, end_node, color, popup, radius=4, opacity=0.5):
    """Creates arrow to indicate edge direction"""
    rot = _geodesic.inv(start_node["lon"], start_node["lat"], end_node["lon"], end_node["lat"])[0] - 90
    diff = [(-start_node["lat"] + end_node["lat"]), (-start_node["lon"] + end_node["lon"])]
    offset_rate = 0.4
    center = [(start_node["lat"] + diff[0] * offset_rate), (start_node["lon"] + diff[1] * offset_rate)]

    return folium.RegularPolygonMarker(
        location=center,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=opacity,
        opacity=opacity,
        number_of_sides=3,
        rotation=rot,
        radius=radius,
        popup=popup,
    )


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


def create_map(location: tuple[float, float], zoom_start: int | None = 10):
    map = folium.Map(
        location=location,
        tiles="OpenStreetMap",
        zoom_start=zoom_start,
    )
    return map


def save_map(map: folium.Map, filename: str | None = None, city_name: str | None = None):
    """Saves map to subdirectory `city_name` with name `filename`

    :param map: Map object
    :type map: folium.Map
    :param filename: Name of output file
    :type filename: Optional[str], optional
    :param city_name: Name of subdirectory to save map to
    :type city_name: Optional[str], optional
    """
    if not filename:
        logger.warning("File name for map is not provided")
        filename = "map.html"
    html_dir = get_html_subdir(city_name)
    full_name = os.path.join(html_dir, filename)
    map.save(full_name)
    logger.info("Saved file %s", os.path.abspath(full_name))


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
    map: folium.Map | None = None,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
):
    """Draws graph on map"""
    if map is None:
        node_data = next(iter(graph.nodes(data=True)))[1]
        location = node_data["lat"], node_data["lon"]
        map = create_map(location)
    if node_popup_keys is None:
        node_popup_keys = ["id", "highway", "zone"]
    if way_popup_keys is None:
        way_popup_keys = [
            "start_node",
            "end_node",
            "osmid",
            "highway",
            "surface",
            "speed (km/h)",
            "lanes",
            "oneway",
            "length (m)",
            "name",
            "capacity (veh/h)",
            "free_flow_time (h)",
        ]
    legend_html = _get_graph_legend_html()
    map.get_root().html.add_child(folium.Element(legend_html))
    opacity = 0.5

    for idx, node_data in graph.nodes(data=True):
        node_data["id"] = idx

        popup = "<br/>".join([f"{key}: {node_data[key]}" for key in node_popup_keys if key in node_data])
        map.add_child(
            folium.Circle(location=(node_data["lat"], node_data["lon"]), fill=True, radius=3, color="blue", popup=popup)
        )

    for start_id, end_id, edge_data in graph.edges(data=True):
        start_node = graph.nodes[start_id]
        end_node = graph.nodes[end_id]

        popup = "<br/>".join([f"{key}: {edge_data[key]}" for key in way_popup_keys if key in edge_data])

        highway_raw = edge_data["highway"]
        if isinstance(highway_raw, list):
            highway = highway_raw[0]
        else:
            highway = highway_raw if not highway_raw.startswith("[") else literal_eval(highway_raw)[0]
        color = highway_color_mapping[highway]
        map.add_child(_create_arrow(start_node, end_node, color, popup, opacity=opacity))
        map.add_child(
            folium.PolyLine(
                locations=[
                    [start_node["lat"], start_node["lon"]],
                    [end_node["lat"], end_node["lon"]],
                ],
                popup=popup,
                opacity=0.7,
                color=color,
            )
        )
    if save:
        save_map(map, filename=filename, city_name=city_name)
    return map


def draw_boundaries(poly: Polygon | MultiPolygon, map: folium.Map | None = None):
    """Draws boundaries of an area of interest"""
    if isinstance(poly, MultiPolygon):
        location_point = poly.geoms[0].centroid
    else:
        location_point = poly.centroid
    location = location_point.y, location_point.x
    if map is None:
        map = create_map(location=location)
    map.add_child(folium.GeoJson(data=poly.__geo_interface__))
    return map


def draw_zones(
    zones_gdf: gpd.GeoDataFrame,
    popup_keys: list[str] | None = None,
    color_map: dict | None = None,
    map: folium.Map | None = None,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
):
    "Draws zones on map"
    if map is None:
        location_point = zones_gdf["geometry"][0].centroid
        location = location_point.y, location_point.x
        map = create_map(location)
    if popup_keys is None:
        popup_keys = ["id", "name", "pop", "poi_count", "poi_attraction", "production"]
    if color_map is None:
        color_map = zones_color_map
    for idx, zone in zones_gdf.iterrows():
        sim_geo = gpd.GeoSeries(zone[["geometry"]])
        geo_j = json.loads(sim_geo.to_json())

        geo_j["features"][0]["properties"]["id"] = idx

        geo_j = folium.GeoJson(
            data=json.dumps(geo_j),
            style_function=lambda x: {
                "fillColor": zones_color_map[x["properties"]["id"]],
                "opacity": 0.4,
                "fillOpacity": 0.5,
            },
        )
        zone["id"] = idx
        popup_dict = {key: zone.get(key) for key in popup_keys if key in zone}
        for key in popup_dict:
            if isinstance(popup_dict[key], float):
                popup_dict[key] = f"{popup_dict[key]:.2f}"
        zone_popup = "<br/>".join([f"{key}: {value}" for key, value in popup_dict.items()])
        folium.Popup(zone_popup).add_to(geo_j)
        geo_j.add_to(map)
    if save:
        save_map(map, filename=filename, city_name=city_name)
    return map


def draw_trips_map(
    graph: nx.DiGraph,
    zones_gdf: gpd.GeoDataFrame | None = None,
    gradient: list[float] | None = None,
    by_abs_value: bool = False,
):
    """Draws graph on map with edges color being gradient from green (low load) to red (high load)."""
    if gradient is None:
        gradient = _build_gradient()
    node_data = next(iter(graph.nodes(data=True)))[1]
    location = node_data["lat"], node_data["lon"]
    map = create_map(location)

    if zones_gdf is not None:
        map = draw_zones(zones_gdf, map=map)
    for start_id, end_id, edge_data in graph.edges(data=True):
        if edge_data["passes_count"] == 0:
            continue
        start_node = graph.nodes[start_id]
        end_node = graph.nodes[end_id]
        popup = "<br/>".join([f"{key}: {edge_data[key]}" for key in edge_data])
        if by_abs_value:
            color_idx = min(edge_data["passes_count"], len(gradient) - 1)
            color = f"rgb{gradient[color_idx]}"
        else:  # by occupied percentage
            color_idx = min(int(edge_data["capacity_occupied"] * len(gradient)), len(gradient) - 1)
            color = f"rgb{gradient[color_idx]}"
        opacity = 0.5
        map.add_child(_create_arrow(start_node, end_node, color, popup, opacity=opacity))
        map.add_child(
            folium.PolyLine(
                locations=[
                    [start_node["lat"], start_node["lon"]],
                    [end_node["lat"], end_node["lon"]],
                ],
                popup=popup,
                opacity=opacity,
                color=color,
            )
        )
    return map


def _get_opacity(value: float, min_opacity: float):
    opacity = max(value / 1000, min_opacity)
    return opacity


def draw_trip_distribution(
    zones_gdf: gpd.GeoDataFrame, trip_mat: np.array, map: folium.Map | None = None, min_opacity: float = 0.01
):
    """Draws OD-matrix on map"""
    if map is None:
        map = draw_zones(zones_gdf)
    n = trip_mat.shape[0]
    for i in range(n):
        for j in range(n):
            value = trip_mat[i, j]
            opacity = _get_opacity(value, min_opacity)
            if opacity == min_opacity:
                continue
            o_zone = zones_gdf.iloc[i]
            d_zone = zones_gdf.iloc[j]

            popup = f"From {o_zone['name']} to {d_zone['name']}: {value}"
            color = "blue"
            origin = {"lat": o_zone["centroid"].y, "lon": o_zone["centroid"].x}
            destination = {"lat": d_zone["centroid"].y, "lon": d_zone["centroid"].x}

            map.add_child(_create_arrow(origin, destination, color, popup, opacity=opacity))
            map.add_child(
                folium.PolyLine(
                    locations=[
                        [origin["lat"], origin["lon"]],
                        [destination["lat"], destination["lon"]],
                    ],
                    popup=popup,
                    opacity=opacity,
                    color=color,
                )
            )
    return map


def _get_pop_color(value: float, vmax: int = 600):
    ratio = min(value / vmax, 1)
    b_g = int(255 * (1 - ratio))
    b_g = min(b_g, 200)
    return f"rgb(255,{b_g},{b_g})"


def draw_population(
    pop_df: pd.DataFrame,
    map: folium.Map | None = None,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
):
    """Draws population distribution on map"""
    point = pop_df["geometry"][0]
    location = point.y, point.x
    if map is None:
        map = create_map(location)
    vmax = pop_df["value"].max()
    for _, row in pop_df.iterrows():
        value = row["value"]
        if not value or value <= 0:
            continue
        color = _get_pop_color(value, vmax=vmax)
        map.add_child(folium.Circle(location=(row["lat"], row["lon"]), fill=True, radius=1, color=color, popup=value))
    if save:
        save_map(map, filename, city_name)
    return map

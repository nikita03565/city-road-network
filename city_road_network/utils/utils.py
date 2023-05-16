import logging
import os
import re
import sys
from pathlib import Path

from geopy import distance
from osgeo import ogr, osr
from shapely import Point

from city_road_network.config import (
    CACHE_DIR,
    DATA_DIR,
    HTML_DIR,
    PLOTS_DIR,
    amenity_rates,
    default_city_name,
    floor_area_multipliers,
    landuse_rates,
    shop_rates,
    speed_map,
    whitelist_node_attrs,
    whitelist_relation_attrs,
    whitelist_way_attrs,
)

mollweide = osr.SpatialReference()
mollweide.SetFromUserInput("ESRI:54009")

wgs = osr.SpatialReference()
wgs.ImportFromEPSG(4326)


wgs_to_mollweide = osr.CoordinateTransformation(wgs, mollweide)
mollweide_to_wgs = osr.CoordinateTransformation(mollweide, wgs)


def convert_coordinates(x, y, *, to_wgs=True):
    if to_wgs:
        transform = mollweide_to_wgs
    else:
        transform = wgs_to_mollweide
    point = ogr.CreateGeometryFromWkt(f"POINT ({x} {y})")
    point.Transform(transform)
    wkt = point.ExportToWkt()  # 'POINT (61.2993700571118 30.9930425659682)'
    result = tuple(float(x) for x in wkt[7:-1].split())
    return result


def get_logger(name):
    logger = logging.Logger(name)
    handler = logging.StreamHandler(sys.stdout)
    log_format = logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s")
    handler.setFormatter(log_format)
    logger.addHandler(handler)
    return logger


logger = get_logger(__name__)


def calc_poi_attraction(poi):
    if poi["amenity"] in amenity_rates:
        return amenity_rates[poi["amenity"]] * floor_area_multipliers.get(poi["amenity"], 1)
    if poi["shop"] in shop_rates:
        return shop_rates[poi["shop"]] * floor_area_multipliers.get(poi["amenity"], 1)
    if poi["landuse"] in landuse_rates:
        return landuse_rates[poi["landuse"]] * floor_area_multipliers.get(poi["amenity"], 1)
    logger.warning("Failed to identify attraction rate for %s", poi)
    return 0


def get_csv_head(items):
    head = [""]
    head_set = set([""])

    for item in items:
        for key in item.keys():
            if key in head_set:
                continue
            head.append(key)
            head_set.add(key)
    return head


def get_subdir(dir_name, city_name=None):
    if city_name is None:
        logger.warning("City name is not provided. Using default name '%s'", default_city_name)
        city_name = default_city_name
    dir = os.path.join(dir_name, city_name)
    Path(dir).mkdir(parents=True, exist_ok=True)
    return dir


def get_html_subdir(city_name=None):
    return get_subdir(HTML_DIR, city_name)


def get_data_subdir(city_name=None):
    return get_subdir(DATA_DIR, city_name)


def get_sumo_subdir(city_name=None):
    data_dir = get_data_subdir(city_name)
    dir = os.path.join(data_dir, "sumo_files")
    Path(dir).mkdir(parents=True, exist_ok=True)
    return dir


def get_plots_subdir(city_name=None):
    return get_subdir(PLOTS_DIR, city_name)


def get_cache_subdir():
    cache_dir = os.path.join(CACHE_DIR)
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_first_coord(geometry):
    if geometry.geom_type == "Point":
        return geometry
    if geometry.geom_type == "LineString":
        return Point(geometry.coords[0])
    if geometry.geom_type == "MultiPolygon":
        geometry = geometry.geoms[0]
    first_coord = geometry.exterior.coords[0]
    return Point(first_coord)


def parse_mph_speed(value: str) -> float:
    value_num = int(value.replace("mph", "").strip())
    return value_num * 1.60934


def get_max_speed(possible_speed):
    if possible_speed in ("signals", "walk"):
        return None
    if "mph" in possible_speed:
        return parse_mph_speed(possible_speed)
    try:
        return int(possible_speed)
    except (ValueError, TypeError):
        if possible_speed not in speed_map:
            logger.warning("Found unknown speed %s", possible_speed)
            return None
        return speed_map[possible_speed]


def get_attrs_from_tags(tags):
    return {tag.attrib["k"]: tag.attrib["v"] for tag in tags}


def get_filtered_node_attrs(attrs):
    return {key: value for key, value in attrs.items() if key in whitelist_node_attrs}


def get_filtered_way_attrs(attrs):
    return {key: value for key, value in attrs.items() if key in whitelist_way_attrs}


def get_filtered_relation_attrs(attrs):
    return {key: value for key, value in attrs.items() if key in whitelist_relation_attrs}


def get_distance(u, v):  # km
    p1 = float(u.get("lat")), float(u.get("lon"))
    p2 = float(v.get("lat")), float(v.get("lon"))
    return distance.distance(p1, p2).kilometers

import logging
import os
import sys
from pathlib import Path

from pyproj import Geod, Transformer
from shapely import Point

from city_road_network.config import (
    CACHE_DIR,
    DATA_DIR,
    GEOJSON_DIR,
    HTML_DIR,
    PLOTS_DIR,
    amenity_rates,
    default_city_name,
    floor_area_multipliers,
    landuse_rates,
    shop_rates,
    speed_map,
)

mollweide = "ESRI:54009"
wgs = "EPSG:4326"


wgs_to_mollweide = Transformer.from_crs(wgs, mollweide)
mollweide_to_wgs = Transformer.from_crs(mollweide, wgs)


def convert_coordinates(x: float, y: float, *, to_wgs=True):
    """Converts coordinates between WGS-84 and Mollweide"""
    if to_wgs:
        transform = mollweide_to_wgs
    else:
        transform = wgs_to_mollweide
    result = transform.transform(x, y)
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


def get_subdir(dir_name, city_name=None):
    if city_name is None:
        logger.warning("City name is not provided. Using default name '%s'", default_city_name)
        city_name = default_city_name
    dir = os.path.join(dir_name, city_name)
    Path(dir).mkdir(parents=True, exist_ok=True)
    return dir


def get_html_subdir(city_name=None):
    return get_subdir(HTML_DIR, city_name)


def get_geojson_subdir(city_name=None):
    return get_subdir(GEOJSON_DIR, city_name)


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


def get_distance(u, v):  # km
    wgs84_geod = Geod(ellps="WGS84")
    p1 = float(u.get("lon")), float(u.get("lat"))
    p2 = float(v.get("lon")), float(v.get("lat"))
    _, _, dist = wgs84_geod.inv(*p1, *p2)
    return dist / 1000

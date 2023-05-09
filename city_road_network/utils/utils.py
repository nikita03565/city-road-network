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
    amenity_rates,
    default_city_name,
    floor_area_multipliers,
    landuse_rates,
    shop_rates,
    speed_map,
    tags_to_ignore_nodes,
    tags_to_ignore_ways,
    tags_to_keep_ways,
    whitelist_node_attrs,
    whitelist_relation_attrs,
    whitelist_way_attrs,
)

# identified by looking at image
# Represents indexes in GHS POP combined array
spb_coords = {
    "left": 9400,
    "right": 10500,
    "top": 1000,
    "bottom": 1600,
}


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


def get_html_subdir(city_name=None):
    if city_name is None:
        logger.warning("City name is not provided. Using default name '%s'", default_city_name)
        city_name = default_city_name
    html_dir = os.path.join("..", "htmls", city_name)
    Path(html_dir).mkdir(parents=True, exist_ok=True)
    return html_dir


def get_data_subdir(city_name=None):
    if city_name is None:
        logger.warning("City name is not provided. Using default name '%s'", default_city_name)
        city_name = default_city_name
    html_dir = os.path.join("..", "data", city_name)
    Path(html_dir).mkdir(parents=True, exist_ok=True)
    return html_dir


def get_cache_subdir():
    cache_dir = os.path.join("..", CACHE_DIR)
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    return cache_dir


class MockRelationship:
    def __init__(self, start_node, end_node, properties):
        self.start_node = start_node
        self.end_node = end_node
        self.properties = properties

    def get(self, key):
        return self.properties[key]


def get_first_coord(geometry):
    if geometry.geom_type == "Point":
        return geometry
    if geometry.geom_type == "LineString":
        return Point(geometry.coords[0])
    if geometry.geom_type == "MultiPolygon":
        geometry = geometry.geoms[0]
    first_coord = geometry.exterior.coords[0]
    return Point(first_coord)


def clean_string(value):
    if not isinstance(value, str):
        return value
    return re.sub("[^0-9a-zA-Zа-яА-я]+", "_", value)


def get_max_speed(possible_speed):
    if possible_speed == "signals":
        return None
    try:
        return int(possible_speed)
    except (ValueError, TypeError):
        if possible_speed not in speed_map:
            logger.warning("Found unknown speed %s", possible_speed)
            return None
        return speed_map[possible_speed]


def check_tags(tags, config):
    for key, values in config.items():
        tag = tags.get(key)
        if (tag and not values) or (tag in values):
            return False
    return True


def check_way_tags(tags):
    return check_tags(tags, tags_to_ignore_ways) or not check_tags(tags, tags_to_keep_ways)


def check_node_tags(tags):
    # keep destination and destination:ref!
    if not tags[":LABEL"]:
        return False
    return check_tags(tags, tags_to_ignore_nodes)


def get_attrs_from_tags(tags):
    return {tag.attrib["k"]: tag.attrib["v"] for tag in tags}


def get_filtered_node_attrs(attrs):
    return {key: value for key, value in attrs.items() if key in whitelist_node_attrs}


def get_filtered_way_attrs(attrs):
    return {key: value for key, value in attrs.items() if key in whitelist_way_attrs}


def get_filtered_relation_attrs(attrs):
    return {key: value for key, value in attrs.items() if key in whitelist_relation_attrs}


def is_road(highway):
    # NOT USED
    words = (
        "motorway",
        "trunc",
        "primary",
        "secondary",
        "tertiary_link",
        "unclassified",
        "residential",
        "service",
        "living_street",
        "track",
        "path",
        "road",
    )
    # {'', 'unclassified', 'tertiary', 'footway', 'steps', 'secondary', 'pedestrian', 'corridor', 'secondary_link', 'service', 'path', 'primary', 'tertiary_link', 'residential', 'primary_link', 'construction'}
    return any(word in highway for word in words)


def is_road1(highway):
    exclude_words = ("footway", "steps", "pedestrian", "construction", "corridor", "service", "path", "proposed")
    return not any(word in highway for word in exclude_words)


def get_distance(u, v):  # km
    p1 = float(u.get("lat")), float(u.get("lon"))
    p2 = float(v.get("lat")), float(v.get("lon"))
    return distance.distance(p1, p2).kilometers


def get_is_link(highway: list):
    for h in highway:
        if h.endswith("_link") or h == "unclassified":
            return True
    return False


def split_rels(rels, start_node, checked_nodes=None, ignore_links=False):
    if checked_nodes is None:
        checked_nodes = set()
    filtered_rels = [rel for rel in rels if rel.start_node.id == start_node.id]  # start relations
    splitted = []
    for rel in filtered_rels:
        path = [rel]
        checked_nodes.add(rel.start_node)
        while True:
            next_rel = [r for r in rels if r.start_node == path[-1].end_node and r.start_node not in checked_nodes]
            if ignore_links:
                next_rel_raw = [
                    r for r in rels if r.start_node == path[-1].end_node and r.start_node not in checked_nodes
                ]
                next_rel = []
                for raw in next_rel_raw:
                    goes_to_same_road = not (raw.end_node.labels - raw.start_node.labels)
                    is_link = get_is_link(raw["highway"])
                    if is_link and goes_to_same_road:
                        print("Ignoring link in split")
                        continue
                    next_rel.append(raw)
                if not next_rel:
                    next_rel = next_rel_raw
            checked_nodes.add(path[-1].end_node)
            if len(next_rel) > 1:
                for r in next_rel:
                    splitted.extend(split_rels(rels, r.start_node, checked_nodes))
            elif next_rel:
                path.append(next_rel[0])
            if not next_rel:
                break
        if len(path) > 1:
            splitted.append(path)
    return splitted

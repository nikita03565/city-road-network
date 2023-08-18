import copy
import os
import subprocess
from pathlib import Path


import geopandas as gpd
import numpy as np
import pandas as pd
from lxml import etree
from osmnx.downloader import overpass_request
from shapely import Polygon
from shapely.ops import transform
from shapely.wkt import loads

from city_road_network.config import default_osm_filter, known_highways, timeout
from city_road_network.downloaders.osm import _get_poly_coord_str
from city_road_network.processing.data_correction import get_speed, guess_lanes
from city_road_network.utils.utils import get_data_subdir, get_logger, get_sumo_subdir

logger = get_logger(__name__)

NET_FILE_NAME = "net.net.xml"
TAZ_FILE_NAME = "tazs.taz.xml"
DISTRICTS_FILE_NAME = "districts.taz.xml"
OD_FILE_NAME = "od_file.od"
TRIPS_FILE_NAME = "out_trips.xml"
DUA_FILE_NAME = "od_route_file.odtrips.rou.xml"
SUMO_CONFIG_FILE_NAME = "map.sumocfg"


def get_raw_data(poly: Polygon) -> dict:
    """Makes Overpass API query and returns response with any changes/simplifications to ways and nodes.

    :param poly: Polygon describing boundaries of an area of interest.
    :type poly: Polygon
    :return: Overpass API response.
    :rtype: dict
    """
    polygon_coord_str = _get_poly_coord_str(poly)
    query_str = f"[out:json][timeout:{timeout}];(way{default_osm_filter}(poly:'{polygon_coord_str}');>;);out;"
    response_json = overpass_request(data={"data": query_str})
    return response_json


def correct_raw_ways(ways: list) -> list:
    """Guesstimating maxspeed and lanes for ways."""
    ways_corrected = copy.deepcopy(ways)
    for way in ways_corrected:
        tags = way["tags"]
        if "maxspeed" not in tags:
            tags["maxspeed"] = None
        if not isinstance(tags.get("maxspeed"), (int, float)):
            tags["maxspeed"] = get_speed(tags)
        if not tags.get("lanes"):
            tags["lanes"] = guess_lanes(tags)
    return ways_corrected


def save_osm_file(elements: list, filename: str):
    """Writes ways and nodes received from Overpass API as OSM/XML file.

    :param elements: Elements from Overpass API response.
    :type elements: list
    :param filename: Name output OSM/XML file.
    :type filename: str
    """
    elements_copy = copy.deepcopy(elements)
    root = etree.Element("osm", version="0.6")
    for element in elements_copy:
        tags = element.pop("tags", {})
        nd_list = element.pop("nodes", [])
        el_type = element.pop("type")

        el = etree.Element(el_type, **{str(k): str(v) for k, v in element.items()})

        for nd in nd_list:
            nd_el = etree.Element("nd", ref=str(nd))
            el.append(nd_el)
        for tag_key, tag_value in tags.items():
            tag_el = etree.Element("tag", k=tag_key, v=str(tag_value))
            el.append(tag_el)
        root.append(el)

    with open(filename, "wb") as f:
        f.write(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8"))


def prepare_sumo_net_file(poly: Polygon, city_name: str | None = None):
    """Gets raw data from Overpass API, saves and OSM/XML file and runs netconvert on this file"""
    resp = get_raw_data(poly)
    ways = [el for el in resp["elements"] if el["type"] == "way" and el["tags"].get("highway") in set(known_highways)]
    nodes = [el for el in resp["elements"] if el["type"] == "node"]

    ways_corrected = correct_raw_ways(ways)
    elements = nodes + ways_corrected
    sumo_dir = get_sumo_subdir(city_name)
    filename = os.path.join(sumo_dir, "out.osm")
    net_filename = os.path.join(sumo_dir, NET_FILE_NAME)
    save_osm_file(elements, filename)
    args = ["netconvert", "--osm", os.path.abspath(filename), "-o", os.path.abspath(net_filename)]
    logger.info("Running %s", " ".join(args))
    subprocess.run(args)


def save_zones(city_name: str | None = None):
    """Saves zones in format that SUMO expects. Uses polyconvert tool."""
    data_dir = get_data_subdir(city_name)
    sumo_dir = get_sumo_subdir(city_name)
    zones_df = pd.read_csv(os.path.join(data_dir, "zones_upd.csv"), index_col=0)
    zones_df["geometry"] = zones_df["geometry"].apply(loads)
    zones_gdf = gpd.GeoDataFrame(zones_df, crs="epsg:4326")
    zones_gdf.geometry = zones_gdf.geometry.map(lambda polygon: transform(lambda x, y: (y, x), polygon))
    taz_dir = os.path.join(sumo_dir, "taz_shapefile")
    Path(taz_dir).mkdir(parents=True, exist_ok=True)
    shapefile_name = os.path.join(taz_dir, "tazs.shp")
    zones_gdf.to_file(shapefile_name)
    net_path = os.path.join(sumo_dir, NET_FILE_NAME)
    outfile = os.path.join(sumo_dir, TAZ_FILE_NAME)
    args = [
        "polyconvert",
        "-v",
        "--shapefile-prefixes",
        os.path.abspath(shapefile_name).replace(".shp", ""),
        "-n",
        os.path.abspath(net_path),
        "-o",
        os.path.abspath(outfile),
    ]
    logger.info("Running %s", " ".join(args))
    subprocess.run(args)
    with open(outfile, "rb") as f:
        tree = etree.fromstring(f.read())
    for element in tree.xpath("//poly"):
        element.tag = "taz"
        del element.attrib["layer"]
        del element.attrib["type"]
    with open(outfile, "wb") as f:
        f.write(etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding="UTF-8"))


def save_od_matrix(city_name: str | None = None, divider: float | None = None):
    """Saves OD-matrix in format that SUMO expects"""
    od_head = """$O;D2
* From-Time\tTo-Time
0.00\t1.00
*Factor
1.00
    """
    data_dir = get_data_subdir(city_name)
    sumo_dir = get_sumo_subdir(city_name)
    trip_mat = np.load(os.path.join(data_dir, "trip_mat.npy"))
    with open(os.path.join(sumo_dir, OD_FILE_NAME), "w") as f:
        f.write(od_head)
        for i in range(trip_mat.shape[0]):
            for j in range(trip_mat.shape[0]):
                value = int(trip_mat[i, j])
                if divider:
                    value = value // divider
                f.write(f"\t\t{i}\t{j}\t{value}\n")


def create_config(city_name: str | None = None, include_zones=True, include_trips=True):
    """Creates SUMO config XML file. Links previously created files like net file, OD-matrix file, zones file into one 'project'."""
    sumo_dir = get_sumo_subdir(city_name)
    netfile = os.path.join(sumo_dir, NET_FILE_NAME)
    tazfile = os.path.join(sumo_dir, DISTRICTS_FILE_NAME)
    duafile = os.path.join(sumo_dir, DUA_FILE_NAME)

    xsi = "http://www.w3.org/2001/XMLSchema-instance"

    etree.register_namespace("xsi", xsi)
    element = etree.Element("configuration")
    element.attrib[etree.QName(xsi, "noNamespaceSchemaLocation")] = "http://sumo.dlr.de/xsd/sumoConfiguration.xsd"
    input_el = etree.Element("input")
    netfile_el = etree.Element("net-file", value=os.path.abspath(netfile))

    additional_el = etree.Element("additional-files", value=os.path.abspath(tazfile))
    tripsfile_el = etree.Element("route-files", value=os.path.abspath(duafile))
    input_el.append(netfile_el)
    if include_zones:
        input_el.append(additional_el)
    if include_trips:
        input_el.append(tripsfile_el)
    element.append(input_el)

    config_file = os.path.join(sumo_dir, SUMO_CONFIG_FILE_NAME)
    with open(config_file, "wb") as f:
        f.write(etree.tostring(element, pretty_print=True, xml_declaration=True, encoding="UTF-8"))


def distribute_edges(city_name: str | None = None, sumo_home=None):
    """Disctibutes edges to zones via edgesInDistricts.py tool that is shipped with SUMO."""
    if sumo_home is None:
        sumo_home = os.path.join(os.sep, "usr", "share", "sumo")
    sumo_dir = get_sumo_subdir(city_name)
    netfile = os.path.abspath(os.path.join(sumo_dir, NET_FILE_NAME))
    tazfile = os.path.abspath(os.path.join(sumo_dir, TAZ_FILE_NAME))
    outfile = os.path.abspath(os.path.join(sumo_dir, DISTRICTS_FILE_NAME))
    python_file_path = os.path.join(sumo_home, "tools", "edgesInDistricts.py")
    args = ["python", python_file_path, "-n", netfile, "-t", tazfile, "-o", outfile]
    logger.info("Running %s", " ".join(args))
    subprocess.run(args)


def generate_trips(city_name: str | None = None):
    """Generates trips by od2trips tool for SUMO."""
    sumo_dir = get_sumo_subdir(city_name)

    netfile = os.path.abspath(os.path.join(sumo_dir, NET_FILE_NAME))
    tazfile = os.path.abspath(os.path.join(sumo_dir, DISTRICTS_FILE_NAME))
    odfile = os.path.abspath(os.path.join(sumo_dir, OD_FILE_NAME))
    tripsfile = os.path.abspath(os.path.join(sumo_dir, TRIPS_FILE_NAME))
    duafile = os.path.abspath(os.path.join(sumo_dir, DUA_FILE_NAME))
    args = ["od2trips", "-n", tazfile, "-d", odfile, "-o", tripsfile]
    logger.info("Running %s", " ".join(args))
    subprocess.run(args)

    dua_args = ["duarouter", "-n", netfile, "--route-files", tripsfile, "-o", duafile, "--ignore-errors", "true"]
    logger.info("Running %s", " ".join(dua_args))
    subprocess.run(dua_args)


def run_sumo(city_name: str | None = None, gui=True):
    """Calls `sumo -c configfile` command"""
    sumo_dir = get_sumo_subdir(city_name)

    configfile = os.path.join(sumo_dir, SUMO_CONFIG_FILE_NAME)
    sumo_keyword = "sumo-gui" if gui else "sumo"
    args = [sumo_keyword, "-c", configfile]
    logger.info("Running %s", " ".join(args))
    subprocess.run(args)


def prepare_all_files(boundaries: Polygon, city_name: str | None = None, sumo_home=None, divider: float | None = None):
    """Wrapper function to prepare SUMO network file, load OD-matrix, generate trips and save config for SUMO 'project'."""
    prepare_sumo_net_file(boundaries, city_name)
    save_zones(city_name)
    distribute_edges(city_name, sumo_home=sumo_home)
    save_od_matrix(city_name, divider=divider)
    generate_trips(city_name)
    create_config(city_name)

import os
import zipfile
from pathlib import Path
from typing import Set

import numpy as np
import requests
from osgeo import gdal, ogr
from shapely import Point
from shapely.geometry import shape

from city_road_network.config import ghsl_shape_url, ghsl_tile_url_template
from city_road_network.utils.utils import get_cache_subdir, get_logger

logger = get_logger(__name__)

cache_dir = get_cache_subdir()
shapefile_zip_path = os.path.join(cache_dir, "ghsl_shapefile.zip")
shapefile_dir_path = os.path.join(cache_dir, "ghsl_shapefile")


def _get_file_by_extension(directory, extension):
    return [name for name in os.listdir(directory) if name.endswith(extension)][0]


def download_shapefile():
    """Downloads shapefile describing GHSL tiles and extracts archive."""
    response = requests.get(ghsl_shape_url)
    response.raise_for_status()
    with open(shapefile_zip_path, "wb") as f:
        f.write(response.content)
    logger.info("Saved shapefile archive to %s", os.path.abspath(shapefile_zip_path))
    with zipfile.ZipFile(shapefile_zip_path, "r") as zip_file:
        zip_file.extractall(shapefile_dir_path)
    logger.info("Extracted shapefile to %s", os.path.abspath(shapefile_dir_path))


def get_shapefile() -> ogr.DataSource:
    """Downloads shapefile or reads from cache.

    :return: Shapefile read by ogr.
    :rtype: ogr.DataSource
    """
    if not Path(shapefile_zip_path).is_file():
        logger.info("Shapefile was not found. Downloading...")
        download_shapefile()

    shp_filename = _get_file_by_extension(shapefile_dir_path, ".shp")
    shapefile = ogr.Open(os.path.join(shapefile_dir_path, shp_filename))
    return shapefile


def get_tile_ids(top: float, left: float, bottom: float, right: float) -> Set[int]:
    """Identifies GHSL tiles ids from given corner coordinates of an area of interest.

    :param top: top coordinate of a bounding box of an area of interest.
    :type top: float
    :param left: left coordinate of a bounding box of an area of interest.
    :type left: float
    :param bottom: bottom coordinate of a bounding box of an area of interest.
    :type bottom: float
    :param right: right coordinate of a bounding box of an area of interest.
    :type right: float
    :return: Ids of tiles where coordinates are.
    :rtype: Set[int]
    """
    points = [Point(left, top), Point(right, top), Point(left, bottom), Point(right, bottom)]
    shapefile = get_shapefile()

    layer = shapefile.GetLayer(0)
    feature_count = layer.GetFeatureCount()

    tile_ids = {}
    for i in range(feature_count):
        feature = layer.GetFeature(i).ExportToJson(as_object=True)
        poly = shape(feature["geometry"])
        if any(poly.contains(point) for point in points):
            tile_ids[feature["properties"]["tile_id"]] = feature
    return tile_ids


def download_tile(tile_id: int):
    """Downloads data for a given tile and extracts archive.

    :param tile_id: Id of tile as per GHSL shapefile.
    :type tile_id: int
    """
    url = ghsl_tile_url_template.format(tile_id=tile_id)
    logger.info("Downloading tile archive from %s", url)
    response = requests.get(url)
    response.raise_for_status()

    out_file = os.path.join(cache_dir, f"{tile_id}.zip")
    with open(out_file, "wb") as f:
        f.write(response.content)
    logger.info("Saved tile archive to %s", os.path.abspath(out_file))

    out_directory = os.path.join(cache_dir, tile_id)
    with zipfile.ZipFile(out_file, "r") as zip_file:
        zip_file.extractall(out_directory)
    logger.info("Extracted tile to %s", os.path.abspath(out_directory))


def get_tile(tile_id: int) -> np.array:
    """Downloads tile or reads from cache.

    :param tile_id: Id of tile as per GHSL shapefile.
    :type tile_id: int
    :return: Tiff file read as numpy array.
    :rtype: np.array
    """
    if not Path(os.path.join(cache_dir, f"{tile_id}.zip")).is_file():
        logger.info("Tile %s was not found. Downloading...", tile_id)
        download_tile(tile_id)
    directory = os.path.join(cache_dir, tile_id)
    tiff_filename = _get_file_by_extension(directory, ".tif")
    full_name = os.path.join(directory, tiff_filename)
    dataset = gdal.Open(full_name, gdal.GA_ReadOnly)
    band = dataset.GetRasterBand(1)
    array = band.ReadAsArray()
    return array

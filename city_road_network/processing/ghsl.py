import re
from math import ceil, floor

import numpy as np
import pandas as pd
from natsort import natsorted
from shapely import Point, Polygon

from city_road_network.downloaders.ghsl import get_tile, get_tile_ids
from city_road_network.utils.utils import convert_coordinates
from city_road_network.writers.csv import save_dataframe


def parse_tile_id(tile_id: str) -> tuple[int, int]:
    """Extracts row and column ids from string like R23_C1

    :param tile_id: String representing id for GHLS tile.
    :type tile_id: str
    :return: Row and Column ids.
    :rtype: Tuple[int, int]
    """
    reg = r"R(?P<row>\d+)_C(?P<col>\d+)"
    match = re.match(reg, tile_id)
    row = int(match.group("row"))
    col = int(match.group("col"))
    return row, col


def get_image_coordinates(bbox) -> tuple[float, float, float, float]:
    """Converts WGS-84 coordinates of bounding box of an area of interest to Mollweide coordinates.

    :param bbox: Bounding box (polygon.bounds) of an area of interest.
    :return: Coordinates in Mollweide CRS.
    :rtype: Tuple[float, float, float, float]
    """
    bbox_points = [(bbox[1], bbox[0]), (bbox[3], bbox[0]), (bbox[3], bbox[2]), (bbox[1], bbox[2])]
    converted_points = []
    for p in bbox_points:
        converted_points.append(convert_coordinates(*p, to_wgs=False))

    min_x = min(p[0] for p in converted_points)
    min_y = min(p[1] for p in converted_points)
    max_x = max(p[0] for p in converted_points)
    max_y = max(p[1] for p in converted_points)

    bottom = floor(min_y)
    left = floor(min_x)
    top = ceil(max_y)
    right = ceil(max_x)

    return top, left, bottom, right


def combine_tiles(tile_ids_sorted: list[str]) -> np.array:
    """Combines several tiles into one.

    :param tile_ids_sorted: Ids of tile as per GHSL shapefile.
    :type tile_ids_sorted: List[str]
    :return: Combined tiles as one np.array.
    :rtype: np.array
    """
    if len(tile_ids_sorted) == 1:
        return get_tile(tile_ids_sorted[0])
    if len(tile_ids_sorted) != 2:
        raise ValueError(f"Unexpected number of tiles {len(tile_ids_sorted)}")
    left_top = tile_ids_sorted[0]
    right_bottom = tile_ids_sorted[1]
    left_top_row, left_top_col = parse_tile_id(left_top)
    right_bottom_row, right_bottom_col = parse_tile_id(right_bottom)
    if (right_bottom_col > left_top_col) and (right_bottom_row > left_top_row):
        raise NotImplementedError("Handle 4 tiles")
    left_top_tile = get_tile(left_top)
    right_bottom_tile = get_tile(right_bottom)
    if (right_bottom_row == left_top_row) and (right_bottom_col > left_top_col):
        tile = np.transpose(np.concatenate([np.transpose(left_top_tile), np.transpose(right_bottom_tile)]))
        return tile
    if (right_bottom_row > left_top_row) and (right_bottom_col == left_top_col):
        tile = np.concatenate([left_top_tile, right_bottom_tile])
        return tile
    raise RuntimeError(f"Unexpected case with tiles {tile_ids_sorted}")


def process_population(poly: Polygon, city_name: str | None = None) -> pd.DataFrame:
    """Reads tiles, joins them and returns only part that is inside of area's of interest bounding box.

    :param poly: Shapely Polygon describing an area of interest
    :type poly: Polygon
    :param city_name: name of subfolder where save data to, defaults to None
    :type city_name: Optional[str], optional
    :rtype: pd.DataFrame
    """
    bbox = poly.bounds
    top, left, bottom, right = get_image_coordinates(bbox)
    tile_ids = get_tile_ids(top, left, bottom, right)
    tile_ids_sorted = natsorted(tile_ids)

    tile = combine_tiles(tile_ids_sorted)

    top_left_tile = tile_ids_sorted[0]
    top_left_tile_props = tile_ids[top_left_tile]["properties"]

    pixel_size = 100

    image_coords = {
        "left": (left - top_left_tile_props["left"]) // pixel_size,
        "top": -(top - top_left_tile_props["top"]) // pixel_size,
        "right": (right - top_left_tile_props["left"]) // pixel_size,
        "bottom": -(bottom - top_left_tile_props["top"]) // pixel_size,
    }

    tile_cropped = tile[image_coords["top"] : image_coords["bottom"], image_coords["left"] : image_coords["right"]]

    df_data = []

    global_offset = {"row": top_left_tile_props["top"], "col": top_left_tile_props["left"]}
    local_offset = {"row": image_coords["top"], "col": image_coords["left"]}
    for row in range(tile_cropped.shape[0]):
        for col in range(tile_cropped.shape[1]):
            value = tile_cropped[row][col]
            if not value or value <= 0:
                continue
            original_row = -(row + local_offset["row"]) * pixel_size + global_offset["row"]
            original_col = (col + local_offset["col"]) * pixel_size + global_offset["col"]
            lat, lon = convert_coordinates(original_col, original_row)
            df_data.append({"lon": lon, "lat": lat, "geometry": Point(lon, lat), "value": value})

    pop_df = pd.DataFrame(df_data)
    save_dataframe(pop_df, "population.csv", city_name=city_name)
    return pop_df

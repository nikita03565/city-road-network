import os
from ast import literal_eval

import numpy as np
import pandas as pd

from city_road_network.config import lane_capacity_mapping
from city_road_network.processing.data_correction import fix_missing_lanes, get_speed
from city_road_network.utils.utils import get_data_subdir, get_logger
from city_road_network.writers.csv import save_dataframe

logger = get_logger(__name__)


def _get_base_capacity(lanes: int | str, oneway: bool) -> int:
    try:
        lanes = int(lanes)
    except ValueError:
        logger.warning("Failed to parse %s as int. Rounding.", lanes)
        lanes = round(float(lanes))
    if lanes == 1:
        return lane_capacity_mapping[lanes]
    if 1 < lanes < 4:
        if oneway:
            return lane_capacity_mapping[lanes] * 2
        return lane_capacity_mapping[lanes]
    if lanes >= 4:
        if oneway:
            return int(lanes * lane_capacity_mapping[lanes if lanes <= 6 else "6+"])
        return _get_base_capacity(lanes // 2, oneway)
    raise ValueError(f"Unexpected number of lanes {lanes}")


def _estimate_capacity(row):
    lanes = literal_eval(row["lanes"])
    if isinstance(lanes, float):
        lanes = round(lanes)
    if isinstance(lanes, int):
        return _get_base_capacity(lanes, row["oneway"])
    if isinstance(lanes, list):
        capacities = [_get_base_capacity(lanes_value, row["oneway"]) for lanes_value in lanes]
        return sum(capacities) // len(capacities)
    raise ValueError(f"Unexpected lanes {lanes} of type {type(lanes)}")


def _get_avg_value(row, key):
    row_value = row[key]
    if isinstance(row_value, str) and row_value.startswith("["):
        row_value = literal_eval(row_value)
    if not isinstance(row_value, list):
        return row[key]
    values = [int(value) for value in row_value]
    return sum(values) // len(values)


def process_edges(city_name: str | None = None) -> pd.DataFrame:
    """Reads DataFrame from `city_name` subdirectory, fixes missing lanes, estimates capacity, estimates flow time, renames columns.

    :param city_name: name of subdirectory to read data from and save to, defaults to None
    :type city_name: Optional[str], optional
    :return: Updated Edges DataFrame
    :rtype: pd.DataFrame
    """
    data_dir = get_data_subdir(city_name)
    edgelist_file = os.path.join(data_dir, "edgelist.csv")
    df_edges = pd.read_csv(edgelist_file, dtype={"oneway": bool}, index_col=0)

    df_edges = fix_missing_lanes(df_edges)
    df_edges["maxspeed"] = df_edges["maxspeed"].fillna(np.nan).replace([np.nan], [None])
    df_edges["maxspeed"] = df_edges.apply(get_speed, axis=1)
    df_edges["length (m)"] = df_edges["length"]
    df_edges["length (km)"] = df_edges["length"] / 1000
    df_edges["capacity (veh/h)"] = df_edges.apply(_estimate_capacity, axis=1)
    df_edges["maxspeed (km/h)"] = df_edges.apply(lambda row: _get_avg_value(row, "maxspeed"), axis=1)
    df_edges["lanes"] = df_edges.apply(lambda row: _get_avg_value(row, "lanes"), axis=1)

    df_edges["flow_time (h)"] = df_edges["length (km)"] / df_edges["maxspeed (km/h)"]
    df_edges["flow_time (s)"] = df_edges["flow_time (h)"] * 3600

    df_edges.drop(
        columns=[
            "key",
            "foot",
            "reversed",
            "lit",
            "bridge",
            "tunnel",
            "ref",
            "junction",
            "access",
            "width",
            "geometry",
            "length",
        ],
        inplace=True,
    )

    save_dataframe(df_edges, "edgelist_upd.csv", city_name=city_name)
    return df_edges

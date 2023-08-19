from ast import literal_eval

import pandas as pd

from city_road_network.config import default_speed_map
from city_road_network.utils.utils import get_logger, get_max_speed

logger = get_logger(__name__)


def guess_speed(row):
    highway = row["highway"]
    living_street = row["living_street"] if "living_street" in row else None
    if "residential" in highway or "unclassified" in highway or "living_street" in highway or living_street == "yes":
        return default_speed_map["living_street"]
    if "motorway_link" in highway:
        return default_speed_map["motorway"]
    if ("trunk" in highway) or ("trunk_link" in highway):
        return default_speed_map["rural"]
    return default_speed_map["urban"]


def guess_lanes(row):
    highway = row["highway"]
    living_street = row["living_street"] if "living_street" in row else None
    if (
        "road" in highway
        or "residential" in highway
        or "unclassified" in highway
        or "living_street" in highway
        or "busway" in highway
        or living_street == "yes"
    ):
        return "1"
    if ("tertiary" in highway) or ("tertiary_link" in highway):
        return "2"
    if ("secondary" in highway) or ("secondary_link" in highway):
        return "2"
    if ("primary" in highway) or ("primary_link" in highway) or ("motorway" in highway) or ("motorway_link" in highway):
        return "3"
    if ("trunk" in highway) or ("trunk_link" in highway):
        return "4"
    logger.error(f"Unexpected case highway: {row['highway']}, full row: {row.to_dict()}")
    return "1"


def get_speed(row):
    speed_raw = row["maxspeed"]
    if not speed_raw:
        return guess_speed(row)
    if isinstance(speed_raw, str) and speed_raw.startswith("["):
        possible_speed = literal_eval(speed_raw)
    else:
        possible_speed = speed_raw
    if ";" in possible_speed:
        possible_speed = possible_speed.split(";")
    if isinstance(possible_speed, list):
        speed_list = [get_max_speed(possible_speed_item) for possible_speed_item in possible_speed]
        speed_list = [speed for speed in speed_list if speed]
        assert speed_list
        return speed_list
    speed = get_max_speed(possible_speed)
    if speed:
        return speed
    return guess_speed(row)


def fix_missing_lanes(df_edges: pd.DataFrame) -> pd.DataFrame:
    """Guesstimating lanes based on value of highway tag.

    :param df_edges: Edges DataFrame with some values for `lanes` tag missing.
    :type df_edges: pd.DataFrame
    :return: Edges DataFrame with guesstimated values for `lanes` tag.
    :rtype: pd.DataFrame
    """
    empty_lanes_condition = df_edges["lanes"].isna() | (df_edges["lanes"] == "0") | (df_edges["lanes"] == 0)
    df_edges.loc[empty_lanes_condition, "lanes"] = df_edges[empty_lanes_condition].apply(guess_lanes, axis=1)
    return df_edges

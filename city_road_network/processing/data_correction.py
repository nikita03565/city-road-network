from ast import literal_eval

from city_road_network.config import speed_map
from city_road_network.utils.utils import get_max_speed


def guess_speed(row):
    highway = row["highway"]
    living_street = row["living_street"]
    if "residential" in highway or "unclassified" in highway or "living_street" in highway or living_street == "yes":
        return speed_map["RU:living_street"]
    if "motorway_link" in highway:
        return speed_map["RU:motorway"]
    if ("trunk" in highway) or ("trunk_link" in highway):
        return speed_map["RU:rural"]
    return speed_map["RU:urban"]


def guess_lanes(row):
    highway = row["highway"]
    living_street = row["living_street"]
    if (
        "road" in highway
        or "residential" in highway
        or "unclassified" in highway
        or "living_street" in highway
        or living_street == "yes"
    ):
        return "1"
    if ("tertiary" in highway) or ("tertiary_link" in highway):
        return "2"
    if ("secondary" in highway) or ("secondary_link" in highway):
        return "2"
    if ("primary" in highway) or ("primary_link" in highway):
        return "3"
    if ("trunk" in highway) or ("trunk_link" in highway):
        return "4"
    raise ValueError(f"Unexpected case {row}")


def get_speed(row):
    speed_raw = row["maxspeed"]
    if not speed_raw:
        return guess_speed(row)
    if speed_raw.startswith("["):
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


def fix_missing_lanes(df_edges):
    empty_lanes_condition = df_edges["lanes"].isna() | (df_edges["lanes"] == "0") | (df_edges["lanes"] == 0)
    df_edges.loc[empty_lanes_condition, "lanes"] = df_edges[empty_lanes_condition].apply(guess_lanes, axis=1)
    return df_edges

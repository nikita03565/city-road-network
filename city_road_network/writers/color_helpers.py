import colorsys
from ast import literal_eval
from collections.abc import Callable

import numpy as np

from city_road_network.config import highway_color_mapping


def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % rgb


def get_pop_color(feature: dict, vmax: int = 600):
    value = feature["properties"]["value"]
    ratio = min(value / vmax, 1)
    b_g = int(255 * (1 - ratio))
    b_g = min(b_g, 200)
    return rgb_to_hex((255, b_g, b_g))


def get_mapping_color_getter(mapping: dict, key: str, default: str) -> Callable:
    def mapping_color_getter(feature, *args, **kwargs):
        value = feature[key]
        return mapping.get(value, default)

    return mapping_color_getter


def get_fixed_color_getter(color: str, *args, **kwargs) -> Callable:
    def fixed_color_getter(*args, **kwargs):
        return color

    return fixed_color_getter


def highway_color_getter(feature: dict) -> str:
    highway_raw = feature["properties"]["highway"]
    if isinstance(highway_raw, list):
        highway = highway_raw[0]
    else:
        highway = highway_raw if not highway_raw.startswith("[") else literal_eval(highway_raw)[0]
    color = highway_color_mapping.get(highway, "#B2BEB5")
    return color


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


def get_occupancy_color_getter(gradient: list | None = None, by_abs_value=False):
    if gradient is None:
        gradient = _build_gradient()

    def occupancy_color_getter(feature: dict) -> str:
        if by_abs_value:
            color_idx = min(feature["properties"]["passes_count"], len(gradient) - 1)
        else:  # by occupied percentage
            color_idx = min(int(feature["properties"]["capacity_occupied"] * len(gradient)), len(gradient) - 1)
        color_rgb = gradient[color_idx]
        return rgb_to_hex(color_rgb)

    return occupancy_color_getter

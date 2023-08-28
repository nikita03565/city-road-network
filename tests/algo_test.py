import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import wkt

from city_road_network.algo.gravity_model import run_gravity_model


def test_gravity_model():
    df = pd.DataFrame(
        data=[
            ["zone1", 140, 300, "POINT (30 60)"],
            ["zone2", 330, 270, "POINT (30.04 60)"],
            ["zone3", 280, 180, "POINT (30.055 60.05)"],
        ],
        columns=["name", "production", "poi_attraction", "centroid"],
    )
    gdf = gpd.GeoDataFrame(df)
    gdf["centroid"] = gdf["centroid"].apply(wkt.loads)
    result = run_gravity_model(gdf)

    sum_attr = result.sum(axis=0)
    sum_prod = result.sum(axis=1)
    for i in range(len(sum_attr)):
        assert sum_attr[i] == gdf["poi_attraction"][i]

    for i in range(len(sum_prod)):
        assert sum_prod[i] == gdf["production"][i]

    expected = np.array(
        [
            [0, 97, 43],
            [193, 0, 137],
            [107, 173, 0],
        ]
    )
    assert np.array_equal(result, expected)

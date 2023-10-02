import os
import pickle

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import wkt

from city_road_network.algo.gravity_model import run_gravity_model
from city_road_network.algo.simulation import (
    BatchPaths,
    yield_batches,
    yield_starts_ends,
)


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


expected_batches = [
    [
        BatchPaths(o_zone=0, d_zone=1, count=151),
        BatchPaths(o_zone=0, d_zone=2, count=47),
        BatchPaths(o_zone=0, d_zone=3, count=169),
        BatchPaths(o_zone=0, d_zone=4, count=16),
        BatchPaths(o_zone=0, d_zone=5, count=87),
        BatchPaths(o_zone=0, d_zone=6, count=98),
        BatchPaths(o_zone=0, d_zone=7, count=432),
    ],
    [
        BatchPaths(o_zone=0, d_zone=7, count=312),
        BatchPaths(o_zone=0, d_zone=8, count=10),
        BatchPaths(o_zone=0, d_zone=9, count=45),
        BatchPaths(o_zone=1, d_zone=0, count=47),
        BatchPaths(o_zone=1, d_zone=2, count=1),
        BatchPaths(o_zone=1, d_zone=3, count=3),
        BatchPaths(o_zone=1, d_zone=5, count=2),
        BatchPaths(o_zone=1, d_zone=6, count=2),
        BatchPaths(o_zone=1, d_zone=7, count=11),
        BatchPaths(o_zone=1, d_zone=9, count=1),
        BatchPaths(o_zone=2, d_zone=0, count=5),
        BatchPaths(o_zone=2, d_zone=7, count=1),
        BatchPaths(o_zone=3, d_zone=0, count=196),
        BatchPaths(o_zone=3, d_zone=1, count=13),
        BatchPaths(o_zone=3, d_zone=2, count=3),
        BatchPaths(o_zone=3, d_zone=4, count=3),
        BatchPaths(o_zone=3, d_zone=5, count=17),
        BatchPaths(o_zone=3, d_zone=6, count=20),
        BatchPaths(o_zone=3, d_zone=7, count=100),
        BatchPaths(o_zone=3, d_zone=8, count=1),
        BatchPaths(o_zone=3, d_zone=9, count=4),
        BatchPaths(o_zone=4, d_zone=0, count=3),
        BatchPaths(o_zone=4, d_zone=7, count=1),
        BatchPaths(o_zone=5, d_zone=0, count=7),
        BatchPaths(o_zone=5, d_zone=3, count=1),
        BatchPaths(o_zone=5, d_zone=6, count=2),
        BatchPaths(o_zone=5, d_zone=7, count=7),
        BatchPaths(o_zone=6, d_zone=0, count=19),
        BatchPaths(o_zone=6, d_zone=1, count=1),
        BatchPaths(o_zone=6, d_zone=3, count=3),
        BatchPaths(o_zone=6, d_zone=5, count=4),
        BatchPaths(o_zone=6, d_zone=7, count=28),
        BatchPaths(o_zone=6, d_zone=8, count=1),
        BatchPaths(o_zone=6, d_zone=9, count=1),
        BatchPaths(o_zone=7, d_zone=0, count=100),
        BatchPaths(o_zone=7, d_zone=1, count=5),
        BatchPaths(o_zone=7, d_zone=2, count=1),
        BatchPaths(o_zone=7, d_zone=3, count=12),
        BatchPaths(o_zone=7, d_zone=4, count=1),
        BatchPaths(o_zone=7, d_zone=5, count=6),
    ],
    [
        BatchPaths(o_zone=7, d_zone=5, count=6),
        BatchPaths(o_zone=7, d_zone=6, count=20),
        BatchPaths(o_zone=7, d_zone=8, count=3),
        BatchPaths(o_zone=7, d_zone=9, count=7),
        BatchPaths(o_zone=8, d_zone=0, count=5),
        BatchPaths(o_zone=8, d_zone=3, count=1),
        BatchPaths(o_zone=8, d_zone=5, count=1),
        BatchPaths(o_zone=8, d_zone=6, count=2),
        BatchPaths(o_zone=8, d_zone=7, count=11),
        BatchPaths(o_zone=8, d_zone=9, count=1),
        BatchPaths(o_zone=9, d_zone=0, count=9),
        BatchPaths(o_zone=9, d_zone=3, count=1),
        BatchPaths(o_zone=9, d_zone=5, count=1),
        BatchPaths(o_zone=9, d_zone=6, count=1),
        BatchPaths(o_zone=9, d_zone=7, count=11),
    ],
]


def test_yield_batches():
    trip_mat = np.array(
        [
            [0, 151, 47, 169, 16, 87, 98, 744, 10, 45],
            [47, 0, 1, 3, 0, 2, 2, 11, 0, 1],
            [5, 0, 0, 0, 0, 0, 0, 1, 0, 0],
            [196, 13, 3, 0, 3, 17, 20, 100, 1, 4],
            [3, 0, 0, 0, 0, 0, 0, 1, 0, 0],
            [7, 0, 0, 1, 0, 0, 2, 7, 0, 0],
            [19, 1, 0, 3, 0, 4, 0, 28, 1, 1],
            [100, 5, 1, 12, 1, 12, 20, 0, 3, 7],
            [5, 0, 0, 1, 0, 1, 2, 11, 0, 1],
            [9, 0, 0, 1, 0, 1, 1, 11, 0, 0],
        ]
    )
    batch_size = 1000
    batches = yield_batches(trip_mat, batch_size=batch_size)

    for i, batch in enumerate(batches):
        for j, b in enumerate(batch):
            exp = expected_batches[i][j]
            assert b.o_zone == exp.o_zone
            assert b.d_zone == exp.d_zone
            assert b.count == exp.count


def test_yield_starts_ends():
    with open(os.path.join("tests", "data", "test_old_paths.pkl"), "rb") as f:
        old_paths = pickle.load(f)
    batch_size = 1000
    batches = yield_starts_ends(old_paths, batch_size=batch_size)
    for i, batch in enumerate(batches):
        for j, b in enumerate(batch):
            exp = expected_batches[i][j]
            lst_starts_ends = list(b.starts_ends)
            for pair in lst_starts_ends:
                assert len(pair) == 2
            assert b.count == len(lst_starts_ends)
            assert b.o_zone == exp.o_zone
            assert b.d_zone == exp.d_zone
            assert b.count == exp.count

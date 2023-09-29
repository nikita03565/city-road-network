import random
from typing import NamedTuple

import networkx as nx
import numpy as np

from city_road_network.algo.common import PathNT
from city_road_network.utils.utils import get_logger

logger = get_logger(__name__)


class BatchPaths(NamedTuple):
    o_zone: int
    d_zone: int
    count: int


class BatchFixedPaths(NamedTuple):
    o_zone: int
    d_zone: int
    o_node: int
    d_node: int


class BuiltPaths(NamedTuple):
    o_zone: int
    d_zone: int
    paths: list[PathNT]


def yield_batches(trip_map, batch_size=1000) -> list[list[BatchPaths]]:
    trip_iter = np.ndenumerate(trip_map)
    lst = []
    cur_cap = batch_size
    while True:
        try:
            (i, j), v = next(trip_iter)
            remainder = v
            while remainder:
                cur_cut = min(cur_cap, remainder)
                remainder -= cur_cut
                cur_cap -= cur_cut
                lst.append(BatchPaths(i, j, int(cur_cut)))
                if cur_cap == 0:
                    yield lst
                    cur_cap = batch_size
                    lst = []
        except StopIteration:
            if lst:
                yield lst
            return


def yield_starts_ends(paths, batch_size=1000) -> list[list[BatchFixedPaths]]:
    lst = []
    for i, row in enumerate(paths):
        for j, cell in enumerate(row):
            for path_nt in cell:
                lst.append(BatchFixedPaths(i, j, path_nt.path[0], path_nt.path[-1]))
                if len(lst) >= batch_size:
                    yield lst
                    lst = []
    if lst:
        yield lst


# normal: needs graph: nx.MultiDiGraph, o_zone: int, d_zone: int
# fixed: needs only pairs
class RandomNodesGetter:
    @staticmethod
    def filter_nodes(graph: nx.MultiDiGraph, zone_id: str):
        nodes = [node for node, data in graph.nodes(data=True) if zone_id == str(data["zone"])]
        return nodes

    @staticmethod
    def get_random_node(graph: nx.MultiDiGraph, zone_id: str):
        return random.choice(RandomNodesGetter.filter_nodes(graph, zone_id))

    # TODO THIS SHOULD BE REPLACED FOR FIXED ENDS CASE
    @staticmethod
    def get_nodes_pair(graph: nx.MultiDiGraph, o_zone: int, d_zone: int):
        u = RandomNodesGetter.get_random_node(graph, str(o_zone))
        v = RandomNodesGetter.get_random_node(graph, str(d_zone))
        return u, v


class FixedNodesGetter:
    def __init__(self, pairs: list[BatchFixedPaths]) -> None:
        self.pairs = (p for p in pairs)  # turn into generator

    def get_nodes_pair(self, graph: nx.MultiDiGraph, o_zone: int, d_zone: int, *args, **kwargs):
        x = next(self.pairs, None)
        assert x.o_zone == o_zone
        assert x.d_zone == d_zone
        return x


class BaseSimulation:
    def __init__(self, graph: nx.MultiDiGraph, weight: str, pairs: list[BatchFixedPaths] | None = None) -> None:
        self.graph = graph
        self.weight = weight
        if pairs is not None:
            self.nodes_getter = FixedNodesGetter(pairs)
        else:
            self.nodes_getter = RandomNodesGetter()

    # THESE TWO ARE GOOD
    def _build_paths(self, o_zone: int, d_zone: int, count: int, max_iter: int = 100_000) -> list[PathNT]:
        paths = []
        i = 0
        while len(paths) != count:
            u, v = self.nodes_getter.get_nodes_pair(self.graph, o_zone, d_zone)

            try:
                path_cost, path = nx.single_source_dijkstra(self.graph, u, v, weight=self.weight)
            except Exception:
                path = None

            if path and path_cost:
                paths.append(PathNT(path, path_cost))

            i += 1
            if i > max_iter:
                raise ValueError(f"Failed to find required number {count} of paths..")
        assert len(paths) == count
        return paths

    def build_paths(self, batches: list[BatchPaths]) -> list[BuiltPaths]:
        print("STARTED!!!")
        all_paths = []
        for batch in batches:
            paths = self._build_paths(batch.o_zone, batch.d_zone, batch.count)
            all_paths.append(BuiltPaths(batch.o_zone, batch.d_zone, paths))
        return all_paths


# class NaiveSimulation(BaseSimulation):
#     pass


# class NaiveSimulationFixedNodes:
#     pass


# class SmarterSimulation(BaseSimulation):
#     pass


# class SmarterSimulationFixedNodes:
#     pass

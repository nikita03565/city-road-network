import numpy as np
import networkx as nx
import random
from city_road_network.algo.common import PathNT
from typing import NamedTuple
from city_road_network.utils.utils import get_logger

logger = get_logger(__name__)


def filter_nodes(graph: nx.MultiDiGraph, zone_id: str):
    nodes = [node for node, data in graph.nodes(data=True) if zone_id == str(data["zone"])]
    return nodes


def get_random_node(graph: nx.MultiDiGraph, zone_id: str):
    return random.choice(filter_nodes(graph, zone_id))


class BatchPaths(NamedTuple):
    o_zone: int
    d_zone: int
    count: int


class BatchFixedPaths(NamedTuple):
    o_node: int
    d_node: int


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
    for row in paths:
        for cell in row:
            for path_nt in cell:
                lst.append(BatchFixedPaths(path_nt.path[0], path_nt.path[-1]))
                if len(lst) >= batch_size:
                    yield lst
                    lst = []
    if lst:
        yield lst


class BaseSimulation:
    def get_nodes_pair(self, graph: nx.MultiDiGraph, o_zone: int, d_zone: int, path_starts_ends=None, path_idx=None):
        if path_starts_ends is None:
            u = get_random_node(graph, str(o_zone))
            v = get_random_node(graph, str(d_zone))
            return u, v
        return path_starts_ends[o_zone][d_zone][path_idx]

    def build_path(
        self, graph: nx.MultiDiGraph, o_zone: int, d_zone: int, weight: str, path_starts_ends, max_iter: int = 100
    ) -> PathNT | None:
        for _ in range(max_iter):
            u, v = self.get_nodes_pair(graph, o_zone, d_zone, path_starts_ends, path_idx="#TODO")
            try:
                path_cost, path = nx.single_source_dijkstra(graph, u, v, weight=weight)
            except Exception:
                path = None
            if path and path_cost:
                return PathNT(path, path_cost)
        logger.error("Failed to find path between zones %s and %s after %s iterations", o_zone, d_zone, max_iter)
        return None

    def build_paths(
        self,
        graph: nx.MultiDiGraph,
        o_zone: int,
        d_zone: int,
        count: int,
        weight: str,
        path_starts_ends,
        max_iter: int = 100_000,
    ) -> list[PathNT]:
        paths = []
        i = 0
        while len(paths) != count:
            u, v = self.get_nodes_pair(graph, o_zone, d_zone, path_starts_ends, path_idx=len(paths))

            try:
                path_cost, path = nx.single_source_dijkstra(graph, u, v, weight=weight)
            except Exception:
                path = None

            if path and path_cost:
                paths.append(PathNT(path, path_cost))

            i += 1
            if i > max_iter:
                raise ValueError(f"Failed to find required number {count} of paths..")
        assert len(paths) == count
        return paths


class NaiveSimulation(BaseSimulation):
    pass


class NaiveSimulationFixedNodes:
    pass


class SmarterSimulation(BaseSimulation):
    pass


class SmarterSimulationFixedNodes:
    pass

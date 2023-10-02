import random
from collections.abc import Generator, Iterator
from dataclasses import dataclass

import networkx as nx
import numpy as np

from city_road_network.algo.common import TimedPath
from city_road_network.utils.utils import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class BatchPaths:
    o_zone: int
    d_zone: int
    count: int


@dataclass(frozen=True)
class BatchFixedPaths(BatchPaths):
    starts_ends: Iterator[tuple[int, int]]


@dataclass(frozen=True)
class BuiltPaths:
    o_zone: int
    d_zone: int
    paths: list[TimedPath]


def yield_batches(trip_mat: np.array, batch_size=1000) -> Generator[list[BatchPaths], None, None]:
    trip_iter = np.ndenumerate(trip_mat)
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


def yield_starts_ends(
    paths: list[list[list[TimedPath]]], batch_size=1000
) -> Generator[list[BatchFixedPaths], None, None]:
    lst = []
    cur_cap = batch_size
    for i, row in enumerate(paths):
        for j, cell in enumerate(row):
            v = len(cell)
            slice_start = 0
            remainder = v
            while remainder:
                cur_cut = min(cur_cap, remainder)
                remainder -= cur_cut
                cur_cap -= cur_cut
                starts_ends = iter([(x.path[0], x.path[-1]) for x in cell[slice_start : slice_start + cur_cut]])
                lst.append(BatchFixedPaths(i, j, int(cur_cut), starts_ends))
                slice_start = cur_cut
                if cur_cap == 0:
                    yield lst
                    cur_cap = batch_size
                    lst = []
    if lst:
        yield lst


class RandomNodesGetter:
    @staticmethod
    def filter_nodes(graph: nx.MultiDiGraph, zone_id: str):
        nodes = [node for node, data in graph.nodes(data=True) if zone_id == str(data["zone"])]
        return nodes

    @staticmethod
    def get_random_node(graph: nx.MultiDiGraph, zone_id: str):
        return random.choice(RandomNodesGetter.filter_nodes(graph, zone_id))

    @staticmethod
    def get_nodes_pair(graph: nx.MultiDiGraph, bp: BatchPaths):
        u = RandomNodesGetter.get_random_node(graph, str(bp.o_zone))
        v = RandomNodesGetter.get_random_node(graph, str(bp.d_zone))
        return u, v


class FixedNodesGetter:
    def get_nodes_pair(self, graph: nx.MultiDiGraph, bp: BatchFixedPaths, *args, **kwargs):
        return next(bp.starts_ends)


class BaseSimulation:
    def __init__(self, graph: nx.MultiDiGraph, weight: str) -> None:
        self.graph = graph
        self.weight = weight

    def _build_paths(self, bp: BatchPaths, max_iter: int = 100_000) -> list[TimedPath]:
        paths = []
        i = 0
        while len(paths) != bp.count:
            u, v = self.nodes_getter.get_nodes_pair(self.graph, bp)

            try:
                path_cost, path = nx.single_source_dijkstra(self.graph, u, v, weight=self.weight)
            except Exception:
                path = None

            if path and path_cost:
                paths.append(TimedPath(path, path_cost))

            i += 1
            if i > max_iter:
                raise ValueError(f"Failed to find required number {bp.count} of paths..")
        assert len(paths) == bp.count
        return paths

    def build_paths(self, batches: list[BatchPaths]) -> list[BuiltPaths]:
        all_paths = []
        for batch in batches:
            paths = self._build_paths(batch)
            all_paths.append(BuiltPaths(batch.o_zone, batch.d_zone, paths))
        return all_paths


class NaiveSimulation(BaseSimulation):
    def __init__(self, graph: nx.MultiDiGraph, weight: str) -> None:
        super().__init__(graph, weight)
        self.nodes_getter = RandomNodesGetter()


class NaiveSimulationFixedNodes(BaseSimulation):
    def __init__(self, graph: nx.MultiDiGraph, weight: str) -> None:
        super().__init__(graph, weight)
        self.nodes_getter = FixedNodesGetter()

    def build_paths(self, batches: list[BatchFixedPaths]) -> list[BuiltPaths]:
        return super().build_paths(batches)


# class SmarterSimulation(BaseSimulation):
#     pass


# class SmarterSimulationFixedNodes:
#     pass

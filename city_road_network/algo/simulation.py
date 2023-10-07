import copy
import os
import time
from collections.abc import Generator, Iterator
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from functools import partial
from itertools import islice

import networkx as nx
import numpy as np

from city_road_network.algo.common import (
    TimedPath,
    add_passes_count,
    recalculate_flow_time,
)
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


def calc_total_paths(trip_mat: np.array = None, old_paths: list[list[list[TimedPath]]] = None) -> int:
    if trip_mat is not None:
        return trip_mat.sum()
    total_paths = 0
    for row in old_paths:
        for cell in row:
            total_paths += len(cell)
    return total_paths


def take(iterable, n):
    return list(islice(iterable, n))


def chunked(iterable, n):
    iterator = iter(partial(take, iter(iterable), n), [])
    return iterator


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


def validate_weight(graph, weight):
    edge_attrs = next(iter(graph.edges(data=True)))[2]
    if weight not in edge_attrs:
        raise ValueError(f"Weight '{weight}' is not in edge attrs: {edge_attrs.keys()}")


def get_matrix_size(n=None, trip_mat=None, old_paths=None):
    if n is not None:
        return n
    if trip_mat is not None:
        return trip_mat.shape[0]
    if old_paths is not None:
        return len(old_paths)
    raise ValueError("One of trip_mat, old_paths must be provided")


class RandomNodesGetter:
    @staticmethod
    def filter_nodes(graph: nx.MultiDiGraph, zone_id: str):
        nodes = [node for node, data in graph.nodes(data=True) if zone_id == str(data["zone"])]
        return nodes

    @staticmethod
    def get_random_node(graph: nx.MultiDiGraph, zone_id: str):
        return np.random.RandomState().choice(RandomNodesGetter.filter_nodes(graph, zone_id))

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
        g = copy.deepcopy(graph)
        validate_weight(g, weight)
        for s, e, edge_data in g.edges(data=True):
            edge_data["passes_count"] = 0
        self.graph = g
        self.weight = weight
        self.nodes_getter = None

    def set_nodes_getter(self, trip_mat, old_paths):
        if trip_mat is not None:
            self.nodes_getter = RandomNodesGetter()
        elif old_paths is not None:
            self.nodes_getter = FixedNodesGetter()
        else:
            raise ValueError("One of trip_mat, old_paths must be provided")

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

    def run(self, trip_mat=None, old_paths=None, n=None, max_workers=None, batch_size=1000):
        if max_workers is None:
            max_workers = os.cpu_count()

        n = get_matrix_size(n, trip_mat, old_paths)
        self.set_nodes_getter(trip_mat, old_paths)

        if trip_mat is not None:
            trip_mat = trip_mat[:n, :n]

        if trip_mat is not None:
            batches = yield_batches(trip_mat, batch_size=batch_size)
        if old_paths is not None:
            batches = yield_starts_ends(old_paths, batch_size=batch_size)

        c = 0
        mat = [[list() for _ in range(n)] for _ in range(n)]
        start = time.time()
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            for result in executor.map(self.build_paths, batches):
                c += 1
                logger.info("processed batch", c)
                for built_paths in result:
                    mat[built_paths.o_zone][built_paths.d_zone].extend(built_paths.paths)

        logger.info("finished in", time.time() - start)

        self.graph = add_passes_count(self.graph, mat)
        return mat, self.graph


class SmarterSimulation(BaseSimulation):
    def calc_batch_size(self, trip_mat=None, old_paths=None, max_workers=None, n_recalc=20):
        total_paths = calc_total_paths(trip_mat, old_paths)
        per_iteration = total_paths // n_recalc
        batch_size = per_iteration // max_workers
        return batch_size

    def run(self, trip_mat=None, old_paths=None, n=None, max_workers=None, n_recalc=20):
        if max_workers is None:
            max_workers = os.cpu_count()

        n = get_matrix_size(n, trip_mat, old_paths)
        self.set_nodes_getter(trip_mat, old_paths)

        if trip_mat is not None:
            trip_mat = trip_mat[:n, :n]

        batch_size = self.calc_batch_size(trip_mat, old_paths, max_workers, n_recalc)

        if trip_mat is not None:
            batches = yield_batches(trip_mat, batch_size=batch_size)
        if old_paths is not None:
            batches = yield_starts_ends(old_paths, batch_size=batch_size)
        chunks = chunked(batches, max_workers)

        c = 0
        mat = [[list() for _ in range(n)] for _ in range(n)]
        start = time.time()
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            for chunk in chunks:
                mat_iter = [[list() for _ in range(n)] for _ in range(n)]
                for result in executor.map(self.build_paths, chunk):
                    c += 1
                    logger.info("processed batch", c)
                    for built_paths in result:
                        mat[built_paths.o_zone][built_paths.d_zone].extend(built_paths.paths)
                        mat_iter[built_paths.o_zone][built_paths.d_zone].extend(built_paths.paths)
                self.graph = recalculate_flow_time(add_passes_count(self.graph, mat_iter))
                logger.info("Processed chunk...")
        logger.info("finished in", time.time() - start)
        return mat, self.graph

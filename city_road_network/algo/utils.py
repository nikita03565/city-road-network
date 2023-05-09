import copy
import random
from math import exp
from typing import NamedTuple

import networkx as nx


class PathNT(NamedTuple):
    path: list[int]
    travel_time: float


def yeild_zone_pairs(n: int, *rest):
    for i in range(n):
        for j in range(n):
            yield i, j, *rest


def add_passes_count(graph: nx.MultiDiGraph, trip_mat: list[list[list[PathNT]]]):
    g = copy.deepcopy(graph)
    for i in range(len(trip_mat)):
        for j in range(len(trip_mat)):
            for path_tuple in trip_mat[i][j]:
                path = path_tuple.path
                for k in range(len(path) - 1):
                    start_node = path[k]
                    end_node = path[k + 1]
                    g[start_node][end_node][0]["passes_count"] += 1
    for start_id, end_id, key, edge_data in g.edges(data=True, keys=True):
        g[start_id][end_id][key]["capacity_occupied"] = edge_data["passes_count"] / edge_data["capacity (veh/h)"]
    return g


def recalculate_flow_time(graph: nx.MultiDiGraph):
    g = copy.deepcopy(graph)
    for start_id, end_id, key, edge_data in g.edges(data=True, keys=True):
        ffs = edge_data["maxspeed (km/h)"]
        occ = edge_data["passes_count"]
        cap = edge_data["capacity (veh/h)"]

        speed = max(ffs * exp(-0.5 * (occ / cap) ** 2), ffs / 10)
        g[start_id][end_id][key]["cur_speed (km/h)"] = speed
        g[start_id][end_id][key]["flow_time (s)"] = int((edge_data["length (km)"] / speed) * 3600)
    return g


def filter_nodes(graph: nx.MultiDiGraph, zone_id: str):
    nodes = [node for node, data in graph.nodes(data=True) if zone_id in data["zones"]]
    return nodes


def get_random_node(graph: nx.MultiDiGraph, zone_id: str):
    return random.choice(filter_nodes(graph, zone_id))


def calc_path_costs(graph: nx.MultiDiGraph, path: list[int]) -> PathNT:
    len_km = 0
    travel_time = 0
    for i in range(len(path) - 1):
        start_node = path[i]
        end_node = path[i + 1]
        edge = graph[start_node][end_node][0]
        len_km += edge["length (km)"]
        travel_time += edge["flow_time (s)"]
    return PathNT(path, len_km, travel_time)


def get_nodes_pair(graph: nx.MultiDiGraph, o_zone: int, d_zone: int, path_starts_ends=None, path_idx=None):
    if path_starts_ends is None:
        u = get_random_node(graph, str(o_zone))
        v = get_random_node(graph, str(d_zone))
        return u, v
    return path_starts_ends[o_zone][d_zone][path_idx]


def build_paths(
    graph: nx.MultiDiGraph, o_zone: int, d_zone: int, count: int, weight: str, path_starts_ends, max_iter: int = 100_000
) -> list[PathNT]:
    paths = []
    i = 0
    while len(paths) != count:
        u, v = get_nodes_pair(graph, o_zone, d_zone, path_starts_ends, path_idx=len(paths))

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

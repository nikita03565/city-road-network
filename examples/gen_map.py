import json
import os
import pickle

import networkx as nx
import pandas as pd

from city_road_network.algo.common import add_passes_count
from city_road_network.downloaders.osm import get_relation_poly
from city_road_network.utils.io import read_graph
from city_road_network.utils.map import (
    draw_boundaries,
    draw_graph,
    draw_poi,
    draw_population,
    draw_trips_map,
    draw_zones,
    generate_map,
)
from city_road_network.utils.utils import get_data_subdir, get_geojson_subdir

if __name__ == "__main__":
    kad_poly = get_relation_poly(relation_id="1861646")
    spb_poly = get_relation_poly(relation_id="337422")
    boundaries = kad_poly.union(spb_poly)
    draw_boundaries(boundaries, save=True, city_name="spb", filename="draw_boundaries.html")

    city_name = "spb"
    json_dir = get_geojson_subdir(city_name)
    data_dir = get_data_subdir(city_name)
    graph = read_graph(
        os.path.join(data_dir, "nodelist_upd.csv"),
        os.path.join(data_dir, "edgelist_upd.csv"),
    )
    zones_df = pd.read_csv(os.path.join(data_dir, "zones.csv"), index_col=0)
    poi_df = pd.read_csv(os.path.join(data_dir, "poi.csv"), index_col=0)
    pop_df = pd.read_csv(os.path.join(data_dir, "population.csv"), dtype={"value": float}, index_col=0)

    with open(os.path.join(data_dir, "smarter_paths_by_flow_time_s_1696597874.pkl"), "rb") as f:
        old_paths = pickle.load(f)

    with open(os.path.join(json_dir, "nodes_last.json")) as f:
        nodes = json.loads(f.read())
    with open(os.path.join(json_dir, "edges_last.json")) as f:
        edges = json.loads(f.read())
    with open(os.path.join(json_dir, "zones_last.json")) as f:
        zones = json.loads(f.read())
    with open(os.path.join(json_dir, "population_last.json")) as f:
        pop = json.loads(f.read())
    with open(os.path.join(json_dir, "poi_last.json")) as f:
        poi = json.loads(f.read())

    generate_map(nodes_data=nodes, save=True, city_name="spb", filename="nodes_only.html")
    generate_map(nodes_data=nodes, edges_data=edges, save=True, city_name="spb", filename="graph.html")
    generate_map(nodes_data=nodes, zones_data=zones, save=True, city_name="spb", filename="nodes_zones.html")
    generate_map(pop_data=pop, save=True, city_name="spb", filename="pop_only.html")
    generate_map(
        nodes_data=nodes,
        edges_data=edges,
        zones_data=zones,
        pop_data=pop,
        poi_data=poi,
        save=True,
        city_name="spb",
        filename="all_data.html",
    )

    draw_graph(graph, save=True, city_name="spb", filename="draw_graph.html")
    nx.set_edge_attributes(graph, 0, "passes_count")
    g = add_passes_count(graph, old_paths)
    draw_trips_map(g, save=True, city_name="spb", filename="draw_trips_map.html")
    draw_poi(poi_df, save=True, city_name="spb", filename="draw_poi.html")
    draw_population(pop_df, save=True, city_name="spb", filename="draw_pop.html")
    draw_zones(zones_df, save=True, city_name="spb", filename="draw_zones.html")

import os

import pandas as pd

from city_road_network.downloaders.osm import get_osm_data, get_relation_poly
from city_road_network.processing.ghsl import process_population
from city_road_network.processing.graph import process_edges
from city_road_network.processing.zones import process_zones
from city_road_network.utils.io import read_graph
from city_road_network.utils.map import draw_graph, draw_population, draw_zones
from city_road_network.utils.utils import get_data_subdir
from city_road_network.writers.csv import save_osm_data

if __name__ == "__main__":
    CITY_NAME = "spb"
    data_dir = get_data_subdir(city_name=CITY_NAME)

    # moscow_rel = "2555133"
    # chel_rel = "4442556"
    # berlin_rel = "62422"
    # london_rel = "175342"
    # paris_rel = "71525"
    # boundaries = get_relation_poly(relation_id=paris_rel)
    kad_poly = get_relation_poly(relation_id="1861646")
    spb_poly = get_relation_poly(relation_id="337422")
    boundaries = kad_poly.union(spb_poly)
    data = get_osm_data(boundaries, admin_level=8)
    len(data.graph.nodes), len(data.graph.edges)
    save_osm_data(data, city_name=CITY_NAME)
    pop_df = process_population(boundaries, CITY_NAME)
    process_edges(city_name=CITY_NAME)
    nodes_df, zones_df = process_zones(city_name=CITY_NAME)
    zones_map = draw_zones(zones_df, save=True, city_name=CITY_NAME, filename="zones.html")
    map = draw_population(pop_df, save=True, filename="population.html", city_name=CITY_NAME)
    graph = read_graph(
        os.path.join(data_dir, "nodelist_upd.csv"),
        os.path.join(data_dir, "edgelist_upd.csv"),
    )
    map = draw_graph(graph, save=True, filename="map.html", city_name=CITY_NAME)
    df = pd.read_csv(os.path.join(data_dir, "nodelist_upd.csv"))
    df.head()

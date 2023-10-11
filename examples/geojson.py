import os

import pandas as pd

from city_road_network.utils.io import read_graph
from city_road_network.utils.utils import get_data_subdir, get_html_subdir
from city_road_network.writers.geojson import (
    export_graph,
    export_poi,
    export_population,
    export_zones,
)

if __name__ == "__main__":
    # loading data...
    city_name = "spb"
    data_dir = get_data_subdir(city_name)
    html_dir = get_html_subdir(city_name)

    zones_df = pd.read_csv(os.path.join(data_dir, "zones_upd.csv"), index_col=0)
    poi_df = pd.read_csv(os.path.join(data_dir, "poi_upd.csv"), index_col=0)
    pop_df = pd.read_csv(os.path.join(data_dir, "population.csv"), dtype={"value": float}, index_col=0)
    G = read_graph(os.path.join(data_dir, "nodelist_upd.csv"), os.path.join(data_dir, "edgelist_upd.csv"))
    nodes, edges = export_graph(
        G, save=True, city_name=city_name, nodes_filename="nodes_last.json", edges_filename="edges_last.json"
    )
    export_zones(zones_df, save=True, city_name=city_name, filename="zones_last.json")
    export_population(pop_df, save=True, city_name=city_name, filename="population_last.json")
    export_poi(poi_df, save=True, city_name=city_name, filename="poi_last.json")

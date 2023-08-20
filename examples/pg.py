import os

import pandas as pd

from city_road_network.utils.utils import get_data_subdir
from city_road_network.writers import postgres

if __name__ == "__main__":
    city_name = "spb"
    data_dir = get_data_subdir(city_name)
    nodes_df = pd.read_csv(os.path.join(data_dir, "nodelist_upd.csv"), index_col=0)
    edges_df = pd.read_csv(os.path.join(data_dir, "edgelist_upd.csv"), index_col=0)
    zones_df = pd.read_csv(os.path.join(data_dir, "zones_upd.csv"), index_col=0)
    poi_df = pd.read_csv(os.path.join(data_dir, "poi_upd.csv"), index_col=0)
    pop_df = pd.read_csv(os.path.join(data_dir, "population.csv"), index_col=0)

    postgres.create_tables()
    postgres.create_zones(zones_df)
    postgres.create_graph(nodes_df, edges_df, zones_df=zones_df)
    postgres.create_poi(poi_df, zones_df=zones_df)
    postgres.create_population(pop_df)

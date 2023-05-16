import os

import pandas as pd

from city_road_network.utils.utils import get_data_subdir
from city_road_network.writers.neo4j_manager import NeoManager


def fill_database(city_name: str):
    data_dir = get_data_subdir(city_name)

    nodes_df = pd.read_csv(os.path.join(data_dir, "nodelist_upd.csv"), index_col=0)
    edges_df = pd.read_csv(os.path.join(data_dir, "edgelist_upd.csv"), index_col=0)
    neo = NeoManager()
    for node_id, node_data in nodes_df.iterrows():
        payload = {"id": str(node_id), "lat": node_data.pop("lat"), "lon": node_data.pop("lon"), **node_data}
        neo.add_node(payload, "")

    for _, edge_data in edges_df.iterrows():
        payload = edge_data.to_dict()
        start = str(payload.pop("start_node"))
        end = str(payload.pop("end_node"))
        neo.create_relationship(start, end, payload)

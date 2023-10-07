import json
import os

from city_road_network.utils.io import read_graph
from city_road_network.utils.utils import get_data_subdir, get_html_subdir
from city_road_network.writers.geojson import export_graph

if __name__ == "__main__":
    # loading data...
    city_name = "spb"
    data_dir = get_data_subdir(city_name)
    html_dir = get_html_subdir(city_name)
    G = read_graph(os.path.join(data_dir, "nodelist_upd.csv"), os.path.join(data_dir, "edgelist_upd.csv"))

    d = export_graph(G)
    with open("geojson1.json", "w") as f:
        f.write(json.dumps(d))

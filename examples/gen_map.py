# import os
# import time

# from city_road_network.utils.utils import get_geojson_subdir, get_html_subdir

# if __name__ == "__main__":
#     json_dir = get_geojson_subdir("spb")

#     with open(os.path.join(json_dir, "nodes_1696867060.json")) as f:
#         nodes = f.read()
#     with open(os.path.join(json_dir, "edges_1696867095.json")) as f:
#         edges = f.read()
#     with open(os.path.join(json_dir, "zones_1696867096.json")) as f:
#         zones = f.read()
#     with open(os.path.join(json_dir, "pop_1696867331.json")) as f:
#         pop = f.read()
#     with open(os.path.join(json_dir, "poi_1696867390.json")) as f:
#         poi = f.read()

#     generate_map(nodes_data=nodes, save=True, city_name="spb", filename="nodes_only.html")
#     generate_map(nodes_data=nodes, edges_data=edges, save=True, city_name="spb", filename="graph.html")
#     generate_map(nodes_data=nodes, zones_data=zones, save=True, city_name="spb", filename="nodes_zones.html")
#     generate_map(pop_data=pop, save=True, city_name="spb", filename="pop_only.html")
#     generate_map(
#         nodes_data=nodes,
#         edges_data=edges,
#         zones_data=zones,
#         pop_data=pop,
#         poi_data=poi,
#         save=True,
#         city_name="spb",
#         filename="all_data.html",
#     )

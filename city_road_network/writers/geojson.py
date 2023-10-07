from ast import literal_eval

import networkx as nx

from city_road_network.config import highway_color_mapping


def export_graph(
    graph: nx.DiGraph,
    node_popup_keys: list[str] | None = None,
    way_popup_keys: list[str] | None = None,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
):
    """Draws graph on map"""
    # node_data = next(iter(graph.nodes(data=True)))[1]
    # location = node_data["lat"], node_data["lon"]

    if node_popup_keys is None:
        node_popup_keys = ["id", "highway", "zone"]
    if way_popup_keys is None:
        way_popup_keys = [
            "start_node",
            "end_node",
            "osmid",
            "highway",
            "surface",
            "speed (km/h)",
            "lanes",
            "oneway",
            "length (m)",
            "name",
            "capacity (veh/h)",
            "free_flow_time (h)",
        ]
    opacity = 0.5
    nodes = {"type": "FeatureCollection", "features": []}
    for idx, node_data in graph.nodes(data=True):
        node_data["id"] = idx

        # popup = "<br/>".join([f"{key}: {node_data[key]}" for key in node_popup_keys if key in node_data])
        nodes["features"].append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [node_data["lon"], node_data["lat"]]},
                "properties": {**node_data, "fill": "blue", "fill-opacity": opacity},
            }
        )

        # map.add_child(
        #     folium.Circle(location=(node_data["lat"], node_data["lon"]), fill=True, radius=3, color="blue", popup=popup)
        # )
    edges = {"type": "FeatureCollection", "features": []}
    for start_id, end_id, edge_data in graph.edges(data=True):
        start_node = graph.nodes[start_id]
        end_node = graph.nodes[end_id]

        # popup = "<br/>".join([f"{key}: {edge_data[key]}" for key in way_popup_keys if key in edge_data])

        highway_raw = edge_data["highway"]
        if isinstance(highway_raw, list):
            highway = highway_raw[0]
        else:
            highway = highway_raw if not highway_raw.startswith("[") else literal_eval(highway_raw)[0]
        color = highway_color_mapping.get(highway, "#B2BEB5")
        edges["features"].append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [start_node["lon"], start_node["lat"]],
                        [end_node["lon"], end_node["lat"]],
                    ],
                },
                "properties": {**edge_data, "fill": color, "fill-opacity": opacity},
            }
        )

        # map.add_child(
        #     folium.PolyLine(
        #         locations=[
        #             [start_node["lat"], start_node["lon"]],
        #             [end_node["lat"], end_node["lon"]],
        #         ],
        #         popup=popup,
        #         opacity=0.7,
        #         color=color,
        #     )
        # )
    # if save:
    #     save_map(map, filename=filename, city_name=city_name)
    return nodes, edges

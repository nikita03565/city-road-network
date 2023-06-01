import networkx as nx
import pandas as pd

from city_road_network.config import default_crs

START_NODE = "start_node"
END_NODE = "end_node"


def read_graph(nodelist_filename: str, edgelist_filename: str) -> nx.DiGraph:
    """Reads graph from nodelist and edgelist files.

    :param nodelist_filename: Name of file containing nodes.
    :type nodelist_filename: str
    :param edgelist_filename: Name of file containing edges.
    :type edgelist_filename: str
    :return: Graph built from nodes and edges.
    :rtype: nx.DiGraph
    """
    nodelist = pd.read_csv(nodelist_filename, index_col=0)
    edgelist = pd.read_csv(
        edgelist_filename, index_col=0, dtype={"length (m)": float, "flow_time (s)": float, "maxspeed (km/h)": float}
    )

    graph = nx.MultiDiGraph(crs=default_crs)

    for _, node in nodelist.iterrows():
        all_attrs = node.to_dict()
        attrs = {k: v for k, v in all_attrs.items()}
        graph.add_node(node["id"], **attrs)

    for _, edge in edgelist.iterrows():
        all_attrs = edge.to_dict()
        attrs = {k: v for k, v in all_attrs.items()}
        graph.add_edge(edge[START_NODE], edge[END_NODE], **attrs)
    return graph


def get_edgelist_from_graph(graph):
    data_list = []
    for start_id, end_id, key, edge_data in graph.edges(data=True, keys=True):
        data_list.append({"start_node": start_id, "end_node": end_id, "key": key, **edge_data})
    return pd.DataFrame(data_list)


def get_nodelist_from_graph(graph):
    data_list = []
    for node_id, node_data in graph.nodes(data=True):
        data_list.append({"id": node_id, **node_data})
    return pd.DataFrame(data_list)

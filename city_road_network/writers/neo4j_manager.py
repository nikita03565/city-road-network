import json

from dotenv import dotenv_values
from neo4j import GraphDatabase

from city_road_network.utils.utils import get_logger


class NeoManager:
    node_query_template = "CREATE (n:Road:`{label}`) SET {attrs};"
    node_query_template_no_label = "CREATE (n:Road) SET {attrs};"
    get_node_query_template = "MATCH (n) WHERE n.id = {node_id} return n;"
    # fmt: off
    way_query_template = """
        MATCH (u), (v)
        WHERE u.id = {u_id} AND v.id = {v_id}
        CREATE (u)-[r:Neighbor {attrs}]->(v)
    """
    # fmt: on

    def __init__(self, uri=None, user=None, password=None, database=None):
        config = dotenv_values()
        self.driver = GraphDatabase.driver(
            uri or config["neo_uri"], auth=(user or config["neo_user"], password or config["neo_password"])
        )
        self.session = self.driver.session(database=database or config["neo_database"])
        self.logger = get_logger(__name__)
        self.log = config["log"].lower() == "true"

    def __del__(self):
        self.close()

    def close(self):
        self.driver.close()

    def _construct_node_query(self, attrs_dict, label):
        attrs = ", ".join(f"n.`{key}` = ${key}" for key in attrs_dict)
        if label:
            return self.node_query_template.format(attrs=attrs, label=label)
        return self.node_query_template_no_label.format(attrs=attrs)

    def _create_node(self, tx, attrs, label):
        query = self._construct_node_query(attrs, label)
        tx.run(query, **attrs)

    def add_node(self, attrs, label):
        if self.log:
            self.logger.debug("Add node")
        self.session.write_transaction(self._create_node, attrs, label)

    def _delete_node_fn(self, tx, n_id):
        tx.run(f'match (n) where n.id="{n_id}" detach delete n;')

    def delete_node(self, n_id):
        if self.log:
            self.logger.debug("Deleting node")
        self.session.write_transaction(self._delete_node_fn, n_id)

    def _delete_nodes_fn(self, tx, ids):
        ids_string = ", ".join([f'"{id}"' for id in ids])
        tx.run(f"match (n) where n.id in [{ids_string}] detach delete n;")

    def delete_nodes(self, ids):
        if self.log:
            self.logger.debug("Deleting nodes")
        self.session.write_transaction(self._delete_nodes_fn, ids)

    def _get_node(self, tx, node_id):
        query = self.get_node_query_template.format(node_id=node_id)
        res = tx.run(query)
        single = res.single()
        if single:
            if self.log:
                self.logger.debug("Found node")
            return single[0]
        if self.log:
            self.logger.debug("Didn't find node")
        return None

    def get_node(self, node_id):
        if self.log:
            self.logger.debug("Select node", extra={"node_id": node_id})
        node = self.session.read_transaction(self._get_node, node_id)
        return node

    def _construct_way_query(self, u_id, v_id, attrs):
        def get_value(value):
            if isinstance(value, (list, set, tuple)):
                v = json.dumps(list(value))
            elif isinstance(value, str):
                v = value
            else:
                return value
            return "'" + v.replace("'", "\\'") + "'"

        attrs_str = "{" + ", ".join(f"`{key}`: {get_value(value)}" for key, value in attrs.items()) + "}"
        return self.way_query_template.format(u_id=u_id, v_id=v_id, attrs=attrs_str)

    def _create_rel(self, tx, u_id, v_id, attrs):
        query = self._construct_way_query(u_id, v_id, attrs)
        return tx.run(query)

    def create_relationship(self, u_id, v_id, attrs):
        if self.log:
            self.logger.debug("Add way")
        res = self.session.write_transaction(self._create_rel, u_id, v_id, attrs)
        return res

    def _read_query_fn(self, tx, query, result_type):
        x = tx.run(query)
        if result_type == "flat":
            return x.values()
        if result_type == "graph":
            return x.graph()
        raise ValueError("Unknown result type")

    def read_query(self, query, result_type="flat"):
        res = self.session.read_transaction(self._read_query_fn, query, result_type)
        return res

    def _write_query_fn(self, tx, query):
        res = tx.run(query)
        return res

    def write_query(self, query):
        res = self.session.write_transaction(self._write_query_fn, query)
        return res

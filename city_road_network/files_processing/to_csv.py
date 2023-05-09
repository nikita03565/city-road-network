import json

import pandas as pd
from lxml import etree
from utils import get_attrs_from_tags, get_filtered_node_attrs, is_road1, speed_map

with open("map.osm", "rb") as f:
    content = f.read()

tree = etree.fromstring(content)

ways = []
keep_nodes = set()
all_highways = set()
for way in tree.xpath("//way"):
    nds = way.xpath("./nd")
    nds_refs = [nd.attrib["ref"] for nd in nds]
    tags = way.xpath("./tag")
    way_attrs = dict(way.attrib)
    tags_attrs = get_attrs_from_tags(tags)
    way_attrs["nds"] = json.dumps(nds_refs)
    highway = tags_attrs.get("highway", "")
    building = tags_attrs.get("building", "no")
    landuse = tags_attrs.get("landuse", "")
    shop = tags_attrs.get("shop", "")
    max_speed = tags_attrs.get("maxspeed")
    try:
        float(max_speed)
    except (ValueError, TypeError):
        tags_attrs["maxspeed"] = speed_map.get(max_speed)
    all_highways.add(highway)
    if is_road1(highway) and building == "no" and not shop and landuse != "commercial":
        way_attrs["tags"] = json.dumps(tags_attrs)
        ways.append(way_attrs)
        keep_nodes.update(nds_refs)

nodes = []
nodes_ids = set()
for node in tree.xpath("//node"):
    if node.attrib["id"] not in keep_nodes:
        continue
    tags = node.xpath("./tag")

    node_attrs = dict(node.attrib)
    tags_attrs = get_attrs_from_tags(tags)
    node_attrs["tags"] = json.dumps(tags_attrs)
    nodes_ids.add(node_attrs["id"])
    nodes.append(get_filtered_node_attrs(node_attrs))

df = pd.DataFrame(nodes)
df.to_csv("nodes.csv")

df = pd.DataFrame(ways)
df.to_csv("ways.csv")

# TODO relations

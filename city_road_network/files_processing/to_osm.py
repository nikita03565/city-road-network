import csv
import json

from lxml.etree import Element, fromstring, tostring

root = Element(
    "osm",
    version="0.6",
    generator="CGImap 0.8.3 (23364 spike-07.openstreetmap.org)",
    copyright="OpenStreetMap and contributors",
    attribution="http://www.openstreetmap.org/copyright",
    license="http://opendatacommons.org/licenses/odbl/1-0/",
)
bounds = Element(
    "bounds",
    minlat="59.9221000",
    minlon="30.3399000",
    maxlat="59.9376000",
    maxlon="30.3734000",
)
root.append(bounds)

nodes_ids = set()
with open("nodes.csv", newline="") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        tags = eval(row.pop("tags"))
        node_el = Element("node", **{key: value for key, value in row.items() if key != "" and value != ""})

        for tag_key, tag_value in tags.items():
            node_el.append(Element("tag", k=tag_key, v=tag_value))
        root.append(node_el)
        nodes_ids.add(row["id"])


ways_ids = set()
with open("ways.csv", newline="") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        nds = eval(row.pop("nds"))
        tags = json.loads(row.pop("tags"))
        way_el = Element("way", **{key: value for key, value in row.items() if key not in ["", "nds"] and value != ""})
        for nd in nds:
            way_el.append(Element("nd", ref=nd))

        for tag_key, tag_value in tags.items():
            way_el.append(Element("tag", k=tag_key, v=str(tag_value)))
        root.append(way_el)
        ways_ids.add(row["id"])


with open("map.osm", "rb") as f:
    content = f.read()

tree = fromstring(content)
for rel in tree.xpath("//relation"):
    for member in rel.xpath("./memeber"):
        if member.attrib["type"] == "node" and member.attrib["ref"] not in nodes_ids:
            print("removed")
            member.getparent().remove(member)
        if member.attrib["type"] == "way" and member.attrib["ref"] not in ways_ids:
            print("removed")
            member.getparent().remove(member)
    root.append(rel)

with open("new.osm", "w") as f:
    f.write(tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode())

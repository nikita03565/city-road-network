import csv
import os
from collections import defaultdict
from datetime import datetime

import pandas as pd
from files_processing.unwind_ways import unwind_ways
from lxml import etree
from utils.utils import (
    CACHE_DIR,
    check_node_tags,
    check_way_tags,
    get_attrs_from_tags,
    get_cache_subdir,
    get_csv_head,
    get_filtered_node_attrs,
    get_filtered_relation_attrs,
    get_filtered_way_attrs,
    get_logger,
    get_max_speed,
    is_road1,
)

logger = get_logger(__name__)


# TODO read from files when parsing isn't needed
class OSMParser:
    SELECTED_STREETS = ()  # for debug and exploration purposes

    def __init__(self, f_name="map.osm", do_attrs_filtering=False, save_csv=False, specific_nodes=None):
        self.do_attrs_filtering = do_attrs_filtering
        self.save_csv = save_csv
        self.f_name = f_name
        self.dir_name = get_cache_subdir([f_name])
        self.specific_nodes = specific_nodes
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
        if not os.path.exists(self.dir_name):
            os.makedirs(self.dir_name)

    @staticmethod
    def _fast_iter(context, func, *args, **kwargs):
        """
        http://lxml.de/parsing.html#modifying-the-tree
        Based on Liza Daly's fast_iter
        http://www.ibm.com/developerworks/xml/library/x-hiperfparse/
        See also http://effbot.org/zone/element-iterparse.htm
        """
        prev_el = None
        for event, elem in context:
            func(elem, *args, **kwargs)
            # It's safe to call clear() here because no descendants will be accessed
            if prev_el is not None and len(prev_el):
                prev_el.clear()
                # Also eliminate now-empty references from the root node to elem
                for ancestor in prev_el.xpath("ancestor-or-self::*"):
                    while ancestor.getprevious() is not None:
                        del ancestor.getparent()[0]
            prev_el = elem

        del context

    def _process_relation(self, element, relations):
        if element.tag != "relation":
            return
        tags = element.xpath("./tag")
        relation_attrs = dict(element.attrib)
        tags_attrs = get_attrs_from_tags(tags)
        members = element.xpath("./member")

        relation_attrs["member_nodes"] = []
        relation_attrs["member_ways"] = []
        relation_attrs["member_relations"] = []

        for member_el in members:
            member_type = member_el.attrib["type"]
            relation_attrs[f"member_{member_type}s"].append(member_el.attrib["ref"])
        relation_attrs.update(tags_attrs)
        if self.do_attrs_filtering:
            relation_attrs = get_filtered_relation_attrs(relation_attrs)

        relations.append(relation_attrs)

    def _process_way(self, element, ways):
        if element.tag != "way":
            return
        nds = element.xpath("./nd")
        nds_refs = [int(nd.attrib["ref"]) for nd in nds]
        tags = element.xpath("./tag")
        way_attrs = dict(element.attrib)
        tags_attrs = get_attrs_from_tags(tags)
        if "name" not in tags_attrs:
            tags_attrs["name"] = ""
        # Exploration Part!
        if (
            tags_attrs.get("name")
            and self.SELECTED_STREETS
            and not any(street in tags_attrs.get("name", "") for street in self.SELECTED_STREETS)
        ):
            return
        # End of Exploration Part!
        way_attrs["nds"] = nds_refs

        possible_speed = tags_attrs.get("maxspeed")
        tags_attrs["maxspeed"] = get_max_speed(possible_speed)

        way_attrs.update(tags_attrs)
        if self.do_attrs_filtering:
            way_attrs = get_filtered_way_attrs(way_attrs)

        ways.append(way_attrs)

    def _process_node(self, element, nodes, specific_nodes):
        if element.tag != "node":
            return
        tags = element.xpath("./tag")
        node_attrs = dict(element.attrib)
        node_attrs["id"] = int(node_attrs["id"])

        if specific_nodes and node_attrs["id"] not in specific_nodes:
            return
        tags_attrs = get_attrs_from_tags(tags)

        if "maxspeed" in tags_attrs and tags_attrs["maxspeed"] != "signals":
            possible_speed = tags_attrs["maxspeed"]
            tags_attrs["maxspeed"] = get_max_speed(possible_speed)

        node_attrs.update(tags_attrs)
        if self.do_attrs_filtering:
            node_attrs = get_filtered_node_attrs(node_attrs)

        nodes.append(node_attrs)

        if specific_nodes:
            print(f"Found {len(nodes)} nodes")

    def _process_relations(self):
        logger.info("Processing relations...")
        s = datetime.now()
        relations = []

        context = etree.iterparse(self.f_name, events=["end"])
        self._fast_iter(context, self._process_relation, relations=relations)

        df_relations = pd.DataFrame(relations)
        logger.info("Finished processing relations in %s", datetime.now() - s)
        return df_relations

    def _process_ways(self):
        logger.info("Processing ways...")
        s = datetime.now()
        ways = []

        context = etree.iterparse(self.f_name, events=["end"])
        self._fast_iter(context, self._process_way, ways=ways)
        df_ways = pd.DataFrame(ways)
        logger.info("Finished processing ways in %s", datetime.now() - s)
        return df_ways

    def _save_to_csv(self, items, filename):
        head = get_csv_head(items)
        out_file = os.path.join(get_cache_subdir([self.f_name]), filename)
        with open(out_file, "w", newline="") as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=head,
            )
            writer.writeheader()
            writer.writerows(items)
        logger.info("Wrote data to %s", out_file)

    def _process_nodes(self, specific_nodes=None):
        logger.info("Processing nodes...")
        s = datetime.now()
        nodes = []

        context = etree.iterparse(self.f_name, events=["end"])
        self._fast_iter(context, self._process_node, nodes=nodes, specific_nodes=specific_nodes)

        try:
            df_nodes = pd.DataFrame(nodes)
        except Exception as e:
            logger.error("Failed to create nodes DataFrame. Trying to save data to csv")
            logger.error(e, exc_info=True)
            df_nodes = pd.DataFrame(columns=["id"])
            self._save_to_csv(nodes, "nodes0.csv")
        logger.info("Finished processing nodes in %s", datetime.now() - s)
        return df_nodes

    def _save_df_to_csv(self, df, csv_name):
        full_name = os.path.join(self.dir_name, csv_name)
        df.to_csv(full_name)
        logger.info("Wrote file %s", full_name)

    def parse(self):
        df_relations = self._process_relations()
        if self.save_csv:
            self._save_df_to_csv(df_relations, "relations.csv")
            df_relations = pd.DataFrame()  # release memory
        df_ways = self._process_ways()
        if self.save_csv:
            self._save_df_to_csv(df_ways, "ways.csv")
            df_ways = pd.DataFrame()  # release memory
        if self.specific_nodes:
            df_nodes = self._process_nodes(self.specific_nodes)
        else:
            df_nodes = self._process_nodes()
        if self.save_csv:
            self._save_df_to_csv(df_nodes, "nodes.csv")
            df_nodes = pd.DataFrame()  # release memory
        return df_relations, df_ways, df_nodes

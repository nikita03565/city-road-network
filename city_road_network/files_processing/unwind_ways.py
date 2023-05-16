import os
from copy import deepcopy
from multiprocessing import Pool

import pandas as pd
from utils.utils import get_distance


def get_chunk_indexes(num_objects, max_threads):
    chunk_size = num_objects // max_threads
    chunks = [[chunk_size * i, chunk_size * (i + 1)] for i in range(max_threads)]
    chunks[-1][1] = None
    return chunks


# df_ways = pd.read_csv(os.path.join(CACHE_DIR, f"ways_{x}.csv"), dtype=str)
# df_nodes = pd.read_csv(os.path.join(CACHE_DIR, f"nodes_{x}.csv"), dtype=str)
# df_nodes.set_index("id", inplace=True)
# nodes_ids = set(df_nodes.index.array)
# df_nodes.fillna("", inplace=True)
# df_ways.fillna("", inplace=True)


def process_way(way, new_rows, nodes_ids, df_nodes):
    way_filtered_attrs = dict(way)
    nds = [nd for nd in way_filtered_attrs.pop("nds") if nd in nodes_ids]

    way_filtered_attrs["highway"] = [way_filtered_attrs.get("highway", "")]
    one_way = way_filtered_attrs.get("oneway", "") == "yes"
    way_filtered_attrs["oneway"] = one_way
    way_filtered_attrs["way_id"] = way_filtered_attrs.pop("id")

    for idx, nd in enumerate(nds):
        if idx == 0:
            continue
        way_filtered_attrs = deepcopy(way_filtered_attrs)
        prev_nd = nds[idx - 1]
        u = df_nodes.loc[prev_nd]
        v = df_nodes.loc[nd]
        if u is None or v is None:
            continue
        way_filtered_attrs["len"] = get_distance(u, v)
        way_filtered_attrs[":START_ID"] = prev_nd
        way_filtered_attrs[":END_ID"] = nd
        new_rows.append(way_filtered_attrs)


def perform_map(args):
    df_piece, nodes_ids, df_nodes = args
    new_rows = []
    df_piece.apply(lambda row: process_way(row, new_rows, nodes_ids, df_nodes), axis=1)
    return new_rows


def unwind_ways(df_nodes, df_ways):
    max_threads = os.cpu_count()
    columns = [col for col in df_ways.columns if col not in ["id", "nds"]]
    out_df_columns = ["way_id", ":START_ID", ":END_ID", "len", *columns]
    out_df = pd.DataFrame(columns=out_df_columns)
    chunks = get_chunk_indexes(len(df_ways), max_threads)
    nodes_ids = set(df_nodes.index.array)
    nodes_ids_arg = [nodes_ids for _ in range(max_threads)]
    df_nodes_arg = [df_nodes for _ in range(max_threads)]
    with Pool(max_threads) as pool:
        r = pool.map(perform_map, zip([df_ways[chunk[0] : chunk[1]] for chunk in chunks], nodes_ids_arg, df_nodes_arg))

    for l in r:
        out_df = pd.concat([out_df, pd.DataFrame(l, columns=out_df_columns)])

    return out_df

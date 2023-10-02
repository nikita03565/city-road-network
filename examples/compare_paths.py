import os
import pickle

from city_road_network.utils.utils import get_data_subdir


def compare_paths(lst1, lst2):
    assert len(lst1) == len(lst2)
    for path1 in lst1:
        found_match = False
        for path2 in lst2:
            time_match = abs(path1.travel_time - path2.travel_time) < 1e-4
            if not time_match:
                continue
            nodes_match = len(path1.path) == len(path2.path)
            if not nodes_match:
                continue
            for old_node, new_node in zip(path1.path, path2.path):
                nodes_match = nodes_match and old_node == new_node
            if nodes_match and time_match:
                found_match = True
                break
        assert found_match, path1


if __name__ == "__main__":
    data_dir = get_data_subdir("spb")

    with open(os.path.join(data_dir, "paths_by_flow_time_s_1695987799.pkl"), "rb") as f:
        old_paths = pickle.load(f)

    with open(os.path.join(data_dir, "paths_by_flow_time_s_1696270771.pkl"), "rb") as f:
        new_paths = pickle.load(f)

    for i, row in enumerate(old_paths):
        assert len(old_paths[i]) == len(new_paths[i])
        for j, cell in enumerate(row):
            compare_paths(new_paths[i][j], old_paths[i][j])
            compare_paths(old_paths[i][j], new_paths[i][j])

from city_road_network.downloaders.osm import get_relation_poly
from city_road_network.writers.sumo import prepare_all_files, run_sumo

if __name__ == "__main__":
    city_name = "chelyabinsk"
    chel_rel = "4442556"
    boundaries = get_relation_poly(relation_id=chel_rel)
    # Assuming zones, poi and other data has already been collected and OD-matrix calculated
    prepare_all_files(boundaries, city_name)
    run_sumo(city_name)

from city_road_network.downloaders.ghsl import get_tile_ids
from city_road_network.downloaders.osm import get_relation_poly
from city_road_network.processing.ghsl import get_image_coordinates


def test_tiles():
    kad_poly = get_relation_poly(relation_id="1861646")
    spb_poly = get_relation_poly(relation_id="337422")
    poly = kad_poly.union(spb_poly)
    bbox = poly.bounds
    top, left, bottom, right = get_image_coordinates(bbox)
    tile_ids = get_tile_ids(top, left, bottom, right).keys()
    assert len(tile_ids) == 2
    assert "R3_C20" in tile_ids and "R3_C21" in tile_ids

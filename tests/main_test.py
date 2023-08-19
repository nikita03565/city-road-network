from city_road_network.downloaders.ghsl import get_tile_ids
from city_road_network.downloaders.osm import get_relation_poly
from city_road_network.processing.ghsl import get_image_coordinates
from city_road_network.utils.utils import convert_coordinates, get_distance


def test_tiles():
    kad_poly = get_relation_poly(relation_id="1861646")
    spb_poly = get_relation_poly(relation_id="337422")
    poly = kad_poly.union(spb_poly)
    bbox = poly.bounds
    top, left, bottom, right = get_image_coordinates(bbox)
    tile_ids = get_tile_ids(top, left, bottom, right).keys()
    assert len(tile_ids) == 2
    assert "R3_C20" in tile_ids and "R3_C21" in tile_ids


def almost_equal(x, y, e=1e-8) -> bool:
    return abs(x - y) < e


def test_convert():
    wgs_x, wgs_y = 61.2993700571118, 30.9930425659682
    moll_x, moll_y = 1959000.0, 7000000.0
    x, y = convert_coordinates(wgs_x, wgs_y, to_wgs=False)
    assert almost_equal(x, moll_x) and almost_equal(y, moll_y)

    wgs_x_back, wgs_y_back = convert_coordinates(moll_x, moll_y, to_wgs=True)
    assert almost_equal(wgs_x_back, wgs_x) and almost_equal(wgs_y_back, wgs_y)


def test_distance():
    p1 = {"lat": 60, "lon": 30}
    p2 = {"lat": 60.1, "lon": 30.1}

    d2 = get_distance(p1, p2)
    assert almost_equal(d2, 12.456775938122396)

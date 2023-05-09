import numpy as np

from city_road_network.utils.utils import get_distance


def calc_distance_mat(zones_gdf):
    distance_mat = np.zeros([zones_gdf.shape[0], zones_gdf.shape[0]])
    for i in range(zones_gdf.shape[0]):
        for j in range(zones_gdf.shape[0]):
            centroid_i = zones_gdf.iloc[i].centroid
            centroid_j = zones_gdf.iloc[j].centroid
            distance_mat[i, j] = get_distance(
                {"lat": centroid_i.y, "lon": centroid_i.x}, {"lat": centroid_j.y, "lon": centroid_j.x}
            )
    return distance_mat


def calc_friction_mat(
    d_mat,
    a=28507,
    b=-0.02,
    c=-0.123,
):
    friction_mat = np.ones((d_mat.shape[0], d_mat.shape[1]))
    for i in range(d_mat.shape[0]):
        for j in range(d_mat.shape[1]):
            distance = d_mat[i, j]
            if distance != 0:
                friction_mat[i, j] = a * (distance**b) * (np.exp(c * distance))
            else:
                friction_mat[i, j] = 0
    return friction_mat


def calc_attraction_friction(attractions, f_mat):
    attraction_friction_mat = np.zeros([f_mat.shape[0], f_mat.shape[0]])
    for i in range(f_mat.shape[0]):
        for j in range(f_mat.shape[1]):
            attraction_friction_mat[i, j] = attractions[j] * f_mat[i, j]
    return attraction_friction_mat


def calc_total_attraction_friction(attraction_friction_mat):
    return np.array([attraction_friction_mat[i].sum() for i in range(attraction_friction_mat.shape[0])])


def calc_trip_mat(f_mat, attr_f_mat, p_array, a_array):
    trip_mat = np.ones((f_mat.shape[0], f_mat.shape[0]))
    for i in range(f_mat.shape[0]):
        for j in range(f_mat.shape[0]):
            trip_mat[i][j] = float(p_array[i] * a_array[j] * f_mat[i, j] / max(0.000001, attr_f_mat[i]))
    return trip_mat


def get_prod_error(trip_mat, prod_expected):
    productions = np.array([trip_mat[i].sum() for i in range(trip_mat.shape[0])])
    return np.square(prod_expected - productions).mean()


def get_attr_error(trip_mat, attr_expected):
    attractions = np.array([trip_mat[:, i].sum() for i in range(trip_mat.shape[0])])
    return np.square(attr_expected - attractions).mean()


def correct_results(trip_mat, given_attr, given_prod, f_mat, a_list, max_iter=100, eps=10e-4):
    prod_error = get_prod_error(trip_mat, given_prod)
    attr_error = get_attr_error(trip_mat, given_attr)
    if (prod_error < eps) and (attr_error < eps):
        return trip_mat
    for iteration in range(1, max_iter):
        corrected_attr = np.zeros(trip_mat.shape[0])
        for i in range(trip_mat.shape[0]):
            actual_total_attr = trip_mat[:, i].sum()
            expected_total_attr = given_attr[i]
            corrected_attr[i] = a_list[iteration - 1][i] * expected_total_attr / actual_total_attr
        a_list.append(corrected_attr)
        attr_f_mat = calc_attraction_friction(corrected_attr, f_mat)
        total_attr_f_mat = calc_total_attraction_friction(attr_f_mat)
        trip_mat = calc_trip_mat(f_mat, total_attr_f_mat, given_prod, corrected_attr)

        prod_error = get_prod_error(trip_mat, given_prod)
        attr_error = get_attr_error(trip_mat, given_attr)
        if (prod_error < eps) and (attr_error < eps):
            return trip_mat
    raise Exception("Didn't find satisfying result")


def run_gravity_model(zones_gdf):
    prod_array = np.array(zones_gdf["production"])
    attr_array = np.array(zones_gdf["poi_attraction"])
    attr_correction_list = [attr_array]
    distance_mat = calc_distance_mat(zones_gdf)
    friction_mat = calc_friction_mat(distance_mat)
    attr_f_mat = calc_attraction_friction(attr_array, friction_mat)
    total_attr_f_mat = calc_total_attraction_friction(attr_f_mat)
    trip_mat = calc_trip_mat(friction_mat, total_attr_f_mat, prod_array, attr_array)
    corrected_trip_mat = correct_results(trip_mat, attr_array, prod_array, friction_mat, attr_correction_list)
    return corrected_trip_mat.round()

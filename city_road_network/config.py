default_avg_daily_trips_per_veh = 3.6  # derived from NHTS
default_avg_household_size = 2.1  # Average in Russia https://rosstat.gov.ru/vpn_popul
default_avg_vehs_per_household = 0.62  # from https://rosstat.gov.ru/folder/13397

default_city_name = "default_city"
default_crs = "epsg:4326"


default_access = '["access"!~"private"]'
default_osm_filter = (
    f'["highway"]["area"!~"yes"]{default_access}'
    f'["highway"!~"abandoned|bridleway|bus_guideway|construction|corridor|cycleway|elevator|'
    f"escalator|footway|path|pedestrian|planned|platform|proposed|raceway|service|no|razed|"
    f'steps|track"]'
    f'["motor_vehicle"!~"no"]["motorcar"!~"no"]'
    f'["service"!~"alley|driveway|emergency_access|parking|parking_aisle|private"]'
)
timeout = 180

CACHE_DIR = "cache"
DATA_DIR = "data"
PLOTS_DIR = "plots"
HTML_DIR = "htmls"

ghsl_shape_url = "https://ghsl.jrc.ec.europa.eu/download/GHSL_data_54009_shapefile.zip"
ghsl_tile_url_template = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2022A/GHS_POP_E2020_GLOBE_R2022A_54009_100/V1-0/tiles/GHS_POP_E2020_GLOBE_R2022A_54009_100_V1_0_{tile_id}.zip"

rus_pop_url = "https://rosstat.gov.ru/storage/mediabank/Tom8_tab2_VPN-2020.xlsx"
nhts_url = "https://nhts.ornl.gov/assets/2016/download/csv.zip"

lane_capacity_mapping = {
    1: 1800,  # in one direction
    2: 1800,  # in one direction
    3: 2000,  # in one direction
    4: 2200,  # per lane
    5: 2200,  # per lane
    6: 2300,  # per lane
    "6+": 2300,  # per lane
}


highway_color_mapping = {
    "motorway": "#E91B59",
    "motorway_link": "#E91B59",
    "primary": "#0004FF",
    "primary_link": "#0004FF",
    "secondary": "#4C4EE0",
    "secondary_link": "#4C4EE0",
    "tertiary": "#05B5FC",
    "tertiary_link": "#05B5FC",
    "residential": "#A600FF",
    "unclassified": "#632A00",
    "road": "#632A00",
    "busway": "#632A00",
    "service": "#A600FF",
    "footway": "#A600FF",
    "trunk": "#FF7400",
    "trunk_link": "#FF7400",
    "living_street": "#1BFC2F",
}

known_highways = list(highway_color_mapping.keys())

speed_map = {
    "RU:urban": 60,
    "RU:rural": 90,
    "RU:living_street": 20,
    "RU:motorway": 110,
    "DE:urban": 50,
    "DE:rural": 100,
    "DE:living_street": 7,
    "DE:motorway": 130,  # legally it is unlimited though
    "DE:bicycle_road": 30,
    "FR:urban": 50,
    "FR:rural": 80,
    "FR:zone30": 30,
    "FR:motorway": 130,
    "GB:motorway": 113,
    "GB:national": 113,
    "GB:nsl_dual": 113,
    "GB:nsl_single": 96,
    None: None,
}

default_speed_map = {
    "living_street": speed_map["RU:living_street"],
    "motorway": speed_map["RU:motorway"],
    "rural": speed_map["RU:rural"],
    "urban": speed_map["RU:urban"],
}

whitelist_relation_attrs = {
    "id",
    "uid",
    "member_nodes",
    "member_ways",
    "member_relations",
    "name:ru",
    "name",
    "shop",
    "amenity",
    "landuse",
    "addr:region",
    "type",
    "boundary",
    "level",
}

whitelist_node_attrs = {
    "id",
    "lat",
    "lon",
    "uid",
    "name",
    "highway",
    "amenity",
    "entrance",
    "shop",
    "landuse",
    ":LABEL",  # generated field
}

whitelist_way_attrs = {
    "id",
    "uid",
    "nds",
    "foot",
    "highway",
    "lanes",
    "lit",
    "maxspeed",
    "name",
    "oneway",
    "surface",
    "railway",
    "smoothness",
    "service",
    "living_street",
    "access",
    "landuse",
    "waterway",
    "leisure",
    "barrier",
    "footway",
    "amenity",
    "tunnel",
    "shop",
}


amenity_rates = {
    "bank": (12.13 + 20.45) / 2,  # Avg of Walk-In Bank + Drive-In Bank
    "bar": 11.36,  # Drinking Place
    "business_centre": 1.15,  # General Office Building
    "cafe": 14.13,  # Fast Casual Restaurant
    "car_wash": (5.54 + 14.20 + 13.60) / 3,  # Avg of Self Service Car Wash +
    # Automated Car Wash + Car Wash and Detail Center
    "car_wash": (5.54 + 14.20 + 13.60) / 3,
    "clinic": (3.28 + 5.18) / 2,  # Avg of General Urban and Dense Multi-Use Urban
    "college": 1.17,  # University/College
    "dentist": 3.46,  # Medical-Dental Office Building
    "doctors": (3.28 + 5.18) / 2,  # Avg of General Urban and Dense Multi-Use Urban
    "fast_food": (28.34 + 32.67 + 78.74 + 42.65) / 4,  # Avg of Fast Food Restaurant without Drive-Through Window
    # and Fast Food Restaurant with Drive-Through Window and
    # Fast Food Restaurant with Drive-Through Window and No Indoor Seating
    "fuel": 109.27,  # Gasoline / Service Station
    "gym": (3.45 + 6.29) / 2,  # Avg of Health/Fitness Club + Athletic Club
    "hospital": 0.97,
    "library": 8.16,
    "office": 1.15,
    "offices": 1.15,
    "parking": 0,
    "parking_entrance": 0,
    "parking_space": 0,
    "pharmacy": (8.51 + 10.29) / 2,  # Avg Pharmacy/Drugstore without and without Drive-Through Window
    "place_of_worship": (0.49 + 2.92 + 4.22) / 3,  # Avg of Church Synagogue Mosque
    "post_office": 11.21,  # United States Post Office
    "pub": 11.36,  # Drinking Place
    "restaurant": 14.13,  # Fast Casual Restaurant
    "school": (1.37 + 1.19 + 0.97) / 3,  # Avg of Elementary + Middle School/Junior High School + High School
    "theatre": 2.45,
    "training": (3.45 + 6.29) / 2,  # Avg of Health/Fitness Club + Athletic Club
    "university": 1.17,  # University/College
    "veterinary": 3.53,
    "doityourself": (0.99 + 2.06) / 2,  # Avg of Construction Equipment Rental and
    # Store and Building Materials and Lumber Store
}

shop_rates = {
    "alcohol": (16.37 + 7.31) / 2,  # Avg of Liquor Store + Winery
    "bakery": (28.00 + 19.02) / 2,  # Avg of Bread/Donut/Bagel Shop without and without Drive-Through Window
    "beauty": (4.12 + 1.12) / 2,  # Avg of Apparel Store
    "car": (2.43 + 3.75) / 2,  # Avg of Automobile Sales New and Used
    "car_parts": 4.91,  # Automobile Parts Sales
    "car_repair": 2.26,  # Automobile Parts and Service Center
    "clothes": (4.12 + 1.12) / 2,  # Avg of Apparel Store
    "convenience": 49.11,  # 49.11
    "mall": 3.81,  # Shopping Center
    "supermarket": 9.24,
}
landuse_rates = {
    "commercial": 1.07,  # Office Park
    "retail": 3.81,  # Shopping Center
}


floor_area_multipliers = {
    "mall": 400,  # 400,000 SQ.FT.
}

# Explicit mapping for colors to be same on all maps
zones_color_map = {
    0: "#90a449",
    1: "#2a548c",
    2: "#e6a83c",
    3: "#a1d275",
    4: "#d9dfc4",
    5: "#e9547e",
    6: "#c3c1c5",
    7: "#3a23e0",
    8: "#13b4a3",
    9: "#c48374",
    10: "#b6c967",
    11: "#bb28be",
    12: "#aaf4b0",
    13: "#7e595c",
    14: "#72621e",
    15: "#ec3575",
    16: "#7c168f",
    17: "#72d1bb",
    18: "#c3f4ad",
    19: "#1e1c30",
    20: "#2ddcdb",
    21: "#32654c",
    22: "#dc0cb2",
    23: "#0eb9ac",
    24: "#081ada",
    25: "#893d08",
    26: "#0ac3ad",
    27: "#a2369c",
    28: "#7def1c",
    29: "#b2fddd",
    30: "#08f94c",
    31: "#e89b24",
    32: "#9232d2",
    33: "#868637",
    34: "#28f85e",
    35: "#7d6b4e",
    36: "#258d28",
    37: "#8ffb5b",
    38: "#d60487",
    39: "#30a194",
    40: "#207fa3",
    41: "#0517db",
    42: "#a042a0",
    43: "#882ccf",
    44: "#b116aa",
    45: "#049e15",
    46: "#07e0f8",
    47: "#d084b6",
    48: "#e3b480",
    49: "#3384dd",
    50: "#61f736",
    51: "#e60980",
    52: "#fdbc9a",
    53: "#46229c",
    54: "#2f459f",
    55: "#43f07b",
    56: "#637c49",
    57: "#ad7a57",
    58: "#5f421d",
    59: "#a93489",
    60: "#63036d",
    61: "#b8b74a",
    62: "#61c572",
    63: "#9bf112",
    64: "#d17689",
    65: "#8db10c",
    66: "#2dd56c",
    67: "#9420ee",
    68: "#bf6dc4",
    69: "#2e172c",
    70: "#c03fad",
    71: "#d3df89",
    72: "#6bc173",
    73: "#d95bc8",
    74: "#7eca26",
    75: "#4a30af",
    76: "#088fff",
    77: "#30b81c",
    78: "#408aec",
    79: "#8e662a",
    80: "#25b987",
    81: "#4c208d",
    82: "#53aad9",
    83: "#2c0702",
    84: "#a5c587",
    85: "#10cc9e",
    86: "#664e71",
    87: "#51c2fc",
    88: "#1ed5e7",
    89: "#e02f7e",
    90: "#c9bf04",
    91: "#88cb18",
    92: "#310a0c",
    93: "#b29605",
    94: "#4618a5",
    95: "#46b48a",
    96: "#80f932",
    97: "#49fbe9",
    98: "#404802",
    99: "#14c971",
    100: "#41f91b",
    101: "#f1a741",
    102: "#969e8f",
    103: "#2693ec",
    104: "#db1ab6",
    105: "#034df0",
    106: "#fc0877",
    107: "#6a072d",
    108: "#a75fd8",
    109: "#6cfe0b",
    110: "#e5368d",
    111: "#adf3f1",
    112: "#7e3c56",
    113: "#69b0b3",
    114: "#85db5c",
    115: "#ade430",
    116: "#f2dc9d",
    117: "#fc8c89",
    118: "#c35958",
    119: "#1ec5a9",
    120: "#53d8be",
    121: "#b941ea",
    122: "#8cacea",
    123: "#a310c0",
    124: "#99d2e4",
    125: "#cee6d4",
    126: "#516e71",
    127: "#98cb1a",
    128: "#50986d",
    129: "#29f4af",
    130: "#7af825",
    131: "#b9be6b",
    132: "#7f5d75",
    133: "#0fc73d",
    134: "#154e49",
    135: "#00ce3b",
    136: "#a94ecd",
    137: "#fe572e",
    138: "#7faa62",
    139: "#5e8d5b",
    140: "#33ccfe",
    141: "#f2413c",
    142: "#463367",
    143: "#048211",
    144: "#3e6662",
    145: "#44385b",
    146: "#699cfc",
    147: "#7f8bc6",
    148: "#391f2c",
    149: "#bb962b",
    150: "#0ce57d",
    151: "#ff2bda",
    152: "#9f2235",
    153: "#2c4225",
    154: "#78d132",
    155: "#758734",
    156: "#8f3be5",
    157: "#7796bd",
    158: "#702297",
    159: "#3011b6",
    160: "#f43e6a",
    161: "#5f0bd4",
    162: "#866cd7",
    163: "#06429a",
    164: "#4f3d1e",
    165: "#f4f713",
    166: "#8a402c",
    167: "#b2449b",
    168: "#b2337a",
    169: "#e823a5",
    170: "#fa3aa1",
    171: "#8e44bd",
    172: "#366048",
    173: "#9cf58b",
    174: "#c53eca",
    175: "#3f1509",
    176: "#394d27",
    177: "#4b5221",
    178: "#de5982",
    179: "#a2594d",
    180: "#04c2e7",
    181: "#e7f461",
    182: "#4179e5",
    183: "#0c8ccf",
    184: "#fa73ed",
    185: "#3204c0",
    186: "#a83258",
    187: "#9210c9",
    188: "#5ffe1e",
    189: "#43a22f",
    190: "#da1033",
    191: "#09c70d",
    192: "#7c2bfc",
    193: "#f5d90d",
    194: "#0e83d5",
    195: "#088cee",
    196: "#422a95",
    197: "#2f57f1",
    198: "#51ffa8",
    199: "#af4936",
}

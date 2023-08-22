import pandas as pd
from dotenv import dotenv_values
from geoalchemy2 import Geometry
from shapely import LineString
from shapely.wkt import loads
from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import (
    Mapped,
    declarative_base,
    mapped_column,
    relationship,
    scoped_session,
    sessionmaker,
)

SRID = 4326
Base = declarative_base()


class Node(Base):
    __tablename__ = "node"
    id = Column(Integer, primary_key=True)
    original_id = Column(String)
    name = Column(String)
    geometry = Column(Geometry("POINT", srid=SRID))
    highway = Column(String)
    amenity = Column(String)

    zone_id = mapped_column(ForeignKey("zone.id"), nullable=True)
    zone: Mapped["Zone"] = relationship(foreign_keys=[zone_id])


class Edge(Base):
    __tablename__ = "edge"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    osmid = Column(String)
    maxspeed = Column(String)
    highway = Column(String)
    oneway = Column(Boolean)
    lanes = Column(Integer)

    surface = Column(String)
    smoothness = Column(String)
    length_km = Column(Float, nullable=True)
    capacity_vehh = Column(Float, nullable=True)
    maxspeed_kmh = Column(Float, nullable=True)
    flow_time_h = Column(Float, nullable=True)

    geometry = Column(Geometry("LINESTRING", srid=SRID))

    start_node_id = mapped_column(ForeignKey("node.id"))
    end_node_id = mapped_column(ForeignKey("node.id"))
    start_node: Mapped["Node"] = relationship(foreign_keys=[start_node_id])
    end_node: Mapped["Node"] = relationship(foreign_keys=[end_node_id])


class Poi(Base):
    __tablename__ = "poi"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    geometry = Column(Geometry("POINT", srid=SRID))

    amenity = Column(String)
    shop = Column(String)
    landuse = Column(String)

    zone_id = mapped_column(ForeignKey("zone.id"), nullable=True)
    zone: Mapped["Zone"] = relationship(foreign_keys=[zone_id])


class Population(Base):
    __tablename__ = "population"
    id = Column(Integer, primary_key=True)
    geometry = Column(Geometry("POINT", srid=SRID))
    value = Column(Float)


class Zone(Base):
    __tablename__ = "zone"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    geometry = Column(Geometry("POLYGON", srid=SRID))
    population = Column(Float, nullable=True)


def get_connection_string():
    config = dotenv_values()
    return f"postgresql+psycopg2://{config['pg_user']}:{config['pg_password']}@{config['pg_host']}:{config['pg_port']}/{config['pg_dbname']}"


def get_session():
    engine = create_engine(get_connection_string())
    session = scoped_session(sessionmaker())
    session.configure(bind=engine, autoflush=False, expire_on_commit=False)
    return session


def create_tables(engine=None):
    if engine is None:
        engine = create_engine(get_connection_string())
    Base.metadata.create_all(engine)


def get_batches(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def _get_optional_field(obj, key, default_value):
    value = obj.get(key, default_value)
    if pd.isna(value):
        return default_value
    return value


def _get_zone_mappings(session, zones_df=None):
    if zones_df is not None:
        zones_names = list(zones_df["name"].values)
        query = session.query(Zone.id, Zone.name).filter(Zone.name.in_(zones_names))
        res = query.all()
        db_zones_mapping = {name: id for id, name in res}
        df_zones_mapping = dict(zip(zones_df.index, zones_df["name"]))
    else:
        db_zones_mapping = {}
        df_zones_mapping = {}
    return db_zones_mapping, df_zones_mapping


def create_nodes(nodes_df, zones_df=None, batch_size=1000):
    session = get_session()
    nodes_df["original_id"] = nodes_df["id"]
    nodes = nodes_df.to_dict("records")
    db_zones_mapping, df_zones_mapping = _get_zone_mappings(session, zones_df)
    all_instances = []
    for batch in get_batches(nodes, batch_size):
        node_instances = []
        for node in batch:
            original_zone = _get_optional_field(node, "zone", None)
            zone_name = df_zones_mapping.get(original_zone)

            node_instances.append(
                Node(
                    name=_get_optional_field(node, "name", ""),
                    original_id=node["original_id"],
                    geometry=node["geometry"],
                    highway=_get_optional_field(node, "highway", ""),
                    amenity=_get_optional_field(node, "amenity", ""),
                    zone_id=db_zones_mapping.get(zone_name),
                )
            )
        session.bulk_save_objects(node_instances, return_defaults=True)
        session.commit()
        all_instances += node_instances
    session.close()
    return all_instances


def create_edges(nodes_df, edges_df, created_nodes, batch_size=1000):
    edges = edges_df.to_dict("records")
    session = get_session()
    created_nodes_mapping = {str(n.original_id): n for n in created_nodes}
    for batch in get_batches(edges, batch_size):
        edges_instances = []
        for edge in batch:
            start = loads(nodes_df[nodes_df["id"] == edge["start_node"]].iloc[0]["geometry"])
            end = loads(nodes_df[nodes_df["id"] == edge["end_node"]].iloc[0]["geometry"])
            geometry = LineString([[start.x, start.y], [end.x, end.y]]).wkt
            edges_instances.append(
                Edge(
                    name=edge["name"],
                    highway=edge["highway"],
                    start_node_id=created_nodes_mapping[str(edge["start_node"])].id,
                    end_node_id=created_nodes_mapping[str(edge["end_node"])].id,
                    osmid=edge["osmid"],
                    maxspeed=edge["maxspeed"],
                    oneway=edge["oneway"],
                    lanes=edge["lanes"],
                    geometry=geometry,
                    surface=_get_optional_field(edge, "surface", ""),
                    smoothness=_get_optional_field(edge, "smoothness", ""),
                    length_km=_get_optional_field(edge, "length (km)", None),
                    capacity_vehh=_get_optional_field(edge, "capacity (veh/h)", None),
                    maxspeed_kmh=_get_optional_field(edge, "maxspeed (km/h)", None),
                    flow_time_h=_get_optional_field(edge, "flow_time (h)", None),
                )
            )
        session.bulk_save_objects(edges_instances)
        session.commit()
    session.close()


def create_graph(nodes_df, edges_df, zones_df=None, batch_size=1000):
    created_nodes = create_nodes(nodes_df, zones_df=zones_df, batch_size=batch_size)
    create_edges(nodes_df, edges_df, created_nodes, batch_size)


def create_zones(zones_df):
    zones = zones_df.to_dict("records")
    session = get_session()
    zone_instances = []
    for zone in zones:
        zone_instances.append(
            Zone(
                name=zone["name"],
                geometry=zone["geometry"],
                population=_get_optional_field(zone, "pop", None),
            )
        )
    session.bulk_save_objects(zone_instances)
    session.commit()
    session.close()


def create_poi(poi_df, zones_df=None, batch_size=1000):
    poi = poi_df.to_dict("records")
    session = get_session()
    db_zones_mapping, df_zones_mapping = _get_zone_mappings(session, zones_df)
    for batch in get_batches(poi, batch_size):
        poi_instances = []
        for point in batch:
            original_zone = _get_optional_field(point, "zone", None)
            zone_name = df_zones_mapping.get(original_zone)
            zone_id = (db_zones_mapping.get(zone_name),)
            poi_instances.append(
                Poi(
                    name=point["name"],
                    geometry=point["geometry"],
                    amenity=_get_optional_field(point, "amenity", ""),
                    shop=_get_optional_field(point, "shop", ""),
                    landuse=_get_optional_field(point, "landuse", ""),
                    zone_id=zone_id,
                )
            )
        session.bulk_save_objects(poi_instances)
        session.commit()
    session.close()


def create_population(pop_df, batch_size=1000):
    pop = pop_df.to_dict("records")
    session = get_session()

    for batch in get_batches(pop, batch_size):
        pop_instances = []
        for point in batch:
            pop_instances.append(
                Population(
                    geometry=point["geometry"],
                    value=point["value"],
                )
            )
        session.bulk_save_objects(pop_instances)
        session.commit()
    session.close()

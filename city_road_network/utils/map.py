import os
import time

import geopandas as gpd
import jinja2
import networkx as nx
import pandas as pd
from shapely import MultiPolygon, Polygon, to_geojson

from city_road_network.config import highway_color_mapping, zones_color_map
from city_road_network.utils.io import get_edgelist_from_graph, get_nodelist_from_graph
from city_road_network.utils.utils import get_html_subdir, get_logger
from city_road_network.writers.color_helpers import get_occupancy_color_getter
from city_road_network.writers.geojson import (
    export_edges,
    export_graph,
    export_nodes,
    export_poi,
    export_population,
    export_zones,
)

print("FILE!!!!", __file__, os.path.dirname(__file__))
logger = get_logger(__name__)

template = """
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/html">
  <head>
    <title>MAP</title>
    <script src="https://unpkg.com/maplibre-gl@latest/dist/maplibre-gl.js"></script>
    <link
      href="https://unpkg.com/maplibre-gl@latest/dist/maplibre-gl.css"
      rel="stylesheet"
    />
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pako/2.1.0/pako.min.js"></script>
    <style>
      #map-container {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
      }

      #map {
        width: 100%;
        height: 100%;
      }
      .maplibregl-popup {
        max-width: 400px;
        font: 12px/20px "Helvetica Neue", Arial, Helvetica, sans-serif;
      }
      #menu {
        background: #fff;
        position: absolute;
        z-index: 1;
        top: 10px;
        right: 10px;
        border-radius: 3px;
        width: 120px;
        border: 1px solid rgba(0, 0, 0, 0.4);
        font-family: "Open Sans", sans-serif;
      }

      #menu a {
        font-size: 13px;
        color: #404040;
        display: block;
        margin: 0;
        padding: 0;
        padding: 10px;
        text-decoration: none;
        border-bottom: 1px solid rgba(0, 0, 0, 0.25);
        text-align: center;
      }

      #menu a:last-child {
        border: none;
      }

      #menu a:hover {
        background-color: #f8f8f8;
        color: #404040;
      }

      #menu a.active {
        background-color: #3887be;
        color: #ffffff;
      }

      #menu a.active:hover {
        background: #3074a4;
      }
    </style>
  </head>

  <body>
    <div id="map-container">
      <nav id="menu"></nav>
      <div id="map"></div>
    </div>
    <script>
      function getCoordinates(e) {
        var selectedFeature = e.features[0];
        const geometry = selectedFeature.geometry;
        if (geometry.type === "Point") {
          return geometry.coordinates;
        }
        if (geometry.type === "LineString") {
          const s = geometry.coordinates[0];
          const e = geometry.coordinates[1];
          const mid = [(s[0] + e[0]) / 2, (s[1] + e[1]) / 2];
          return mid;
        }
        return e.lngLat;
      }
      function displayInfo(e) {
        var selectedFeature = e.features[0];

        const popupObj = { ...selectedFeature.properties };
        delete popupObj.geometry;
        delete popupObj.color;
        delete popupObj.lat;
        delete popupObj.lon;
        delete popupObj.centroid;

        let popupStr = "";
        Object.keys(popupObj).forEach((k) => {
          popupStr += k + ": " + popupObj[k] + "\\n<br/>";
        });

        var popup = new maplibregl.Popup()
          .setLngLat(getCoordinates(e))
          .setHTML("<p>" + popupStr + "</p>")
          .addTo(map);
      }

      const style = {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "&copy; OpenStreetMap Contributors",
            maxzoom: 19,
          },
        },
        layers: [
          {
            id: "osm",
            type: "raster",
            source: "osm",
          },
        ],
      };

      var map = new maplibregl.Map({
        container: "map",
        style: style,
        center: [{{center_lon}}, {{center_lat}}],  // 30.3, 59.95
        zoom: 10,
      });
      let presentLayers = [];
      map.on("load", function () {
        map.loadImage(
          "https://cdn3.iconfinder.com/data/icons/faticons/32/arrow-up-01-512.png",
          (error, image) => {
            if (error) throw error;
            map.addImage("arrow", image);
          }
        );

        const nodesData = {{nodes_data}};
        const edgesData = {{edges_data}};
        const zonesData = {{zones_data}};
        const popData = {{pop_data}};
        const poiData = {{poi_data}};
        const boundsData = {{bounds_data}};

        if (boundsData != null) {
          map.addSource("bounds", {
            type: "geojson",
            data: boundsData,
          });
          map.addLayer({
            id: "bounds-layer",
            type: "fill",
            source: "bounds",
            paint: {
              "fill-color": ["get", "display_color"],
              "fill-opacity": 0.5,
            },
          });
          presentLayers.push("bounds-layer");
        }

        if (zonesData != null) {
          map.addSource("zones", {
            type: "geojson",
            data: zonesData,
          });
          map.addLayer({
            id: "zones-layer",
            type: "fill",
            source: "zones",
            paint: {
              "fill-color": ["get", "display_color"],
              "fill-opacity": 0.5,
            },
          });
          presentLayers.push("zones-layer");
        }
        if (poiData != null) {
          map.addSource("poi", {
            type: "geojson",
            data: poiData,
          });
          map.addLayer({
            id: "poi-layer",
            type: "circle",
            source: "poi",
            paint: {
              "circle-radius": 4,
              "circle-color": ["get", "display_color"],
              "circle-opacity": 1,
            },
          });
          presentLayers.push("poi-layer");
        }

        if (popData != null) {
          map.addSource("pop", {
            type: "geojson",
            data: popData,
          });
          map.addLayer({
            id: "pop-layer",
            type: "circle",
            source: "pop",
            paint: {
              "circle-radius": 4,
              "circle-color": ["get", "display_color"],
              "circle-opacity": 1,
            },
          });
          presentLayers.push("pop-layer");
        }

        if (edgesData != null) {
          map.addSource("edges", {
            type: "geojson",
            data: edgesData,
          });
          map.addLayer({
            id: "edges-layer",
            type: "line",
            source: "edges",
            layout: {
              "line-join": "round",
              "line-cap": "round",
            },
            paint: {
              "line-color": ["get", "display_color"],
              "line-width": 3,
            },
          });

          map.addLayer({
            id: "directions-layer",
            type: "symbol",
            source: "edges",
            paint: {},
            layout: {
              "symbol-placement": "line",
              "icon-image": "arrow",
              "icon-rotate": 90,
              "icon-rotation-alignment": "map",
              "icon-allow-overlap": true,
              "icon-ignore-placement": true,
              "icon-size": 0.05,
            },
          });
          presentLayers.push("edges-layer");
          presentLayers.push("directions-layer");
        }
        if (nodesData != null) {
          map.addSource("nodes", {
            type: "geojson",
            data: nodesData,
          });
          map.addLayer({
            id: "nodes-layer",
            type: "circle",
            source: "nodes",
            paint: {
              "circle-radius": 4,
              "circle-color": ["get", "display_color"],
              "circle-opacity": 1,
            },
          });
          presentLayers.push("nodes-layer");
        }

        const layers = presentLayers;
        for (let layer of layers) {
          map.on("click", layer, displayInfo);

          map.on("mouseenter", layer, function () {
            map.getCanvas().style.cursor = "pointer";
          });

          map.on("mouseleave", layer, function () {
            map.getCanvas().style.cursor = "";
          });
        }
      });
      // After the last frame rendered before the map enters an "idle" state.
      map.on("idle", () => {
        // If these two layers were not added to the map, abort
        if (presentLayers.length < 2) {
          return;
        }

        // Enumerate ids of the layers.
        const toggleableLayerIds = presentLayers;

        // Set up the corresponding toggle button for each layer.
        for (const id of toggleableLayerIds) {
          // Skip layers that already have a button set up.
          if (document.getElementById(id)) {
            continue;
          }

          // Create a link.
          const link = document.createElement("a");
          link.id = id;
          link.href = "#";
          link.textContent = id;
          link.className = "active";

          // Show or hide layer when the toggle is clicked.
          link.onclick = function (e) {
            const clickedLayer = this.textContent;
            e.preventDefault();
            e.stopPropagation();

            const visibility = map.getLayoutProperty(
              clickedLayer,
              "visibility"
            );

            // Toggle layer visibility by changing the layout object's visibility property.
            if (visibility === "visible") {
              map.setLayoutProperty(clickedLayer, "visibility", "none");
              this.className = "";
            } else {
              this.className = "active";
              map.setLayoutProperty(clickedLayer, "visibility", "visible");
            }
          };

          const layers = document.getElementById("menu");
          layers.appendChild(link);
        }
      });
    </script>
  </body>
</html>
"""


def get_center(
    nodes_data: dict | None = None,
    edges_data: dict | None = None,
    zones_data: dict | None = None,
    pop_data: dict | None = None,
    poi_data: dict | None = None,
    bounds_data: dict | None = None,
):
    for data in [nodes_data, pop_data, poi_data]:
        if data is not None:
            feature = data["features"][0]
            return feature["geometry"]  # TODO parse??
    if zones_data is not None:
        feature = data["features"][0]
        return feature["geometry"]  # TODO parse?? return first coordinate
    if edges_data is not None:
        feature = edges_data["features"][0]
        return feature["geometry"]  # TODO parse?? return first coordinate
    if bounds_data is not None:
        return bounds_data["coordinates"][0][0][0]  # ...
    raise ValueError("No data to identify map center")


# TODO BIG TODO remove all color bullshit from geojson module??
def generate_map(
    nodes_data: dict | None = None,
    edges_data: dict | None = None,
    zones_data: dict | None = None,
    pop_data: dict | None = None,
    poi_data: dict | None = None,
    bounds_data: dict | None = None,
    save=True,
    filename=None,
    city_name=None,
):
    e = jinja2.Environment()
    t = e.from_string(template)

    center = get_center(nodes_data, edges_data, zones_data, pop_data, poi_data, bounds_data)
    new_html = t.render(
        **{
            "center_lat": center[0],
            "center_lon": center[1],
            "nodes_data": nodes_data if nodes_data is not None else "null",
            "edges_data": edges_data if edges_data is not None else "null",
            "zones_data": zones_data if zones_data is not None else "null",
            "bounds_data": bounds_data if bounds_data is not None else "null",
            "pop_data": pop_data if pop_data is not None else "null",
            "poi_data": poi_data if poi_data is not None else "null",
        }
    )

    if save:
        html_dir = get_html_subdir(city_name=city_name)
        name = filename
        if name is None:
            ts = int(time.time())
            name = f"map_{ts}.html"
        full_name = os.path.join(html_dir, name)
        with open(full_name, "w") as f:
            f.write(new_html)
        print("Saved file %s" % os.path.abspath(full_name))
    return new_html


def _get_graph_legend_html() -> str:
    item_txt = """<br> &nbsp; {item} &nbsp; <i class="fa fa-minus fa-4" style="color:{col}"></i>"""

    item_txt_list = [item_txt.format(item=highway, col=color) for highway, color in highway_color_mapping.items()]
    html_itms = "\n".join(item_txt_list)

    legend_html = """
        <div style="
        position: fixed;
        bottom: 50px; left: 50px;;
        border:2px solid grey; z-index:9999;

        background-color:white;
        opacity: .85;

        font-size:14px;
        font-weight: bold;

        ">
        &nbsp; {title}

        {itm_txt}

        </div> """.format(
        title="Highway Types", itm_txt=html_itms
    )
    return legend_html


def draw_graph(
    graph: nx.DiGraph,
    node_popup_keys: list[str] | None = None,
    way_popup_keys: list[str] | None = None,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
):
    """Draws graph on map"""
    nodes_data, edges_data = export_graph(graph, node_export_keys=node_popup_keys, edge_export_keys=way_popup_keys)
    html = generate_map(nodes_data=nodes_data, edges_data=edges_data, save=save, filename=filename, city_name=city_name)
    return html


def draw_boundaries(
    poly: Polygon | MultiPolygon,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
):
    """Draws boundaries of an area of interest"""
    html = generate_map(bounds_data=to_geojson(poly), save=save, filename=filename, city_name=city_name)
    return html


def draw_zones(
    zones_gdf: gpd.GeoDataFrame,
    popup_keys: list[str] | None = None,
    color_map: dict | None = None,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
):
    """Draws zones on map"""
    zones_data = export_zones(zones_gdf, keys=popup_keys)
    # TODO ADD COLORS HERE?
    # PASS KEYS FROM HERE?

    if color_map is None:
        color_map = zones_color_map
    html = generate_map(zones_data=zones_data, save=save, filename=filename, city_name=city_name)
    return html


def draw_trips_map(
    graph: nx.DiGraph,
    zones_gdf: gpd.GeoDataFrame | None = None,
    gradient: list[float] | None = None,
    by_abs_value: bool = False,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
):
    """Draws graph on map with edges color being gradient from green (low load) to red (high load)."""
    # TODO BIG TODO EXPORT GRAPH WITH COLOR GETTER
    # REMOVE EDGES THAT HAVE NO PASSES COUNTS!!!!
    # DONT FORGET TO INCLUDE ZONES?!??!?!
    color_getter = get_occupancy_color_getter(gradient=gradient, by_abs_value=by_abs_value)
    nodes_df = get_nodelist_from_graph(graph)
    edges_df = get_edgelist_from_graph(graph)

    edges_df = edges_df[edges_df["passes_count"] > 0]

    nodes_data = export_nodes(
        nodes_df=nodes_df,
        keys=None,
        save=False,
    )
    edges_data = export_edges(edges_df=edges_df, keys=None, save=False, color_getter=color_getter)
    kwargs = {"nodes_data": nodes_data, "edges_data": edges_data}
    if zones_gdf:
        zones_data = export_zones(zones_gdf)
        kwargs["zones_data"] = zones_data
    html = generate_map(**kwargs, save=save, filename=filename, city_name=city_name)
    return html


def draw_population(
    pop_df: pd.DataFrame,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
):
    pop_data = export_population(pop_df)
    """Draws population distribution on map"""
    html = generate_map(pop_data=pop_data, save=save, filename=filename, city_name=city_name)
    return html


def draw_poi(
    poi_df: pd.DataFrame,
    save: bool = False,
    filename: str | None = None,
    city_name: str | None = None,
):
    """Draws population distribution on map"""
    poi_data = export_poi(poi_df)
    html = generate_map(poi_data=poi_data, save=save, filename=filename, city_name=city_name)
    return html

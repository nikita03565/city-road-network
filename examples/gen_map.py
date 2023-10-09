import os
import time

import jinja2

from city_road_network.utils.utils import get_geojson_subdir, get_html_subdir

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
    </style>
  </head>

  <body>
    <div id="map-container">
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
        center: [30.3, 59.95],
        zoom: 10,
      });

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
            "circle-color": ["get", "color"],
            "circle-opacity": 1,
          },
        });

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
            "circle-color": ["get", "color"],
            "circle-opacity": 1,
          },
        });

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
            "circle-color": ["get", "color"],
            "circle-opacity": 1,
          },
        });

        map.addSource("zones", {
          type: "geojson",
          data: zonesData,
        });
        map.addLayer({
          id: "zones-layer",
          type: "fill",
          source: "zones",
          paint: {
            "fill-color": ["get", "color"],
            "fill-opacity": 0.5,
          },
        });

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
            "line-color": ["get", "color"],
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

        const layers = [
          "nodes-layer",
          "edges-layer",
          "directions-layer",
          "zones-layer",
          "poi-layer",
          "pop-layer",
        ];
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
    </script>
  </body>
</html>
"""


def generate_map(
    nodes_data: str | None = None,
    edges_data: str | None = None,
    zones_data: str | None = None,
    pop_data: str | None = None,
    poi_data: str | None = None,
    save=True,
    filename=None,
    city_name=None,
):
    e = jinja2.Environment()
    t = e.from_string(template)

    new_html = t.render(
        **{
            "nodes_data": nodes_data if nodes_data is not None else "null",
            "edges_data": edges_data if edges_data is not None else "null",
            "zones_data": zones_data if zones_data is not None else "null",
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


if __name__ == "__main__":
    json_dir = get_geojson_subdir("spb")

    with open(os.path.join(json_dir, "nodes_1696864879.json")) as f:
        nodes = f.read()
    with open(os.path.join(json_dir, "edges_1696864879.json")) as f:
        edges = f.read()
    with open(os.path.join(json_dir, "zones_1696864879.json")) as f:
        zones = f.read()
    with open(os.path.join(json_dir, "pop_1696864879.json")) as f:
        pop = f.read()
    with open(os.path.join(json_dir, "poi_1696864879.json")) as f:
        poi = f.read()

    generate_map(nodes_data=nodes, save=True, city_name="spb")
    time.sleep(1)
    generate_map(nodes_data=nodes, edges_data=edges, save=True, city_name="spb")
    time.sleep(1)
    generate_map(nodes_data=nodes, zones_data=zones, save=True, city_name="spb")
    time.sleep(1)
    generate_map(pop_data=pop, save=True, city_name="spb")
    time.sleep(1)
    generate_map(
        nodes_data=nodes,
        edges_data=edges,
        zones_data=zones,
        pop_data=pop,
        poi_data=poi,
        save=True,
        city_name="spb",
    )

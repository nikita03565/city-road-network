import jinja2

template = """
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/html">
  <head>
    <title>Map of negative factors in Berlin that affect housing comfort</title>
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
    </style>
  </head>

  <body>
    <div id="map-container">
      <!-- <pre id="info"></pre> -->
      <div id="map"></div>
    </div>
    <script>
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
        const nodes_data = {{nodes_data}};
        const edges_data = {{edges_data}};

        map.addSource("nodes", {
          type: "geojson",
          data: nodes_data,
        });

        map.addSource("edges", {
          type: "geojson",
          data: edges_data,
        });

        map.addLayer({
          id: "nodes-layer",
          type: "circle",
          source: "nodes",
          paint: {
            "circle-radius": 4,
            "circle-color": "blue",
            "circle-opacity": 1,
          },
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
            "line-color": "#888",
            "line-width": 8,
          },
        });

        map.addLayer({
          id: "directions",
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
        // map.on("click", "geojson-layer", function (e) {
        //   var selectedFeature = e.features[0];
        //   displayInfo(selectedFeature);
        // });

        // map.on("mouseenter", "geojson-layer", function () {
        //   map.getCanvas().style.cursor = "pointer";
        // });

        // map.on("mouseleave", "geojson-layer", function () {
        //   map.getCanvas().style.cursor = "";
        // });
        // map.on("mousemove", (e) => {
        //   document.getElementById("info").innerHTML =
        //     // e.point is the x, y coordinates of the mousemove event relative
        //     // to the top-left corner of the map
        //     `${JSON.stringify(e.point)}<br />${
        //       // e.lngLat is the longitude, latitude geographical position of the event
        //       JSON.stringify(e.lngLat.wrap())
        //     }`;
        // });
      });
    </script>
  </body>
</html>
"""

if __name__ == "__main__":
    with open("index.html") as f:
        html_template = f.read()
    with open("geojson_nodes.json") as f:
        nodes = f.read()
    with open("geojson_edges.json") as f:
        edges = f.read()
    e = jinja2.Environment()
    t = e.from_string(html_template)
    new_html = t.render(**{"nodes_json_data": nodes, "edges_json_data": edges})
    with open("index_filled.html", "w") as f:
        f.write(new_html)

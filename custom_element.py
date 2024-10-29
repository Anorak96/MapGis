import folium
import geopandas as gpd
import rasterio
from folium import Map, TileLayer, LayerControl, FeatureGroup
from folium.raster_layers import ImageOverlay
from jinja2 import Template
import json
import os


class CustomTileLayer(TileLayer):
    """Custom Tile Layer to add TileLayers with unique configurations."""

    def __init__(self, tiles='OpenStreetMap', min_zoom=1, max_zoom=18, name=None):
        super(CustomTileLayer, self).__init__(
            tiles=tiles, min_zoom=min_zoom, max_zoom=max_zoom, name=name
        )


class TIFFLayer:
    """Class for handling TIFF layers."""

    def __init__(self, file_path):
        self.file_path = file_path

    def add_to_map(self, folium_map):
        with rasterio.open(self.file_path) as src:
            bounds = [[src.bounds.bottom, src.bounds.left], [src.bounds.top, src.bounds.right]]
            image_overlay = ImageOverlay(
                image=src.read(1),
                bounds=bounds,
                opacity=0.6,
                name=os.path.basename(self.file_path),
                interactive=True,
                cross_origin=True,
                overlay=True
            )
            image_overlay.add_to(folium_map)
            return image_overlay


class ShapefileLayer:
    """Class for handling Shapefile layers."""

    def __init__(self, file_path):
        self.file_path = file_path

    def add_to_map(self, folium_map):
        geodata = gpd.read_file(self.file_path)
        shapefile_layer = folium.GeoJson(
            geodata,
            name=os.path.basename(self.file_path),
            style_function=lambda feature: {
                'fillColor': 'blue',
                'color': 'black',
                'weight': 2,
                'fillOpacity': 0.5
            }
        )
        shapefile_layer.add_to(folium_map)
        return shapefile_layer


class GeoJSONLayer:
    """Class for handling GeoJSON layers."""

    def __init__(self, file_path):
        self.file_path = file_path

    def add_to_map(self, folium_map):
        with open(self.file_path) as f:
            geojson_data = json.load(f)
        geojson_layer = folium.GeoJson(
            geojson_data,
            name=os.path.basename(self.file_path),
            style_function=lambda feature: {
                'fillColor': 'green',
                'color': 'black',
                'weight': 2,
                'fillOpacity': 0.6
            }
        )
        geojson_layer.add_to(folium_map)
        return geojson_layer


# Usage example
m = Map(location=[0, 0], zoom_start=3)

# Adding a custom tile layer
tile_layer = CustomTileLayer(tiles='OpenStreetMap', name='Custom Tile Layer')
tile_layer.add_to(m)

# Adding TIFF, Shapefile, and GeoJSON layers
tiff_layer = TIFFLayer('data/PERSIANN_1y2009.tif')
tiff_layer.add_to_map(m)

shapefile_layer = ShapefileLayer('data/Oyo.shp')
shapefile_layer.add_to_map(m)

geojson_layer = GeoJSONLayer('data/Oyo.geojson')
geojson_layer.add_to_map(m)

# Add Layer Control
LayerControl(collapsed=False).add_to(m)

# Save the map
m.save("custom_layers_map.html")

import sys
from pathlib import Path
import folium.raster_layers
from folium.plugins import GroupedLayerControl
import pandas as pd
import json
import io
import geopandas as gpd
from http.server import SimpleHTTPRequestHandler, HTTPServer
import threading
import rasterio
from rasterio.transform import from_origin
import folium
from folium.plugins import Draw, MousePosition
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget, QFileDialog, QLabel, QHBoxLayout, QCheckBox, QListWidget, QTableWidget, QTableWidgetItem, QToolBar, QDialog, QDialogButtonBox, QTabWidget, QPushButton, QMessageBox, QTextEdit, QInputDialog, QComboBox
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import QUrl, QSize, Qt
from folium.raster_layers import ImageOverlay
import os
os.environ["QT_OPENGL"] = "software"
os.environ["QTWEBENGINE_DISABLE_GPU"] = "0"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"

class TIFFLayer:
    """Class for handling TIFF layers."""

    def __init__(self, file_name):
        self.file_path = file_name
        self.options = {"name": file_name}

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

    def __init__(self, file_name):
        self.file_path = file_name
        self.options = {"name": file_name}

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

    def __init__(self, file_name):
        self.file_path = file_name
        self.options = {"name": file_name}

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
    
class BasemapDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Basemap")
        self.setFixedSize(200, 100)

        # Create a layout for the dialog
        layout = QVBoxLayout()

        # Create and add a label
        label = QLabel("Select a basemap from the list:")
        layout.addWidget(label)

        # Create a QComboBox (dropdown) for basemap selection
        self.basemap_combo = QComboBox()
        # Add folium basemaps
        basemaps = [
            'OpenStreetMap', 'Stadia StamenToner', 'Stadia StamenWaterColor', 'CartoDB positron', 'CartoDB dark_matter'
        ]
        self.basemap_combo.addItems(basemaps)
        layout.addWidget(self.basemap_combo)

        # Add an OK button
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)  # Close dialog on clicking OK
        layout.addWidget(ok_button)

        self.setLayout(layout)

    def get_selected_basemap(self):
        return self.basemap_combo.currentText()

class GISApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MapGIS")
        self.setFixedSize(1500, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.path = None
        self.filters = 'Shp Files (*.shp)'
        self.m = folium.Map(tiles=None, control_scale=True)

        self.main_layout = QHBoxLayout(self.central_widget)

        self.layer_list_widget = QListWidget()
        self.layer_list = QVBoxLayout(self.layer_list_widget)
        self.layer_list_widget.setFixedWidth(160)  # Set fixed width in pixels
        self.main_layout.addWidget(self.layer_list_widget)

        self.layer_list_label = QLabel("Layers")
        self.layer_list.addWidget(self.layer_list_label)
        self.layer_list.addStretch()

        self.layer_checboxes = {}
        self.layers = []

        self.create_layer()


        # Create a QWebEngineView to display the Folium map
        self.web_view_widget = QWidget()
        self.web_view = QWebEngineView(self.web_view_widget)
        self.main_layout.addWidget(self.web_view)

        self.right_list_widget = QWidget()
        self.right_list = QVBoxLayout(self.right_list_widget)
        self.right_list_widget.setFixedWidth(160)
        self.main_layout.addWidget(self.right_list_widget)

        self.table_widget = QTableWidget(self)
        self.table_widget.setColumnCount(1)
        self.table_widget.setRowCount(10)
        self.right_list.addWidget(self.table_widget)
        
        self.main_layout.setStretch(0, 1)  # Stretch factor for the layer_list layout
        self.main_layout.setStretch(1, 14)
        self.main_layout.setStretch(2, 1)

        self.geodata = None  # Placeholder for GeoDataFrame

        self.create_menu_bar()
        self.create_tool_bar()
        self.status_bar = self.statusBar()

    def create_menu_bar(self):
        # Create a menu bar
        menubar = self.menuBar()

        # Create a 'File' menu
        file_menu = menubar.addMenu('File')
        edit_menu = menubar.addMenu('Edit')
        view_menu = menubar.addMenu('View')
        help_menu = menubar.addMenu('Help')
        geop_menu = menubar.addMenu('GeoProcessing')
        insert_menu = menubar.addMenu('Insert')

        # Create file actions using QAction
        new_action = QAction(QIcon("icons/new-text.png"), 'New File', self)
        new_action.setShortcut('Ctrl+N') 
        file_menu.addAction(new_action)

        file_menu.addSeparator()

        load_action = QAction('Load Data', self)
        load_action.setShortcut('Ctrl+L')  # Optional: Set shortcut
        load_action.triggered.connect(self.load_data)  # Connect action to function
        file_menu.addAction(load_action)
        
        save_action = QAction('Save', self)
        save_action.setShortcut('Ctrl+S') 
        save_action.triggered.connect(self.save_data)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()

        quit_action = QAction('Quit', self)
        quit_action.setShortcut('Alt+F4')  # Optional: Set shortcut
        quit_action.triggered.connect(self.close)  # Connect action to quit the app
        file_menu.addAction(quit_action)

        # Create view actions using QAction
        table_action = QAction('Attribute Table', self)
        table_action.triggered.connect(self.attribute_table)  # Connect action to function
        view_menu.addAction(table_action)

        # Create edit actions using QAction
        undo_action = QAction(QIcon('icons/undo.png'), '&Undo', self)
        undo_action.setStatusTip('Undo')
        undo_action.setShortcut('Ctrl+Z')
        edit_menu.addAction(undo_action)

        redo_action = QAction(QIcon('icons/redo.png'), '&Redo', self)
        redo_action.setStatusTip('Redo')
        redo_action.setShortcut('Ctrl+Y')
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        copy_action = QAction('Copy', self)
        edit_menu.addAction(copy_action)
        cut_action = QAction('Cut', self)
        edit_menu.addAction(cut_action)
        paste_action = QAction('Paste', self)
        edit_menu.addAction(paste_action)
        edit_menu.addSeparator()
        
        findMenu = edit_menu.addMenu("Add Basemap")
        findMenu.addAction("Find...")
        findMenu.addAction("Replace...")
        
        # Create Geop actions using QAction
        buffer = QAction(QIcon('icons/buffer.png'), 'Buffer', self)
        buffer.triggered.connect(self.buffer_data)
        geop_menu.addAction(buffer)

        clip = QAction('Clip', self)
        geop_menu.addAction(clip)

        union = QAction('Union', self)
        union.triggered.connect(self.union_data)
        geop_menu.addAction(union)
        
        # Create insert actions using QAction
        basemap_action = QAction('Add Basemap', self)
        insert_menu.addAction(basemap_action)

    def create_tool_bar(self):
        toolbar = QToolBar("My main toolbar")
        self.addToolBar(toolbar)
        toolbar.setIconSize(QSize(15, 15))

        new_button = QAction(QIcon("icons/new.png"), "New File", self)
        # button_action.triggered.connect(self.onMyToolBarButtonClick)
        toolbar.addAction(new_button)

        paste_button = QAction(QIcon("icons/paste.png"), "Paste", self)
        # button_action.triggered.connect(self.onMyToolBarButtonClick)
        toolbar.addAction(paste_button)

        copy_button = QAction(QIcon("icons/copy.png"), "Copy", self)
        # button_action.triggered.connect(self.onMyToolBarButtonClick)
        toolbar.addAction(copy_button)

        cut_button = QAction(QIcon("icons/cut.png"), "Cut", self)
        # button_action.triggered.connect(self.onMyToolBarButtonClick)
        toolbar.addAction(cut_button)

        draw_button = QAction(QIcon("icons/polygon.png"), "Draw", self)
        draw_button.triggered.connect(self.draw_polygon)
        toolbar.addAction(draw_button)

        basemap_button = QAction(QIcon("icons/basemap.png"), "BaseMap", self)
        basemap_button.triggered.connect(self.open_basemap_dialog)
        toolbar.addAction(basemap_button)
        
    def save_data(self):
        text_edit = QTextEdit()

        if (self.path):
            return self.path.write_text(text_edit.toPlainText())
        
        filename, _ = QFileDialog.getSaveFileName(self, 'Save File', filter=self.filters)

        if not filename:
            return
        
        self.path = Path(filename)
        self.path.write_text(text_edit.toPlainText())

    def buffer_data(self):
        try:
            distance, ok = QInputDialog.getDouble(self, 'Buffer', 'Enter buffer distance:', min=0)
            if ok and self.geodata is not None:
                buffered = self.geodata.buffer(distance)
                self.geodata.geometry = buffered
                self.display_map()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Buffer operation failed: {e}")

    def union_data(self):
        try:
            if self.geodata is not None:
                unioned = self.geodata.unary_union
                unioned_geodata = gpd.GeoDataFrame(geometry=[unioned])
                self.geodata = unioned_geodata
                self.display_map()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Union operation failed: {e}")
    
    def open_basemap_dialog(self):
        """Open a dialog to select and load a basemap."""
        dialog = BasemapDialog(self)
        if dialog.exec():
            selected_basemap = dialog.get_selected_basemap()

            # Call method to add the selected basemap
            self.add_basemap(selected_basemap)

    def add_basemap(self, basemap_name):
        """Add the selected basemap to the map."""
        # Ensure the map object is initialized
        if self.m is None:
            self.m = folium.Map(location=[0, 0], zoom_start=2, control_scale=True)

        # Dictionary of Folium basemaps and their corresponding TileLayers
        basemap_dict = {
            'OpenStreetMap': 'openstreetmap',
            'Stadia StamenToner': 'stadiastamentoner',
            'Stadia StamenWaterColor': 'stadiastamenwatercolor',
            'CartoDB positron': 'cartodbpositron',
            'CartoDB dark_matter': 'cartodbdark_matter',
        }

        if basemap_name in basemap_dict:
            tile_layer_name = basemap_dict[basemap_name]

            # Add the selected TileLayer to the map with attribution
            basemap_layer = folium.raster_layers.TileLayer(tile_layer_name)
            basemap_layer.add_to(self.m)

            self.add_layer_checkbox(basemap_layer, basemap_name)
            self.layers.append(basemap_layer)
            
            data = io.BytesIO()
            self.m.save(data, close_file=False)
            self.web_view.setHtml(data.getvalue().decode())
        else:
            QMessageBox.critical(self, "Error", f"Basemap {basemap_name} is not recognized.")

    def load_data(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load GeoData",
            "",
            "DataSets, Layers (*.tif *.tiff *.shp *.geojson)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if file_path:
            self.create_layer(file_path)

    def create_layer(self):
        tiff_layer = TIFFLayer('data/PERSIANN_1y2009.tif')
        tiff_layer.add_to_map(self.m)
        self.add_layer_checkbox(layer=tiff_layer, file_name='data/PERSIANN_1y2009.tif')
        self.layers.append(tiff_layer)

        shapefile_layer = ShapefileLayer('data/Oyo.shp')
        shapefile_layer.add_to_map(self.m)
        self.add_layer_checkbox(layer=shapefile_layer, file_name='data/Oyo.shp')
        self.layers.append(shapefile_layer)

        geojson_layer = GeoJSONLayer('data/Oyo.geojson')
        geojson_layer.add_to_map(self.m)
        self.add_layer_checkbox(layer=geojson_layer, file_name='data/Oyo.geojson')
        self.layers.append(geojson_layer)

        # Add Layer Control
        folium.LayerControl(collapsed=False).add_to(self.m)

        # Save the map
        self.m.save("custom_layers_map.html")
        self.web_view.setUrl(QUrl("http://localhost:8000/custom_layers_map.html"))

    def add_layer_checkbox(self, layer, file_name):
        layer_name = layer.options.get("name", file_name)
        checkbox = QCheckBox(layer_name)
        checkbox.setCheckState(Qt.CheckState.Checked)
        self.layer_list.addWidget(checkbox)
        self.layer_checboxes[layer_name] = {"checkbox": checkbox, "layer": layer}
        checkbox.stateChanged.connect(lambda state: self.toggle_layer(state, layer))

    def toggle_layer(self, state, layer):
        # Check the state without changing it
        print(state)

    def attribute_table(self, file_path):
        if file_path:
            try:
                # data = gpd.read_file(fifile_pathle)
                # data.head()
                pass
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Falied to load csv file")

    def draw_polygon(self):
        Draw(export=True).add_to(self.m)
        self.m.save("map.html")

        # Load the HTML file in the QWebEngineView
        self.web_view.setUrl(QUrl("http://localhost:8000/map.html"))


def run_local_server():
    htttd = HTTPServer(('localhost', 8000), SimpleHTTPRequestHandler)
    htttd.serve_forever()

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_local_server)
    server_thread.daemon = True
    server_thread.start()

    app = QApplication(sys.argv)
    window = GISApp()
    window.show()
    sys.exit(app.exec())

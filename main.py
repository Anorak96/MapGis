import sys
from pathlib import Path
import folium.raster_layers
import pandas as pd
from shapely.geometry import Point
import numpy as np
import json
import io
import geopandas as gpd
import rasterio
import folium
from folium.plugins import Draw, MousePosition
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget, QFileDialog, QLabel, QHBoxLayout, QCheckBox, QListWidget, QTableWidget, QToolBar, QDialog, QTabWidget, QPushButton, QMessageBox, QTextEdit, QInputDialog, QComboBox, QProgressBar, QTreeWidget, QTreeWidgetItem
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import QSize, Qt, QUrl
from folium.raster_layers import ImageOverlay
import os
import time
os.environ["QT_OPENGL"] = "software"
os.environ["QT_QUICK_BACKEND"] = "software"
# os.environ["QTWEBENGINE_DISABLE_GPU"] = "0"
# os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"

class TIFFLayer:
    def __init__(self, file_name):
        self.file_path = file_name
        self.layer = None

    def add_to_map(self, folium_map):
        with rasterio.open(self.file_path) as src:
            bounds = [[src.bounds.bottom, src.bounds.left], [src.bounds.top, src.bounds.right]]
            self.layer = ImageOverlay(
                image=src.read(1),
                bounds=bounds,
                opacity=0.6,
                name=os.path.basename(self.file_path),
                interactive=True,
                cross_origin=True,
                overlay=True
            )
            self.layer.add_to(folium_map)
            return self.layer
        
    def remove_from_map(self, folium_map):
        if self.layer:
            # Remove the layer using JavaScript if needed
            folium_map._children.pop(self.layer._name)
            self.layer = None  # Clear reference after removing

class ShapefileLayer:
    def __init__(self, file_name):
        self.file_path = file_name
        self.layer = None

    def add_to_map(self, folium_map):
        geodata = gpd.read_file(self.file_path)
        self.layer = folium.GeoJson(
            geodata,
            name=os.path.basename(self.file_path),
            style_function=lambda feature: {
                'fillColor': 'blue',
                'color': 'black',
                'weight': 2,
                'fillOpacity': 0.5
            }
        )
        self.layer.add_to(folium_map)
        return self.layer
    
    def remove_from_map(self, folium_map):
        if self.layer:
            folium_map._children.pop(self.layer._name)
            self.layer = None

class GeoJSONLayer:
    def __init__(self, file_name):
        self.file_path = file_name
        self.layer = None

    def add_to_map(self, folium_map):
        with open(self.file_path) as f:
            geojson_data = json.load(f)
        self.layer = folium.GeoJson(
            geojson_data,
            name=os.path.basename(self.file_path),
            style_function=lambda feature: {
                'fillColor': 'green',
                'color': 'black',
                'weight': 2,
                'fillOpacity': 0.6
            }
        )
        self.layer.add_to(folium_map)
        return self.layer

    def remove_from_map(self, folium_map):
        if self.layer:
            folium_map._children.pop(self.layer._name)
            self.layer = None

class CircleMarker:
    def __init__(self, file_name):
        self.file_path = file_name
        self.layer = []
    
    def add_to_map(self, folium_map):
        geodata = gpd.read_file(self.file_path)
        for idx, row in geodata.iterrows():
            print(f"Adding marker at: ({row.geometry.y}, {row.geometry.x})")
            circle_marker  = folium.CircleMarker(
                location=(row.geometry.y, row.geometry.x),
                radius=2,  # You can adjust the size
                color='black',
                fill=True,
                fill_opacity=0.5,
                popup=str(row['value'])  # Optionally add a popup with the value
            )
            circle_marker.add_to(folium_map)
            self.layer.append(circle_marker)

class BasemapDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Basemap")
        self.setFixedSize(200, 100)
        layout = QVBoxLayout()
        label = QLabel("Select a basemap from the list:")
        layout.addWidget(label)
        
        self.basemap_combo = QComboBox()

        basemaps = [
            'OpenStreetMap', 'Stadia StamenToner', 'Stadia StamenWaterColor', 'CartoDB positron', 'CartoDB dark_matter'
        ]
        self.basemap_combo.addItems(basemaps)
        layout.addWidget(self.basemap_combo)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)

        self.setLayout(layout)

    def get_selected_basemap(self):
        return self.basemap_combo.currentText()

def raster_to_point(raster_file, output_file):
    with rasterio.open(raster_file) as src:
        # Read the data from the first band
        band = src.read(1)

        # Get the affine transformation
        transform = src.transform

        default_crs="EPSG:4326"
        crs = src.crs if src.crs is not None else "EPSG:4326"
        # Get the row and column indices of the non-null pixels
        rows, cols = np.where(band != src.nodata)

        # Create a list to hold point geometries
        points = []
        values = []

        for r, c in zip(rows, cols):
            # Get the value of the pixel
            value = band[r, c]
            values.append(value)

            # Calculate the x, y coordinates
            x, y = transform * (c, r)
            points.append(Point(x, y))

        # Create a GeoDataFrame
        gdf = gpd.GeoDataFrame({'value': values, 'geometry': points}, crs=crs)

        # Save to a shapefile
        gdf.to_file(output_file, driver='ESRI Shapefile')
            
class GISApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MapGIS")
        self.setWindowIcon(QIcon("icons/mapgis.ico"))
        self.setGeometry(100, 100, 1000, 900)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.setStyleSheet("""
            QProgressBar {
                height: 7px;
            }
            QWebEngineView {
                border-color: "black";
            }
        """)

        self.path = None
        self.filters = 'Shp Files (*.shp)'
        self.m = folium.Map(tiles=None, control_scale=True)
        MousePosition().add_to(self.m)

        self.main_layout = QHBoxLayout(self.central_widget)

        self.layer_list_widget = QListWidget()
        self.layer_list = QVBoxLayout(self.layer_list_widget)
        self.layer_list_widget.setFixedWidth(160)
        self.main_layout.addWidget(self.layer_list_widget)
        
        
        self.layer_list_label = QLabel("Layers")
        self.layer_list.addWidget(self.layer_list_label)
        self.layer_list.addStretch()

        self.layer_checboxes = {}
        self.layers = []

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
        
        self.main_layout.setStretch(0, 1)
        self.main_layout.setStretch(1, 14)
        self.main_layout.setStretch(2, 1)

        self.geodata = None

        self.create_menu_bar()
        self.toolbar1()
        self.toolbar2()
        
        self.statusBar().showMessage('Ready', 10000)

    def create_menu_bar(self):
        menubar = self.menuBar()
        # Create a menu
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
        load_action.setShortcut('Ctrl+L')
        load_action.triggered.connect(self.load_data)
        file_menu.addAction(load_action)
        
        save_action = QAction('Save', self)
        save_action.setShortcut('Ctrl+S') 
        save_action.triggered.connect(self.save_data)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()

        quit_action = QAction('Quit', self)
        quit_action.setShortcut('Alt+F4')
        quit_action.triggered.connect(self.close) 
        file_menu.addAction(quit_action)

        # Create view actions using QAction
        table_action = QAction('Attribute Table', self)
        table_action.triggered.connect(self.attribute_table)
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
        copy_action.setShortcut('Ctrl+C')
        
        cut_action = QAction('Cut', self)
        edit_menu.addAction(cut_action)
        cut_action.setShortcut('Ctrl+X')
        
        paste_action = QAction('Paste', self)
        edit_menu.addAction(paste_action)
        paste_action.setShortcut('Ctrl+Y')
        
        edit_menu.addSeparator()
        
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
        basemap_action.triggered.connect(self.open_basemap_dialog)
        insert_menu.addAction(basemap_action)

    def toolbar1(self):
        toolbar = QToolBar("My main toolbar")
        self.addToolBar(toolbar)
        toolbar.setIconSize(QSize(15, 15))

        new_button = QAction(QIcon("icons/new.png"), "New File", self)
        toolbar.addAction(new_button)

        paste_button = QAction(QIcon("icons/paste.png"), "Paste", self)
        toolbar.addAction(paste_button)

        copy_button = QAction(QIcon("icons/copy.png"), "Copy", self)
        toolbar.addAction(copy_button)

        cut_button = QAction(QIcon("icons/cut.png"), "Cut", self)
        toolbar.addAction(cut_button)

        draw_button = QAction(QIcon("icons/polygon.png"), "Draw", self)
        draw_button.triggered.connect(self.draw_polygon)
        toolbar.addAction(draw_button)

        basemap_button = QAction(QIcon("icons/basemap.png"), "BaseMap", self)
        basemap_button.triggered.connect(self.open_basemap_dialog)
        toolbar.addAction(basemap_button)
    
    def toolbar2(self):
        toolbar = QToolBar("My main toolbar")
        self.addToolBar(toolbar)
        toolbar.setIconSize(QSize(15, 15))

        toolbox_button = QAction(QIcon("icons/toolbox.png"), "ToolBox", self)
        toolbox_button.triggered.connect(self.toolbox_dialog)
        toolbar.addAction(toolbox_button)

    def toolbox_dialog(self):
        dialog = ToolDialog()
        dialog.exec()

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
        dialog = BasemapDialog(self)
        if dialog.exec():
            selected_basemap = dialog.get_selected_basemap()
            self.add_basemap(selected_basemap)

    def add_basemap(self, basemap_name):
        basemap_dict = {
            'OpenStreetMap': 'openstreetmap',
            'Stadia StamenToner': 'stadiastamentoner',
            'Stadia StamenWaterColor': 'stadiastamenwatercolor',
            'CartoDB positron': 'cartodbpositron',
            'CartoDB dark_matter': 'cartodbdark_matter',
        }

        if basemap_name in basemap_dict:
            tile_layer_name = basemap_dict[basemap_name]
            basemap_layer = folium.TileLayer(tiles=tile_layer_name, name=basemap_name)
            basemap_layer.add_to(self.m)

            self.add_layer_checkbox(basemap_layer, basemap_name)
            self.layers.append(basemap_layer)
            
            data = io.BytesIO()
            self.m.save(data, close_file=False)
            self.web_view.setHtml(data.getvalue().decode())
        else:
            QMessageBox.critical(self, "Error", f"Basemap {basemap_name} is not recognized.")

    def load_data(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load GeoData", "", "DataSets, Layers (*.tif *.tiff *.shp *.geojson)",
            options=QFileDialog.Option.DontUseNativeDialog
        )

        if file_path:
            self.create_layer(file_path)

    def create_layer(self, file_path):
        file_name = os.path.basename(file_path)
        file_extension = os.path.splitext(file_path)[1]
        
        temp_status_widget = QWidget(self)
        temp_layout = QHBoxLayout()
        temp_status_widget.setLayout(temp_layout)

        progress_bar = QProgressBar(self)
        progress_bar.setValue(0)

        temp_layout.addWidget(QLabel("Loading: "))
        temp_layout.addWidget(progress_bar)

        self.statusBar().addPermanentWidget(temp_status_widget)
        self.statusBar().showMessage(f"Loading {file_name}")

        def progress(self):
            for i in range(1, 101):
                time.sleep(0.02)  # Simulating load time for each step
                progress_bar.setValue(i)
                QApplication.processEvents()
        try:
            if file_extension in (".tif", ".tiff"):
                layer = TIFFLayer(file_path)
                progress(self)
            elif file_extension == ".shp":
                layer = ShapefileLayer(file_path)
                progress(self)
            elif file_extension == ".geojson":
                layer = GeoJSONLayer(file_path)
                progress(self)

            layer.add_to_map(self.m)

            self.add_layer_checkbox(layer, file_name)
            self.layers.append(layer)

            # Save the map
            data = io.BytesIO()
            self.m.save(data, close_file=False)
            self.web_view.setHtml(data.getvalue().decode())
            self.statusBar().showMessage(f"{file_name} loaded successfully", 5000)
        except Exception as e:
            self.statusBar().showMessage(f"Error loading data: {e}")
        finally:
            self.statusBar().removeWidget(temp_status_widget)

    def add_layer_checkbox(self, layer, file_name):
        checkbox = QCheckBox(file_name)
        checkbox.setCheckState(Qt.CheckState.Checked)
        checkbox.stateChanged.connect(lambda state: self.toggle_layer(layer, state))
        self.layer_list.addWidget(checkbox)

    def toggle_layer(self, state, layer):
        if state == 2:
            layer.add_to_map(self.m)
        else:
            layer.remove_from_map(self.m)

    def attribute_table(self, file_path):
        if file_path:
            try:
                pass
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Falied to load csv file")

    def draw_polygon(self):
        Draw(export=True).add_to(self.m)
        data = io.BytesIO()
        self.m.save(data, close_file=False)
        self.web_view.setHtml(data.getvalue().decode())

class ToolDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.main_window = GISApp()
        self.setWindowTitle("Toolbox")
        self.setGeometry(100, 100, 300, 400)

        # Layout for the dialog
        layout = QVBoxLayout()

        # Label for description
        label = QLabel("Select a tool to use:")
        layout.addWidget(label)

        # Tree widget for tools with categories
        self.tool_tree = QTreeWidget()
        self.tool_tree.setHeaderLabel("Tools")

        # Define categories and tools with their icons
        categories = {
            "Conversion Tools": {
                "Raster to Point": "icons/toolbox.png",
                "Raster to Polygon": "icons/toolbox.png",
                "Vector to Raster": "icons/toolbox.png"
            },
            "Geoprocessing Tools": {
                "Clip": "icons/toolbox.png",
                "Buffer": "icons/toolbox.png",
                "Dissolve": "icons/toolbox.png"
            },
            "Spatial Analysis Tools": {
                "Spatial Join": "icons/toolbox.png",
                "Intersect": "icons/toolbox.png",
                "Union": "icons/toolbox.png"
            },
            "Projections": {
                "Define Projection": "icons/toolbox.png",
                "Reproject": "icons/toolbox.png"
            }
        }

        # Populate the tree with categories and tools
        for category, tools in categories.items():
            category_item = QTreeWidgetItem([category])
            category_item.setIcon(0, QIcon("icons/toolbox.png"))
            for tool, icon_path in tools.items():
                tool_item = QTreeWidgetItem([tool])
                tool_item.setIcon(0, QIcon(icon_path))  # Set the icon for the tool
                category_item.addChild(tool_item)
            self.tool_tree.addTopLevelItem(category_item)

        # Connect the selection event
        self.tool_tree.itemClicked.connect(self.tool_selected)

        layout.addWidget(self.tool_tree)
        self.setLayout(layout)

    def tool_selected(self, item):
        # Perform action based on tool selection
        if item.parent():  # Ensure it's a tool (not a category)
            selected_tool = item.text(0)
            if selected_tool == "Raster to Point":
                self.perform_raster_to_point()

    def perform_raster_to_point(self):
        raster_file, _ = QFileDialog.getOpenFileName(self, "Select Raster File", "", "TIF Files (*.tif)")
        if raster_file:
            input_raster_path = os.path.abspath(raster_file)
            directory = os.path.dirname(raster_file)
            filename = os.path.basename(input_raster_path)
            file_root, file_extension = os.path.splitext(filename) 
            output_filename = file_root + "_points.shp"
            output_path = os.path.join(directory, output_filename)
            print(output_path)
            
            if output_path:
                raster_to_point(raster_file, output_path)
                points = CircleMarker(file_name=output_path)
                points.add_to_map(self.main_window.m)
                data = io.BytesIO()
                self.main_window.m.save(data, close_file=False)
                self.main_window.web_view.setHtml(data.getvalue().decode())
                print(self.main_window.layers, self.main_window.layer_checboxes)

app = QApplication(sys.argv)
window = GISApp()
window.show()
sys.exit(app.exec())

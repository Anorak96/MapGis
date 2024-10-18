import sys
import geopandas as gpd
from http.server import SimpleHTTPRequestHandler, HTTPServer
import threading
import rasterio
from rasterio.transform import from_origin
import folium
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget, QFileDialog, QLabel, QHBoxLayout, QCheckBox, QListWidget, QTableWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QUrl
import os
os.environ["QT_OPENGL"] = "software"
# os.environ["QTWEBENGINE_DISABLE_GPU"] = "0"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"

class GISApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setStyleSheet(
            """
            Qlabel, QMainWindow {
                background-color: #f0f0f0;
            }
            """
        )
        self.setWindowTitle("GIS Application")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QHBoxLayout(self.central_widget)

        self.layer_list_widget = QListWidget()
        self.layer_list = QVBoxLayout(self.layer_list_widget)
        self.layer_list_widget.setFixedWidth(160)  # Set fixed width in pixels
        self.main_layout.addWidget(self.layer_list_widget)

        self.layer_list_label = QLabel("Layers")
        self.layer_list.addWidget(self.layer_list_label)
        self.layer_list.addStretch()

        self.layer_checboxes = {}
        self.layers = {}

        # Create a QWebEngineView to display the Folium map
        self.web_view = QWebEngineView()
        self.main_layout.addWidget(self.web_view)

        self.right_list_widget = QWidget()
        self.right_list = QVBoxLayout(self.right_list_widget)
        self.right_list_widget.setFixedWidth(160)
        self.main_layout.addWidget(self.right_list_widget)

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(6)
        # self.table_widget.setHorizontalHeaderlabels()
        self.right_list.addWidget(self.table_widget)
        
        self.main_layout.setStretch(0, 1)  # Stretch factor for the layer_list layout
        self.main_layout.setStretch(1, 14)
        self.main_layout.setStretch(2, 1)

        self.load_data()

        self.geodata = None  # Placeholder for GeoDataFrame

        self.create_menu_bar()

    def create_menu_bar(self):
        # Create a menu bar
        menubar = self.menuBar()

        # Create a 'File' menu
        file_menu = menubar.addMenu('File')
        edit_menu = menubar.addMenu('Edit')
        view_menu = menubar.addMenu('View')
        help_menu = menubar.addMenu('Help')

        # Create actions using QAction
        load_action = QAction('Load Data', self)
        load_action.setShortcut('Ctrl+L')  # Optional: Set shortcut
        load_action.triggered.connect(self.load_data)  # Connect action to function
        save_action = QAction('Save', self)
        save_action.triggered.connect(self.save_data)
        file_menu.addAction(load_action)
        add_layer_action = QAction('Add Layer', self)
        add_layer_action.triggered.connect(self.create_layer)  # Connect action to function
        file_menu.addAction(add_layer_action)
        quit_action = QAction('Quit', self)
        quit_action.setShortcut('Ctrl+Q')  # Optional: Set shortcut
        quit_action.triggered.connect(self.close)  # Connect action to quit the app
        file_menu.addAction(quit_action)

        table_action = QAction('Attribute Table', self)
        table_action.triggered.connect(self.attribute_table)  # Connect action to function
        view_menu.addAction(table_action)
        
        paste_action = QAction('Paste', self)
        edit_menu.addAction(paste_action)
        
    def load_data(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Load GeoData",
            "",
            "Shapefiles (*.shp)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if file_name:
            self.geodata = gpd.read_file(file_name)
            self.display_map()
    def save_data(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if dir_path:
            folder_path = os.path.join(dir_path, 'Saved')
    def display_map(self):
        # self.label = QLabel("Map")
        if self.geodata is not None and not self.geodata.empty:
            # Create a Folium map centered around the data's centroid
            combined_geometry = gpd.GeoSeries(self.geodata.geometry).union_all()
            centroid = combined_geometry.centroid

            self.m = folium.Map(location=[centroid.y, centroid.x], zoom_start=8)

            # Add GeoData to the map
            geo_layer = folium.GeoJson(self.geodata, name='Geodata')
            geo_layer.add_to(self.m)

            # folium.LayerControl().add_to(self.m)

            self.add_layer_checkbox("Geo_Layer", geo_layer)

            # Save the map to an HTML file
            map_file = "map.html"
            self.m.save(map_file)

            # Load the HTML file in the QWebEngineView
            self.web_view.setUrl(QUrl("http://localhost:8000/map.html"))

    def create_layer(self):
        tif_file , _ = QFileDialog.getOpenFileName(self, "open tiff file", "", "TIFF Files (*.tif *.tiff)")
        if tif_file:
            try:
                if self.m is None:
                    print("no map. load a shapefile.")
                    return
                
                with rasterio.open(tif_file) as src:
                    bounds = src.bounds

                    # transform = from_origin(bounds.left, bounds.top, abs(bounds.right - bounds.left) / src.width, abs(bounds.top - bounds.bottom) / src.height)

                    image_overlay = folium.raster_layers.ImageOverlay(
                        image=src.read(1),
                        bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
                        opacity=0.6,
                        name="Tiff Layer"
                    )

                    image_overlay.add_to(self.m)

                    self.add_layer_checkbox("tif_file", image_overlay, file_name=os.path.basename(tif_file))
                    
                    map_file = "map.html"
                    self.m.save(map_file)

                    # Load the HTML file in the QWebEngineView
                    self.web_view.setUrl(QUrl("http://localhost:8000/map.html"))
            except Exception as e:
                print(f"Error loading TIFF file: {e}")

    def add_layer_checkbox(self, layer_name, layer_object, file_name=None):
        label_text = layer_name
        if file_name:
            label_text += f" ({file_name})"
        checkbox = QCheckBox(label_text)
        checkbox.setChecked(True)
        self.layer_list.addWidget(checkbox)

        self.layer_checboxes[layer_name] = checkbox
        self.layers[layer_name] = layer_object  # Store layer reference

        checkbox.stateChanged.connect(lambda state: self.toggle_layer(state, checkbox.text()))

    def toggle_layer(self, state, layer_name):
        if layer_name in self.layers:
            layer = self.layers[layer_name]

            if state == 0:
                # Uncheck means to remove the layer
                if layer in self.m._children:
                    self.m._children.remove(layer)  # Remove layer from the map
            else:
                # Check means to add the layer back
                if layer not in self.m._children:
                    layer.add_to(self.m)

            # Save the map and reload in the web view
            map_file = "map.html"
            self.m.save(map_file)
            self.web_view.setUrl(QUrl("http://localhost:8000/map.html"))
        else:
            print(f"Layer '{layer_name}' not found.")

    def attribute_table(self):
        file = QFileDialog.getOpenFileName(self, "open tiff file", "", "Shp Files (*.shp)")
        table = gpd.read_file(file)
        table.head()

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

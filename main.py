import sys
from pathlib import Path
import geopandas as gpd
from http.server import SimpleHTTPRequestHandler, HTTPServer
import threading
import rasterio
from rasterio.transform import from_origin
import folium
from folium.plugins import Draw, MousePosition
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget, QFileDialog, QLabel, QHBoxLayout, QCheckBox, QListWidget, QTableWidget, QTableWidgetItem, QToolBar, QDialog, QDialogButtonBox, QTabWidget, QPushButton, QMessageBox, QTextEdit, QInputDialog
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import QUrl, QSize
import os
os.environ["QT_OPENGL"] = "software"
# os.environ["QTWEBENGINE_DISABLE_GPU"] = "0"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"

class GISApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GIS Application")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.path = None
        self.filters = 'Shp Files (*.shp)'

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

        # Create a QWebEngineView to display the Folium map
        self.web_view_widget = QWidget()
        self.web_view = QWebEngineView(self.web_view_widget)
        self.main_layout.addWidget(self.web_view)

        self.right_list_widget = QWidget()
        self.right_list = QVBoxLayout(self.right_list_widget)
        self.right_list_widget.setFixedWidth(160)
        self.main_layout.addWidget(self.right_list_widget)

        self.table_widget = QTableWidget(self)
        self.table_widget.setColumnCount(6)
        self.right_list.addWidget(self.table_widget)
        
        self.main_layout.setStretch(0, 1)  # Stretch factor for the layer_list layout
        self.main_layout.setStretch(1, 14)
        self.main_layout.setStretch(2, 1)

        self.load_data()

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

        # Create file actions using QAction
        new_action = QAction(QIcon("fugue-icons-3.5.6/icons/new-text.png"), 'New File', self)
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

        add_layer_action = QAction('Add Layer', self)
        add_layer_action.triggered.connect(self.create_layer)  # Connect action to function
        file_menu.addAction(add_layer_action)
        
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
        undo_action = QAction(QIcon('fugue-icons-3.5.6/icons/arrow-return-180.png'), '&Undo', self)
        undo_action.setStatusTip('Undo')
        undo_action.setShortcut('Ctrl+Z')
        edit_menu.addAction(undo_action)

        redo_action = QAction(QIcon('fugue-icons-3.5.6/icons/arrow-return.png'), '&Redo', self)
        redo_action.setStatusTip('Redo')
        redo_action.setShortcut('Ctrl+Y')
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        paste_action = QAction('Paste', self)
        edit_menu.addAction(paste_action)
        edit_menu.addSeparator()

        # Create Geop actions using QAction
        buffer = QAction('Buffer', self)
        buffer.triggered.connect(self.buffer_data)
        geop_menu.addAction(buffer)

        clip = QAction('Clip', self)
        geop_menu.addAction(clip)

        union = QAction('Union', self)
        union.triggered.connect(self.union_data)
        geop_menu.addAction(union)

    def create_tool_bar(self):
        toolbar = QToolBar("My main toolbar")
        self.addToolBar(toolbar)
        toolbar.setIconSize(QSize(16, 16))

        new_button = QAction(QIcon("fugue-icons-3.5.6/icons/new-text.png"), "New File", self)
        # button_action.triggered.connect(self.onMyToolBarButtonClick)
        toolbar.addAction(new_button)

        paste_button = QAction(QIcon("fugue-icons-3.5.6/icons/clipboard-paste.png"), "Paste", self)
        # button_action.triggered.connect(self.onMyToolBarButtonClick)
        toolbar.addAction(paste_button)

        copy_button = QAction(QIcon("fugue-icons-3.5.6/icons/document-copy.png"), "Copy", self)
        # button_action.triggered.connect(self.onMyToolBarButtonClick)
        toolbar.addAction(copy_button)

        cut_button = QAction(QIcon("fugue-icons-3.5.6/icons/scissors.png"), "Cut", self)
        # button_action.triggered.connect(self.onMyToolBarButtonClick)
        toolbar.addAction(cut_button)

        draw_button = QAction(QIcon("fugue-icons-3.5.6/icons/layer-shape-polygon.png"), "Draw", self)
        draw_button.triggered.connect(self.draw_polygon)
        toolbar.addAction(draw_button)

    def load_data(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load GeoData",
            "",
            "Shapefiles (*.shp)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if file_path:
            self.geodata = gpd.read_file(file_path)
            file_name = os.path.basename(file_path)
            self.display_map(file_name)
    
    def set_title(self, filename=None):
        title = f"{filename if filename else 'Untitled'}"
        self.setWindowTitle(title)

    def save_data(self):
        text_edit = QTextEdit()

        if (self.path):
            return self.path.write_text(text_edit.toPlainText())
        
        filename, _ = QFileDialog.getSaveFileName(self, 'Save File', filter=self.filters)

        if not filename:
            return
        
        self.path = Path(filename)
        self.path.write_text(text_edit.toPlainText())
        self.set_title(filename)
            
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
        
    def display_map(self, file_name):
        if self.geodata is not None and not self.geodata.empty:
            # Create a Folium map centered around the data's centroid
            combined_geometry = gpd.GeoSeries(self.geodata.geometry).union_all()
            centroid = combined_geometry.centroid

            self.m = folium.Map(location=[centroid.y, centroid.x], zoom_start=8)

            # Add GeoData to the map
            geo_layer = folium.GeoJson(self.geodata, name=file_name)
            geo_layer.add_to(self.m)
            MousePosition().add_to(self.m)

            self.add_layer_checkbox(file_name=geo_layer)
            self.layers.append(geo_layer)
            folium.LayerControl().add_to(self.m)

            # Save the map to an HTML file
            map_file = "map.html"
            self.m.save(map_file)

            # Load the HTML file in the QWebEngineView
            self.web_view.setUrl(QUrl("http://localhost:8000/map.html"))

    def create_layer(self):
        tif_file , _ = QFileDialog.getOpenFileName(self, "open tiff file", "", "TIFF Files (*.tif *.tiff)")
        file_name = os.path.basename(tif_file)
        if tif_file:
            try:                
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

                    self.add_layer_checkbox(image_overlay)
                    self.layers.append(image_overlay)
                    
                    map_file = "map.html"
                    self.m.save(map_file)

                    # Load the HTML file in the QWebEngineView
                    self.web_view.setUrl(QUrl("http://localhost:8000/map.html"))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error loading TIFF file: {e}")

    def add_layer_checkbox(self, file_name=None):
        if file_name:
            checkbox = QCheckBox(file_name)
            checkbox.setChecked(True)
            self.layer_list.addWidget(checkbox)
            self.layer_checboxes[file_name] = checkbox
            checkbox.stateChanged.connect(lambda state: self.toggle_layer(state, file_name))

    def toggle_layer(self, state, file_name):
        if file_name:
            print(state)
            print(file_name)
            print(self.layers)
            print(self.layer_checboxes[file_name])

    def attribute_table(self):
        file, _ = QFileDialog.getOpenFileName(self, "open shp file", "", "csv Files (*.shp)")
        if file:
            try:
                data = gpd.read_file(file)
                data.head()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Falied to load csv file")

    def draw_polygon(self):
        Draw(export=True).add_to(self.m)
        map_file = "map.html"
        self.m.save(map_file)

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

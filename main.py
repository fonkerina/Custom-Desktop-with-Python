import sys
import spotipy as sp
from spotipy.oauth2 import SpotifyOAuth
import requests
import os
import math

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QListWidget, QPushButton, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QFont, QPixmap, QFontDatabase, QPainter, QBrush, QColor, QCursor, QRegion, QPolygon, QPainterPath
from PyQt6.QtCore import Qt, QTimer, QPoint

# ADD RESIZE FEATURE TO ALL
#todo here: code to deal with overflow, set up saves in json file and delete previous json file!!

class TodoList(QWidget):
    def __init__(self, ax:int, ay:int, aw:int, ah:int):
        super().__init__()
        self.ax = ax
        self.ay = ay
        self.aw = aw
        self.ah = ah
        
        self.load_assets()
        self.init_ui()
        self.config_ui()

    def load_assets(self):
        font_id = QFontDatabase.addApplicationFont("assets/Tangerine-Regular.ttf")
        family = QFontDatabase.applicationFontFamilies(font_id)[0]
        self.font = QFont(family, 12) # load in font
        self.bg_pixmap = QPixmap("assets/listbg.jpeg") # background image
    
    class MinButton(QPushButton):
        def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QBrush(QColor(255, 255, 255, 200)))  # white 
            
            """shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(20)         # how soft the shadow is
            shadow.setOffset(0, 2)           # x and y offset
            shadow.setColor(QColor(0, 0, 0, 180))  # semi-transparent black
            self.setGraphicsEffect(shadow)"""
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(0, 0, 7, 3)  # draw rectangle
            super().paintEvent(event)

    def init_ui(self):
        """Initialise widget"""
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(self.ax, self.ay, self.aw, self.ah)
        
        self.is_minimised = False
        self._offset = None
        

    def config_ui(self):
        """Configure UI"""
        
        # Place background image
        self.bg = QLabel(self)
        self.bg.setPixmap(self.bg_pixmap)
        self.bg.setGeometry(0, 0, self.width(), self.height())

        self.bg.mousePressEvent = self.start_move
        self.bg.mouseMoveEvent = self.do_move
        
        # Create entry box
        self.entry = QLineEdit(self)
        self.entry.setFont(self.font)
        self.entry.setPlaceholderText("What are we going to do?...")
        self.entry.setGeometry(7, 24, 195, 34)
        self.entry.setStyleSheet("""
            QLineEdit {
                margin: 5px;
                font-size: 18px;
                padding: 2px;
                background: rgba(255,255,255,95);
                border-bottom: 1.5px solid rgba(79, 12, 58, 0.4);
                border-radius: 0px;
            }
            QLineEdit {
                border-radius: 0px;
            }
        """)
        self.entry.returnPressed.connect(self.add_to_list)

        # Create listbox
        self.listbox = QListWidget(self)
        self.listbox.setFont(self.font)
        self.listbox.setGeometry(12, 57, 185, 340)
        self.listbox.setStyleSheet("""
            QListWidget {
                margin-bottom: 3px;
                background: rgba(255,255,255,120);
                color: black;
            }
            QListWidget::item:selected {
                background: rgba(255,255,255,128);
            }
        """)
        self.listbox.itemClicked.connect(self.complete_task)

        # Initialise minimise button
        self.min_btn = self.MinButton(self)  
        self.min_btn.setGeometry(190, 10, 9, 3)
        self.min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.min_btn.clicked.connect(self.minimise)

        self.show()
    
    # WIDGET FEATURES
    def add_to_list(self):
        """Add item from entrybox to listbox upon pressing enter key"""
        
        text = self.entry.text().strip()
        if text:
            self.listbox.addItem(text)
            self.entry.clear()
    
    def complete_task(self, selected):
        """ Mark item as completed in listbox, add strikethrough, and delete any list overflow"""
        selected = self.listbox.currentItem()
        
        if self.font.strikeOut():
            self.font.setStrikeOut(False)
            selected.setFont(self.font)
            selected.setForeground()
        else:
            self.font.setStrikeOut(True)
            selected.setFont(self.font)
            selected.setForeground(QColor(150,150,150))
    
    def minimise(self):
        """ Minimise window """
        
        if self.is_minimised:
            return
        
        self.prev_geometry = self.geometry()
        self.listbox.hide()
        self.entry.hide()
        self.min_btn.hide()

        # Mini square with title
        self.small_label = QLabel("📌 To-Do", self)
        self.small_label.setFont(self.font)
        self.small_label.setStyleSheet("background-color: rgba(0,0,0,180); color: white;")
        self.small_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.small_label.setGeometry(0, 0, 122, 40)
        self.small_label.show()
        self.small_label.mouseDoubleClickEvent = lambda e: self.restore()

        self.setGeometry(self.x(), self.y(), 122, 40)
        self.small_label.mousePressEvent = self.start_move
        self.small_label.mouseMoveEvent = self.do_move
        self.is_minimised = True

    def restore(self, event = None):
        """ Restore a minimised window"""
        if not self.is_minimised:
            return
        
        self.small_label.hide()
        self.setGeometry(self.prev_geometry)
        self.listbox.show()
        self.entry.show()
        self.min_btn.show()
        
        self.is_minimised = False

    def start_move(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._offset = event.pos()

    def do_move(self, event):
        if self._offset is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(self.pos() + event.pos() - self._offset)

#todo here: get album art to show, make words bolder

SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPE = "user-read-playback-state user-read-currently-playing user-modify-playback-state"

class SpotifyWidget(QWidget):
    def __init__(self, ax:int, ay:int, aw:int, ah:int):
        super().__init__()
        self.ax = ax
        self.ay = ay
        self.aw = aw
        self.ah = ah
        
        self.song_name = "[Track]"
        self.artist_name = "[Artist]"
        
        self.sp = sp.Spotify(auth_manager=SpotifyOAuth(
        client_id = os.environ.get("SPOTIFY_CLIENT_ID"),
        client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET"),
        redirect_uri = SPOTIFY_REDIRECT_URI,
        scope = SCOPE
    ))
        #devices = self.sp.devices()
        #print("devices",devices)
        
        self.load_assets()
        self.init_ui()
        self.config_ui()
        self.update_track()
        
        self.track_timer = QTimer()
        self.track_timer.timeout.connect(self.update_track)
        self.track_timer.start(2000)
        
    
    def load_assets(self):
        font_id = QFontDatabase.addApplicationFont("assets/Tangerine-Regular.ttf")
        family = QFontDatabase.applicationFontFamilies(font_id)[0]
        self.font = QFont(family, 14) # load in font
        self.backg_pixmap = QPixmap("assets/spotbg.jpeg") # background image
        
    def init_ui(self):
        """Initialise widget"""
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setGeometry(self.ax, self.ay, self.aw, self.ah)
        self._offset = None
    
    def config_ui(self):
        self.backg = QLabel(self)
        self.scaled_pixmap = self.backg_pixmap.scaled(
        self.width(), self.height(), 
        Qt.AspectRatioMode.KeepAspectRatio, 
        Qt.TransformationMode.SmoothTransformation
    )
        self.backg.setPixmap(self.scaled_pixmap)
        self.backg.setGeometry(0, 0, self.width(), self.height())
        
        self.backg.mousePressEvent = self.start_move
        self.backg.mouseMoveEvent = self.do_move
        
        self.album_art = QLabel(self)
        self.album_art.setGeometry(self.ax//40, self.ay//6, self.aw//5, self.ah//2)
        self.album_art.setStyleSheet("border-radius: 4px;")
        self.album_art.setScaledContents(True)

        self.song_label = QLabel(self.song_name, self)
        self.song_label.setFont(self.font)
        self.song_label.setStyleSheet("color: black;")
        self.song_label.setGeometry(self.ax//4, self.ay//6, self.aw//2, self.ah//4)

        self.artist_label = QLabel(self.artist_name, self)
        self.artist_label.setFont(self.font)
        self.artist_label.setStyleSheet("color: black;")
        self.artist_label.setGeometry(self.ax//4, self.ay//2, self.aw//2, self.ah//5)
            
        # Playback buttons
        self.prev_btn = QPushButton("⏮", self)
        self.play_btn = QPushButton("⏯", self)
        self.next_btn = QPushButton("⏭", self)
        for i, btn in enumerate([self.prev_btn, self.play_btn, self.next_btn]):
            btn.setFont(self.font)
            btn.setStyleSheet("""
                QPushButton {
                    color: white; 
                    background-color: rgba(50,50,50,110); 
                    border: 2px white;
                }
                QPushButton:hover {
                    background-color: rgba(100,100,100,180);
                }
            """)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setGeometry(80 + i*50, 55, 40, 20)

        self.play_btn.clicked.connect(self.play_pause)
        self.prev_btn.clicked.connect(self.prev_track)
        self.next_btn.clicked.connect(self.next_track)
    
    def start_move(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._offset = event.pos()

    def do_move(self, event):
        if self._offset is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(self.pos() + event.pos() - self._offset)

    def mouseReleaseEvent(self, event):
        self._offset = None

    # SPOTIFY API CONNECTIONS
    def update_track(self):
        track_info = self.sp.current_playback()

        if not track_info or not track_info.get("item"):
            return

        self.track = track_info["item"]
        self.song_name = self.track["name"]
        self.artist_name = ", ".join([artist["name"] for artist in self.track["artists"]])
        self.album_cover_url = self.track["album"]["images"][0]["url"]

        self.song_label.setText(self.song_name)
        self.artist_label.setText(self.artist_name)

        data = requests.get(self.album_cover_url).content
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        self.album_art.setPixmap(pixmap)

    def play_pause(self):
        try:
            devices = self.sp.devices().get("devices", [])
            if not devices:
                print("No active Spotify device found.")
                return
        
            track_info = self.sp.current_playback()
        
            if track_info and track_info["is_playing"]:
                self.sp.pause_playback()
            else:
                self.sp.start_playback()
        
        except sp.exceptions.SpotifyException as e:
            print("Spotify error:", e)

    def next_track(self):
        self.sp.next_track()

    def prev_track(self):
        self.sp.previous_track()
    
    
class PicWidget(QWidget):
    def __init__(self, shape: str, asset: str, width: int, height: int, x: int, y: int):
        super().__init__()
        self._offset = None
        self.shape = shape.lower()
        self.setGeometry(x, y, width, height)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Apply shape mask first
        self.apply_mask(width, height)
        
        # Load image and scale to widget size exactly
        self.frame = QLabel(self)
        pixmap = QPixmap(asset).scaled(width, height, 
                                       Qt.AspectRatioMode.IgnoreAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
        self.frame.setPixmap(pixmap)
        self.frame.setGeometry(0, 0, width, height)
        self.frame.mousePressEvent = self.start_move
        self.frame.mouseMoveEvent = self.do_move
        self.show()
    
    def apply_mask(self, width, height, radius = 20):
        """Apply mask according to shape"""
        if self.shape == 'circle':
            region = QRegion(0, 0, width, height, QRegion.Ellipse)
            self.setMask(region)
        elif self.shape == 'rectangle':
            region = QRegion(0, 0, width, height)
            self.setMask(region)
        elif self.shape == 'rounded':
            path = QPainterPath()
            path.addRoundedRect(0, 0, width, height, radius, radius)
            region = QRegion(path.toFillPolygon().toPolygon())
            self.setMask(region)
        elif self.shape == 'star':
            points = [
                QPoint(int(width*0.5), 0),  # top centre
                QPoint(int(width*0.62), int(height*0.35)),
                QPoint(int(width), int(height*0.4)),
                QPoint(int(width*0.68), int(height*0.6)),
                QPoint(int(width*0.79), int(height)),
                QPoint(int(width*0.5), int(height*0.75)), # middle bottom
                QPoint(int(width*0.21), int(height)),
                QPoint(int(width*0.32), int(height*0.6)), 
                QPoint(0, int(height*0.34)),
                QPoint(int(width*0.38), int(height*0.35))
            ]
            polygon = QPolygon(points)
            region = QRegion(polygon)
            self.setMask(region)
        else:
            raise ValueError("Shape must be 'circle', 'rectangle', or 'star'.")
        
    def start_move(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._offset = event.pos()

    def do_move(self, event):
        if self._offset is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(self.pos() + event.pos() - self._offset)
    

class StudyWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # To do widget
    window = TodoList(5, 300, 210, 390)
    
    # Music widget
    spotify = SpotifyWidget(400, 60, 210, 110)
    spotify.show()
    
    # Picture widgets
    Bloodorange = PicWidget("rounded", "assets/bloodorange.jpeg", 260, 230, 340, 10)
    Bloodorange.show()
    
    Lady = PicWidget("rounded", "assets/Lady.jpeg", 200, 200, 110, 400)
    Lady.show()
    
    #Me = PicWidget("star", "assets/DSCF7458.JPG", 110, 110, 710, 390)
    #minilady = PicWidget("rounded", "assets/Lady icon.jpeg", )
    
    sys.exit(app.exec())



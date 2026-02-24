import sys
import spotipy as sp
from spotipy.oauth2 import SpotifyOAuth
import requests
import os
import math

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QListWidget, QPushButton, QGraphicsOpacityEffect
)
from PyQt6.QtGui import QFont, QPixmap, QFontDatabase, QPainter, QBrush, QColor, QCursor, QRegion, QPolygon, QPainterPath
from PyQt6.QtCore import Qt, QTimer, QPoint, QTime

GRID_WIDTH = 1280
GRID_HEIGHT = 672

GRID_MARGIN = 30 # distance between widgets
GRID_SIZE = 75 # distance between grid points
SNAP_THRESHOLD = 18 # how close before snapping

ALL_WIDGETS = []


class MagneticWidget(QWidget):
    """
    drag property, collision detection, grid snapping
    """
    def __init__(self, x: int, y: int, w: int, h: int, parent = None, name = 'new widget'):
        super().__init__(parent) # establishes hierarchy if there is a parent
        
        self.name = name
        self.offset = None
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                
        # try initial position then use find nearest unoccupied snap point
        snap_x, snap_y = self.snap_coords(x, y)
        others = [w["widget"] for w in ALL_WIDGETS if w["widget"] is not self]

        if not self.collision_at(snap_x, snap_y, others):
            final_x, final_y = snap_x, snap_y
        else:
            final_x, final_y = self.find_nearest_free_snap(snap_x, snap_y, others)

        self.setGeometry(final_x, final_y, w, h)
                    
        ALL_WIDGETS.append({"widget": self, "name": name})
        
        
    def collision(self, others):
        widget_box = self.geometry()
        for widget in others:
            if widget_box.intersects(widget.geometry()):
                return True
        return False
    
    def collision_at(self, x, y, others):
        widget_box = self.geometry()
        widget_box.moveTo(x, y)
        for w in others:
            if widget_box.intersects(w.geometry()):
                return True
        return False
    
    def snap_coords(self, x, y):
        snapx = round(x / GRID_WIDTH) * GRID_WIDTH + GRID_MARGIN
        snapy = round(y / GRID_HEIGHT) * GRID_HEIGHT + GRID_MARGIN
        return snapx, snapy
    
    def find_nearest_free_snap(self, snap_x, snap_y, others, max_radius=5):
        """
        Searches grid points around (snap_x, snap_y)
        max_radius = how many grid steps outward to search
        """

        for r in range(max_radius + 1):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):

                    x = snap_x + dx * GRID_WIDTH
                    y = snap_y + dy * GRID_HEIGHT

                    if not self.collision_at(x, y, others):
                        return x, y

        return snap_x, snap_y  

    def start_move(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._offset = event.pos()

    def do_move(self, event):
        if self._offset and event.buttons() == Qt.MouseButton.LeftButton:
            move_pos = self.pos() + event.pos() - self._offset

            snap_x, snap_y = self.snap_coords(move_pos.x(), move_pos.y())
            others = [w["widget"] for w in ALL_WIDGETS if w["widget"] is not self]
            
            if not self.collision_at(snap_x, snap_y, others):
                self.move(snap_x, snap_y)
            else:
                free_x, free_y = self.find_nearest_free_snap(
                    snap_x, snap_y, others
                )
                self.move(free_x, free_y)

    def mouseReleaseEvent(self, event):
        self._offset = None
        
        
#todo here: code to deal with overflow, set up saves in json file and delete previous json file!!
class TodoList(MagneticWidget):
    def __init__(self, x: int, y: int, w: int, h: int):
        super().__init__(x,y,w,h, name = 'ToDoList')
        self.load_assets()
        
        self.is_minimised = False
        self.setGeometry(x, y, w, h)
        
        self.config_ui()
     
    def load_assets(self):
        font_id = QFontDatabase.addApplicationFont("public_assets/Tangerine-Regular.ttf")
        family = QFontDatabase.applicationFontFamilies(font_id)[0]
        self.font = QFont(family, 12)
        self.bg_pixmap = QPixmap("public_assets/todobg.jpg") 
    
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
        pass
        

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
                background: rgba(255,255,255,110);
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
                background: rgba(0,0,0,55);
                color: black;
            }
            QListWidget::item:selected {
                background: rgba(0,0,0,90);
            }
        """)
        self.listbox.itemClicked.connect(self.complete_task)
        self.listbox.mousePressEvent = self.start_move
        self.listbox.mouseMoveEvent = self.do_move

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

#todo spotify: make words bolder
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPE = "user-read-playback-state user-read-currently-playing user-modify-playback-state"

class SpotifyWidget(MagneticWidget):
    def __init__(self, x:int, y:int, w:int, h:int):
        super().__init__(x,y,w,h, name = 'SpotifyWidget')
        
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
        self.setGeometry(x, y, w, h)
        
        self.config_ui()
        self.update_track()
        
        self.track_timer = QTimer()
        self.track_timer.timeout.connect(self.update_track)
        self.track_timer.start(2000)
        
    
    def load_assets(self):
        font_id = QFontDatabase.addApplicationFont("public_assets/RobotoMono-VariableFont_wght.ttf")
        family = QFontDatabase.applicationFontFamilies(font_id)[0]
        self.font = QFont(family, 14) # load in font
        self.backg_pixmap = QPixmap("public_assets/newspotbg.jpg") # background image
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(0.8)  
        
    def init_ui(self):
        """Initialise widget"""
        pass
    
    def config_ui(self):
        self.backg = QLabel(self)
        self.scaled_pixmap = self.backg_pixmap.scaled(
        self.width(), self.height(), 
        Qt.AspectRatioMode.KeepAspectRatio, 
        Qt.TransformationMode.SmoothTransformation
    )
        self.backg.setPixmap(self.scaled_pixmap)
        self.backg.setGraphicsEffect(self.opacity_effect)
        self.backg.setGeometry(0, 0, self.width(), self.height())
        self.backg.mousePressEvent = self.start_move
        self.backg.mouseMoveEvent = self.do_move
        
        self.album_art = QLabel(self)
        self.album_art.setGeometry(4*self.x() + self.width()//2, 0, self.width()//3, self.height())
        #self.album_art.setStyleSheet("border-radius: 4px;")
        self.album_art.setScaledContents(True)

        self.song_label = QLabel(self.song_name, self)
        self.song_label.setFont(self.font)
        self.song_label.setStyleSheet("color: black;")
        self.song_label.setGeometry(self.x()//4 + 4, 4, self.width()//4, self.height()//4)

        self.artist_label = QLabel(self.artist_name, self)
        self.artist_label.setFont(self.font)
        self.artist_label.setStyleSheet("color: black;")
        self.artist_label.setGeometry(self.x()//4 + 4, self.y()//10 +4, self.width()//4, self.height()//5)
            
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
    
class PicWidget(MagneticWidget):
    def __init__(self, shape: str, asset: str, x:int, y:int, w:int, h:int):
        super().__init__(x,y,w,h, name = 'PicWidgetConstructor')
        self.x = x
        self.y = y
        self.w = w
        self.h = h 
        
        self.shape = shape.lower()
        self.apply_mask(w, h)
        
        # Load image and scale to widget size exactly
        self.frame = QLabel(self)
        pixmap = QPixmap(asset).scaled(w, h, 
                                       Qt.AspectRatioMode.IgnoreAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
        self.frame.setPixmap(pixmap)
        self.frame.setGeometry(0, 0, w, h)
        self.frame.mousePressEvent = self.start_move
        self.frame.mouseMoveEvent = self.do_move
        self.show()
    
    def apply_mask(self, w, h, radius = 20):
        """Apply mask according to shape"""
        if self.shape == 'circle':
            region = QRegion(0, 0, w, h, QRegion.Ellipse)
            self.setMask(region)
        elif self.shape == 'rectangle':
            region = QRegion(0, 0, w, h)
            self.setMask(region)
        elif self.shape == 'rounded':
            path = QPainterPath()
            path.addRoundedRect(0, 0, w, h, radius, radius)
            region = QRegion(path.toFillPolygon().toPolygon())
            self.setMask(region)
        elif self.shape == 'star':
            points = [
                QPoint(int(w*0.5), 0),  # top centre
                QPoint(int(w*0.62), int(h*0.35)),
                QPoint(int(w), int(h*0.4)),
                QPoint(int(w*0.68), int(h*0.6)),
                QPoint(int(w*0.79), int(h)),
                QPoint(int(w*0.5), int(h*0.75)), # middle bottom
                QPoint(int(w*0.21), int(h)),
                QPoint(int(w*0.32), int(h*0.6)), 
                QPoint(0, int(h*0.34)),
                QPoint(int(w*0.38), int(h*0.35))
            ]
            polygon = QPolygon(points)
            region = QRegion(polygon)
            self.setMask(region)
        else:
            raise ValueError("Shape must be 'circle', 'rectangle', or 'star'.")
         
class ClockWidget(MagneticWidget):
    def __init__(self, x:int, y:int, w:int, h:int):
        super().__init__(x, y, w, h, name = 'ClockWidget')
        
        self.load_assets()
        self.setGeometry(x, y, w, h)
        self.config_ui()
        self.update_time()

        # Timer to update every second
        timer = QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(900)

    def init_ui(self):
        pass
    
    def load_assets(self):
        font_id = QFontDatabase.addApplicationFont("public_assets/RobotoMono-VariableFont_wght.ttf")
        family = QFontDatabase.applicationFontFamilies(font_id)[0]
        self.font = QFont(family, 40) # load in font
        self.backg_pixmap = QPixmap("public_assets/clockbg.jpg") 
        
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
        
        self.time_label = QLabel(self)
        self.time_label.setGeometry(-10, 0, self.width(), self.height())
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setFont(self.font)
        self.time_label.setStyleSheet("""
                                      QLabel { 
                                        color: white;
                                        font-size: 24px; 
                                        }""")
        self.time_label.mousePressEvent = self.start_move
        self.time_label.mouseMoveEvent = self.do_move

    def update_time(self):
        """Update the label with the current time"""
        current_time = QTime.currentTime().toString("HH:mm:ss")
        self.time_label.setText(current_time)
        

        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # To do widget
    window = TodoList(820, 10, 210, 440)
    
    # Music widget
    spotify = SpotifyWidget(10, 300, 260, 100)
    spotify.show()
    
    # Clock widget
    clock = ClockWidget(10, 10, 350, 170) 
    clock.show()
    
    # Picture widgets
    Bloodorange = PicWidget("rounded", "assets/bloodorange.jpeg", 1070, 10, 130, 120) 
    Bloodorange.show()
    
    Lady = PicWidget("rounded", "assets/Lady.jpeg", 1070, 300, 70, 60)
    Lady.show()
    
    #me = PicWidget("rounded", "assets/mini1.JPG", 1070, 350, 130, 120)
    #me.show()
    
    maki = PicWidget("rounded", "assets/mini2.jpg", 1070, 200, 70, 60)
    maki.show()
    
    print(ALL_WIDGETS)
    #minilady = PicWidget("rounded", "assets/Lady icon.jpeg", )
    
    sys.exit(app.exec())



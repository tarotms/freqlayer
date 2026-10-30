import sys
import os
import ctypes
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QStackedLayout, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent, QFont, QIcon

from widgets import DropZone, FilterWidget, TimelineWidget, SoftnessKnob
from engine import AudioEngine

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("freqlayer 1.1")
        self.resize(980, 340)
        self.setStyleSheet("background-color: #0d1117; color: #c9d1d9;")

        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.engine = AudioEngine()
        self.layout = QStackedLayout(self)

        self.drop_zone = DropZone()
        self.layout.addWidget(self.drop_zone)

        self.player_widget = QWidget()
        self.player_layout = QVBoxLayout(self.player_widget)
        self.player_layout.setContentsMargins(15, 12, 15, 12)
        self.player_layout.setSpacing(10)

        top_bar = QHBoxLayout()
        top_bar.addStretch()

        knob_box = QHBoxLayout()
        knob_label = QLabel("FEATHER (BW)")
        knob_label.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        knob_label.setStyleSheet("color: #7d8b99;")
        self.knob = SoftnessKnob()
        knob_box.addWidget(knob_label)
        knob_box.addWidget(self.knob)
        top_bar.addLayout(knob_box)

        self.player_layout.addLayout(top_bar)

        self.filter_ui = FilterWidget()
        self.player_layout.addWidget(self.filter_ui)

        self.timeline = TimelineWidget()
        self.player_layout.addWidget(self.timeline)

        self.layout.addWidget(self.player_widget)

        self.drop_zone.file_dropped.connect(self._on_file_dropped)
        self.engine.progress_updated.connect(self.timeline.update_time)
        self.engine.spectrum_updated.connect(self.filter_ui.update_spectrum)
        self.timeline.seek_requested.connect(self.engine.seek)

        self.filter_ui.region_changed.connect(self.engine.set_filter)
        self.knob.valueChanged.connect(self.filter_ui.set_feather)

    def _on_file_dropped(self, filepath):
        self.layout.setCurrentWidget(self.player_widget)
        self.engine.load_file(filepath)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Space:
            if self.engine.is_playing:
                self.engine.pause()
            else:
                self.engine.play()
        super().keyPressEvent(event)

if __name__ == "__main__":
    if sys.platform == 'win32':
        app_id = 'freqlayer.precision.isolator.1.1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

    app = QApplication(sys.argv)
    app.setApplicationName("freqlayer 1.1")
    app.setStyle("Fusion")

    icon_path = get_resource_path("icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
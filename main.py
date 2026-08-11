import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QStackedLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent

from widgets import DropZone, FilterWidget, TimelineWidget
from engine import AudioEngine

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FREQ")
        self.resize(800, 280)
        self.setStyleSheet("background-color: #121212;")
        
        self.engine = AudioEngine()
        self.layout = QStackedLayout(self)
        
        self.drop_zone = DropZone()
        self.layout.addWidget(self.drop_zone)
        
        self.player_widget = QWidget()
        self.player_layout = QVBoxLayout(self.player_widget)
        self.player_layout.setContentsMargins(15, 15, 15, 15)
        self.player_layout.setSpacing(15)
        
        self.filter_ui = FilterWidget()
        self.timeline = TimelineWidget()
        
        self.player_layout.addWidget(self.filter_ui)
        self.player_layout.addWidget(self.timeline)
        
        self.layout.addWidget(self.player_widget)
        
        self.drop_zone.file_dropped.connect(self._on_file_dropped)
        self.engine.progress_updated.connect(self.timeline.update_progress)
        self.timeline.seek_requested.connect(self.engine.seek)
        self.filter_ui.region_changed.connect(self.engine.set_filter)
        
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
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())
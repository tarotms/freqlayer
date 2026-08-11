import math
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QLineEdit
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIntValidator

class DropZone(QLabel):
    file_dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__("DROP WAV FILE HERE")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #555555;
                border-radius: 8px;
                color: #888888;
                font-size: 16px;
                font-weight: bold;
                background-color: #1e1e1e;
            }
        """)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.file_dropped.emit(urls[0].toLocalFile())

class FreqInput(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QLineEdit {
                background: transparent;
                color: #ffffff;
                font-size: 68px;
                font-weight: bold;
                border: none;
            }
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setValidator(QIntValidator(20, 20000))
        self.setFixedWidth(220)

class CustomViewBox(pg.ViewBox):
    sigDragRegion = pyqtSignal(float, float)
    sigDragFinished = pyqtSignal()

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.setMouseEnabled(x=False, y=False)
        self.drawing = False
        self.start_x = 0

    def mouseDragEvent(self, ev, axis=None):
        if ev.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if ev.button() == Qt.MouseButton.LeftButton:
                if ev.isStart():
                    self.drawing = True
                    self.start_x = self.mapSceneToView(ev.buttonDownScenePos()).x()
                elif ev.isFinish():
                    self.drawing = False
                    self.sigDragFinished.emit()
                elif self.drawing:
                    current_x = self.mapSceneToView(ev.scenePos()).x()
                    self.sigDragRegion.emit(min(self.start_x, current_x), max(self.start_x, current_x))
                ev.accept()
                return
        super().mouseDragEvent(ev, axis)

class FilterWidget(QWidget):
    region_changed = pyqtSignal(float, float)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.min_input = FreqInput()
        self.max_input = FreqInput()
        
        hz_style = "color: #555555; font-size: 24px; font-weight: bold; padding-bottom: 12px;"
        hz_label1 = QLabel("Hz")
        hz_label2 = QLabel("Hz")
        hz_label1.setStyleSheet(hz_style)
        hz_label2.setStyleSheet(hz_style)
        hz_label1.setAlignment(Qt.AlignmentFlag.AlignBottom)
        hz_label2.setAlignment(Qt.AlignmentFlag.AlignBottom)

        header_layout.addStretch()
        header_layout.addWidget(self.min_input)
        header_layout.addWidget(hz_label1)
        header_layout.addSpacing(80)
        header_layout.addWidget(self.max_input)
        header_layout.addWidget(hz_label2)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)

        pg.setConfigOption('background', '#161616')
        pg.setConfigOption('foreground', '#888888')

        self.view_box = CustomViewBox()
        self.plot_widget = pg.PlotWidget(viewBox=self.view_box)
        self.plot_widget.setFixedHeight(130)
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.hideAxis('left')
        self.plot_widget.showGrid(x=True, y=False, alpha=0.15)
        
        self.plot_widget.plotItem.hideButtons()
        
        self.plot_widget.setLogMode(x=True, y=False)
        self.plot_widget.setXRange(math.log10(20), math.log10(20000), padding=0)
        self.plot_widget.setYRange(0, 1, padding=0)
        
        tick_dict = {}
        def add_tick(f, tier, label):
            if f not in tick_dict:
                tick_dict[f] = [" ", " ", " "]
            tick_dict[f][tier] = label

        notes = {
            32.7: "C1", 65.4: "C2", 130.8: "C3", 261.6: "C4",
            523.3: "C5", 1046.5: "C6", 2093.0: "C7", 4186.0: "C8", 8372.0: "C9"
        }
        bands = {
            20.0: "<SUB", 45.0: "SUB", 120.0: "BASS", 350.0: "LOW MID",
            1000.0: "MID", 3000.0: "HIGH MID", 6000.0: "PRS", 12000.0: "TREBLE"
        }
        freqs = {
            20.0: "20", 50.0: "50", 100.0: "100", 200.0: "200", 500.0: "500",
            1000.0: "1k", 2000.0: "2k", 5000.0: "5k", 10000.0: "10k"
        }

        for f, lbl in notes.items(): add_tick(f, 0, lbl)
        for f, lbl in bands.items(): add_tick(f, 1, lbl)
        for f, lbl in freqs.items(): add_tick(f, 2, lbl)
        
        ticks = []
        for f, lines in tick_dict.items():
            tick_str = "\n".join(lines)
            ticks.append((math.log10(f), tick_str))

        self.plot_widget.getAxis('bottom').setTicks([ticks])
        self.plot_widget.getAxis('bottom').setHeight(65)

        self.region = pg.LinearRegionItem(
            [math.log10(100), math.log10(1000)],
            bounds=[math.log10(20), math.log10(20000)], 
            brush=(80, 80, 80, 100), 
            pen='#aaaaaa'
        )
        self.region.setZValue(10)
        self.plot_widget.addItem(self.region)
        
        layout.addWidget(self.plot_widget)

        self.view_box.sigDragRegion.connect(self._on_ctrl_drag)
        self.view_box.sigDragFinished.connect(self._on_region_changed)
        
        self.region.sigRegionChangeFinished.connect(self._on_region_changed)
        self.region.sigRegionChanged.connect(self._on_region_dragging)
        self.min_input.editingFinished.connect(self._on_text_changed)
        self.max_input.editingFinished.connect(self._on_text_changed)

        self._on_region_dragging()

    def _on_ctrl_drag(self, min_x, max_x):
        min_x = max(math.log10(20), min_x)
        max_x = min(math.log10(20000), max_x)
        if min_x == max_x:
            max_x = min_x + 0.0001
        self.region.setRegion([min_x, max_x])

    def _on_region_dragging(self):
        min_log, max_log = self.region.getRegion()
        self.min_input.setText(str(int(10 ** min_log)))
        self.max_input.setText(str(int(10 ** max_log)))

    def _on_region_changed(self):
        self._on_region_dragging()
        min_freq = float(self.min_input.text())
        max_freq = float(self.max_input.text())
        self.region_changed.emit(min_freq, max_freq)

    def _on_text_changed(self):
        try:
            min_freq = max(20, min(20000, int(self.min_input.text())))
            max_freq = max(20, min(20000, int(self.max_input.text())))
            
            if min_freq >= max_freq:
                min_freq = max_freq - 1

            self.min_input.setText(str(min_freq))
            self.max_input.setText(str(max_freq))

            self.region.setRegion([math.log10(min_freq), math.log10(max_freq)])
            self.region_changed.emit(min_freq, max_freq)
        except ValueError:
            self._on_region_dragging()

class TimelineWidget(QSlider):
    seek_requested = pyqtSignal(float)
    
    def __init__(self):
        super().__init__(Qt.Orientation.Horizontal)
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #333333;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #888888;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::sub-page:horizontal {
                background: #666666;
                border-radius: 2px;
            }
        """)
        self.setMinimum(0)
        self.setMaximum(1000)
        self.sliderMoved.connect(self._on_slider_moved)
        
    def _on_slider_moved(self, value):
        self.seek_requested.emit(value / 1000.0)

    def update_progress(self, ratio):
        self.blockSignals(True)
        self.setValue(int(ratio * 1000))
        self.blockSignals(False)
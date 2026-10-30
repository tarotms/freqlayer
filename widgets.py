import math
import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QLinearGradient, 
    QFont, QDragEnterEvent, QDropEvent, QImage
)
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel

class SoftnessKnob(QWidget):
    valueChanged = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(70, 75)
        self.default_val = 50.0
        self.min_val = 0.0001
        self.max_val = 2000.0
        self.current_val = self.default_val
        self.is_dragging = False
        self.last_y = 0

    def val_to_ratio(self, val):
        val = max(self.min_val, min(self.max_val, val))
        return (math.log10(val) - math.log10(self.min_val)) / (math.log10(self.max_val) - math.log10(self.min_val))

    def ratio_to_val(self, ratio):
        log_val = math.log10(self.min_val) + ratio * (math.log10(self.max_val) - math.log10(self.min_val))
        return 10 ** log_val

    def mousePressEvent(self, event):
        # 鼠标中键重置为默认值
        if event.button() == Qt.MouseButton.MiddleButton:
            self.current_val = self.default_val
            self.valueChanged.emit(self.current_val)
            self.update()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.last_y = event.position().y()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            dy = self.last_y - event.position().y()
            self.last_y = event.position().y()
            r = self.val_to_ratio(self.current_val)
            r = max(0.0, min(1.0, r + dy * 0.005))
            self.current_val = self.ratio_to_val(r)
            self.valueChanged.emit(self.current_val)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = 35.0
        center_y = 30.0
        radius = 20.0

        painter.setBrush(QBrush(QColor("#181c22")))
        painter.setPen(QPen(QColor("#2d333b"), 1.5))
        painter.drawEllipse(QPointF(center_x, center_y), radius, radius)

        inner_grad = QLinearGradient(center_x - radius, center_y - radius, center_x + radius, center_y + radius)
        inner_grad.setColorAt(0.0, QColor("#2a303c"))
        inner_grad.setColorAt(1.0, QColor("#14171d"))
        painter.setBrush(inner_grad)
        painter.setPen(QPen(QColor("#0d1117"), 1.0))
        painter.drawEllipse(QPointF(center_x, center_y), radius - 3, radius - 3)

        ratio = self.val_to_ratio(self.current_val)
        angle = 135.0 + ratio * 270.0
        rad = math.radians(angle)
        px = center_x + (radius - 6) * math.cos(rad)
        py = center_y + (radius - 6) * math.sin(rad)

        painter.setPen(QPen(QColor("#00ffc8"), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(center_x, center_y), QPointF(px, py))

        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        painter.setPen(QColor("#8b949e"))
        text = f"{self.current_val:.1f}Hz" if self.current_val >= 1 else f"{self.current_val:.4f}Hz"
        painter.drawText(QRectF(0, 54, 70, 20), Qt.AlignmentFlag.AlignCenter, text)


class FilterWidget(QWidget):
    region_changed = pyqtSignal(float, float, float)

    AUDIO_BANDS = [
        ("SUB", 20.0, 60.0),
        ("BASS", 60.0, 250.0),
        ("LOW-MID", 250.0, 500.0),
        ("MID", 500.0, 2000.0),
        ("HIGH-MID", 2000.0, 4000.0),
        ("PRS", 4000.0, 6000.0),
        ("TREBLE", 6000.0, 20000.0)
    ]

    def __init__(self):
        super().__init__()
        self.setFixedHeight(220)
        self.setMouseTracking(True)  # 开启全局鼠标悬停跟踪
        
        self.min_freq = 20.0
        self.max_freq = 20000.0
        self.cut_low = 100.0
        self.cut_high = 2000.0
        self.feather_hz = 50.0

        self.spectrum_data = None
        self.freq_bins = None
        self.drag_mode = None
        self.drag_start_x = 0
        
        # 顶部频段悬停与跨区拖拽状态
        self.hover_band_idx = -1
        self.drag_band_start = -1

    def update_spectrum(self, freqs, db_levels):
        self.freq_bins = freqs
        self.spectrum_data = db_levels
        self.update()

    def set_feather(self, val):
        self.feather_hz = val
        self.region_changed.emit(self.cut_low, self.cut_high, self.feather_hz)
        self.update()

    def freq_to_x(self, freq):
        freq = max(self.min_freq, min(self.max_freq, freq))
        r = (math.log10(freq) - math.log10(self.min_freq)) / (math.log10(self.max_freq) - math.log10(self.min_freq))
        return r * self.width()

    def x_to_freq(self, x):
        r = max(0.0, min(1.0, x / max(1.0, self.width())))
        log_f = math.log10(self.min_freq) + r * (math.log10(self.max_freq) - math.log10(self.min_freq))
        return 10 ** log_f

    def _get_band_index_by_x(self, x):
        for idx, (_, start_f, end_f) in enumerate(self.AUDIO_BANDS):
            if self.freq_to_x(start_f) <= x <= self.freq_to_x(end_f):
                return idx
        return -1

    def _update_band_selection(self, start_idx, end_idx):
        i1 = min(start_idx, end_idx)
        i2 = max(start_idx, end_idx)
        self.cut_low = self.AUDIO_BANDS[i1][1]
        self.cut_high = self.AUDIO_BANDS[i2][2]
        self.region_changed.emit(self.cut_low, self.cut_high, self.feather_hz)
        self.update()

    def leaveEvent(self, event):
        if self.hover_band_idx != -1:
            self.hover_band_idx = -1
            self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        pos = event.position()
        x = pos.x()
        y = pos.y()
        top_header_h = 24

        # 顶部频段分类栏：支持点击并启动滑动范围选择
        if y <= top_header_h:
            idx = self._get_band_index_by_x(x)
            if idx != -1:
                self.drag_mode = "BAND_RANGE"
                self.drag_band_start = idx
                self._update_band_selection(idx, idx)
                return

        # 下方频谱区：游标与声带移动
        x1 = self.freq_to_x(self.cut_low)
        x2 = self.freq_to_x(self.cut_high)
        margin = 10.0

        if abs(x - x1) <= margin:
            self.drag_mode = "LOW"
        elif abs(x - x2) <= margin:
            self.drag_mode = "HIGH"
        elif x1 < x < x2:
            self.drag_mode = "PAN"
            self.drag_start_x = x
            self.drag_orig_low = self.cut_low
            self.drag_orig_high = self.cut_high
        else:
            self.drag_mode = None

    def mouseMoveEvent(self, event):
        pos = event.position()
        x = pos.x()
        y = pos.y()
        top_header_h = 24

        # 悬停高光更新
        if y <= top_header_h:
            cur_hover = self._get_band_index_by_x(x)
            if cur_hover != self.hover_band_idx:
                self.hover_band_idx = cur_hover
                self.update()
        else:
            if self.hover_band_idx != -1:
                self.hover_band_idx = -1
                self.update()

        # 顶部频段跨区滑动选取 (例如从 BASS 滑到 MID)
        if self.drag_mode == "BAND_RANGE":
            cur_idx = self._get_band_index_by_x(x)
            if cur_idx != -1:
                self._update_band_selection(self.drag_band_start, cur_idx)
            return

        # 游标拖拽
        if self.drag_mode == "LOW":
            f = self.x_to_freq(x)
            self.cut_low = min(f, self.cut_high - 10.0)
            self.region_changed.emit(self.cut_low, self.cut_high, self.feather_hz)
            self.update()
        elif self.drag_mode == "HIGH":
            f = self.x_to_freq(x)
            self.cut_high = max(f, self.cut_low + 10.0)
            self.region_changed.emit(self.cut_low, self.cut_high, self.feather_hz)
            self.update()
        elif self.drag_mode == "PAN":
            dx = x - self.drag_start_x
            f_low = self.x_to_freq(self.freq_to_x(self.drag_orig_low) + dx)
            f_high = self.x_to_freq(self.freq_to_x(self.drag_orig_high) + dx)
            if f_low >= self.min_freq and f_high <= self.max_freq:
                self.cut_low = f_low
                self.cut_high = f_high
                self.region_changed.emit(self.cut_low, self.cut_high, self.feather_hz)
                self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_mode = None
            self.drag_band_start = -1

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        top_header_h = 24
        bottom_axis_h = 22
        spec_h = h - top_header_h - bottom_axis_h

        painter.fillRect(0, 0, w, h, QColor("#080a0d"))

        # 1. 顶部频段分类标尺、悬停高光与选中状态
        painter.fillRect(0, 0, w, top_header_h, QColor("#101318"))
        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))

        for idx, (name, start_f, end_f) in enumerate(self.AUDIO_BANDS):
            bx1 = self.freq_to_x(start_f)
            bx2 = self.freq_to_x(end_f)
            rect = QRectF(bx1, 0, bx2 - bx1, top_header_h)

            is_active = (start_f >= self.cut_low - 1.0) and (end_f <= self.cut_high + 1.0)
            is_hover = (idx == self.hover_band_idx)

            # 背景渲染：选中态与悬停高光
            if is_active:
                painter.fillRect(rect, QColor("#142628"))
            elif is_hover:
                painter.fillRect(rect, QColor("#18202a"))

            # 边框分隔线
            painter.setPen(QPen(QColor("#242b35"), 1))
            painter.drawLine(int(bx1), 0, int(bx1), top_header_h)

            # 字体颜色渲染：悬停白光 / 选中青绿 / 默认暗灰
            if is_hover:
                painter.setPen(QColor("#ffffff"))
            elif is_active:
                painter.setPen(QColor("#00ffc8"))
            else:
                painter.setPen(QColor("#7d8b99"))

            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, name)

        painter.setPen(QPen(QColor("#202630"), 1))
        painter.drawLine(0, top_header_h, w, top_header_h)

        # 2. 参考网格与频率刻度
        grid_freqs = [20, 50, 100, 200, 500, 1000, 2000, 4000, 6000, 10000, 20000]
        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))

        for gf in grid_freqs:
            gx = self.freq_to_x(gf)
            painter.setPen(QPen(QColor("#151a22"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(int(gx), top_header_h, int(gx), h - bottom_axis_h)

            painter.setPen(QColor("#5c6975"))
            text = f"{gf}Hz" if gf < 1000 else f"{gf//1000}k"
            painter.drawText(int(gx) + 3, h - 6, text)

        # 3. 对数边界计算
        x1 = self.freq_to_x(self.cut_low)
        x2 = self.freq_to_x(self.cut_high)
        x1_feather = self.freq_to_x(max(self.min_freq, self.cut_low - self.feather_hz))
        x2_feather = self.freq_to_x(min(self.max_freq, self.cut_high + self.feather_hz))

        # 4. 频谱绘制（Alpha Mask 渐变衰减混合）
        if self.spectrum_data is not None and self.freq_bins is not None:
            num_steps = max(200, int(w))
            xs = np.linspace(0, w, num_steps)
            target_freqs = 10 ** (math.log10(self.min_freq) + (xs / w) * (math.log10(self.max_freq) - math.log10(self.min_freq)))
            interp_db = np.interp(target_freqs, self.freq_bins, self.spectrum_data)

            points = []
            for x_val, db_val in zip(xs, interp_db):
                norm_y = np.clip((db_val + 85.0) / 85.0, 0.0, 1.0)
                py = top_header_h + (1.0 - norm_y) * spec_h
                points.append(QPointF(x_val, py))

            if len(points) > 1:
                poly = [QPointF(0, top_header_h + spec_h)] + points + [QPointF(w, top_header_h + spec_h)]

                # A. 深灰基底
                painter.save()
                painter.setBrush(QBrush(QColor("#161a20")))
                painter.setPen(QPen(QColor("#2b323c"), 1.0))
                painter.drawPolygon(poly)
                painter.restore()

                # B. 离屏彩色热图层与羽化渐变蒙版
                color_layer = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
                color_layer.fill(Qt.GlobalColor.transparent)

                cl_painter = QPainter(color_layer)
                cl_painter.setRenderHint(QPainter.RenderHint.Antialiasing)

                poly_grad = QLinearGradient(0, top_header_h, 0, top_header_h + spec_h)
                poly_grad.setColorAt(0.0, QColor(255, 60, 0, 220))
                poly_grad.setColorAt(0.3, QColor(255, 170, 0, 160))
                poly_grad.setColorAt(0.7, QColor(0, 255, 180, 90))
                poly_grad.setColorAt(1.0, QColor(0, 30, 40, 0))

                cl_painter.setBrush(QBrush(poly_grad))
                cl_painter.setPen(QPen(QColor("#00ffd0"), 1.2))
                cl_painter.drawPolygon(poly)

                cl_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)

                mask_grad = QLinearGradient(0, 0, w, 0)
                p_left_start = max(0.0, min(1.0, x1_feather / w))
                p_left_end = max(0.0, min(1.0, x1 / w))
                p_right_start = max(0.0, min(1.0, x2 / w))
                p_right_end = max(0.0, min(1.0, x2_feather / w))

                mask_grad.setColorAt(0.0, QColor(0, 0, 0, 0))
                if p_left_start > 0.0:
                    mask_grad.setColorAt(p_left_start, QColor(0, 0, 0, 0))

                if p_left_end > p_left_start:
                    mask_grad.setColorAt(p_left_end, QColor(0, 0, 0, 255))
                else:
                    mask_grad.setColorAt(p_left_start, QColor(0, 0, 0, 255))

                if p_right_start > p_left_end:
                    mask_grad.setColorAt(p_right_start, QColor(0, 0, 0, 255))

                if p_right_end > p_right_start:
                    mask_grad.setColorAt(p_right_end, QColor(0, 0, 0, 0))
                else:
                    mask_grad.setColorAt(p_right_start, QColor(0, 0, 0, 0))

                mask_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

                cl_painter.fillRect(0, 0, w, h, QBrush(mask_grad))
                cl_painter.end()

                painter.drawImage(0, 0, color_layer)

        # 5. 通带与羽化遮罩提示
        painter.fillRect(QRectF(x1, top_header_h, max(0.0, x2 - x1), spec_h), QColor(0, 255, 180, 20))

        if x1 > x1_feather:
            grad_l = QLinearGradient(x1_feather, 0, x1, 0)
            grad_l.setColorAt(0.0, QColor(0, 255, 180, 0))
            grad_l.setColorAt(1.0, QColor(0, 255, 180, 20))
            painter.fillRect(QRectF(x1_feather, top_header_h, x1 - x1_feather, spec_h), QBrush(grad_l))

        if x2_feather > x2:
            grad_r = QLinearGradient(x2, 0, x2_feather, 0)
            grad_r.setColorAt(0.0, QColor(0, 255, 180, 20))
            grad_r.setColorAt(1.0, QColor(0, 255, 180, 0))
            painter.fillRect(QRectF(x2, top_header_h, x2_feather - x2, spec_h), QBrush(grad_r))

        # 6. 游标线与标注
        painter.setPen(QPen(QColor("#00ffc8"), 1.8))
        painter.drawLine(int(x1), top_header_h, int(x1), top_header_h + spec_h)
        painter.drawLine(int(x2), top_header_h, int(x2), top_header_h + spec_h)

        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        low_str = f"{int(self.cut_low)}Hz"
        high_str = f"{int(self.cut_high)}Hz"

        painter.fillRect(QRectF(x1 + 3, top_header_h + 4, 52, 16), QColor("#091014"))
        painter.setPen(QColor("#00ffc8"))
        painter.drawText(QRectF(x1 + 3, top_header_h + 4, 52, 16), Qt.AlignmentFlag.AlignCenter, low_str)

        painter.fillRect(QRectF(x2 - 55, top_header_h + 4, 52, 16), QColor("#091014"))
        painter.setPen(QColor("#00ffc8"))
        painter.drawText(QRectF(x2 - 55, top_header_h + 4, 52, 16), Qt.AlignmentFlag.AlignCenter, high_str)


class TimelineBar(QWidget):
    seek_requested = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.setFixedHeight(18)
        self.progress = 0.0
        self.is_dragging = False

    def update_progress(self, val):
        if not self.is_dragging:
            self.progress = val
            self.update()

    def _calc_ratio(self, x):
        return max(0.0, min(1.0, x / max(1.0, self.width())))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.progress = self._calc_ratio(event.position().x())
            self.seek_requested.emit(self.progress)
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            self.progress = self._calc_ratio(event.position().x())
            self.seek_requested.emit(self.progress)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.progress = self._calc_ratio(event.position().x())
            self.seek_requested.emit(self.progress)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        painter.fillRect(0, 0, w, h, QColor("#11151c"))
        fill_color = QColor("#00b386") if self.is_dragging else QColor("#008a66")
        painter.fillRect(0, 0, int(w * self.progress), h, fill_color)

        cx = int(w * self.progress)
        painter.setPen(QPen(QColor("#00ffc8"), 2))
        painter.drawLine(cx, 0, cx, h)

        painter.setBrush(QBrush(QColor("#ffffff" if self.is_dragging else "#00ffc8")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(QRectF(cx - 2, 0, 4, h))


class TimelineWidget(QWidget):
    seek_requested = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.setFixedHeight(24)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.bar = TimelineBar()
        self.bar.seek_requested.connect(self.seek_requested)
        layout.addWidget(self.bar, stretch=1)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        self.time_label.setStyleSheet("color: #485260;")
        self.time_label.setFixedWidth(95)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.time_label)

    def update_time(self, ratio, cur_sec, total_sec):
        self.bar.update_progress(ratio)
        c_m, c_s = divmod(int(cur_sec), 60)
        t_m, t_s = divmod(int(total_sec), 60)
        self.time_label.setText(f"{c_m:02d}:{c_s:02d} / {t_m:02d}:{t_s:02d}")


class DropZone(QWidget):
    file_dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            fpath = url.toLocalFile()
            if fpath.lower().endswith(('.wav', '.mp3', '.flac', '.aiff', '.ogg')):
                self.file_dropped.emit(fpath)
                break

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#080a0d"))
        painter.setPen(QPen(QColor("#242c35"), 1.5, Qt.PenStyle.DashLine))
        painter.drawRoundedRect(QRectF(20, 20, self.width() - 40, self.height() - 40), 6, 6)

        painter.setPen(QColor("#7d8b99"))
        painter.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "DROP AUDIO FILE HERE\n[ MP3 / WAV / FLAC / AIFF ]")
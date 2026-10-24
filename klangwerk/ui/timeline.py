import math
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget
from klangwerk.model import RATE


class Timeline(QWidget):
    seek = Signal(int)
    selected = Signal(str, str)
    move_clip = Signal(str, str, int)
    range_changed = Signal(int, int)
    ROW = 104
    HEADER = 30

    def __init__(self, project, assets):
        super().__init__()
        self.project, self.assets = project, assets
        self.scale = 80.  # Pixel pro Sekunde
        self.position = 0
        self.selection = ("", "")
        self.region = None
        self.drag = None
        self.preview = None
        self.range_anchor = None
        self._waves = {}
        self.resize_content()
        self.setToolTip("Lineal: Abspielposition · Clip ziehen: verschieben · Umschalt+Ziehen: Bereich markieren")

    def resize_content(self):
        seconds = max(30, self.project.end / RATE + 8)
        self.setFixedSize(max(1000, int(seconds * self.scale)), max(360, self.HEADER + len(self.project.tracks) * self.ROW))
        self.update()

    def frame(self, x):
        return max(0, round(x / self.scale * RATE))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor("#141b29"))
        left, right = event.rect().left(), event.rect().right()
        step = max(1, math.ceil(65 / self.scale))
        for sec in range(max(0, int(left / self.scale) // step * step), int(right / self.scale) + step, step):
            x = sec * self.scale
            painter.setPen(QColor("#293347"))
            painter.drawLine(int(x), 0, int(x), self.height())
            painter.setPen(QColor("#b5c1d5"))
            painter.drawText(int(x + 4), 20, f"{sec // 60}:{sec % 60:02d}")
        for row, track in enumerate(self.project.tracks):
            top = self.HEADER + row * self.ROW
            painter.setPen(QColor("#354055"))
            painter.drawLine(left, top, right, top)
            for clip in track.clips:
                start = self.preview if self.drag and self.drag[1] == clip.id and self.preview is not None else clip.start
                rect = QRectF(start / RATE * self.scale, top + 5, max(2, clip.length / RATE * self.scale), self.ROW - 10)
                if not rect.intersects(QRectF(event.rect())):
                    continue
                selected = self.selection == (track.id, clip.id)
                painter.setPen(QPen(QColor("#efce82" if selected else "#477b90"), 2 if selected else 1))
                painter.setBrush(QColor("#254c60" if track.reference else "#28443f"))
                painter.drawRoundedRect(rect, 5, 5)
                visible_left = max(rect.left(), left)
                visible_right = min(rect.right(), right)
                pixel_start = int(visible_left)
                width = max(1, int(visible_right) - pixel_start)
                a = clip.offset + max(0, self.frame(visible_left - rect.left()))
                length = min(clip.offset + clip.length - a, self.frame(visible_right - visible_left))
                key = (clip.asset, a, length, width)
                if key not in self._waves:
                    if len(self._waves) > 150:
                        self._waves.clear()
                    self._waves[key] = self.assets.waveform(clip.asset, a, max(1, length), width)
                painter.setPen(QColor("#71cfb8" if not track.reference else "#77b8e5"))
                center = top + 60
                for x, (low, high) in enumerate(self._waves[key]):
                    painter.drawLine(pixel_start + x, int(center - high * 27), pixel_start + x, int(center - low * 27))
                painter.setPen(QColor("#edf5ff"))
                painter.drawText(int(visible_left + 7), top + 24, track.name)
        if self.region:
            a, b = sorted(self.region)
            painter.fillRect(QRectF(a / RATE * self.scale, self.HEADER, (b - a) / RATE * self.scale, self.height()), QColor(245, 205, 112, 40))
        painter.setPen(QPen(QColor("#f6cf83"), 2))
        x = int(self.position / RATE * self.scale)
        painter.drawLine(x, 0, x, self.height())

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        x, y = event.position().x(), event.position().y()
        if event.modifiers() & Qt.ShiftModifier:
            self.range_anchor = self.frame(x)
            self.region = (self.range_anchor, self.range_anchor)
            return
        if y < self.HEADER:
            self.seek.emit(self.frame(x))
            return
        row = int((y - self.HEADER) // self.ROW)
        if row < len(self.project.tracks):
            track = self.project.tracks[row]
            for clip in reversed(track.clips):
                if clip.start <= self.frame(x) < clip.end:
                    self.selection = (track.id, clip.id)
                    self.selected.emit(track.id, clip.id)
                    self.drag = (track.id, clip.id, self.frame(x), clip.start)
                    self.update()
                    return
        self.seek.emit(self.frame(x))

    def mouseMoveEvent(self, event):
        if self.range_anchor is not None:
            self.region = (self.range_anchor, self.frame(event.position().x()))
            self.update()
        elif self.drag:
            self.preview = max(0, self.drag[3] + self.frame(event.position().x()) - self.drag[2])
            self.update()

    def mouseReleaseEvent(self, event):
        if self.range_anchor is not None:
            self.range_anchor = None
            self.region = tuple(sorted(self.region))
            self.range_changed.emit(*self.region)
        if self.drag and self.preview is not None and self.preview != self.drag[3]:
            self.move_clip.emit(self.drag[0], self.drag[1], self.preview)
        self.drag = self.preview = None
        self.update()

    def mouseDoubleClickEvent(self, event):
        self.seek.emit(self.frame(event.position().x()))

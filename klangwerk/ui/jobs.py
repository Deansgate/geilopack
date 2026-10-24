from threading import Event
from PySide6.QtCore import QThread, Signal
from klangwerk.audio.assets import Cancelled


class Job(QThread):
    progress = Signal(int)
    result = Signal(object)
    error = Signal(str)
    cancelled = Signal()

    def __init__(self, function, parent=None):
        super().__init__(parent)
        self.function = function
        self.cancel = Event()

    def run(self):
        try:
            value = self.function(self.cancel, self.progress.emit)
            self.result.emit(value)
        except Cancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.error.emit(str(exc))

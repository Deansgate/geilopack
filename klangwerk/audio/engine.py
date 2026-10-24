from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from queue import Queue, Full
from threading import Thread
import numpy as np
import sounddevice as sd
import soundfile as sf

from klangwerk.audio.mixer import mix_block
from klangwerk.model import RATE, uid


class Engine:
    def __init__(self, assets):
        self.assets = assets
        self.stream = None
        self.position = 0
        self.record_start = 0
        self.recording = False
        self.peak = 0.
        self.overload = False
        self.warning = ""
        self._writer_error = ""
        self._queue = None
        self._writer = None
        self._record_path = None

    @property
    def active(self):
        return self.stream is not None and self.stream.active

    def start(self, project, position, *, record=False, input_device=None, output_device=None):
        if self.stream is not None:
            raise RuntimeError("Bitte zuerst die laufende Wiedergabe beenden.")
        self.project = deepcopy(project)
        self.position = position
        self.record_start = position
        self.recording = record
        self.warning = self._writer_error = ""
        self.overload = False
        self._record_path = None
        if record:
            self._record_path = self.assets.directory / f"aufnahme-{uid()}.wav"
            self._queue = Queue(maxsize=256)
            # Datei synchron öffnen: Datenträgerfehler vor Aufnahmebeginn melden.
            file = sf.SoundFile(self._record_path, mode="w", samplerate=RATE, channels=1, subtype="FLOAT")
            self._writer = Thread(target=self._write, args=(file,), daemon=True)
            self._writer.start()
        try:
            if record:
                self.stream = sd.Stream(samplerate=RATE, blocksize=1024, dtype="float32",
                                        channels=(1, 2), device=(input_device, output_device),
                                        callback=self._duplex)
            else:
                self.stream = sd.OutputStream(samplerate=RATE, blocksize=1024, dtype="float32",
                                              channels=2, device=output_device, callback=self._output)
            self.stream.start()
        except BaseException:
            self.stop()
            raise

    def _write(self, file):
        try:
            with file:
                while True:
                    block = self._queue.get()
                    if block is None:
                        break
                    file.write(block)
                    file.flush()  # Bereits erfasste Takes bei Programmfehlern erhalten.
        except Exception as exc:
            self._writer_error = f"Aufnahme konnte nicht weiter gespeichert werden: {exc}"

    def _render(self, outdata, frames, status):
        if status:
            self.warning = "Audioaussetzer erkannt. Größeren Geräte-Puffer verwenden oder andere Programme schließen."
        outdata[:] = mix_block(self.project, self.assets, self.position, frames)
        if np.max(np.abs(outdata), initial=0) > 1:
            self.overload = True
        np.clip(outdata, -1, 1, out=outdata)  # Geräteschutz; Übersteuerung wird angezeigt.
        self.position += frames

    def _output(self, outdata, frames, time, status):
        self._render(outdata, frames, status)
        if self.position >= self.project.end:
            raise sd.CallbackStop

    def _duplex(self, indata, outdata, frames, time, status):
        self._render(outdata, frames, status)
        self.peak = float(np.max(np.abs(indata), initial=0))
        if self._writer_error:
            self.warning = self._writer_error
            raise sd.CallbackStop
        try:
            self._queue.put_nowait(indata.copy())
        except Full:
            self.warning = "Aufnahme gestoppt: SSD konnte nicht schnell genug schreiben. Der bisherige Take bleibt erhalten."
            raise sd.CallbackStop

    def stop(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if self._writer is not None:
            # Beim Schreibfehler kann die Queue voll sein; der Thread ist bereits beendet.
            while self._writer.is_alive():
                try:
                    self._queue.put(None, timeout=.1)
                    break
                except Full:
                    continue
            self._writer.join()
            self._writer = None
        self.recording = False
        if self._writer_error:
            self.warning = self._writer_error
        path, self._record_path = self._record_path, None
        return path

    @staticmethod
    def devices():
        return list(enumerate(sd.query_devices()))

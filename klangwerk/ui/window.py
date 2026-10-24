from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QScrollArea, QTableWidget, QTableWidgetItem,
    QSlider, QCheckBox, QComboBox, QProgressBar, QSplitter, QAbstractItemView,
)

from klangwerk.model import Project, Clip, Track, History, RATE, split_clip
from klangwerk.audio.assets import Assets
from klangwerk.audio.engine import Engine
from klangwerk.audio.export import export_wav
from klangwerk.project import save_project, load_project
from klangwerk.hardware import detect
from klangwerk.ui.jobs import Job
from klangwerk.ui.timeline import Timeline
from klangwerk.ai.models import MODEL_FILE, download_model
from klangwerk.ai.separation import runtime_available, separate_clip


class Window(QMainWindow):
    def __init__(self, data_directory):
        super().__init__()
        self.directory = Path(data_directory)
        self.assets = Assets(self.directory / "cache")
        self.project = Project()
        self.engine = Engine(self.assets)
        self.history = History()
        self.path = None
        self.dirty = False
        self.job = None
        self.selected = ("", "")
        self.clipboard = None
        self._take_start = 0
        self._rebuild = False
        self.setWindowTitle("Klangwerk · Lokales Musikstudio 0.2")
        self.resize(1280, 850)
        self._build()
        self._menus()
        self.refresh()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(50)
        self.autosave = QTimer(self)
        self.autosave.timeout.connect(self.backup)
        self.autosave.start(120000)
        QTimer.singleShot(100, self.first_start)

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        heading = QLabel("KLANGWERK   /   Dein lokales Musikstudio")
        heading.setStyleSheet("font-size: 23px; font-weight: 700; padding: 12px")
        layout.addWidget(heading)
        transport = QHBoxLayout()
        self.import_button = self.button("Audio importieren", self.import_audio, transport)
        self.play_button = self.button("▶ Wiedergabe", self.play, transport)
        self.stop_button = self.button("■ Stoppen", self.stop, transport)
        self.record_button = self.button("● Aufnahme", self.record, transport)
        self.clock = QLabel("00:00.000")
        transport.addWidget(self.clock)
        self.button("−", lambda: self.zoom(.75), transport)
        self.button("+", lambda: self.zoom(1.33), transport)
        layout.addLayout(transport)
        devices = QHBoxLayout()
        devices.addWidget(QLabel("Mikrofon:"))
        self.inputs = QComboBox()
        devices.addWidget(self.inputs, 1)
        devices.addWidget(QLabel("Ausgabe:"))
        self.outputs = QComboBox()
        devices.addWidget(self.outputs, 1)
        self.button("Geräte neu suchen", self.scan_devices, devices)
        devices.addWidget(QLabel("Eingang"))
        self.meter = QProgressBar()
        self.meter.setRange(0, 100)
        self.meter.setMaximumWidth(120)
        devices.addWidget(self.meter)
        layout.addLayout(devices)
        hint = QLabel("Kopfhörer verwenden: Begleitmusik und Referenz dürfen nicht über Lautsprecher ins Mikrofon gelangen.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        splitter = QSplitter(Qt.Vertical)
        self.timeline = Timeline(self.project, self.assets)
        self.timeline.seek.connect(self.seek)
        self.timeline.selected.connect(self.select)
        self.timeline.move_clip.connect(self.move)
        self.timeline.range_changed.connect(lambda a, b: self.statusBar().showMessage(f"Bereich: {a / RATE:.2f}–{b / RATE:.2f} s"))
        scroll = QScrollArea()
        scroll.setWidget(self.timeline)
        splitter.addWidget(scroll)
        self.mixer = QTableWidget(0, 7)
        self.mixer.setHorizontalHeaderLabels(["Spur", "Lautstärke", "Panorama", "Stumm", "Solo", "Referenz¹", "Spur wählen"])
        self.mixer.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.mixer.verticalHeader().hide()
        self.mixer.horizontalHeader().setStretchLastSection(True)
        splitter.addWidget(self.mixer)
        splitter.setSizes([400, 200])
        layout.addWidget(splitter, 1)
        foot = QHBoxLayout()
        foot.addWidget(QLabel("¹ Referenzspuren werden beim Export ausgeschlossen.   Master:"))
        self.master = QSlider(Qt.Horizontal)
        self.master.setRange(0, 100)
        self.master.setValue(80)
        self.master.valueChanged.connect(self.master_changed)
        foot.addWidget(self.master)
        layout.addLayout(foot)
        ai = QHBoxLayout()
        self.setup_ai_button = self.button("KI-Modell einrichten …", self.setup_ai, ai)
        self.separate_button = self.button("Gewählten Clip in Gesang / Instrumental trennen", self.separate, ai)
        layout.addLayout(ai)
        planned = QLabel("Lokale CPU-Gesangstrennung · weiterhin geplant: Tonhöhen-/Timingkorrektur, Vorlagen-Effekte und automatisches Mixing")
        planned.setWordWrap(True)
        layout.addWidget(planned)
        progress = QHBoxLayout()
        self.progress_label = QLabel("")
        self.progress = QProgressBar()
        self.progress.hide()
        self.cancel_button = QPushButton("Abbrechen")
        self.cancel_button.clicked.connect(lambda: self.job.cancel.set() if self.job else None)
        self.cancel_button.hide()
        progress.addWidget(self.progress_label)
        progress.addWidget(self.progress, 1)
        progress.addWidget(self.cancel_button)
        layout.addLayout(progress)
        self.scan_devices()

    @staticmethod
    def button(text, function, layout):
        button = QPushButton(text)
        button.clicked.connect(function)
        layout.addWidget(button)
        return button

    def action(self, menu, name, function, shortcut=None):
        action = QAction(name, self)
        action.triggered.connect(function)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        menu.addAction(action)
        return action

    def _menus(self):
        file = self.menuBar().addMenu("Datei")
        self.action(file, "Neues Projekt", self.new, "Ctrl+N")
        self.action(file, "Projekt öffnen …", self.open, "Ctrl+O")
        self.action(file, "Projekt speichern", self.save, "Ctrl+S")
        self.action(file, "Projekt speichern unter …", lambda: self.save(force=True), "Ctrl+Shift+S")
        self.action(file, "Audio importieren …", self.import_audio, "Ctrl+I")
        self.action(file, "Song als WAV exportieren …", self.export)
        self.action(file, "Markierten Bereich exportieren …", lambda: self.export(region=True))
        self.action(file, "Gewählte Spur exportieren …", lambda: self.export(single=True))
        self.action(file, "Letzte automatische Sicherung öffnen", self.recover)
        self.action(file, "Beenden", self.close)
        edit = self.menuBar().addMenu("Bearbeiten")
        self.action(edit, "Rückgängig", self.undo, "Ctrl+Z")
        self.action(edit, "Wiederholen", self.redo, "Ctrl+Y")
        self.action(edit, "Clip an Abspielposition teilen", self.split, "S")
        self.action(edit, "Clip kopieren", self.copy, "Ctrl+C")
        self.action(edit, "Clip an Abspielposition einfügen", self.paste, "Ctrl+V")
        self.action(edit, "Gewählten Clip löschen", self.delete, "Delete")
        self.action(edit, "Gewählte Spur löschen", self.delete_track)
        self.action(edit, "Bereichsmarkierung aufheben", self.clear_range, "Escape")
        ai = self.menuBar().addMenu("KI-Produzent")
        self.action(ai, "Modell einrichten …", self.setup_ai)
        self.action(ai, "Gewählten Clip in Gesang und Instrumental trennen", self.separate)
        help_menu = self.menuBar().addMenu("Hilfe")
        self.action(help_menu, "Hardware und Speicher", lambda: QMessageBox.information(self, "Lokale Verarbeitung", detect(self.directory)))
        self.action(help_menu, "Bedienung und Entwicklungsstand", self.help)

    def idle(self):
        if self.job or self.engine.stream is not None:
            self.statusBar().showMessage("Bitte zuerst Wiedergabe/Aufnahme oder die laufende Verarbeitung beenden.")
            return False
        return True

    def checkpoint(self):
        self.history.push(self.project)
        self.dirty = True

    def refresh(self):
        self._rebuild = True
        self.timeline.project = self.project
        self.timeline.selection = self.selected
        self.timeline.resize_content()
        self.mixer.setRowCount(len(self.project.tracks))
        for row, track in enumerate(self.project.tracks):
            self.mixer.setItem(row, 0, QTableWidgetItem(track.name))
            for col, field, low, high, value in [(1, "gain", 0, 200, round(track.gain * 100)),
                                                 (2, "pan", -100, 100, round(track.pan * 100))]:
                slider = QSlider(Qt.Horizontal)
                slider.setRange(low, high)
                slider.setValue(value)
                slider.setToolTip(f"{value}%")
                slider.valueChanged.connect(lambda v, t=track, f=field, s=slider: self.set_track(t, f, v / 100, s))
                self.mixer.setCellWidget(row, col, slider)
            for col, field in [(3, "mute"), (4, "solo"), (5, "reference")]:
                box = QCheckBox()
                box.setChecked(getattr(track, field))
                box.toggled.connect(lambda v, t=track, f=field: self.toggle_track(t, f, v))
                self.mixer.setCellWidget(row, col, box)
            button = QPushButton("Auswählen")
            button.clicked.connect(lambda checked=False, t=track: self.select(t.id, t.clips[0].id if t.clips else ""))
            self.mixer.setCellWidget(row, 6, button)
        self.mixer.setColumnWidth(0, 210)
        self.mixer.setColumnWidth(1, 190)
        self.mixer.setColumnWidth(2, 150)
        self.master.setValue(round(self.project.master * 100))
        self._rebuild = False
        self.setWindowTitle(f"{'* ' if self.dirty else ''}{self.project.name} · Klangwerk 0.2")

    def set_track(self, track, field, value, slider):
        self.checkpoint()
        setattr(track, field, value)
        slider.setToolTip(f"{value * 100:.0f}%")
        self.dirty = True
        if self.engine.stream is not None:
            self.engine.project = deepcopy(self.project)

    def toggle_track(self, track, field, value):
        self.checkpoint()
        setattr(track, field, value)
        if self.engine.stream is not None:
            self.engine.project = deepcopy(self.project)
        self.timeline.update()

    def master_changed(self, value):
        if self._rebuild:
            return
        self.checkpoint()
        self.project.master = value / 100
        self.dirty = True
        if self.engine.stream is not None:
            self.engine.project = deepcopy(self.project)

    def select(self, track_id, clip_id):
        self.selected = (track_id, clip_id)
        self.timeline.selection = self.selected
        self.timeline.update()

    def chosen(self):
        for track in self.project.tracks:
            if track.id == self.selected[0]:
                return track, next((c for c in track.clips if c.id == self.selected[1]), None)
        return None, None

    def run_job(self, label, function, result=lambda value: None, *, cancellable=True):
        if self.job:
            return
        self.progress_label.setText(label)
        self.progress.setValue(0)
        self.progress.show()
        self.cancel_button.setVisible(cancellable)
        # Verarbeitung nur über Abbrechen bedienbar; verhindert konkurrierende Änderungen.
        for widget in (self.timeline, self.mixer, self.master, self.import_button, self.play_button,
                       self.record_button, self.stop_button, self.inputs, self.outputs,
                       self.setup_ai_button, self.separate_button):
            widget.setEnabled(False)
        self.menuBar().setEnabled(False)
        job = Job(function, self)
        self.job = job
        job.progress.connect(self.progress.setValue)
        job.result.connect(result)
        job.error.connect(self.error)
        job.cancelled.connect(lambda: self.statusBar().showMessage("Verarbeitung abgebrochen; das Original bleibt erhalten."))
        job.finished.connect(self.job_finished)
        job.start()

    def job_finished(self):
        old = self.job
        self.job = None
        if old:
            old.deleteLater()
        self.progress.hide()
        self.cancel_button.hide()
        self.progress_label.setText("")
        for widget in (self.timeline, self.mixer, self.master, self.import_button, self.play_button,
                       self.record_button, self.stop_button, self.inputs, self.outputs,
                       self.setup_ai_button, self.separate_button):
            widget.setEnabled(True)
        self.menuBar().setEnabled(True)
        self.refresh()

    def error(self, message):
        QMessageBox.warning(self, "Klangwerk – Vorgang nicht abgeschlossen", message)

    def setup_ai(self):
        if not self.idle():
            return
        if not runtime_available():
            self.error("Die KI-Laufzeit fehlt in dieser Ausgabe. Der Windows-Build muss mit CPU-KI erstellt werden. Die Basisfunktionen bleiben verfügbar.")
            return
        answer = QMessageBox.question(self, "Lokales KI-Modell einrichten",
            "Demucs HTDemucs trennt Gesang und Instrumental auf der CPU.\n\n"
            "Einmaliger Download: etwa 84 MB von dl.fbaipublicfiles.com (Meta). "
            "Modell und Demucs stehen unter MIT; Lizenzhinweise liegen der Anwendung bei.\n\n"
            "Es werden keine Audiodateien oder Projekte übertragen. Nach der Einrichtung "
            "funktioniert die Trennung offline. CPU-Berechnungen können deutlich länger als der Song dauern.\n\n"
            "Modell jetzt herunterladen und prüfen?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        self.run_job("Trennungsmodell wird heruntergeladen und geprüft …",
            lambda c, p: download_model(self.directory / "models", c, p),
            lambda path: self.statusBar().showMessage("KI-Modell geprüft und lokal gespeichert. Einen Song-Clip auswählen und die Trennung starten."))

    def separate(self):
        if not self.idle():
            return
        track, clip = self.chosen()
        if clip is None:
            self.error("Bitte zuerst den zu trennenden Song-Clip in der Timeline auswählen.")
            return
        if not (self.directory / "models" / MODEL_FILE).exists():
            self.error("Bitte zuerst über „KI-Modell einrichten“ das lokale Trennungsmodell herunterladen.")
            return
        original_track_id = track.id
        original_solo = track.solo
        snapshot = deepcopy(clip)
        name = track.name
        def done(keys):
            self.checkpoint()
            backing, voice = keys
            instrumental = Track(name + " · Instrumental", [Clip(backing, snapshot.start, 0, snapshot.length)], solo=original_solo)
            reference = Track(name + " · Referenzgesang", [Clip(voice, snapshot.start, 0, snapshot.length)],
                              reference=True, gain=.5, solo=original_solo)
            # Original bleibt samt Clips erhalten; Stummschaltung vermeidet doppelte Wiedergabe.
            for old in self.project.tracks:
                if old.id == original_track_id:
                    old.mute = True
                    old.solo = False
            self.project.tracks.extend((instrumental, reference))
            self.select(instrumental.id, instrumental.clips[0].id)
            self.statusBar().showMessage("Trennung fertig. Originalspur stummgeschaltet und unverändert erhalten; Referenzgesang vom Export ausgeschlossen.")
        self.run_job("Lokale CPU-Trennung · längere Rechenschritte können den Fortschritt vorübergehend anhalten …",
            lambda c, p: separate_clip(self.assets, snapshot, self.directory / "models" / MODEL_FILE, c, p), done)

    def import_audio(self):
        if not self.idle():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Audio importieren", "", "Audio (*.wav *.mp3 *.flac *.ogg);;Alle Dateien (*)")
        if not path:
            return
        def done(asset_id):
            self.checkpoint()
            track = Track(Path(path).stem, [Clip(asset_id, 0, 0, len(self.assets.data[asset_id]))])
            self.project.tracks.append(track)
            self.select(track.id, track.clips[0].id)
        self.run_job("Audio wird lokal eingelesen …", lambda c, p: self.assets.import_file(path, c, p), done)

    def scan_devices(self):
        if self.job or self.engine.stream is not None:
            return
        self.inputs.clear()
        self.outputs.clear()
        self.inputs.addItem("Systemstandard", None)
        self.outputs.addItem("Systemstandard", None)
        try:
            for index, device in self.engine.devices():
                if device["max_input_channels"]:
                    self.inputs.addItem(device["name"], index)
                if device["max_output_channels"] >= 2:
                    self.outputs.addItem(device["name"], index)
        except Exception as exc:
            self.statusBar().showMessage(f"Audiogeräte konnten nicht gelesen werden: {exc}")

    def play(self):
        if not self.idle() or not self.project.end:
            return
        try:
            if self.timeline.position >= self.project.end:
                self.timeline.position = 0
            self.engine.start(self.project, self.timeline.position, output_device=self.outputs.currentData())
        except Exception as exc:
            self.error(f"Wiedergabe nicht möglich. Bitte ein Stereo-Ausgabegerät mit 48 kHz auswählen.\n{exc}")

    def record(self):
        if not self.idle():
            return
        self._take_start = self.timeline.position
        try:
            self.engine.start(self.project, self._take_start, record=True,
                              input_device=self.inputs.currentData(), output_device=self.outputs.currentData())
            self.statusBar().showMessage("Aufnahme läuft · Mikrofon wird separat gespeichert · Stoppen beendet den Take.")
        except Exception as exc:
            self.error(f"Aufnahme nicht möglich. Windows-Mikrofonfreigabe und Geräte mit 48 kHz prüfen.\n{exc}")

    def stop(self):
        if self.job or self.engine.stream is None:
            return
        def finish(cancel, progress):
            path = self.engine.stop()
            if path and path.exists():
                import soundfile as sf
                if sf.info(path).frames:
                    # Take-Übernahme ist nicht abbrechbar: gesicherte Aufnahme behalten.
                    return self.assets.import_file(str(path), cancel, progress)
            return None
        def done(asset_id):
            if asset_id:
                self.checkpoint()
                take = sum(t.name.startswith("Gesang Take") for t in self.project.tracks) + 1
                track = Track(f"Gesang Take {take}", [Clip(asset_id, self._take_start, 0, len(self.assets.data[asset_id]))])
                self.project.tracks.append(track)
                self.select(track.id, track.clips[0].id)
            if self.engine.warning:
                self.error(self.engine.warning)
        self.run_job("Audio wird beendet und der Take gesichert …", finish, done, cancellable=False)

    def tick(self):
        if self.engine.stream is not None and not self.job:
            self.timeline.position = self.engine.position
            self.meter.setValue(min(100, round(self.engine.peak * 100)))
            self.timeline.update()
            if self.engine.overload:
                self.statusBar().showMessage("Übersteuerung in der Wiedergabe: Spur- oder Masterlautstärke reduzieren.")
            if not self.engine.active:
                self.stop()
        seconds = self.timeline.position / RATE
        self.clock.setText(f"{int(seconds // 60):02d}:{seconds % 60:06.3f}")

    def seek(self, position):
        if not self.idle():
            return
        self.timeline.position = position
        self.timeline.update()

    def zoom(self, factor):
        self.timeline.scale = min(800, max(5, self.timeline.scale * factor))
        self.timeline.resize_content()

    def move(self, track_id, clip_id, start):
        if not self.idle():
            return
        for track in self.project.tracks:
            for clip in track.clips:
                if track.id == track_id and clip.id == clip_id:
                    self.checkpoint()
                    clip.start = start
                    self.refresh()
                    return

    def split(self):
        if not self.idle():
            return
        track, clip = self.chosen()
        if clip and clip.start < self.timeline.position < clip.end:
            self.checkpoint()
            split_clip(track, clip.id, self.timeline.position)
            self.refresh()
        else:
            self.statusBar().showMessage("Clip auswählen und Abspielposition innerhalb des Clips setzen.")

    def copy(self):
        _, clip = self.chosen()
        if clip:
            self.clipboard = deepcopy(clip)

    def paste(self):
        if not self.idle() or not self.clipboard:
            return
        track, _ = self.chosen()
        if track:
            self.checkpoint()
            c = self.clipboard
            clip = Clip(c.asset, self.timeline.position, c.offset, c.length)
            track.clips.append(clip)
            self.select(track.id, clip.id)
            self.refresh()

    def delete(self):
        if not self.idle():
            return
        track, clip = self.chosen()
        if clip:
            self.checkpoint()
            track.clips.remove(clip)
            self.refresh()

    def delete_track(self):
        if not self.idle():
            return
        track, _ = self.chosen()
        if track:
            self.checkpoint()
            self.project.tracks.remove(track)
            self.refresh()

    def clear_range(self):
        self.timeline.region = None
        self.timeline.update()

    def undo(self):
        if self.idle():
            self.project = self.history.undo(self.project)
            self.dirty = True
            self.refresh()

    def redo(self):
        if self.idle():
            self.project = self.history.redo(self.project)
            self.dirty = True
            self.refresh()

    def discard_ok(self):
        if not self.dirty:
            return True
        return QMessageBox.question(self, "Ungespeicherte Änderungen", "Änderungen verwerfen? Zum Speichern bitte Abbrechen wählen und anschließend Strg+S verwenden.",
                                    QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Cancel) == QMessageBox.Discard

    def new(self):
        if self.idle() and self.discard_ok():
            self.project = Project()
            self.path = None
            self.history = History()
            self.dirty = False
            self.timeline.position = 0
            self.timeline.region = None
            self.refresh()

    def open(self, checked=False, path=None):
        if not self.idle() or not self.discard_ok():
            return
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Projekt öffnen", "", "Klangwerk (*.klang *.bak)")
        if not path:
            return
        def done(project):
            self.project = project
            self.path = Path(path)
            self.dirty = False
            self.history = History()
            self.timeline.position = 0
            self.timeline.region = None
        self.run_job("Projekt wird geöffnet …", lambda c, p: load_project(Path(path), self.assets, c, p), done)

    def save(self, checked=False, force=False):
        if not self.idle():
            return
        path = self.path
        if path is None or force:
            name, _ = QFileDialog.getSaveFileName(self, "Projekt speichern", str(path or "Mein Song.klang"), "Klangwerk (*.klang)")
            if not name:
                return
            path = Path(name)
            if path.suffix != ".klang":
                path = path.with_suffix(".klang")
        snapshot = deepcopy(self.project)
        snapshot.name = path.stem
        def done(value):
            self.path = path
            self.project.name = snapshot.name
            self.dirty = False
            self.statusBar().showMessage("Projekt und zugehörige Audiodateien gespeichert.")
        self.run_job("Projekt wird gespeichert …", lambda c, p: save_project(path, snapshot, self.assets, c, p), done)

    def backup(self):
        if self.job or self.engine.stream is not None or not self.dirty:
            return
        snapshot = deepcopy(self.project)
        self.run_job("Automatische Sicherung …", lambda c, p: save_project(self.directory / "Wiederherstellung.klang", snapshot, self.assets, c, p))

    def recover(self):
        path = self.directory / "Wiederherstellung.klang"
        if path.exists():
            self.open(path=path)
        else:
            self.statusBar().showMessage("Noch keine automatische Sicherung vorhanden.")

    def first_start(self):
        recovery = self.directory / "Wiederherstellung.klang"
        if recovery.exists():
            answer = QMessageBox.question(self, "Wiederherstellung", "Die letzte automatische Sicherung öffnen?")
            if answer == QMessageBox.Yes:
                self.recover()
        marker = self.directory / "erster-start.txt"
        if not marker.exists():
            QMessageBox.information(self, "Willkommen bei Klangwerk", "Alle Audiodaten bleiben lokal.\n\n" + detect(self.directory) +
                                    "\n\nAufnahme, Timeline, WAV-Export und lokale Gesangstrennung.\nBedienung: Hilfe → Bedienung und Entwicklungsstand.")
            marker.write_text("0.2", encoding="utf-8")

    def export(self, checked=False, region=False, single=False):
        if not self.idle():
            return
        start, end = 0, self.project.end
        track_id = None
        if region:
            if not self.timeline.region or self.timeline.region[0] == self.timeline.region[1]:
                self.error("Mit Umschalt+Ziehen zuerst einen Bereich in der Timeline markieren.")
                return
            start, end = self.timeline.region
        if single:
            track, _ = self.chosen()
            if not track:
                self.error("Bitte zuerst eine Spur auswählen.")
                return
            if track.reference:
                self.error("Referenzspuren sind vom Export ausgeschlossen. Bei eigenen Aufnahmen kann die Referenzmarkierung entfernt werden.")
                return
            track_id = track.id
        path, _ = QFileDialog.getSaveFileName(self, "WAV exportieren · 48 kHz / 24 Bit", "Mein Song.wav", "WAV (*.wav)")
        if not path:
            return
        if not path.lower().endswith(".wav"):
            path += ".wav"
        snapshot = deepcopy(self.project)
        self.run_job("WAV wird berechnet und exportiert …",
                     lambda c, p: export_wav(path, snapshot, self.assets, c, p, start=start, end=end, track_id=track_id),
                     lambda gain: self.statusBar().showMessage(f"Export fertig. Pegel zur Clipping-Vermeidung: {gain * 100:.1f}%. Referenzspuren ausgeschlossen."))

    def help(self):
        QMessageBox.information(self, "Bedienung / Version 0.2", "Audio importieren → Mikrofon/Ausgabe wählen → Kopfhörer aufsetzen → Aufnahme.\n"
            "Stoppen sichert jeden Take auf einer neuen Spur. Kein Mikrofon-Monitoring.\n\n"
            "Lineal anklicken: Position · Clip ziehen: verschieben · S: teilen\n"
            "Strg+C / Strg+V: Clip kopieren/einfügen · Entf: Clip löschen\n"
            "Umschalt+Ziehen: Exportbereich · Strg+Z / Strg+Y: Rückgängig/Wiederholen\n"
            "Wiedergabe zum Bearbeiten und Positionieren zuerst stoppen.\n\n"
            "Projektdatei und gleichnamigen .audio-Ordner zusammen aufbewahren.\n"
            "Alle 2 Minuten wird im Leerlauf eine automatische Sicherung erstellt.\n\n"
            "Gesangstrennung: Modell einmal einrichten, Song-Clip wählen und Trennung starten. Original bleibt erhalten.\n"
            "Geplant: Korrekturen, EQ/Kompression/Hall/Delay, MP3-Export, Aufnahme-Latenzkalibrierung.\n"
            "Aufnahme kann durch Gerätelatenz versetzt sein: Take bei Bedarf verschieben.\n"
            "Echte Windows-/Mikrofontests sind vor produktivem Einsatz erforderlich.")

    def closeEvent(self, event):
        if self.job:
            event.ignore()
            self.statusBar().showMessage("Bitte den laufenden Vorgang abschließen oder abbrechen und danach schließen.")
        elif self.engine.stream is not None:
            event.ignore()
            self.stop()
            self.statusBar().showMessage("Audio wird beendet. Anschließend Projekt speichern und Fenster schließen.")
        elif not self.discard_ok():
            event.ignore()
        else:
            event.accept()

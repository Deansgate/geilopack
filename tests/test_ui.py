import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import numpy as np
import soundfile as sf
from threading import Event
from PySide6.QtWidgets import QApplication
from klangwerk.ui.window import Window
from klangwerk.model import Track, Clip, RATE
from PySide6.QtTest import QTest
import time


def test_window_imported_timeline_edit_and_render(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(Window, "first_start", lambda self: None)
    monkeypatch.setattr(Window, "scan_devices", lambda self: None)
    window = Window(tmp_path / "data")
    path = tmp_path / "take.wav"
    sf.write(path, np.sin(np.arange(10000) * .1) * .2, RATE)
    key = window.assets.import_file(str(path), Event())
    track = Track("Test-Take", [Clip(key, 0, 0, 10000)])
    window.project.tracks.append(track)
    window.select(track.id, track.clips[0].id)
    window.refresh()
    window.timeline.position = 5000
    window.split()
    assert len(track.clips) == 2
    window.undo()
    assert len(window.project.tracks[0].clips) == 1
    window.redo()
    assert len(window.project.tracks[0].clips) == 2
    window.show()
    app.processEvents()
    assert not window.grab().isNull()
    window.dirty = False
    window.close()


def test_separation_ui_preserves_original_and_sets_reference(tmp_path, monkeypatch):
    from klangwerk.ai.models import MODEL_FILE
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(Window, "first_start", lambda self: None)
    monkeypatch.setattr(Window, "scan_devices", lambda self: None)
    window = Window(tmp_path / "data")
    original = tmp_path / "song.wav"
    sf.write(original, np.ones((2000, 2)) * .1, RATE)
    key = window.assets.import_file(str(original), Event())
    track = Track("Song", [Clip(key, 321, 10, 1000)], solo=True)
    window.project.tracks.append(track)
    window.select(track.id, track.clips[0].id)
    model = window.directory / "models" / MODEL_FILE
    model.parent.mkdir()
    model.touch()
    monkeypatch.setattr("klangwerk.ui.window.separate_clip", lambda *a: (key, key))
    window.separate()
    deadline = time.monotonic() + 5
    while window.job is not None and time.monotonic() < deadline:
        app.processEvents()
        QTest.qWait(5)
    assert window.job is None
    assert len(window.project.tracks) == 3
    assert track.mute and not track.solo
    assert track.clips[0].offset == 10
    assert window.project.tracks[1].clips[0].start == 321
    assert window.project.tracks[2].reference
    window.undo()
    assert len(window.project.tracks) == 1
    assert not window.project.tracks[0].mute
    assert window.project.tracks[0].solo
    window.dirty = False
    window.close()


def test_ui_background_import_save_and_reopen(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(Window, "first_start", lambda self: None)
    monkeypatch.setattr(Window, "scan_devices", lambda self: None)
    window = Window(tmp_path / "data")
    source = tmp_path / "Gesang.wav"
    sf.write(source, np.sin(np.arange(50000) * .1) * .2, RATE)
    project = tmp_path / "Mein Song.klang"
    monkeypatch.setattr("klangwerk.ui.window.QFileDialog.getOpenFileName", lambda *a: (str(source), ""))
    monkeypatch.setattr("klangwerk.ui.window.QFileDialog.getSaveFileName", lambda *a: (str(project), ""))
    errors = []
    window.error = errors.append
    def finish():
        deadline = time.monotonic() + 5
        while window.job is not None and time.monotonic() < deadline:
            app.processEvents()
            QTest.qWait(5)
        assert window.job is None
        assert not errors
    window.import_audio()
    finish()
    assert len(window.project.tracks) == 1
    assert window.dirty
    window.save()
    finish()
    assert project.exists()
    assert window.project.name == "Mein Song"
    assert not window.dirty
    window.new()
    assert not window.project.tracks
    window.open(path=project)
    finish()
    assert len(window.project.tracks) == 1
    assert window.project.tracks[0].name == "Gesang"
    assert not window.grab().isNull()
    window.close()

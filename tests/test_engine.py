from threading import Event
import numpy as np
import soundfile as sf
from klangwerk.audio.assets import Assets
from klangwerk.audio.engine import Engine
from klangwerk.model import Project, Track, Clip, RATE


class FakeStream:
    """Gerätevertrag testen; ersetzt keinen echten Windows-Audiotest."""
    def __init__(self, **kwargs):
        self.callback = kwargs["callback"]
        self.active = False
    def start(self):
        self.active = True
    def stop(self):
        self.active = False
    def close(self):
        pass


def test_recording_contains_microphone_only_and_starts_at_cursor(tmp_path, monkeypatch):
    monkeypatch.setattr("klangwerk.audio.engine.sd.Stream", FakeStream)
    assets = Assets(tmp_path / "cache")
    path = tmp_path / "instrumental.wav"
    sf.write(path, np.ones((3000, 2), dtype="float32") * .6, RATE, subtype="FLOAT")
    key = assets.import_file(str(path), Event())
    project = Project(master=1, tracks=[Track("Instrumental", [Clip(key, 0, 0, 3000)])])
    engine = Engine(assets)
    engine.start(project, 500, record=True)
    microphone = np.ones((1024, 1), dtype="float32") * .1
    output = np.empty((1024, 2), dtype="float32")
    engine.stream.callback(microphone, output, 1024, None, None)
    recorded = engine.stop()
    data, rate = sf.read(recorded, always_2d=True)
    assert rate == RATE
    assert engine.record_start == 500
    assert engine.position == 1524
    np.testing.assert_allclose(data, microphone)
    np.testing.assert_allclose(output, .6)
    assert not engine.recording


def test_open_device_error_closes_writer_and_retains_file(tmp_path, monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("kein Gerät")
    monkeypatch.setattr("klangwerk.audio.engine.sd.Stream", fail)
    engine = Engine(Assets(tmp_path))
    import pytest
    with pytest.raises(RuntimeError):
        engine.start(Project(), 0, record=True)
    assert engine.stream is None
    assert engine._writer is None

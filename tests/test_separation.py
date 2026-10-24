from pathlib import Path
from threading import Event, Thread
import hashlib
import io
import json
import os
import socket
import sys
import time

import numpy as np
import pytest
import soundfile as sf

from klangwerk.ai import models
from klangwerk.ai.separation import separate_clip, wait_for_worker
from klangwerk.ai.worker import windows, overlap_weight, run
from klangwerk.audio.assets import Assets, Cancelled
from klangwerk.model import Clip, RATE


def test_model_download_verifies_before_replacing(tmp_path, monkeypatch):
    content = b"test model weights"
    monkeypatch.setattr(models, "MODEL_SIZE", len(content))
    monkeypatch.setattr(models, "MODEL_SHA256", hashlib.sha256(content).hexdigest())
    monkeypatch.setattr(models.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(content))
    path = models.download_model(tmp_path, Event())
    assert path.read_bytes() == content
    assert models.verify_model(path)
    # Beschädigte Übertragung darf eine bestehende Datei nicht überschreiben.
    path.write_bytes(b"alte Datei")
    monkeypatch.setattr(models.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(b"ungueltig"))
    with pytest.raises(ValueError):
        models.download_model(tmp_path, Event())
    assert path.read_bytes() == b"alte Datei"
    assert not list(tmp_path.glob("*.partial"))


def test_download_cancel_removes_partial_file(tmp_path, monkeypatch):
    cancel = Event()
    content = b"x" * (512 * 1024)
    monkeypatch.setattr(models, "MODEL_SIZE", len(content))
    monkeypatch.setattr(models.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(content))
    with pytest.raises(Cancelled):
        models.download_model(tmp_path, cancel, lambda p: cancel.set())
    assert not list(tmp_path.iterdir())


def test_cancellation_terminates_actual_subprocess(tmp_path):
    cancel = Event()
    child_script = tmp_path / "child.py"
    ready = tmp_path / "ready"
    child_script.write_text("import pathlib,time\npathlib.Path(__file__).with_name('ready').touch()\ntime.sleep(60)\n")
    def request_cancel():
        deadline = time.monotonic() + 5
        while not ready.exists() and time.monotonic() < deadline:
            cancel.wait(.01)
        cancel.set()
    requester = Thread(target=request_cancel)
    requester.start()
    started = time.monotonic()
    try:
        with pytest.raises(Cancelled):
            wait_for_worker([sys.executable, str(child_script)], tmp_path, cancel, lambda p: None)
        assert ready.exists()
        assert time.monotonic() - started < 6
    finally:
        cancel.set()
        requester.join()


def test_worker_failure_is_reported(tmp_path):
    with pytest.raises(RuntimeError, match="absichtlicher Testfehler"):
        wait_for_worker([sys.executable, "-c", "raise RuntimeError('absichtlicher Testfehler')"],
                        tmp_path, Event(), lambda p: None)


@pytest.mark.parametrize("length", [1, 159, 48001, RATE * 20, RATE * 23 + 13, RATE * 41])
def test_overlap_has_no_gaps_and_preserves_constant_signal(length):
    total = np.zeros((length, 1), dtype=np.float32)
    weights = np.zeros_like(total)
    for start, end in windows(length):
        weight = overlap_weight(end - start)
        weights[start:end] += weight
        total[start:end] += .25 * weight
    assert np.all(weights > 0)
    np.testing.assert_allclose(total / weights, .25, atol=1e-7)


def test_two_stems_are_not_committed_if_second_is_invalid(tmp_path, monkeypatch):
    from klangwerk.ai import separation
    assets = Assets(tmp_path / "cache")
    original = tmp_path / "original.wav"
    sf.write(original, np.ones((1000, 2)) * .1, RATE)
    key = assets.import_file(str(original), Event())
    monkeypatch.setattr(separation, "runtime_available", lambda: True)
    monkeypatch.setattr(separation, "verify_model", lambda *a: True)
    def incomplete(command, root, cancel, progress):
        sf.write(root / "instrumental.wav", np.ones((1000, 2)) * .05, RATE)
        sf.write(root / "vocals.wav", np.ones((500, 2)) * .03, RATE)
    monkeypatch.setattr(separation, "wait_for_worker", incomplete)
    before = set(assets.directory.iterdir())
    with pytest.raises(ValueError, match="Länge"):
        separate_clip(assets, Clip(key, 2000, 0, 1000), tmp_path / "model", Event())
    assert set(assets.data) == {key}
    assert set(assets.directory.iterdir()) == before


@pytest.mark.skipif(not os.environ.get("KLANGWERK_TEST_MODEL"), reason="Echtes Modell separat aktivieren")
def test_real_demucs_cpu_inference_without_network(tmp_path, monkeypatch):
    # Echte Modellrechnung, kein Stub. Netzoperationen werden im Prozess untersagt.
    import torch
    import demucs.apply
    import demucs.states
    def forbidden(*a, **k):
        raise AssertionError("Netzwerkzugriff bei Offline-Inferenz")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(models.urllib.request, "urlopen", forbidden)
    source = tmp_path / "source.npy"
    t = np.arange(RATE) / RATE
    audio = np.stack([.1 * np.sin(2 * np.pi * 220 * t), .1 * np.sin(2 * np.pi * 330 * t)], axis=1).astype("float32")
    np.save(source, audio)
    run({"source": str(source), "offset": 0, "length": RATE,
         "model": os.environ["KLANGWERK_TEST_MODEL"], "output": str(tmp_path)})
    voice, rate = sf.read(tmp_path / "vocals.wav", always_2d=True)
    backing, _ = sf.read(tmp_path / "instrumental.wav", always_2d=True)
    assert rate == RATE
    assert voice.shape == backing.shape == audio.shape
    assert np.isfinite(voice).all() and np.isfinite(backing).all()
    assert np.max(np.abs(backing)) > .001
    assert not np.array_equal(voice, backing)
    assert json.loads((tmp_path / "status.json").read_text())["progress"] == 100

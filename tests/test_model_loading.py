"""Regression für Legacy-NumPy-Pickle-Pfade und eingeschränktes Modellladen."""
from fractions import Fraction
import io
import os
from pathlib import Path
import pickle
import zipfile

import numpy as np
import pytest

from klangwerk.ai.loading import load_htdemucs, checkpoint_types


def test_legacy_numpy_scalar_loads_with_restricted_loader():
    torch = pytest.importorskip("torch")
    pytest.importorskip("demucs")
    original = io.BytesIO()
    torch.save({"scalar": np.float64(.25), "segment": Fraction(39, 5)}, original)
    legacy = io.BytesIO()
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(legacy, "w") as target:
        for name in source.namelist():
            data = source.read(name)
            if name.endswith("data.pkl"):
                data = data.replace(b"numpy._core.multiarray", b"numpy.core.multiarray")
                assert b"numpy.core.multiarray" in data
            target.writestr(name, data)
    legacy.seek(0)
    before = torch.serialization.get_safe_globals().copy()
    with torch.serialization.safe_globals(checkpoint_types()):
        result = torch.load(legacy, weights_only=True, map_location="cpu")
    assert result == {"scalar": .25, "segment": Fraction(39, 5)}
    assert set(torch.serialization.get_safe_globals()) == set(before)


def test_hash_failure_never_deserializes(tmp_path, monkeypatch):
    torch = pytest.importorskip("torch")
    pytest.importorskip("demucs")
    file = tmp_path / "bad.th"
    file.write_bytes(b"not the approved model")
    calls = []
    monkeypatch.setattr(torch, "load", lambda *a, **k: calls.append(k))
    with pytest.raises(ValueError, match="Prüfsumme"):
        load_htdemucs(file)
    assert not calls


def test_loader_refuses_unknown_pickle_global(tmp_path, monkeypatch):
    torch = pytest.importorskip("torch")
    pytest.importorskip("demucs")
    file = tmp_path / "not-approved.th"
    torch.save({"unexpected": eval}, file)
    # Nur um die zusätzliche Unpickler-Schranke hinter der Hashprüfung zu prüfen.
    monkeypatch.setattr("klangwerk.ai.loading.verify_model_stream", lambda source: True)
    with pytest.raises(pickle.UnpicklingError, match="Unsupported global"):
        load_htdemucs(file)


@pytest.mark.skipif(not os.environ.get("KLANGWERK_TEST_MODEL"), reason="Echtes Modell separat aktivieren")
def test_real_model_uses_weights_only_on_cpu(monkeypatch):
    import torch
    original_load = torch.load
    calls = []
    def restricted(*args, **kwargs):
        calls.append(kwargs.copy())
        return original_load(*args, **kwargs)
    monkeypatch.setattr(torch, "load", restricted)
    model = load_htdemucs(Path(os.environ["KLANGWERK_TEST_MODEL"]))
    assert model.sources == ["drums", "bass", "other", "vocals"]
    assert model.samplerate == 44100
    assert all(p.device.type == "cpu" for p in model.parameters())
    assert not model.training
    assert calls == [{"map_location": "cpu", "weights_only": True}]

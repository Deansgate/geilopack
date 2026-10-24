"""Festgelegten HTDemucs-Checkpoint mit eingeschränktem PyTorch-Lader öffnen."""
from fractions import Fraction
from pathlib import Path

import numpy as np
# Dieser echte NumPy-2-Kompatibilitätsimport muss auch im PyInstaller-Paket sein.
# Keine sys.modules-Aliase und kein Ersetzen des Pickle-Unpicklers.
from numpy.core.multiarray import scalar

from klangwerk.ai.models import verify_model_stream


def checkpoint_types():
    from demucs.htdemucs import HTDemucs
    # Exakt die im freigegebenen Checkpoint benötigten Typen. Kein automatisches
    # Freischalten unbekannter Globals aus einer Datei oder Fehlermeldung.
    return [HTDemucs, Fraction, np.dtype,
            (scalar, "numpy.core.multiarray.scalar"), type(np.dtype("float64"))]


def load_htdemucs(path):
    import torch
    from demucs.htdemucs import HTDemucs
    from demucs.states import load_model

    with Path(path).open("rb") as source:
        if not verify_model_stream(source):
            raise ValueError("Das lokale Modell fehlt oder seine Prüfsumme stimmt nicht.")
        with torch.serialization.safe_globals(checkpoint_types()):
            package = torch.load(source, map_location="cpu", weights_only=True)
    if package.get("klass") is not HTDemucs:
        raise ValueError("Unerwartete Architektur im Trennungsmodell.")
    model = load_model(package)
    model.to("cpu").eval()
    if (model.samplerate != 44100 or model.audio_channels != 2
            or model.sources != ["drums", "bass", "other", "vocals"]):
        raise ValueError("Unerwartete Modellparameter.")
    return model

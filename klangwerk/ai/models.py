"""Ein einziges freigegebenes Modell; keine Audioübertragung und kein Auto-Download."""
from pathlib import Path
import hashlib
import os
import urllib.request

from klangwerk.audio.assets import Cancelled

MODEL_FILE = "955717e8-8726e21a.th"
MODEL_URL = "https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/" + MODEL_FILE
MODEL_SHA256 = "8726e21a993978c7ba086d3872e7608d7d5bfca646ca4aca459ffda844faa8b4"
MODEL_SIZE = 84141911


def verify_model(path, cancel=None):
    path = Path(path)
    if not path.is_file() or path.stat().st_size != MODEL_SIZE:
        return False
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            if cancel is not None and cancel.is_set():
                raise Cancelled()
            digest.update(block)
    return digest.hexdigest() == MODEL_SHA256


def download_model(directory, cancel, progress=lambda p: None):
    """Nur nach Klick im Einrichtungsdialog aufrufen. Hash vor atomarer Übernahme."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / MODEL_FILE
    if verify_model(target, cancel):
        progress(100)
        return target
    partial = directory / (MODEL_FILE + ".partial")
    try:
        request = urllib.request.Request(MODEL_URL, headers={"User-Agent": "Klangwerk/0.2"})
        with urllib.request.urlopen(request, timeout=15) as source, partial.open("wb") as out:
            received = 0
            while True:
                if cancel.is_set():
                    raise Cancelled()
                block = source.read(256 * 1024)
                if not block:
                    break
                received += len(block)
                if received > MODEL_SIZE:
                    raise ValueError("Der Modellserver liefert eine unerwartete Dateigröße.")
                out.write(block)
                progress(min(99, int(received / MODEL_SIZE * 100)))
            out.flush()
            os.fsync(out.fileno())
        if not verify_model(partial, cancel):
            raise ValueError("Modellprüfung fehlgeschlagen. Bitte den Download erneut starten.")
        if cancel.is_set():
            raise Cancelled()
        os.replace(partial, target)
        progress(100)
        return target
    finally:
        partial.unlink(missing_ok=True)

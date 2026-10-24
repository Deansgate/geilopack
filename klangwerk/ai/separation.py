from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import json
import os
import shutil
import subprocess
import sys

from klangwerk.ai.models import verify_model
from klangwerk.audio.assets import Assets, Cancelled


def runtime_available():
    return all(importlib.util.find_spec(name) is not None for name in ("torch", "torchaudio", "demucs"))


def worker_command(config):
    if getattr(sys, "frozen", False):
        return [sys.executable, "--separate-worker", str(config)]
    return [sys.executable, "-m", "klangwerk.ai.worker", str(config)]


def wait_for_worker(command, directory, cancel, progress):
    """Kurzes Event-Warten hält den Worker-Thread unterbrechbar; keine GUI-Sperre."""
    if cancel.is_set():
        raise Cancelled()
    directory = Path(directory)
    with (directory / "worker.log").open("wb") as log:
        child = subprocess.Popen(command, stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        last_progress = -1
        try:
            while child.poll() is None:
                if cancel.wait(.1):
                    raise Cancelled()
                try:
                    status = json.loads((directory / "status.json").read_text(encoding="utf-8"))
                    current = min(85, max(0, int(status["progress"]) * 85 // 100))
                    if current != last_progress:
                        progress(current)
                        last_progress = current
                except (OSError, ValueError, KeyError):
                    pass
            if cancel.is_set():
                raise Cancelled()
            if child.returncode:
                tail = (directory / "worker.log").read_bytes()[-3000:].decode("utf-8", errors="replace")
                raise RuntimeError("Die lokale Gesangstrennung konnte nicht abgeschlossen werden.\n" + tail)
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()


def separate_clip(assets, clip, model_path, cancel, progress=lambda p: None):
    if not runtime_available():
        raise RuntimeError("Diese Ausgabe enthält die KI-Laufzeit nicht. Bitte den Klangwerk-Installer mit CPU-KI verwenden.")
    if not verify_model(model_path, cancel):
        raise ValueError("Das Trennungsmodell fehlt oder ist beschädigt. Bitte die KI-Einrichtung starten.")
    # Zwei Caches, drei temporäre Arrays und WAVs; zusätzliche Reserve für SSD-I/O.
    required = clip.length * 64 + 512 * 1024 * 1024
    if shutil.disk_usage(assets.directory).free < required:
        raise OSError(f"Für die Trennung werden mindestens {required / 1024 ** 3:.1f} GB freier Speicher benötigt.")
    with TemporaryDirectory(prefix="trennung-", dir=assets.directory) as directory:
        root = Path(directory)
        config = root / "config.json"
        config.write_text(json.dumps({"source": str(assets.data[clip.asset].filename),
                                      "offset": clip.offset, "length": clip.length,
                                      "model": str(model_path), "output": str(root)}), encoding="utf-8")
        wait_for_worker(worker_command(config), root, cancel, progress)
        # Erst beide Ergebnisse validieren, dann gemeinsam in den aktiven Cache übernehmen.
        staged = Assets(assets.directory)
        keys = []
        try:
            for index, name in enumerate(("instrumental", "vocals")):
                key = staged.import_file(str(root / f"{name}.wav"), cancel,
                                         lambda p, n=index: progress(85 + n * 7 + p * 7 // 100))
                keys.append(key)
                if len(staged.data[key]) != clip.length:
                    raise ValueError("Die Länge der getrennten Spuren stimmt nicht mit dem Original überein.")
            if cancel.is_set():
                raise Cancelled()
        except BaseException:
            paths = [Path(array.filename) for array in staged.data.values()]
            staged.data.clear()
            staged.peaks.clear()
            for path in paths:
                path.unlink(missing_ok=True)
            raise
        assets.data.update(staged.data)
        assets.peaks.update(staged.peaks)
        progress(100)
        return tuple(keys)

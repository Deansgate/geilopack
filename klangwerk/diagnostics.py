"""Automatischer Starttest für die eingefrorene Windows-Anwendung ohne Audiogerät."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import traceback


def smoke_test(report):
    result = {"ok": False}
    try:
        import numpy as np
        import soundfile as sf
        import sounddevice
        import torch
        import torchaudio
        import demucs
        from demucs.htdemucs import HTDemucs
        from PySide6.QtWidgets import QApplication
        from klangwerk.audio.assets import Assets
        from klangwerk.audio.export import export_wav
        from klangwerk.model import Project, Track, Clip, RATE
        from klangwerk.ui.timeline import Timeline
        from klangwerk.ui.window import Window

        app = QApplication.instance() or QApplication([])
        if torch.version.cuda is not None:
            raise RuntimeError("Der Windows-Build enthält keine reine CPU-Laufzeit.")
        with TemporaryDirectory(prefix="klangwerk-starttest-") as directory:
            root = Path(directory)
            source = root / "input.wav"
            sf.write(source, np.sin(np.arange(4000) * .1) * .1, RATE)
            assets = Assets(root / "cache")
            key = assets.import_file(str(source), Event())
            project = Project(tracks=[Track("Starttest", [Clip(key, 0, 0, 4000)])])
            timeline = Timeline(project, assets)
            if timeline.grab().isNull():
                raise RuntimeError("Qt konnte die Timeline nicht zeichnen.")
            target = root / "output.wav"
            export_wav(target, project, assets, Event())
            if sf.info(target).frames != 4000:
                raise RuntimeError("Audioexport hat eine unerwartete Länge.")
            timeline.close()
            # Freigabe vor TemporaryDirectory-Cleanup ist unter Windows erforderlich.
            for audio in assets.data.values():
                audio._mmap.close()
            assets.data.clear()
        result = {"ok": True, "numpy": np.__version__, "demucs": demucs.__version__,
                  "torch": torch.__version__, "cuda": torch.version.cuda,
                  "torchaudio": torchaudio.__version__, "checks": [
                      "Qt-Timeline", "Audioimport", "WAV-Export", "PortAudio-Import", "CPU-KI-Import"],
                  "physical_audio_test": False}
    except Exception:
        result["error"] = traceback.format_exc()
    Path(report).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if result["ok"] else 1


def model_test(model_path, report):
    """Echter Checkpoint und Inferenz innerhalb der gebauten EXE, ohne Netz."""
    result = {"ok": False}
    try:
        import numpy as np
        import soundfile as sf
        import torch
        import demucs
        import socket
        import urllib.request
        from unittest.mock import patch
        from klangwerk.ai.loading import load_htdemucs
        from klangwerk.ai.worker import run
        from klangwerk.model import RATE

        def no_network(*args, **kwargs):
            raise RuntimeError("Netzwerkzugriff während Offline-Modelltest untersagt")

        if torch.version.cuda is not None:
            raise RuntimeError("Der Test erfordert die gebündelte CPU-Laufzeit.")
        with patch.object(socket.socket, "connect", no_network), \
                patch.object(socket.socket, "connect_ex", no_network), \
                patch.object(socket, "create_connection", no_network), \
                patch.object(urllib.request, "urlopen", no_network):
            model = load_htdemucs(model_path)
            if any(parameter.device.type != "cpu" for parameter in model.parameters()):
                raise RuntimeError("Das Modell wurde nicht vollständig auf CPU geladen.")
            del model
            with TemporaryDirectory(prefix="klangwerk-modeltest-") as directory:
                root = Path(directory)
                samples = np.arange(RATE) / RATE
                source = np.stack([.1 * np.sin(2 * np.pi * 220 * samples),
                                   .1 * np.sin(2 * np.pi * 330 * samples)], axis=1).astype("float32")
                np.save(root / "source.npy", source)
                run({"model": str(model_path), "source": str(root / "source.npy"),
                     "offset": 0, "length": RATE, "output": str(root)})
                stems = [sf.read(root / (name + ".wav"), always_2d=True)
                         for name in ("vocals", "instrumental")]
                for data, rate in stems:
                    if rate != RATE or data.shape != source.shape or not np.isfinite(data).all():
                        raise RuntimeError("Ungültiges Trennungsergebnis.")
                if np.array_equal(stems[0][0], stems[1][0]) or np.max(np.abs(stems[1][0])) < .001:
                    raise RuntimeError("Die Trennung hat keine unterscheidbaren Audiospuren erzeugt.")
        result = {"ok": True, "numpy": np.__version__, "torch": torch.__version__,
                  "demucs": demucs.__version__, "cuda": torch.version.cuda,
                  "weights_only": True, "network_connect_forbidden": True,
                  "model_loaded": True, "separation_frames": RATE, "rate": RATE}
    except Exception:
        result["error"] = traceback.format_exc()
    Path(report).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if result["ok"] else 1

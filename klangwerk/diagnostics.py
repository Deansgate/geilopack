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
        result = {"ok": True, "torch": torch.__version__, "cuda": torch.version.cuda,
                  "torchaudio": torchaudio.__version__, "checks": [
                      "Qt-Timeline", "Audioimport", "WAV-Export", "PortAudio-Import", "CPU-KI-Import"],
                  "physical_audio_test": False}
    except Exception:
        result["error"] = traceback.format_exc()
    Path(report).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if result["ok"] else 1

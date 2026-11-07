from pathlib import Path
import os
import numpy as np
import soundfile as sf

from klangwerk.audio.assets import Cancelled
from klangwerk.audio.mixer import MixSession, mix_end
from klangwerk.model import RATE


def export_wav(path, project, assets, cancel, progress=lambda p: None, *, start=0, end=None, track_id=None):
    """Zwei Durchläufe: Spitzenwert messen, dann ggf. gleichmäßig leiser exportieren."""
    end = mix_end(project, export=True, track_id=track_id) if end is None else end
    if end <= start:
        raise ValueError("Der Exportbereich enthält keine Audiodaten.")
    block = 65536
    peak = 0.
    # Bereichsexport mit Vorlauf: Hall/Delay am Bereichsbeginn wie im Gesamtsong.
    def blocks():
        session = MixSession(project)
        for pos in range(0, end, block):
            if cancel.is_set():
                raise Cancelled()
            audio = session.render(project, assets, pos, min(block, end - pos), export=True, track_id=track_id)
            yield pos, audio[max(0, start - pos):]
    for pos, audio in blocks():
        if cancel.is_set():
            raise Cancelled()
        peak = max(peak, float(np.max(np.abs(audio), initial=0)))
        progress(int(pos / end * 45))
    gain = min(1., .999 / peak) if peak else 1.
    path = Path(path)
    temporary = path.with_name(path.name + ".partial")
    try:
        with sf.SoundFile(temporary, "w", samplerate=RATE, channels=2, subtype="PCM_24", format="WAV") as out:
            # TPDF-Dither vor 24-Bit-Quantisierung, ohne Pegelanhebung.
            rng = np.random.default_rng(0)
            for pos, audio in blocks():
                if cancel.is_set():
                    raise Cancelled()
                dither = (rng.random(audio.shape) - rng.random(audio.shape)) / (2 ** 23)
                out.write(np.clip(audio * gain + dither, -1, 1 - 2 ** -23))
                progress(45 + int(pos / end * 55))
        if cancel.is_set():
            raise Cancelled()
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    progress(100)
    return gain

from __future__ import annotations

from pathlib import Path
from threading import Event
from math import gcd
import re
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from klangwerk.model import RATE, uid


class Cancelled(Exception):
    pass


class Assets:
    """48-kHz-Float32-Cache auf SSD statt vollständiger Songs im Arbeitsspeicher."""
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.data: dict[str, np.ndarray] = {}
        self.peaks: dict[str, np.ndarray] = {}

    def register(self, path: Path, asset_id: str | None = None, cancel: Event | None = None) -> str:
        asset_id = asset_id or uid()
        if not re.fullmatch(r"[0-9a-f]{32}", asset_id):
            raise ValueError("Ungültige Audiodatei-ID im Projekt.")
        audio = np.load(path, mmap_mode="r", allow_pickle=False)
        try:
            if audio.ndim != 2 or audio.shape[1] != 2 or audio.dtype != np.float32 or len(audio) == 0:
                raise ValueError("Ungültiges internes Audioformat.")
            # Kleine Übersicht vorab im Import-Worker berechnen, nicht im GUI-Paint.
            blocks = len(audio) // 1024
            overview = np.empty((blocks + bool(len(audio) % 1024), 2), dtype=np.float32)
            for start in range(0, blocks, 4096):
                if cancel is not None and cancel.is_set():
                    raise Cancelled()
                end = min(blocks, start + 4096)
                chunk = audio[start * 1024:end * 1024].reshape(-1, 1024, 2)
                if not np.isfinite(chunk).all():
                    raise ValueError("Der Audiocache enthält ungültige Werte.")
                overview[start:end, 0] = chunk.min(axis=(1, 2))
                overview[start:end, 1] = chunk.max(axis=(1, 2))
            if len(audio) % 1024:
                if not np.isfinite(audio[blocks * 1024:]).all():
                    raise ValueError("Der Audiocache enthält ungültige Werte.")
                overview[-1] = audio[blocks * 1024:].min(), audio[blocks * 1024:].max()
            if cancel is not None and cancel.is_set():
                raise Cancelled()
            self.data[asset_id] = audio
            self.peaks[asset_id] = overview
            return asset_id
        except BaseException:
            # Unter Windows muss der Cache vor Entfernen der Teil-Datei geschlossen sein.
            self.data.pop(asset_id, None)
            self.peaks.pop(asset_id, None)
            mapping = getattr(audio, "_mmap", None)
            if mapping is not None:
                mapping.close()
            raise

    def import_file(self, path: str, cancel: Event, progress=lambda x: None) -> str:
        asset_id = uid()
        target = self.directory / f"{asset_id}.npy"
        try:
            with sf.SoundFile(path) as source:
                if source.channels > 2:
                    raise ValueError("Bitte zuerst eine Mono- oder Stereo-Datei exportieren.")
                if source.frames <= 0:
                    raise ValueError("Die Audiodatei ist leer.")
                # Rationale Konvertierung mit Polyphasenfilter, kein einfaches Auslassen.
                divisor = gcd(RATE, source.samplerate)
                up, down = RATE // divisor, source.samplerate // divisor
                length = (source.frames * up + down - 1) // down
                out = np.lib.format.open_memmap(target, mode="w+", dtype="float32", shape=(length, 2))
                # Blockgrenzen auf Vielfachen von down; Überlappung vermeidet Filterkanten.
                block = max(down, (262144 // down) * down)
                pad = 64 * down
                for start in range(0, source.frames, block):
                    if cancel.is_set():
                        raise Cancelled()
                    end = min(source.frames, start + block)
                    lo, hi = max(0, start - pad), min(source.frames, end + pad)
                    source.seek(lo)
                    audio = source.read(hi - lo, dtype="float32", always_2d=True)
                    if not np.isfinite(audio).all():
                        raise ValueError("Die Datei enthält ungültige Audiowerte.")
                    if source.channels == 1:
                        audio = np.repeat(audio, 2, axis=1)
                    if up != down:
                        audio = resample_poly(audio, up, down, axis=0)
                    dest_start = start * up // down
                    dest_end = min(length, (end * up + down - 1) // down)
                    trim = (start - lo) * up // down
                    out[dest_start:dest_end] = audio[trim:trim + dest_end - dest_start]
                    progress(int(end / source.frames * 100))
                out.flush()
                del out
            if cancel.is_set():
                raise Cancelled()
            return self.register(target, asset_id, cancel)
        except BaseException:
            # Memmap vor dem Löschen freigeben (Windows-Dateisperre).
            if "out" in locals():
                del out
            target.unlink(missing_ok=True)
            raise

    def waveform(self, asset_id: str, offset: int, length: int, bins: int):
        audio = self.data[asset_id]
        edges = np.linspace(offset, offset + length, max(2, bins + 1), dtype=np.int64)
        result = []
        for a, b in zip(edges[:-1], edges[1:]):
            if b - a >= 2048:
                chunk = self.peaks[asset_id][a // 1024:(b + 1023) // 1024]
                result.append((float(chunk[:, 0].min()), float(chunk[:, 1].max())) if chunk.size else (0., 0.))
            else:
                chunk = audio[a:max(a + 1, b)]
                result.append((float(chunk.min()), float(chunk.max())) if chunk.size else (0., 0.))
        return result

"""Isolierter CPU-Prozess. Lädt ausschließlich das hashgeprüfte lokale Modell."""
from pathlib import Path
import json
import os
import sys
import traceback

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from klangwerk.ai.models import verify_model
from klangwerk.model import RATE
from klangwerk.project import atomic_json


def windows(length, rate=RATE):
    """20-s-Kontext mit 50 % Überlappung; RAM-Bedarf unabhängig von Songlänge."""
    size, hop = 20 * rate, 10 * rate
    for start in range(0, length, hop):
        end = min(start + size, length)
        yield start, end
        if end == length:
            break


def overlap_weight(length, rate=RATE):
    index = np.arange(length, dtype=np.float32)
    return np.minimum(1., np.minimum(index + 1, length - index) / (10 * rate))[:, None]


def run(config):
    import torch
    from demucs.states import load_model
    from demucs.apply import apply_model

    root = Path(config["output"])
    status = root / "status.json"
    atomic_json(status, {"progress": 0, "stage": "Modell wird geladen"})
    model_path = Path(config["model"])
    if not verify_model(model_path):
        raise ValueError("Das lokale Modell fehlt oder seine Prüfsumme stimmt nicht.")
    torch.set_num_threads(max(1, min(8, (os.cpu_count() or 2) // 2)))
    torch.manual_seed(0)
    # Demucs-Checkpoints enthalten eine Python-Modellklasse. Nur die oben
    # vollständig hashgeprüfte, festgelegte Datei wird mit Pickle geladen.
    model = load_model(torch.load(model_path, map_location="cpu", weights_only=False))
    model.eval()
    if model.samplerate != 44100 or model.audio_channels != 2:
        raise ValueError("Unerwartete Modellparameter.")
    vocal_index = model.sources.index("vocals")
    other_indices = [i for i in range(len(model.sources)) if i != vocal_index]
    audio = np.load(config["source"], mmap_mode="r", allow_pickle=False)
    offset, length = int(config["offset"]), int(config["length"])
    if offset < 0 or length <= 0 or offset + length > len(audio):
        raise ValueError("Ungültiger Quellbereich für die Gesangstrennung.")
    vocals = np.lib.format.open_memmap(root / "vocals.npy", mode="w+", dtype="float32", shape=(length, 2))
    instrumental = np.lib.format.open_memmap(root / "instrumental.npy", mode="w+", dtype="float32", shape=(length, 2))
    weights = np.lib.format.open_memmap(root / "weights.npy", mode="w+", dtype="float32", shape=(length, 1))
    vocals[:] = 0
    instrumental[:] = 0
    weights[:] = 0
    try:
        for start, end in windows(length):
            atomic_json(status, {"progress": int(start / length * 90), "stage": "Gesang und Instrumental werden getrennt"})
            source = np.asarray(audio[offset + start:offset + end])
            converted = resample_poly(source, 147, 160, axis=0)
            tensor = torch.from_numpy(np.ascontiguousarray(converted.T))
            mean = tensor.mean()
            std = tensor.mean(0).std(unbiased=False)
            if float(std) < 1e-8:
                voice = np.zeros_like(source)
                backing = source.copy()
            else:
                with torch.inference_mode():
                    estimates = apply_model(model, ((tensor - mean) / std)[None],
                                            device="cpu", shifts=1, split=True,
                                            overlap=.25, progress=False, num_workers=0)[0]
                voice44 = (estimates[vocal_index] * std).T.numpy()
                backing44 = (estimates[other_indices].sum(0) * std + mean).T.numpy()
                voice = resample_poly(voice44, 160, 147, axis=0)[:end - start]
                backing = resample_poly(backing44, 160, 147, axis=0)[:end - start]
                del estimates
            weight = overlap_weight(end - start)
            vocals[start:end] += voice * weight
            instrumental[start:end] += backing * weight
            weights[start:end] += weight
        # Float-WAV erhält Spitzen oberhalb 0 dBFS; Masterpegel/Export schützen später.
        with sf.SoundFile(root / "vocals.wav", "w", samplerate=RATE, channels=2, subtype="FLOAT") as v, \
                sf.SoundFile(root / "instrumental.wav", "w", samplerate=RATE, channels=2, subtype="FLOAT") as i:
            for start in range(0, length, 65536):
                end = min(length, start + 65536)
                voice = vocals[start:end] / weights[start:end]
                backing = instrumental[start:end] / weights[start:end]
                if not np.isfinite(voice).all() or not np.isfinite(backing).all():
                    raise ValueError("Die Trennung hat ungültige Audiowerte erzeugt.")
                v.write(voice)
                i.write(backing)
                atomic_json(status, {"progress": 90 + int(end / length * 10), "stage": "Ergebnis wird gespeichert"})
    finally:
        del vocals, instrumental, weights, audio
    atomic_json(status, {"progress": 100, "stage": "Fertig"})


def main(config_path):
    try:
        with open(config_path, encoding="utf-8") as file:
            config = json.load(file)
        run(config)
        return 0
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))

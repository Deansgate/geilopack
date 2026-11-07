"""Serialisierbare Einstellungen der lokalen Spureffekte."""
from dataclasses import dataclass
import math


@dataclass
class Effects:
    enabled: bool = False
    eq: bool = True
    low_db: float = 0.0
    mid_db: float = 0.0
    high_db: float = 0.0
    compressor: bool = False
    threshold_db: float = -18.0
    ratio: float = 3.0
    makeup_db: float = 0.0
    reverb: bool = False
    reverb_mix: float = 0.15
    delay: bool = False
    delay_ms: float = 250.0
    delay_feedback: float = 0.25
    delay_mix: float = 0.15

    def validate(self):
        for key in ("enabled", "eq", "compressor", "reverb", "delay"):
            if type(getattr(self, key)) is not bool:
                raise ValueError("Ungültiger Effekt-Schalter.")
        limits = {"low_db": (-12, 12), "mid_db": (-12, 12), "high_db": (-12, 12),
                  "threshold_db": (-48, 0), "ratio": (1, 10), "makeup_db": (0, 12),
                  "reverb_mix": (0, .5), "delay_ms": (50, 1000),
                  "delay_feedback": (0, .6), "delay_mix": (0, .5)}
        for key, (low, high) in limits.items():
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f"Ungültiger Effektwert: {key}")
        return self

    @property
    def tail_frames(self):
        from klangwerk.model import RATE
        if not self.enabled:
            return 0
        tail = 0
        if self.eq and any((self.low_db, self.mid_db, self.high_db)):
            tail += RATE // 4
        if self.reverb and self.reverb_mix:
            tail += 3 * RATE  # Feste Hallgröße; Abklingen bis unter etwa -90 dB.
        if self.delay and self.delay_mix:
            echoes = 1 if not self.delay_feedback else 1 + math.ceil(math.log(1e-5) / math.log(self.delay_feedback))
            tail += math.ceil(self.delay_ms / 1000 * RATE) * echoes
        return tail


"""Zustandsbehaftete CPU-Effekte; Originalassets bleiben unverändert."""
import math
import numpy as np
from scipy.signal import sosfilt, lfilter

from klangwerk.model import RATE
from klangwerk.effect_settings import Effects



def _peak(hz, db, q):
    """RBJ-Peaking-EQ, normalisierte SOS-Koeffizienten."""
    w = 2 * np.pi * hz / RATE
    alpha = np.sin(w) / (2 * q)
    a = 10 ** (db / 40)
    return np.array([1 + alpha * a, -2 * np.cos(w), 1 - alpha * a,
                     1 + alpha / a, -2 * np.cos(w), 1 - alpha / a]) / (1 + alpha / a)


class _Delay:
    def __init__(self, frames, feedback):
        self.buffer = np.zeros((frames, 2), dtype=np.float32)
        self.position = 0
        self.feedback = feedback

    def process(self, audio):
        result = np.empty_like(audio)
        pos = 0
        while pos < len(audio):
            n = min(len(audio) - pos, len(self.buffer) - self.position)
            old = self.buffer[self.position:self.position + n]
            result[pos:pos + n] = old
            old[:] = audio[pos:pos + n] + old * self.feedback
            self.position = (self.position + n) % len(self.buffer)
            pos += n
        return result


class Processor:
    """Feste Effektparameter je Wiedergabe; Zustand wird über Blöcke erhalten."""
    def __init__(self, settings):
        self.settings = settings.validate()
        self.sos = np.array([_peak(150, settings.low_db, .7),
                             _peak(1800, settings.mid_db, .8),
                             _peak(8000, settings.high_db, .7)])
        self.eq_state = np.zeros((3, 2, 2))
        self.power_state = np.zeros(1)
        self.gain_state = np.ones(1)
        self.combs = [_Delay(round(RATE * ms / 1000), .72) for ms in (29.7, 37.1, 41.1, 43.7)]
        self.diffusers = [_Delay(round(RATE * ms / 1000), .5) for ms in (5.0, 1.7)]
        self.delay = _Delay(round(RATE * settings.delay_ms / 1000), settings.delay_feedback)

    def process(self, audio):
        s = self.settings
        if not s.enabled:
            return audio
        out = np.array(audio, dtype=np.float32, copy=True)
        if s.eq and any((s.low_db, s.mid_db, s.high_db)):
            out, self.eq_state = sosfilt(self.sos, out, axis=0, zi=self.eq_state)
        if s.compressor:
            # Stereo-gekoppelter RMS-Kompressor: 10 ms Detektor, 50 ms Gain-Glättung.
            alpha = math.exp(-1 / (RATE * .010))
            power, self.power_state = lfilter([1 - alpha], [1, -alpha],
                np.mean(np.square(out), axis=1), zi=self.power_state)
            level = 10 * np.log10(np.maximum(power, 1e-12))
            reduction = np.maximum(level - s.threshold_db, 0) * (1 - 1 / s.ratio)
            target = 10 ** (-reduction / 20)
            alpha = math.exp(-1 / (RATE * .050))
            gain, self.gain_state = lfilter([1 - alpha], [1, -alpha], target, zi=self.gain_state)
            out = out * gain[:, None] * 10 ** (s.makeup_db / 20)
        out = np.asarray(out, dtype=np.float32)
        if s.reverb and s.reverb_mix:
            wet = sum(line.process(out) for line in self.combs) * .14
            for line in self.diffusers:
                delayed = line.process(wet)
                wet = delayed * .75 - wet * .5  # Schroeder-Allpass mit g=.5.
            wet = wet[:, ::-1]
            out = out * (1 - s.reverb_mix) + wet * s.reverb_mix
        if s.delay and s.delay_mix:
            out = out * (1 - s.delay_mix) + self.delay.process(out) * s.delay_mix
        return np.asarray(out, dtype=np.float32)

from __future__ import annotations
import numpy as np
from klangwerk.model import Project
from klangwerk.audio.effects import Processor


def mix_end(project, *, export=False, track_id=None):
    tracks = [t for t in project.tracks if not (export and t.reference)
              and (track_id is None or t.id == track_id)]
    solo = any(t.solo for t in tracks)
    return max((c.end + t.effects.tail_frames for t in tracks
                if not t.mute and (not solo or t.solo) for c in t.clips), default=0)


class MixSession:
    """Ein Zustand pro Durchlauf; nie zwischen Peak-Messung und Export teilen."""
    def __init__(self, project):
        self.processors = {t.id: Processor(t.effects) for t in project.tracks if t.effects.enabled}

    def render(self, project, assets, start, frames, *, export=False, track_id=None):
        return mix_block(project, assets, start, frames, export=export,
                         track_id=track_id, session=self)


def mix_block(project: Project, assets, start: int, frames: int, *, export=False, track_id=None, session=None):
    if session is None:
        session = MixSession(project)
    result = np.zeros((frames, 2), dtype=np.float32)
    eligible = [t for t in project.tracks if not (export and t.reference)
                and (track_id is None or t.id == track_id)]
    solo = any(t.solo for t in eligible)
    for track in eligible:
        # Balance-Panorama erhält bei Mittelstellung den Stereopegel.
        gains = np.array([min(1., 1. - track.pan), min(1., 1. + track.pan)], dtype=np.float32)
        gains *= track.gain * project.master
        audio = np.zeros((frames, 2), dtype=np.float32)
        for clip in track.clips:
            left, right = max(start, clip.start), min(start + frames, clip.end)
            if right <= left:
                continue
            source = clip.offset + left - clip.start
            audio[left - start:right - start] += assets.data[clip.asset][source:source + right - left]
        if track.id in session.processors:
            audio = session.processors[track.id].process(audio)
        if not track.mute and (not solo or track.solo):
            result += audio * gains
    return result

from __future__ import annotations
import numpy as np
from klangwerk.model import Project


def mix_block(project: Project, assets, start: int, frames: int, *, export=False, track_id=None):
    result = np.zeros((frames, 2), dtype=np.float32)
    eligible = [t for t in project.tracks if not (export and t.reference)
                and (track_id is None or t.id == track_id)]
    solo = any(t.solo for t in eligible)
    for track in eligible:
        if track.mute or (solo and not track.solo):
            continue
        # Balance-Panorama erhält bei Mittelstellung den Stereopegel.
        gains = np.array([min(1., 1. - track.pan), min(1., 1. + track.pan)], dtype=np.float32)
        gains *= track.gain * project.master
        for clip in track.clips:
            left, right = max(start, clip.start), min(start + frames, clip.end)
            if right <= left:
                continue
            source = clip.offset + left - clip.start
            result[left - start:right - start] += assets.data[clip.asset][source:source + right - left] * gains
    return result

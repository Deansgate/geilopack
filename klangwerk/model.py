from __future__ import annotations

from dataclasses import asdict, dataclass, field
from copy import deepcopy
import math
from uuid import uuid4

RATE = 48000


def uid() -> str:
    return uuid4().hex


@dataclass
class Clip:
    asset: str
    start: int
    offset: int
    length: int
    id: str = field(default_factory=uid)

    @property
    def end(self) -> int:
        return self.start + self.length


@dataclass
class Track:
    name: str
    clips: list[Clip] = field(default_factory=list)
    gain: float = 1.0
    pan: float = 0.0
    mute: bool = False
    solo: bool = False
    reference: bool = False
    id: str = field(default_factory=uid)


@dataclass
class Project:
    name: str = "Neuer Song"
    rate: int = RATE
    tracks: list[Track] = field(default_factory=list)
    master: float = 0.8

    @property
    def end(self) -> int:
        return max((c.end for t in self.tracks for c in t.clips), default=0)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Project:
        if data.get("rate") != RATE:
            raise ValueError("Dieses Projekt verwendet keine unterstützten 48 kHz.")
        tracks = []
        for row in data["tracks"]:
            row = dict(row)
            clips = [Clip(**c) for c in row.pop("clips")]
            for c in clips:
                if any(type(n) is not int for n in (c.start, c.offset, c.length)) or min(c.start, c.offset) < 0 or c.length <= 0:
                    raise ValueError("Ungültige Clip-Position im Projekt.")
            track = Track(clips=clips, **row)
            if not math.isfinite(track.gain) or not 0 <= track.gain <= 4:
                raise ValueError("Ungültige Spurlautstärke.")
            if not math.isfinite(track.pan) or not -1 <= track.pan <= 1:
                raise ValueError("Ungültiges Panorama.")
            tracks.append(track)
        master = float(data.get("master", 0.8))
        if not math.isfinite(master) or not 0 <= master <= 1:
            raise ValueError("Ungültige Masterlautstärke.")
        return cls(name=str(data["name"]), rate=RATE, tracks=tracks, master=master)


class History:
    """Metadaten-Snapshots; große Audioarrays werden nicht kopiert."""
    def __init__(self):
        self.undo_stack: list[Project] = []
        self.redo_stack: list[Project] = []

    def push(self, project: Project):
        self.undo_stack.append(deepcopy(project))
        self.undo_stack = self.undo_stack[-100:]
        self.redo_stack.clear()

    def undo(self, project: Project) -> Project:
        if not self.undo_stack:
            return project
        self.redo_stack.append(deepcopy(project))
        return self.undo_stack.pop()

    def redo(self, project: Project) -> Project:
        if not self.redo_stack:
            return project
        self.undo_stack.append(deepcopy(project))
        return self.redo_stack.pop()


def split_clip(track: Track, clip_id: str, position: int):
    for index, clip in enumerate(track.clips):
        if clip.id == clip_id and clip.start < position < clip.end:
            left = position - clip.start
            track.clips[index:index + 1] = [
                Clip(clip.asset, clip.start, clip.offset, left),
                Clip(clip.asset, position, clip.offset + left, clip.length - left),
            ]
            return
    raise ValueError("Die Teilposition muss innerhalb des Clips liegen.")

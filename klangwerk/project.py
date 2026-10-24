from __future__ import annotations

from pathlib import Path
import json
import os
import shutil

from klangwerk.model import Project


def atomic_json(path: Path, document: dict):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as file:
        json.dump(document, file, ensure_ascii=False, indent=2)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary, path)


def save_project(path: Path, project: Project, assets, cancel, progress=lambda p: None):
    """Portables Manifest plus unveränderliche Audioassets im Nachbarverzeichnis."""
    path = Path(path)
    media = path.parent / (path.name + ".audio")
    media.mkdir(parents=True, exist_ok=True)
    asset_ids = sorted({c.asset for t in project.tracks for c in t.clips})
    mappings = {}
    for index, asset_id in enumerate(asset_ids):
        from klangwerk.audio.assets import Cancelled
        if cancel.is_set():
            raise Cancelled()
        target = media / f"{asset_id}.npy"
        if not target.exists():
            temporary = target.with_suffix(".tmp")
            try:
                with open(assets.data[asset_id].filename, "rb") as source, temporary.open("wb") as dest:
                    while block := source.read(4 * 1024 * 1024):
                        if cancel.is_set():
                            raise Cancelled()
                        dest.write(block)
                    dest.flush()
                    os.fsync(dest.fileno())
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
        mappings[asset_id] = f"{media.name}/{target.name}"
        progress(int((index + 1) / max(1, len(asset_ids)) * 95))
    document = {"format": "klangwerk", "version": 1, "project": project.to_dict(), "assets": mappings}
    from klangwerk.audio.assets import Cancelled
    if cancel.is_set():
        raise Cancelled()
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    atomic_json(path, document)
    progress(100)


def load_project(path: Path, assets, cancel, progress=lambda p: None):
    path = Path(path)
    with path.open(encoding="utf-8") as file:
        document = json.load(file)
    if document.get("format") != "klangwerk" or document.get("version") != 1:
        raise ValueError("Unbekanntes Projektformat oder nicht unterstützte Version.")
    project = Project.from_dict(document["project"])
    # Erst alle Assets prüfen, dann den gemeinsamen Cache verändern.
    from klangwerk.audio.assets import Cancelled
    from klangwerk.audio.assets import Assets
    staged = Assets(assets.directory)
    for index, (asset_id, relative) in enumerate(document["assets"].items()):
        if cancel.is_set():
            raise Cancelled()
        resolved = (path.parent / relative).resolve()
        if not resolved.is_relative_to(path.parent.resolve()):
            raise ValueError("Projekt verweist auf Audiodateien außerhalb seines Ordners.")
        staged.register(resolved, asset_id, cancel)
        progress(int((index + 1) / max(1, len(document["assets"])) * 100))
    for track in project.tracks:
        for clip in track.clips:
            if clip.asset not in staged.data or clip.offset + clip.length > len(staged.data[clip.asset]):
                raise ValueError("Eine Audiodatei fehlt oder ein Clip überschreitet ihre Länge.")
    assets.data.update(staged.data)
    assets.peaks.update(staged.peaks)
    return project

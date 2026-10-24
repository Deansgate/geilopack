"""Installierte Lizenztexte mit Pfaden erhalten; Fehler verhindern stilles Weglassen."""
from importlib.metadata import distribution
from pathlib import Path
import shutil

packages = ["numpy", "scipy", "soundfile", "sounddevice", "cffi", "pycparser",
            "PySide6", "PySide6-Essentials", "PySide6-Addons", "shiboken6",
            "torch", "torchaudio", "demucs", "dora-search", "einops", "julius",
            "lameenc", "openunmix", "PyYAML", "tqdm", "omegaconf", "retrying",
            "submitit", "treetable", "cloudpickle", "sympy", "mpmath", "filelock",
            "networkx", "Jinja2", "MarkupSafe", "fsspec", "typing_extensions"]
root = Path("build/licenses")
root.mkdir(parents=True, exist_ok=True)
for package in packages:
    dist = distribution(package)
    dest = root / package
    dest.mkdir(exist_ok=True)
    (dest / "METADATA.txt").write_text(dist.read_text("METADATA") or "", encoding="utf-8")
    count = 0
    for file in dist.files or []:
        if any(word in str(file).lower() for word in ("license", "copying", "copyright", "notice")):
            source = Path(dist.locate_file(file))
            if source.is_file():
                target = dest / str(file).replace("..", "_parent_")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                count += 1
    if package in {"PySide6", "PySide6-Essentials", "PySide6-Addons", "shiboken6"}:
        # 6.8.3-Wheels deklarieren Lizenzen in METADATA, enthalten jedoch keine Texte.
        qt_licenses = Path(__file__).parent / "licenses" / "qt"
        required = ["LGPL-3.0-only.txt", "GPL-2.0-only.txt", "GPL-3.0-only.txt"]
        for name in required:
            source = qt_licenses / name
            if not source.is_file():
                raise RuntimeError(f"Erforderlicher Qt-Lizenztext fehlt: {source}")
            shutil.copy2(source, dest / name)
            count += 1
        shutil.copy2(qt_licenses / "QUELLEN.md", dest / "QUELLEN.md")
    if not count:
        raise RuntimeError(f"Keine Lizenzdatei für {package} gefunden; manuell vor Release prüfen.")
print("Lizenzdateien gesammelt; Qt-/Codec-Binärlizenzen vor Veröffentlichung zusätzlich prüfen.")
shutil.copytree(Path(__file__).parent / "licenses" / "demucs", root / "demucs-model", dirs_exist_ok=True)

# Drittanbieter und Weitergabe

Der eigene Klangwerk-Quelltext steht unter MIT. Die Abhängigkeiten behalten ihre
eigenen Lizenzen. `packaging/collect-licenses.py` sammelt ihre installierten
Lizenztexte und Metadaten für den Windows-Build. Diese Übersicht ersetzt die
Lizenztexte nicht.

| Bestandteil | Lizenz / Hinweis |
| --- | --- |
| NumPy, SciPy | BSD; mitgelieferte numerische Bibliotheken haben zusätzliche Notices |
| SoundFile | BSD-3-Clause; libsndfile LGPL-2.1-or-later und Codec-Notices beachten |
| SoundDevice | MIT; PortAudio MIT und seine Plattformhinweise |
| CFFI | MIT; libffi-Notices beachten |
| pycparser | BSD-3-Clause |
| PySide6, Shiboken6 | LGPLv3/GPLv3 oder kommerzielle Lizenz; verwendete Qt-Module prüfen |
| Qt | Dynamische Bibliotheken im Onedir-Build austauschbar lassen; LGPLv3-Text,
  Notices und korrespondierende Quellcode-/Bezugsinformationen bei Weitergabe bereitstellen |
| PyInstaller | GPL mit Bootloader-Ausnahme; Build-Werkzeug |
| Inno Setup | Eigene Inno-Setup-Lizenz; Build-Werkzeug |

Ab Version 0.2 werden zusätzlich CPU-PyTorch/TorchAudio (BSD), Demucs (MIT),
Dora, Julius, Einops und Open-Unmix (MIT) verwendet. Der offizielle HTDemucs-
Checkpoint wird separat nach Benutzerentscheidung geladen; Kennung, Hash und
MIT-Lizenzhinweise liegen in `packaging/licenses/demucs/`.
Die Lizenzsammlung umfasst auch transitive KI-Abhängigkeiten. Dazu zählen
Lameenc (LGPL, ungenutzte Demucs-CLI-Abhängigkeit), tqdm (MPL/MIT), Retrying
(Apache), SymPy/MPMath und weitere Komponenten mit ihren jeweiligen Notices.
Die tatsächlich gebündelten Binärbibliotheken müssen vor Veröffentlichung
zusätzlich geprüft werden.

Es werden nur Qt Core/Gui/Widgets verwendet. Keine FFmpeg-, Pedalboard- oder
kommerziellen Cloud-Dienste enthalten. MP3-Import erfolgt über
die MP3-Unterstützung der mitgelieferten libsndfile-Version. Vor öffentlicher
Weitergabe sind die tatsächlich enthaltenen DLLs, Lizenztexte, Qt-Quellcodezugang
und zusätzliche Codec-/BLAS-Lizenzen zu prüfen. Kein rechtliches Prüfergebnis
wird behauptet. Der Build ist eine Entwicklungsdistribution.

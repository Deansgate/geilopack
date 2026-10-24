import sys
import traceback
from pathlib import Path
from PySide6.QtCore import QStandardPaths, QTranslator, QLibraryInfo
from PySide6.QtWidgets import QApplication, QMessageBox


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--separate-worker":
        from klangwerk.ai.worker import main as worker_main
        return worker_main(sys.argv[2])
    app = QApplication(sys.argv)
    app.setApplicationName("Klangwerk")
    app.setOrganizationName("KlangwerkLocal")
    app.setStyle("Fusion")
    translator = QTranslator(app)
    if translator.load("qtbase_de", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(translator)
    app._german_translator = translator
    app.setStyleSheet("""
        QWidget { background: #192231; color: #e4ebf5; font-size: 13px; }
        QPushButton { background: #304257; border: 1px solid #4c6078; padding: 7px 11px; border-radius: 5px; }
        QPushButton:hover { background: #426075; }
        QPushButton:disabled { color: #7d8797; background: #252d39; }
        QMenuBar, QMenu, QHeaderView::section { background: #243247; padding: 5px; }
        QSlider::groove:horizontal { background: #3a4b60; height: 5px; }
        QSlider::handle:horizontal { background: #79cbb7; width: 13px; margin: -5px 0; border-radius: 6px; }
        QProgressBar { border: 1px solid #4c6078; text-align: center; }
        QProgressBar::chunk { background: #3c9683; }
    """)
    directory = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
    try:
        directory.mkdir(parents=True, exist_ok=True)
        from klangwerk.ui.window import Window
    except Exception as exc:
        QMessageBox.critical(None, "Klangwerk kann nicht starten", f"Lokaler Datenordner oder Audio-Bibliothek nicht verfügbar.\nBitte die Anwendung neu installieren oder die Schreibrechte prüfen.\n\n{exc}")
        return 1
    def report_exception(kind, value, tb):
        try:
            with (directory / "fehler.log").open("a", encoding="utf-8") as log:
                traceback.print_exception(kind, value, tb, file=log)
        except OSError:
            pass
        QMessageBox.critical(None, "Unerwarteter Fehler", f"{value}\n\nBitte das Projekt nach Möglichkeit unter einem neuen Namen speichern. Der Fehlerbericht bleibt lokal im Datenordner.")
    sys.excepthook = report_exception
    window = Window(directory)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

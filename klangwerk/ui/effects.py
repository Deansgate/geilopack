from copy import deepcopy
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QCheckBox, QGroupBox,
    QFormLayout, QDoubleSpinBox, QDialogButtonBox)


class EffectsDialog(QDialog):
    """Einstellungen erst bei Übernehmen ändern; Original bleibt im Assetcache."""
    def __init__(self, track, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Spureffekte · {track.name}")
        self.settings = deepcopy(track.effects)
        self.controls = {}
        layout = QVBoxLayout(self)
        hint = QLabel("Effekte wirken auf die gesamte Spur. Zum Vergleichen Effekte ein-/ausschalten und erneut abspielen.\n"
                      "Das Original bleibt erhalten. Effekte bitte bei gestoppter Wiedergabe ändern.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.enabled = QCheckBox("Spureffekte einschalten")
        self.enabled.setChecked(self.settings.enabled)
        layout.addWidget(self.enabled)
        groups = [
            ("eq", "EQ · drei breite Bänder", [
                ("low_db", "Tiefen · 150 Hz", -12, 12, " dB", 1),
                ("mid_db", "Mitten · 1,8 kHz", -12, 12, " dB", 1),
                ("high_db", "Höhen · 8 kHz", -12, 12, " dB", 1)]),
            ("compressor", "Kompression · Pegel glätten", [
                ("threshold_db", "Schwelle", -48, 0, " dB", 1),
                ("ratio", "Verhältnis", 1, 10, " : 1", .5),
                ("makeup_db", "Pegel nach Kompression", 0, 12, " dB", 1)]),
            ("reverb", "Hall · fester kleiner Raum", [
                ("reverb_mix", "Hallanteil", 0, .5, "", .05)]),
            ("delay", "Delay · Echo", [
                ("delay_ms", "Echoabstand", 50, 1000, " ms", 10),
                ("delay_feedback", "Rückkopplung", 0, .6, "", .05),
                ("delay_mix", "Echoanteil", 0, .5, "", .05)]),
        ]
        for key, title, fields in groups:
            group = QGroupBox(title)
            group.setCheckable(True)
            group.setChecked(getattr(self.settings, key))
            self.controls[key] = group
            form = QFormLayout(group)
            for field, label, low, high, suffix, step in fields:
                control = QDoubleSpinBox()
                control.setRange(low, high)
                control.setDecimals(2)
                control.setSingleStep(step)
                control.setSuffix(suffix)
                control.setValue(getattr(self.settings, field))
                control.setToolTip("0 = kein Anteil; 0,5 = 50 %" if high <= .6 else label)
                self.controls[field] = control
                form.addRow(label, control)
            layout.addWidget(group)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Übernehmen")
        buttons.button(QDialogButtonBox.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        self.settings.enabled = self.enabled.isChecked()
        for key, control in self.controls.items():
            setattr(self.settings, key, control.isChecked() if isinstance(control, QGroupBox) else control.value())
        self.settings.validate()
        super().accept()

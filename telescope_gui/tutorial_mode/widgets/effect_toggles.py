"""Effect toggle checkboxes for Act 3 scenarios."""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QCheckBox
from PyQt6.QtCore import pyqtSignal


_ALL_EFFECTS = [
    ("obstruction",  "Obstruction"),
    ("spider_vanes", "Spider Vanes"),
    ("coma",         "Coma"),
    ("vignetting",   "Vignetting"),
    ("seeing",       "Seeing"),
    ("chromatic",    "Chromatic"),
]


class EffectTogglesPanel(QWidget):
    """Row of checkboxes for toggling individual optical effects.

    Only effects listed in set_visible_toggles() are shown; the rest
    are hidden. Emits toggled whenever any visible checkbox changes.
    """

    toggled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)  # Hidden until an Act 3 scenario is loaded
        self._checkboxes: dict[str, QCheckBox] = {}
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(16)

        lbl = QLabel("Toggle effects:")
        lbl.setStyleSheet("font-weight: bold; font-size: 9pt; color: #555;")
        layout.addWidget(lbl)

        for key, display in _ALL_EFFECTS:
            cb = QCheckBox(display)
            cb.setChecked(True)
            cb.toggled.connect(lambda _checked: self.toggled.emit())
            layout.addWidget(cb)
            self._checkboxes[key] = cb

        layout.addStretch()

    def set_visible_toggles(self, keys: tuple[str, ...]) -> None:
        """Show only the toggles relevant to the current scenario."""
        has_any = bool(keys)
        for key, cb in self._checkboxes.items():
            cb.setVisible(key in keys)
            if key in keys:
                cb.setChecked(True)  # Reset to enabled on scenario load
        self.setVisible(has_any)

    def get_active_effects(self) -> dict[str, bool]:
        """Return {effect_key: is_enabled} for all visible toggles."""
        return {
            key: cb.isChecked()
            for key, cb in self._checkboxes.items()
            if cb.isVisible()
        }

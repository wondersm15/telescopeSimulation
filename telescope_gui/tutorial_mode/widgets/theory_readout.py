"""Numeric theory-vs-simulation comparison panel."""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt


class TheoryReadoutPanel(QWidget):
    """Displays 'Theory: X   Sim: Y   Δ: Z%' comparisons.

    Shows quantitative agreement between theoretical predictions and
    simulation output for the current scenario.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(60)
        self.setStyleSheet(
            "background-color: #f0f4f8; border: 1px solid #c8d0da; "
            "border-radius: 4px;"
        )
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(24)

        self.metric_label = QLabel("")
        self.metric_label.setStyleSheet("font-size: 9pt; color: #555; font-style: italic;")

        self.theory_label = QLabel("Theory: —")
        self.theory_label.setStyleSheet("font-weight: bold; color: #0055cc; font-size: 10pt;")

        self.sim_label = QLabel("Sim: —")
        self.sim_label.setStyleSheet("font-weight: bold; color: #007700; font-size: 10pt;")

        self.delta_label = QLabel("")
        self.delta_label.setStyleSheet("color: #666; font-size: 9pt;")

        self.formula_label = QLabel("")
        self.formula_label.setStyleSheet("color: #888; font-size: 8pt; font-style: italic;")

        layout.addWidget(self.metric_label)
        layout.addWidget(self.theory_label)
        layout.addWidget(self.sim_label)
        layout.addWidget(self.delta_label)
        layout.addStretch()
        layout.addWidget(self.formula_label)

    def update_theory(self, theory_value: float, unit: str = "",
                      label: str = "", formula: str = "") -> None:
        """Show theory value only (before simulation runs)."""
        unit_str = f" {unit}" if unit else ""
        self.metric_label.setText(label)
        self.theory_label.setText(f"Theory: {theory_value:.3g}{unit_str}")
        self.sim_label.setText("Sim: —")
        self.delta_label.setText("")
        self.formula_label.setText(formula)

    def update_values(self, theory_value: float, sim_value: float,
                      unit: str = "", label: str = "", formula: str = "") -> None:
        """Update both theory and simulation values with delta."""
        unit_str = f" {unit}" if unit else ""
        if theory_value != 0:
            delta_pct = abs(sim_value - theory_value) / abs(theory_value) * 100.0
            delta_str = f"\u0394 {delta_pct:.1f}%"
            color = "#007700" if delta_pct < 5 else "#cc6600" if delta_pct < 15 else "#cc0000"
        else:
            delta_str = ""
            color = "#666"

        self.metric_label.setText(label)
        self.theory_label.setText(f"Theory: {theory_value:.3g}{unit_str}")
        self.sim_label.setText(f"Sim: {sim_value:.3g}{unit_str}")
        self.delta_label.setText(delta_str)
        self.delta_label.setStyleSheet(f"color: {color}; font-size: 9pt; font-weight: bold;")
        self.formula_label.setText(formula)

    def show_extra(self, extra_text: str) -> None:
        """Show an extra info string (e.g. 'Seeing-limited' warning)."""
        self.delta_label.setText(extra_text)
        self.delta_label.setStyleSheet("color: #cc6600; font-size: 9pt; font-weight: bold;")

    def clear(self) -> None:
        self.metric_label.setText("")
        self.theory_label.setText("Theory: —")
        self.sim_label.setText("Sim: —")
        self.delta_label.setText("")
        self.formula_label.setText("")

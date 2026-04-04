"""Left sidebar widget showing the scenario list grouped by act."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QLabel, QPushButton
)
from PyQt6.QtCore import pyqtSignal, Qt

from telescope_gui.tutorial_mode.scenario_registry import get_scenarios_by_act


_ACT_COLORS = {1: "#2a6496", 2: "#5a3e7a", 3: "#2e6b4f"}
_BTN_ACTIVE = "text-align: left; padding: 4px 8px 4px 16px; background-color: #d6e8f7; font-weight: bold; border-left: 3px solid #2a6496;"
_BTN_ENABLED = "text-align: left; padding: 4px 8px 4px 16px; border-left: 3px solid transparent;"
_BTN_DISABLED = "text-align: left; padding: 4px 8px 4px 16px; color: #aaa; border-left: 3px solid transparent;"


class ScenarioSidebar(QWidget):
    """Left sidebar showing all scenarios grouped by act.

    Emits scenario_selected(scenario_id) when user clicks an implemented scenario.
    Placeholder scenarios are shown but disabled ("coming soon").
    """

    scenario_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(240)
        self._buttons: dict[str, QPushButton] = {}
        self._active_id: str | None = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none;")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 4, 0, 8)
        content_layout.setSpacing(0)

        scenarios_by_act = get_scenarios_by_act()
        act_titles = {
            1: "Act 1 — Isolated Effects",
            2: "Act 2 — Compounding",
            3: "Act 3 — Real Objects",
        }

        for act_num in [1, 2, 3]:
            scenarios = scenarios_by_act.get(act_num, [])
            if not scenarios:
                continue

            act_label = QLabel(act_titles[act_num])
            color = _ACT_COLORS[act_num]
            act_label.setStyleSheet(
                f"font-weight: bold; font-size: 9pt; color: {color}; "
                f"padding: 8px 8px 4px 8px; background: transparent;"
            )
            content_layout.addWidget(act_label)

            for scenario in scenarios:
                if scenario.implemented:
                    text = f"  {scenario.title}"
                    btn = QPushButton(text)
                    btn.setFlat(True)
                    btn.setStyleSheet(_BTN_ENABLED)
                    btn.clicked.connect(
                        lambda checked, sid=scenario.id: self._on_clicked(sid)
                    )
                else:
                    text = f"  {scenario.title}"
                    btn = QPushButton(text)
                    btn.setFlat(True)
                    btn.setEnabled(False)
                    btn.setToolTip("Coming soon")
                    btn.setStyleSheet(_BTN_DISABLED)

                content_layout.addWidget(btn)
                self._buttons[scenario.id] = btn

        content_layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _on_clicked(self, scenario_id: str):
        self.set_active(scenario_id)
        self.scenario_selected.emit(scenario_id)

    def set_active(self, scenario_id: str):
        """Highlight the active scenario button."""
        self._active_id = scenario_id
        for sid, btn in self._buttons.items():
            if sid == scenario_id:
                btn.setStyleSheet(_BTN_ACTIVE)
            elif btn.isEnabled():
                btn.setStyleSheet(_BTN_ENABLED)

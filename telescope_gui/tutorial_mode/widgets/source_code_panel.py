"""Collapsible source-code viewer panel for the Tutorial tab.

Shows the implementation of the current scenario's plot function and its
key helper functions via inspect.getsource(), so users can see the physics
happening under the hood.
"""

from __future__ import annotations

import inspect

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit, QSizePolicy
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt


class SourceCodePanel(QWidget):
    """Collapsible panel that displays source code of plot functions.

    Starts collapsed. Toggle button expands/collapses. Content is a
    monospace read-only dark-themed text area matching the terminal style.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(4)

        self.toggle_btn = QPushButton("Show Source Code ▼")
        self.toggle_btn.setStyleSheet(
            "font-size: 8pt; color: #2a6496; background: transparent; "
            "border: none; text-align: left; padding: 2px 0;")
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self._toggle)
        layout.addWidget(self.toggle_btn)

        self.code_view = QTextEdit()
        self.code_view.setReadOnly(True)
        self.code_view.setFont(QFont("Courier", 8))
        self.code_view.setStyleSheet(
            "background: #1e1e1e; color: #d4d4d4; border: 1px solid #444; "
            "border-radius: 3px; padding: 4px;")
        self.code_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.code_view.setMinimumHeight(200)
        self.code_view.setMaximumHeight(400)
        self.code_view.setVisible(False)
        layout.addWidget(self.code_view)

    def _toggle(self):
        self._expanded = not self._expanded
        self.code_view.setVisible(self._expanded)
        if self._expanded:
            self.toggle_btn.setText("Hide Source Code ▲")
        else:
            self.toggle_btn.setText("Show Source Code ▼")

    def set_functions(self, func_list: list):
        """Display source code for the given list of callables.

        Each function is shown with a header comment separating it.
        If source cannot be retrieved (e.g. C extension), a note is shown.
        """
        parts = []
        for func in func_list:
            name = getattr(func, "__name__", repr(func))
            parts.append(f"# {'─' * 60}")
            parts.append(f"# {name}")
            parts.append(f"# {'─' * 60}")
            try:
                parts.append(inspect.getsource(func))
            except (OSError, TypeError):
                parts.append(f"# (source not available for {name})\n")
        self.code_view.setPlainText("\n".join(parts))

    def clear(self):
        self.code_view.setPlainText("")

"""Read-only terminal panel showing Python API calls for the current scenario."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt


class TerminalPanel(QWidget):
    """Dark-themed read-only panel displaying Python API calls.

    Shows the actual telescope_sim API calls being executed by the GUI,
    so users can learn the programmatic interface and copy commands for
    use in their own scripts.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(175)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Header row
        header_row = QHBoxLayout()
        header = QLabel("Python API")
        header.setStyleSheet("font-weight: bold; font-size: 9pt; color: #888;")
        header_row.addWidget(header)
        header_row.addStretch()

        copy_btn = QPushButton("Copy")
        copy_btn.setFixedSize(50, 20)
        copy_btn.setStyleSheet(
            "font-size: 8pt; padding: 1px 4px; color: #aaa; "
            "background: #333; border: 1px solid #555; border-radius: 3px;"
        )
        copy_btn.clicked.connect(self._copy_to_clipboard)
        header_row.addWidget(copy_btn)
        layout.addLayout(header_row)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Courier", 9))
        self.text_edit.setStyleSheet(
            "background-color: #1e1e1e; color: #d4d4d4; "
            "border: 1px solid #3a3a3a; padding: 4px; "
            "selection-background-color: #264f78;"
        )
        layout.addWidget(self.text_edit)

    def set_command(self, command_str: str) -> None:
        """Display the given Python command string."""
        self.text_edit.setPlainText(command_str)

    def clear(self) -> None:
        self.text_edit.clear()

    def _copy_to_clipboard(self) -> None:
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.text_edit.toPlainText())

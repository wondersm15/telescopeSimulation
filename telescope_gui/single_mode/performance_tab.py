"""
Performance tab for single telescope mode.

Shows PSF analysis, spot diagram, and performance metrics.
"""

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout


class PerformanceTab(QWidget):
    """Performance tab - PSF analysis and metrics."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()
        label = QLabel("Performance Tab - Coming Soon\n\nWill show:\n- PSF Analysis\n- Spot Diagram\n- Performance Metrics")
        label.setStyleSheet("font-size: 14pt; padding: 50px;")
        layout.addWidget(label)

        self.setLayout(layout)

"""Side-by-side before/after matplotlib canvas panel."""

from matplotlib.figure import Figure
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel
)
from PyQt6.QtCore import Qt

from telescope_gui.widgets.matplotlib_canvas import MatplotlibCanvas


class BeforeAfterPanel(QWidget):
    """Two MatplotlibCanvas widgets side by side with labels.

    The 'before' side shows a static baseline image rendered once when
    a scenario loads. The 'after' side is updated whenever the user
    tweaks parameters and clicks Update.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.before_canvas = MatplotlibCanvas(figsize=(5, 5))
        self.after_canvas = MatplotlibCanvas(figsize=(5, 5))

        for canvas, attr in [(self.before_canvas, "before"), (self.after_canvas, "after")]:
            col = QVBoxLayout()
            col.setSpacing(2)
            label = QLabel("—")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-weight: bold; font-size: 9pt; color: #444;")
            setattr(self, f"{attr}_label", label)
            col.addWidget(label)
            col.addWidget(canvas)
            layout.addLayout(col, stretch=1)

    def set_before(self, fig: Figure, label: str = "Baseline") -> None:
        """Set the static before image."""
        self.before_label.setText(label)
        self.before_canvas.set_figure(fig)

    def set_after(self, fig: Figure, label: str = "With Effect") -> None:
        """Update the live after image."""
        self.after_label.setText(label)
        self.after_canvas.set_figure(fig)

    def clear_after(self) -> None:
        """Reset the after canvas to blank."""
        self.after_label.setText("—")
        self.after_canvas.figure.clear()
        self.after_canvas.canvas.draw()

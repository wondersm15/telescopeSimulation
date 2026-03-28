"""
Simulated images comparison tab for comparison mode.

Shows side-by-side simulated images of multiple telescope configurations.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt

from telescope_gui.widgets.matplotlib_canvas import MatplotlibCanvas
from telescope_gui.widgets.telescope_controls import TelescopeControlPanel
from telescope_gui.widgets.source_controls import get_source, get_seeing
from telescope_gui.telescope_builder import build_telescope
from telescope_sim.plotting import plot_source_image

SIDEBAR_WIDTH = 220


class ImagesTab(QWidget):
    """Simulated images comparison tab - side-by-side images."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # ---- T1 sidebar (left) ----
        t1_scroll = QScrollArea()
        t1_scroll.setWidgetResizable(True)
        t1_scroll.setFixedWidth(SIDEBAR_WIDTH)
        t1_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        t1_container = QWidget()
        t1_layout = QVBoxLayout(t1_container)
        t1_layout.setContentsMargins(6, 6, 6, 6)
        t1_layout.setSpacing(4)

        header1 = QLabel("Telescope 1")
        header1.setStyleSheet("font-weight: bold; font-size: 12pt; padding-bottom: 4px;")
        header1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t1_layout.addWidget(header1)

        self.panel1 = TelescopeControlPanel(
            number=1, layout_mode="sidebar", show_group_box=True,
            default_type="Newtonian", default_fratio=5.0
        )
        t1_layout.addWidget(self.panel1)

        # Source selection
        t1_layout.addWidget(QLabel("Source:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems([
            "Jupiter", "Saturn", "Moon", "Star Field",
            "Point Source (Star)", "None"
        ])
        t1_layout.addWidget(self.source_combo)

        # Seeing selection
        t1_layout.addWidget(QLabel("Seeing:"))
        self.seeing_combo = QComboBox()
        self.seeing_combo.addItems(["Excellent", "Good", "Average", "Poor", "None"])
        self.seeing_combo.setCurrentText("Good")
        t1_layout.addWidget(self.seeing_combo)

        self.update_button = QPushButton("Update Comparison")
        self.update_button.clicked.connect(self.update_view)
        t1_layout.addWidget(self.update_button)

        t1_layout.addStretch()
        t1_scroll.setWidget(t1_container)
        main_layout.addWidget(t1_scroll)

        # ---- T1 canvas ----
        self.canvas1 = MatplotlibCanvas(figsize=(8, 6))
        self.canvas1.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.canvas1, stretch=1)

        # ---- T2 canvas ----
        self.canvas2 = MatplotlibCanvas(figsize=(8, 6))
        self.canvas2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.canvas2, stretch=1)

        # ---- T2 sidebar (right) ----
        t2_scroll = QScrollArea()
        t2_scroll.setWidgetResizable(True)
        t2_scroll.setFixedWidth(SIDEBAR_WIDTH)
        t2_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        t2_container = QWidget()
        t2_layout = QVBoxLayout(t2_container)
        t2_layout.setContentsMargins(6, 6, 6, 6)
        t2_layout.setSpacing(4)

        header2 = QLabel("Telescope 2")
        header2.setStyleSheet("font-weight: bold; font-size: 12pt; padding-bottom: 4px;")
        header2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t2_layout.addWidget(header2)

        self.panel2 = TelescopeControlPanel(
            number=2, layout_mode="sidebar", show_group_box=True,
            default_type="Cassegrain", default_fratio=10.0
        )
        t2_layout.addWidget(self.panel2)

        t2_layout.addStretch()
        t2_scroll.setWidget(t2_container)
        main_layout.addWidget(t2_scroll)

        self.setLayout(main_layout)

        # Initial render
        self.update_view()

    def update_view(self):
        """Update simulated images comparison."""
        try:
            source = get_source(self.source_combo.currentText())
            seeing = get_seeing(self.seeing_combo.currentText())

            if source is None:
                return

            for panel, canvas in [(self.panel1, self.canvas1), (self.panel2, self.canvas2)]:
                telescope = panel.build()

                result = plot_source_image(
                    telescope,
                    source,
                    seeing_arcsec=seeing
                )

                if isinstance(result, list):
                    fig = result[0]
                    for extra_fig in result[1:]:
                        if extra_fig is not None:
                            plt.close(extra_fig)
                else:
                    fig = result

                canvas.set_figure(fig)
                plt.close(fig)

        except Exception as e:
            print(f"Error updating images comparison: {e}")
            import traceback
            traceback.print_exc()

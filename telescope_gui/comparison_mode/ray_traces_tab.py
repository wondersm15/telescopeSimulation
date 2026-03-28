"""
Ray traces comparison tab for comparison mode.

Shows side-by-side ray traces of multiple telescope configurations.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt

from telescope_gui.widgets.matplotlib_canvas import MatplotlibCanvas
from telescope_gui.widgets.telescope_controls import TelescopeControlPanel
from telescope_gui.telescope_builder import build_telescope
from telescope_sim.plotting import plot_ray_trace
from telescope_sim.source.light_source import create_parallel_rays

SIDEBAR_WIDTH = 220


class RayTracesTab(QWidget):
    """Ray traces comparison tab - side-by-side ray traces."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # T1 sidebar (left)
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

        self.update_button = QPushButton("Update Comparison")
        self.update_button.clicked.connect(self.update_view)
        t1_layout.addWidget(self.update_button)

        t1_layout.addStretch()
        t1_scroll.setWidget(t1_container)
        main_layout.addWidget(t1_scroll)

        # T1 ray trace canvas
        self.canvas1 = MatplotlibCanvas(figsize=(8, 6))
        self.canvas1.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.canvas1, stretch=1)

        # T2 ray trace canvas
        self.canvas2 = MatplotlibCanvas(figsize=(8, 6))
        self.canvas2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.canvas2, stretch=1)

        # T2 sidebar (right)
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
        """Update ray trace comparison."""
        try:
            panels = [self.panel1, self.panel2]
            canvases = [self.canvas1, self.canvas2]

            # First pass: create all figures and collect axis limits
            figures = []
            all_xlims = []
            all_ylims = []

            for panel in panels:
                telescope = panel.build()

                rays = create_parallel_rays(
                    num_rays=11,
                    aperture_diameter=telescope.primary_diameter,
                    entry_height=telescope.tube_length * 1.15,
                )
                telescope.trace_rays(rays)
                components = telescope.get_components_for_plotting()

                ttype = panel.type_combo.currentText()
                title = f"{telescope.primary_diameter:.0f}mm f/{telescope.focal_ratio:.1f} {ttype}"
                fig = plot_ray_trace(rays, components, title=title)
                figures.append(fig)

                for ax in fig.axes:
                    all_xlims.append(ax.get_xlim())
                    all_ylims.append(ax.get_ylim())

            # Compute shared axis limits
            if all_xlims and all_ylims:
                shared_xlim = (min(lim[0] for lim in all_xlims),
                              max(lim[1] for lim in all_xlims))
                shared_ylim = (min(lim[0] for lim in all_ylims),
                              max(lim[1] for lim in all_ylims))

                for fig in figures:
                    for ax in fig.axes:
                        ax.set_xlim(shared_xlim)
                        ax.set_ylim(shared_ylim)

            # Display
            for canvas, fig in zip(canvases, figures):
                canvas.set_figure(fig)
                plt.close(fig)

        except Exception as e:
            print(f"Error updating ray traces comparison: {e}")
            import traceback
            traceback.print_exc()

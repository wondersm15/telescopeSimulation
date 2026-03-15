"""
Design tab for single telescope mode.

Shows ray trace and simulated image side-by-side.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QDoubleSpinBox, QGroupBox
)
from PyQt6.QtCore import pyqtSignal
import matplotlib.pyplot as plt

from telescope_gui.widgets.matplotlib_canvas import MatplotlibCanvas
from telescope_sim.geometry import NewtonianTelescope, CassegrainTelescope, RefractingTelescope, MaksutovCassegrainTelescope
from telescope_sim.plotting import plot_ray_trace
from telescope_sim.plotting.ray_trace_plot import _render_source_through_telescope
from telescope_sim.source.sources import JupiterSource, MoonSource


class DesignTab(QWidget):
    """Design tab - ray trace + simulated image side-by-side."""

    config_changed = pyqtSignal()  # Signal when configuration changes

    def __init__(self, parent=None):
        super().__init__(parent)

        # Default configuration
        self.telescope_type = "newtonian"
        self.primary_diameter = 200.0
        self.focal_length = 1000.0
        self.primary_type = "parabolic"
        self.source_type = "jupiter"
        self.seeing = "good"

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout()

        # Top: Side-by-side plots
        plots_layout = QHBoxLayout()

        # Left: Ray trace
        self.ray_trace_canvas = MatplotlibCanvas(figsize=(7, 6))
        plots_layout.addWidget(self.ray_trace_canvas)

        # Right: Simulated image
        self.image_canvas = MatplotlibCanvas(figsize=(7, 6))
        plots_layout.addWidget(self.image_canvas)

        main_layout.addLayout(plots_layout)

        # Bottom: Controls
        controls_group = QGroupBox("Controls")
        controls_layout = QGridLayout()

        row = 0

        # Telescope type
        controls_layout.addWidget(QLabel("Telescope Type:"), row, 0)
        self.telescope_combo = QComboBox()
        self.telescope_combo.addItems(["Newtonian", "Cassegrain", "Refractor", "Maksutov-Cassegrain"])
        self.telescope_combo.setCurrentText("Newtonian")
        controls_layout.addWidget(self.telescope_combo, row, 1)

        # Aperture
        controls_layout.addWidget(QLabel("Aperture (mm):"), row, 2)
        self.aperture_spin = QDoubleSpinBox()
        self.aperture_spin.setRange(50.0, 500.0)
        self.aperture_spin.setSingleStep(10.0)
        self.aperture_spin.setValue(200.0)
        controls_layout.addWidget(self.aperture_spin, row, 3)

        row += 1

        # Primary type
        controls_layout.addWidget(QLabel("Primary Type:"), row, 0)
        self.primary_combo = QComboBox()
        self.primary_combo.addItems(["Parabolic", "Spherical"])
        self.primary_combo.setCurrentText("Parabolic")
        controls_layout.addWidget(self.primary_combo, row, 1)

        # f-ratio
        controls_layout.addWidget(QLabel("f-ratio:"), row, 2)
        self.fratio_spin = QDoubleSpinBox()
        self.fratio_spin.setRange(3.0, 15.0)
        self.fratio_spin.setSingleStep(0.5)
        self.fratio_spin.setValue(5.0)
        controls_layout.addWidget(self.fratio_spin, row, 3)

        row += 1

        # Source
        controls_layout.addWidget(QLabel("Source:"), row, 0)
        self.source_combo = QComboBox()
        self.source_combo.addItems(["Jupiter", "Moon", "None"])
        self.source_combo.setCurrentText("Jupiter")
        controls_layout.addWidget(self.source_combo, row, 1)

        # Seeing
        controls_layout.addWidget(QLabel("Seeing:"), row, 2)
        self.seeing_combo = QComboBox()
        self.seeing_combo.addItems(["Excellent", "Good", "Average", "Poor", "None"])
        self.seeing_combo.setCurrentText("Good")
        controls_layout.addWidget(self.seeing_combo, row, 3)

        row += 1

        # Update button
        self.update_button = QPushButton("Update View")
        self.update_button.clicked.connect(self.update_view)
        controls_layout.addWidget(self.update_button, row, 0, 1, 4)

        controls_group.setLayout(controls_layout)
        main_layout.addWidget(controls_group)

        self.setLayout(main_layout)

        # Initial render
        self.update_view()

    def build_telescope(self):
        """Build telescope object from current configuration."""
        telescope_type = self.telescope_combo.currentText().lower().replace("-", "")
        primary_diameter = self.aperture_spin.value()
        f_ratio = self.fratio_spin.value()
        focal_length = primary_diameter * f_ratio

        if telescope_type == "newtonian":
            primary_type = self.primary_combo.currentText().lower()
            telescope = NewtonianTelescope(
                primary_diameter=primary_diameter,
                focal_length=focal_length,
                primary_type=primary_type
            )
        elif telescope_type == "cassegrain":
            telescope = CassegrainTelescope(
                primary_diameter=primary_diameter,
                primary_focal_length=focal_length,
                secondary_magnification=3.0
            )
        elif telescope_type == "refractor":
            telescope = RefractingTelescope(
                primary_diameter=primary_diameter,
                focal_length=focal_length
            )
        elif telescope_type == "maksutovcassegrain":
            telescope = MaksutovCassegrainTelescope(
                primary_diameter=primary_diameter,
                primary_focal_length=focal_length,
                secondary_magnification=3.0
            )
        else:
            # Default to Newtonian
            telescope = NewtonianTelescope(
                primary_diameter=primary_diameter,
                focal_length=focal_length
            )

        return telescope

    def build_source(self):
        """Build source object from current configuration."""
        source_type = self.source_combo.currentText().lower()

        if source_type == "jupiter":
            return JupiterSource()
        elif source_type == "moon":
            return MoonSource()
        else:
            return None

    def get_seeing_value(self):
        """Convert seeing dropdown to numeric value."""
        seeing_presets = {
            "excellent": 0.8,
            "good": 1.5,
            "average": 2.5,
            "poor": 4.0,
            "none": None
        }
        seeing = self.seeing_combo.currentText().lower()
        return seeing_presets.get(seeing, None)

    def update_view(self):
        """Update both ray trace and simulated image."""
        try:
            # Build telescope and source
            telescope = self.build_telescope()
            source = self.build_source()
            seeing = self.get_seeing_value()

            # Update ray trace
            fig_ray_trace = plot_ray_trace(telescope, num_display_rays=11)
            self.ray_trace_canvas.set_figure(fig_ray_trace)
            plt.close(fig_ray_trace)  # Close to free memory

            # Update simulated image (if source selected)
            if source is not None:
                fig_image = _render_source_through_telescope(
                    telescope,
                    source,
                    seeing_arcsec=seeing,
                    polychromatic=False
                )
                self.image_canvas.set_figure(fig_image)
                plt.close(fig_image)
            else:
                # Clear image canvas
                self.image_canvas.figure.clear()
                self.image_canvas.canvas.draw()

            self.config_changed.emit()

        except Exception as e:
            print(f"Error updating view: {e}")
            import traceback
            traceback.print_exc()

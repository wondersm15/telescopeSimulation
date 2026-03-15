"""
Performance tab for single telescope mode.

Shows PSF analysis, spot diagram, and performance metrics.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QDoubleSpinBox, QGroupBox
)
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt
import numpy as np

from telescope_gui.widgets.matplotlib_canvas import MatplotlibCanvas
from telescope_sim.geometry import NewtonianTelescope, CassegrainTelescope, RefractingTelescope, MaksutovCassegrainTelescope
from telescope_sim.plotting import plot_psf_2d, plot_spot_diagram


class PerformanceTab(QWidget):
    """Performance tab - PSF analysis and metrics."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Default configuration
        self.telescope_type = "newtonian"
        self.primary_diameter = 200.0
        self.focal_length = 1000.0
        self.wavelength = 550.0  # nm

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout()

        # Top: Side-by-side plots
        plots_layout = QHBoxLayout()

        # Left: PSF
        psf_container = QVBoxLayout()
        psf_label = QLabel("Point Spread Function (PSF)")
        psf_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        psf_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        psf_container.addWidget(psf_label)

        self.psf_canvas = MatplotlibCanvas(figsize=(6, 6))
        psf_container.addWidget(self.psf_canvas)
        plots_layout.addLayout(psf_container)

        # Right: Spot Diagram
        spot_container = QVBoxLayout()
        spot_label = QLabel("Spot Diagram")
        spot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spot_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        spot_container.addWidget(spot_label)

        self.spot_canvas = MatplotlibCanvas(figsize=(6, 6))
        spot_container.addWidget(self.spot_canvas)
        plots_layout.addLayout(spot_container)

        main_layout.addLayout(plots_layout)

        # Metrics display
        self.metrics_label = QLabel("")
        self.metrics_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.metrics_label.setStyleSheet("font-size: 11pt; padding: 10px; background-color: #f0f0f0;")
        main_layout.addWidget(self.metrics_label)

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

        # f-ratio
        controls_layout.addWidget(QLabel("f-ratio:"), row, 0)
        self.fratio_spin = QDoubleSpinBox()
        self.fratio_spin.setRange(3.0, 15.0)
        self.fratio_spin.setSingleStep(0.5)
        self.fratio_spin.setValue(5.0)
        controls_layout.addWidget(self.fratio_spin, row, 1)

        # Wavelength
        controls_layout.addWidget(QLabel("Wavelength (nm):"), row, 2)
        self.wavelength_spin = QDoubleSpinBox()
        self.wavelength_spin.setRange(400.0, 700.0)
        self.wavelength_spin.setSingleStep(10.0)
        self.wavelength_spin.setValue(550.0)
        controls_layout.addWidget(self.wavelength_spin, row, 3)

        row += 1

        # Update button
        self.update_button = QPushButton("Update Analysis")
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
            telescope = NewtonianTelescope(
                primary_diameter=primary_diameter,
                focal_length=focal_length
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
            telescope = NewtonianTelescope(
                primary_diameter=primary_diameter,
                focal_length=focal_length
            )

        return telescope

    def calculate_metrics(self, telescope):
        """Calculate performance metrics."""
        wavelength_nm = self.wavelength_spin.value()
        wavelength_m = wavelength_nm * 1e-9
        aperture_m = telescope.primary_diameter * 1e-3

        # Rayleigh criterion
        rayleigh_arcsec = 1.22 * wavelength_m / aperture_m * 206265

        # Dawes limit (empirical for visual double stars)
        dawes_arcsec = 116.0 / telescope.primary_diameter

        # Airy disk diameter
        airy_disk_arcsec = 2.44 * wavelength_m / aperture_m * 206265

        return {
            "rayleigh": rayleigh_arcsec,
            "dawes": dawes_arcsec,
            "airy_disk": airy_disk_arcsec,
            "wavelength": wavelength_nm
        }

    def update_metrics_label(self, metrics):
        """Update the metrics display."""
        text = (
            f"Resolution Limits: Rayleigh = {metrics['rayleigh']:.2f}\", "
            f"Dawes = {metrics['dawes']:.2f}\" | "
            f"Airy Disk = {metrics['airy_disk']:.2f}\" | "
            f"Wavelength = {metrics['wavelength']:.0f} nm"
        )
        self.metrics_label.setText(text)

    def update_view(self):
        """Update PSF, spot diagram, and metrics."""
        try:
            telescope = self.build_telescope()
            wavelength_nm = self.wavelength_spin.value()

            # Calculate and display metrics
            metrics = self.calculate_metrics(telescope)
            self.update_metrics_label(metrics)

            # Update PSF (plot_psf_2d generates its own title)
            telescope_type = self.telescope_combo.currentText()
            fig_psf = plot_psf_2d(
                telescope,
                wavelength_nm=wavelength_nm,
                figsize=(6, 6)
            )
            self.psf_canvas.set_figure(fig_psf)
            plt.close(fig_psf)

            # Update spot diagram (requires traced rays)
            from telescope_sim.source.light_source import create_parallel_rays
            rays = create_parallel_rays(
                num_rays=21,  # More rays for better spot diagram
                aperture_diameter=telescope.primary_diameter,
                entry_height=telescope.tube_length * 1.15,
            )
            telescope.trace_rays(rays)

            title = f"{telescope.primary_diameter:.0f}mm f/{telescope.focal_ratio:.1f} {telescope_type} — Spot Diagram"
            fig_spot = plot_spot_diagram(
                rays,
                title=title,
                figsize=(6, 6)
            )
            self.spot_canvas.set_figure(fig_spot)
            plt.close(fig_spot)

        except Exception as e:
            print(f"Error updating performance view: {e}")
            import traceback
            traceback.print_exc()

"""
Performance tab for single telescope mode.

Shows PSF analysis, spot diagram, and performance metrics.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QDoubleSpinBox, QGroupBox, QCheckBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt
import numpy as np

from telescope_gui.widgets.matplotlib_canvas import MatplotlibCanvas
from telescope_sim.geometry import NewtonianTelescope, CassegrainTelescope, RefractingTelescope, MaksutovCassegrainTelescope
from telescope_sim.plotting import plot_psf_2d, plot_psf_profile, plot_spot_diagram
from matplotlib.figure import Figure
from scipy.signal import fftconvolve


class PerformanceTab(QWidget):
    """Performance tab - PSF analysis and metrics."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Default configuration
        self.telescope_type = "newtonian"
        self.primary_diameter = 200.0
        self.focal_length = 1000.0
        self.wavelength = 550.0  # nm

        # PSF display options
        self.psf_mode = "2d"  # "1d" or "2d"
        self.psf_scale = "log"  # "log" or "linear"
        self.lock_psf_axes = False
        self.locked_psf_xlim = None
        self.locked_psf_ylim = None

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

        # PSF Display Options
        psf_options_group = QGroupBox("PSF Display Options")
        psf_options_layout = QHBoxLayout()

        # PSF Mode (1D vs 2D)
        psf_options_layout.addWidget(QLabel("PSF Type:"))
        self.psf_1d_radio = QRadioButton("1D Profile")
        self.psf_2d_radio = QRadioButton("2D Image")
        self.psf_2d_radio.setChecked(True)

        self.psf_mode_group = QButtonGroup()
        self.psf_mode_group.addButton(self.psf_1d_radio)
        self.psf_mode_group.addButton(self.psf_2d_radio)

        psf_options_layout.addWidget(self.psf_1d_radio)
        psf_options_layout.addWidget(self.psf_2d_radio)

        psf_options_layout.addSpacing(20)

        # Scale (log vs linear)
        psf_options_layout.addWidget(QLabel("Scale:"))
        self.psf_log_radio = QRadioButton("Logarithmic")
        self.psf_linear_radio = QRadioButton("Linear")
        self.psf_log_radio.setChecked(True)

        self.psf_scale_group = QButtonGroup()
        self.psf_scale_group.addButton(self.psf_log_radio)
        self.psf_scale_group.addButton(self.psf_linear_radio)

        psf_options_layout.addWidget(self.psf_log_radio)
        psf_options_layout.addWidget(self.psf_linear_radio)

        psf_options_layout.addSpacing(20)

        # Lock axes
        self.lock_axes_check = QCheckBox("Lock PSF Axes")
        self.lock_axes_check.setToolTip("Keep PSF plot axes fixed when updating parameters")
        psf_options_layout.addWidget(self.lock_axes_check)

        psf_options_layout.addStretch()
        psf_options_group.setLayout(psf_options_layout)
        main_layout.addWidget(psf_options_group)

        # Connect PSF option changes to auto-update
        self.psf_1d_radio.toggled.connect(self.on_psf_options_changed)
        self.psf_2d_radio.toggled.connect(self.on_psf_options_changed)
        self.psf_log_radio.toggled.connect(self.on_psf_options_changed)
        self.psf_linear_radio.toggled.connect(self.on_psf_options_changed)

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

        # Connect lock axes checkbox
        self.lock_axes_check.toggled.connect(self.on_lock_axes_toggled)

        # Initial render
        self.update_view()

    def on_lock_axes_toggled(self, checked):
        """Handle lock axes checkbox toggle."""
        if not checked:
            # Unlocking - clear stored limits
            self.locked_psf_xlim = None
            self.locked_psf_ylim = None

    def on_psf_options_changed(self):
        """Handle PSF display option changes - auto-update view."""
        # Only update if we have a valid configuration
        if hasattr(self, 'update_button'):
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

            # Store current PSF axes if lock is enabled
            if self.lock_axes_check.isChecked() and self.locked_psf_xlim is None:
                # First time locking - store current limits from canvas
                try:
                    current_fig = self.psf_canvas.figure
                    if current_fig.axes:
                        ax = current_fig.axes[0]
                        self.locked_psf_xlim = ax.get_xlim()
                        self.locked_psf_ylim = ax.get_ylim()
                except:
                    pass

            # Update PSF based on mode
            telescope_type = self.telescope_combo.currentText()
            psf_mode = "1d" if self.psf_1d_radio.isChecked() else "2d"
            psf_scale = "log" if self.psf_log_radio.isChecked() else "linear"

            if psf_mode == "1d":
                # 1D radial profile - create custom single-scale plot
                title = f"{telescope.primary_diameter:.0f}mm f/{telescope.focal_ratio:.1f} {telescope_type} — PSF Profile"

                # Generate the full plot (has both linear and log)
                fig_full = plot_psf_profile(
                    telescope,
                    title=title,
                    wavelength_nm=wavelength_nm,
                    figsize=(14, 7)  # Original size with both plots
                )

                # Extract the subplot we want (0=linear, 1=log)
                subplot_idx = 1 if psf_scale == "log" else 0
                source_ax = fig_full.axes[subplot_idx]

                # Create new figure with just this plot, expanded
                fig_psf = Figure(figsize=(8, 6))
                ax = fig_psf.add_subplot(111)

                # Copy all lines from source to new axis
                for line in source_ax.get_lines():
                    ax.plot(line.get_xdata(), line.get_ydata(),
                           color=line.get_color(),
                           linestyle=line.get_linestyle(),
                           linewidth=line.get_linewidth(),
                           label=line.get_label())

                # Copy axis properties
                ax.set_xlabel(source_ax.get_xlabel())
                ax.set_ylabel(source_ax.get_ylabel())
                ax.set_title(f"{title} ({'Logarithmic' if psf_scale == 'log' else 'Linear'} scale)")

                # Set scale
                if psf_scale == "log":
                    ax.set_yscale('log')
                    ax.set_ylim(source_ax.get_ylim())
                else:
                    ax.set_ylim(source_ax.get_ylim())

                ax.set_xlim(source_ax.get_xlim())
                ax.legend(fontsize=9)
                ax.grid(True, alpha=0.3)

                fig_psf.tight_layout()
                plt.close(fig_full)  # Close the temporary full figure
            else:
                # 2D image (plot_psf_2d uses log scale internally)
                fig_psf = plot_psf_2d(
                    telescope,
                    wavelength_nm=wavelength_nm,
                    figsize=(6, 6)
                )

            # Apply linear scale if requested (for 2D mode)
            if psf_mode == "2d" and psf_scale == "linear":
                # Get the image from the plot and convert to linear scale
                for ax in fig_psf.axes:
                    for im in ax.images:
                        # Get current data
                        data = im.get_array()
                        # Convert from log to linear (undo the log transformation)
                        linear_data = 10 ** data
                        im.set_data(linear_data)
                        im.set_norm(plt.Normalize(vmin=linear_data.min(), vmax=linear_data.max()))
                        # Update colorbar if it exists
                        if hasattr(im, 'colorbar') and im.colorbar is not None:
                            im.colorbar.update_normal(im)

            # Apply locked axes if enabled
            if self.lock_axes_check.isChecked() and self.locked_psf_xlim is not None:
                for ax in fig_psf.axes:
                    ax.set_xlim(self.locked_psf_xlim)
                    ax.set_ylim(self.locked_psf_ylim)

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

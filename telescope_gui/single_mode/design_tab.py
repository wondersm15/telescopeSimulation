"""
Design tab for single telescope mode.

Shows ray trace and simulated image side-by-side.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QDoubleSpinBox, QGroupBox, QCheckBox
)
from PyQt6.QtCore import pyqtSignal, Qt
import matplotlib.pyplot as plt

from telescope_gui.widgets.matplotlib_canvas import MatplotlibCanvas
from telescope_gui.widgets.image_popout import ImagePopoutWindow
from telescope_sim.geometry import NewtonianTelescope, CassegrainTelescope, RefractingTelescope, MaksutovCassegrainTelescope
from telescope_sim.geometry.eyepiece import Eyepiece
from telescope_sim.plotting import plot_ray_trace, plot_source_image
from telescope_sim.source.sources import Jupiter, Moon
from telescope_sim.source.light_source import create_parallel_rays


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
        self.current_figure = None  # Store current figure for pop-out
        self.true_size_figure = None  # Store true angular size figure (with eyepiece)
        self.display_mode = "scaled"  # "scaled" or "true_size"

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout()

        # Top: Side-by-side plots
        plots_layout = QHBoxLayout()

        # Left: Ray trace
        ray_trace_container = QVBoxLayout()
        self.ray_trace_canvas = MatplotlibCanvas(figsize=(7, 6))
        ray_trace_container.addWidget(self.ray_trace_canvas)
        plots_layout.addLayout(ray_trace_container)

        # Right: Simulated image with display controls
        image_container = QVBoxLayout()
        self.image_canvas = MatplotlibCanvas(figsize=(7, 6))
        image_container.addWidget(self.image_canvas)

        # Display mode buttons
        display_buttons_layout = QHBoxLayout()

        self.true_size_button = QPushButton("True Angular Size")
        self.true_size_button.setCheckable(True)
        self.true_size_button.clicked.connect(self.show_true_size)
        self.true_size_button.setEnabled(False)
        display_buttons_layout.addWidget(self.true_size_button)

        self.scaled_button = QPushButton("Standardized Size")
        self.scaled_button.setCheckable(True)
        self.scaled_button.setChecked(True)  # Default mode
        self.scaled_button.clicked.connect(self.show_scaled)
        self.scaled_button.setEnabled(False)
        display_buttons_layout.addWidget(self.scaled_button)

        self.popout_button = QPushButton("Pop Out")
        self.popout_button.clicked.connect(self.popout_image)
        self.popout_button.setEnabled(False)
        display_buttons_layout.addWidget(self.popout_button)

        image_container.addLayout(display_buttons_layout)

        plots_layout.addLayout(image_container)

        main_layout.addLayout(plots_layout)

        # Performance info label
        self.performance_label = QLabel("")
        self.performance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.performance_label.setStyleSheet("font-weight: bold; padding: 5px;")
        main_layout.addWidget(self.performance_label)

        # Eyepiece info label
        self.eyepiece_label = QLabel("")
        self.eyepiece_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.eyepiece_label.setStyleSheet("color: #0066cc; padding: 5px;")
        main_layout.addWidget(self.eyepiece_label)

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

        # Eyepiece controls
        controls_layout.addWidget(QLabel("Eyepiece:"), row, 0)
        self.eyepiece_check = QCheckBox("Use Eyepiece")
        self.eyepiece_check.setChecked(False)
        self.eyepiece_check.toggled.connect(self.toggle_eyepiece)
        controls_layout.addWidget(self.eyepiece_check, row, 1)

        controls_layout.addWidget(QLabel("Focal Length (mm):"), row, 2)
        self.eyepiece_spin = QDoubleSpinBox()
        self.eyepiece_spin.setRange(3.0, 40.0)
        self.eyepiece_spin.setSingleStep(1.0)
        self.eyepiece_spin.setValue(10.0)
        self.eyepiece_spin.setEnabled(False)
        controls_layout.addWidget(self.eyepiece_spin, row, 3)

        row += 1

        # Eyepiece AFOV
        controls_layout.addWidget(QLabel(""), row, 0)  # Empty
        controls_layout.addWidget(QLabel("Apparent FOV (°):"), row, 2)
        self.afov_spin = QDoubleSpinBox()
        self.afov_spin.setRange(30.0, 100.0)
        self.afov_spin.setSingleStep(5.0)
        self.afov_spin.setValue(50.0)  # Plössl standard
        self.afov_spin.setEnabled(False)
        controls_layout.addWidget(self.afov_spin, row, 3)

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

    def toggle_eyepiece(self, checked):
        """Enable/disable eyepiece controls."""
        self.eyepiece_spin.setEnabled(checked)
        self.afov_spin.setEnabled(checked)

    def show_true_size(self):
        """Switch to true angular size display mode."""
        self.display_mode = "true_size"
        self.true_size_button.setChecked(True)
        self.scaled_button.setChecked(False)
        self.refresh_image_display()

    def show_scaled(self):
        """Switch to standardized size display mode."""
        self.display_mode = "scaled"
        self.true_size_button.setChecked(False)
        self.scaled_button.setChecked(True)
        self.refresh_image_display()

    def refresh_image_display(self):
        """Refresh the image canvas based on current display mode."""
        if self.display_mode == "true_size" and self.true_size_figure is not None:
            # Show true angular size view
            self.image_canvas.set_figure(self.true_size_figure)
        elif self.current_figure is not None:
            # Show standardized size view
            self.image_canvas.set_figure(self.current_figure)
        else:
            # No figure available
            self.image_canvas.figure.clear()
            self.image_canvas.canvas.draw()

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
            return Jupiter()
        elif source_type == "moon":
            return Moon()
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

    def get_eyepiece(self, telescope):
        """Build eyepiece object if enabled."""
        if self.eyepiece_check.isChecked():
            eyepiece_fl = self.eyepiece_spin.value()
            afov = self.afov_spin.value()
            return Eyepiece(
                focal_length_mm=eyepiece_fl,
                apparent_fov_deg=afov
            )
        return None

    def calculate_diffraction_limit(self, aperture_mm, wavelength_nm=550.0):
        """Calculate diffraction limit in arcseconds."""
        # Rayleigh criterion: θ = 1.22 * λ / D
        wavelength_m = wavelength_nm * 1e-9
        aperture_m = aperture_mm * 1e-3
        theta_rad = 1.22 * wavelength_m / aperture_m
        theta_arcsec = theta_rad * 206265  # radians to arcseconds
        return theta_arcsec

    def update_performance_label(self, telescope, seeing_arcsec):
        """Update the performance info label."""
        diffraction_limit = self.calculate_diffraction_limit(telescope.primary_diameter)

        if seeing_arcsec is None:
            # No atmospheric seeing
            self.performance_label.setText(
                f"✓ Diffraction-limited: {diffraction_limit:.2f}\" resolution "
                f"(no atmospheric seeing)"
            )
            self.performance_label.setStyleSheet(
                "font-weight: bold; padding: 5px; color: green;"
            )
        elif seeing_arcsec > diffraction_limit:
            # Seeing-limited
            self.performance_label.setText(
                f"⚠ Seeing-limited: {seeing_arcsec:.1f}\" resolution "
                f"(telescope capable of {diffraction_limit:.2f}\" but atmosphere limits performance)"
            )
            self.performance_label.setStyleSheet(
                "font-weight: bold; padding: 5px; color: #cc6600;"
            )
        else:
            # Diffraction-limited (seeing better than telescope resolution)
            self.performance_label.setText(
                f"✓ Diffraction-limited: {diffraction_limit:.2f}\" resolution "
                f"(seeing is {seeing_arcsec:.1f}\", better than telescope limit)"
            )
            self.performance_label.setStyleSheet(
                "font-weight: bold; padding: 5px; color: green;"
            )

    def update_eyepiece_label(self, telescope, eyepiece):
        """Update the eyepiece info label."""
        if eyepiece is not None:
            mag = telescope.focal_length / eyepiece.focal_length_mm
            exit_pupil = telescope.primary_diameter / mag
            true_fov = eyepiece.apparent_fov_deg / mag

            self.eyepiece_label.setText(
                f"Eyepiece: {eyepiece.focal_length_mm:.0f}mm ({eyepiece.apparent_fov_deg:.0f}° AFOV) → "
                f"{mag:.0f}× magnification, {exit_pupil:.1f}mm exit pupil, {true_fov:.2f}° true FOV"
            )
        else:
            self.eyepiece_label.setText("Direct focal plane view (no eyepiece)")

    def popout_image(self):
        """Pop out the simulated image - uses true angular size figure if available."""
        # Use the true angular size figure (from CLI logic) if available (eyepiece mode)
        # Otherwise use the normal figure
        figure_to_show = self.true_size_figure if self.true_size_figure is not None else self.current_figure

        if figure_to_show is None:
            return

        telescope = self.build_telescope()
        eyepiece = self.get_eyepiece(telescope)

        # Build title
        title = f"{telescope.primary_diameter:.0f}mm f/{telescope.focal_ratio:.1f}"
        if eyepiece:
            mag = telescope.focal_length / eyepiece.focal_length_mm
            title += f" with {eyepiece.focal_length_mm:.0f}mm eyepiece ({mag:.0f}× magnification)"
        else:
            title += " — Direct Focal Plane"

        # Simple pop-out - just display the figure
        # The CLI logic already sized it correctly for perceived angular size
        window = ImagePopoutWindow(
            figure_to_show,
            title=title,
            parent=self
        )
        window.exec()

    def update_view(self):
        """Update both ray trace and simulated image."""
        try:
            # Build telescope and source
            telescope = self.build_telescope()
            source = self.build_source()
            seeing = self.get_seeing_value()
            eyepiece = self.get_eyepiece(telescope)

            # Update performance label
            self.update_performance_label(telescope, seeing)

            # Update eyepiece label
            self.update_eyepiece_label(telescope, eyepiece)

            # Update ray trace
            # Create and trace rays
            rays = create_parallel_rays(
                num_rays=11,
                aperture_diameter=telescope.primary_diameter,
                entry_height=telescope.tube_length * 1.15,
            )
            telescope.trace_rays(rays)
            components = telescope.get_components_for_plotting()

            # Plot
            telescope_type = self.telescope_combo.currentText()
            title = f"{telescope.primary_diameter:.0f}mm f/{telescope.focal_ratio:.1f} {telescope_type} — Ray Trace"
            fig_ray_trace = plot_ray_trace(rays, components, title=title)
            self.ray_trace_canvas.set_figure(fig_ray_trace)
            plt.close(fig_ray_trace)  # Close to free memory

            # Update simulated image (if source selected)
            if source is not None:
                result = plot_source_image(
                    telescope,
                    source,
                    seeing_arcsec=seeing,
                    eyepiece=eyepiece  # Pass eyepiece to enable magnification/washout effects
                )

                # plot_source_image returns a list if eyepiece is used, single figure otherwise
                if isinstance(result, list):
                    # With eyepiece: [normal_view, true_angular_size_view]
                    # Store both figures
                    self.current_figure = result[0]  # Standardized size
                    if len(result) > 1:
                        self.true_size_figure = result[1]  # True angular size
                    else:
                        self.true_size_figure = None
                else:
                    # Without eyepiece: single figure
                    self.current_figure = result
                    self.true_size_figure = None

                # Enable buttons
                self.scaled_button.setEnabled(True)
                self.popout_button.setEnabled(True)

                # Enable true size button only if we have the true size figure
                if self.true_size_figure is not None:
                    self.true_size_button.setEnabled(True)
                else:
                    self.true_size_button.setEnabled(False)
                    # If we were in true_size mode but no longer have the figure, switch to scaled
                    if self.display_mode == "true_size":
                        self.display_mode = "scaled"
                        self.scaled_button.setChecked(True)
                        self.true_size_button.setChecked(False)

                # Display based on current mode
                self.refresh_image_display()

                # Don't close these - we need them for display/pop-out
            else:
                # Clear image canvas
                self.image_canvas.figure.clear()
                self.image_canvas.canvas.draw()
                self.current_figure = None
                self.true_size_figure = None
                self.scaled_button.setEnabled(False)
                self.true_size_button.setEnabled(False)
                self.popout_button.setEnabled(False)

            self.config_changed.emit()

        except Exception as e:
            print(f"Error updating view: {e}")
            import traceback
            traceback.print_exc()

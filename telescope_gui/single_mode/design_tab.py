"""
Design tab for single telescope mode.

Shows ray trace and simulated image side-by-side.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QDoubleSpinBox, QGroupBox, QCheckBox,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
import matplotlib.pyplot as plt
import numpy as np

from telescope_gui.widgets.matplotlib_canvas import MatplotlibCanvas
from telescope_gui.widgets.image_popout import ImagePopoutWindow
from telescope_gui.widgets.telescope_controls import TelescopeControlPanel
from telescope_gui.widgets.source_controls import get_source, get_seeing
from telescope_gui.telescope_builder import build_telescope
from telescope_sim.geometry.eyepiece import Eyepiece
from telescope_sim.plotting import plot_ray_trace, plot_source_image, plot_polychromatic_ray_trace
from telescope_sim.source.light_source import create_parallel_rays
from telescope_sim.physics.diffraction import rayleigh_criterion_arcsec


class DesignTab(QWidget):
    """Design tab - ray trace + simulated image side-by-side."""

    config_changed = pyqtSignal()  # Signal when configuration changes

    def __init__(self, parent=None):
        super().__init__(parent)

        # Default configuration
        self.current_figure = None  # Store current figure for pop-out
        self.true_size_figure = None  # Store true angular size figure (with eyepiece)
        self.eyepiece_view_figure = None  # Store eyepiece view figure
        self.display_mode = "scaled"  # "scaled", "true_size", or "eyepiece_view"

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface.

        Three-column layout:
          Left:   scrollable controls sidebar (single column)
          Middle: ray trace diagram (tall — telescopes are vertical)
          Right:  simulated image (buttons below) — twice the ray-trace width
        """
        main_layout = QHBoxLayout()

        # ── Build canvases first (controls reference them indirectly) ──
        self.ray_trace_canvas = MatplotlibCanvas(figsize=(5, 10))
        self.ray_trace_canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.image_canvas = MatplotlibCanvas(figsize=(6, 6))
        self.image_canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # ── RIGHT COLUMN: simulated image + display buttons ──
        image_column = QVBoxLayout()

        # Display mode buttons (stacked vertically to fit narrow column)
        display_buttons_layout = QVBoxLayout()

        self.true_size_button = QPushButton("True Angular Size")
        self.true_size_button.setCheckable(True)
        self.true_size_button.clicked.connect(self.show_true_size)
        self.true_size_button.setEnabled(False)
        self.true_size_button.setToolTip(
            "Display source at true apparent angular size (assumes 50cm viewing distance)\n"
            "Scaled by eyepiece AFOV. Only available when eyepiece is configured."
        )
        display_buttons_layout.addWidget(self.true_size_button)

        self.eyepiece_view_button = QPushButton("Eyepiece View")
        self.eyepiece_view_button.setCheckable(True)
        self.eyepiece_view_button.clicked.connect(self.show_eyepiece_view)
        self.eyepiece_view_button.setEnabled(False)
        self.eyepiece_view_button.setToolTip(
            "Fixed-size circular eyepiece field view.\n"
            "Shows correct proportions (source vs FOV) without oversized figure.\n"
            "Only available when eyepiece is configured."
        )
        display_buttons_layout.addWidget(self.eyepiece_view_button)

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

        image_column.addWidget(self.image_canvas, stretch=1)
        image_column.addLayout(display_buttons_layout)

        # ── LEFT COLUMN: controls sidebar (single-column layout) ──
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)

        # Performance info label
        self.performance_label = QLabel("")
        self.performance_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.performance_label.setWordWrap(True)
        self.performance_label.setStyleSheet("font-weight: bold; padding: 5px;")
        sidebar_layout.addWidget(self.performance_label)

        # Eyepiece info label
        self.eyepiece_label = QLabel("")
        self.eyepiece_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.eyepiece_label.setWordWrap(True)
        self.eyepiece_label.setStyleSheet("color: #0066cc; padding: 5px;")
        sidebar_layout.addWidget(self.eyepiece_label)

        # Shared telescope control panel
        self.telescope_panel = TelescopeControlPanel(
            number=1, layout_mode="sidebar", show_group_box=True
        )
        sidebar_layout.addWidget(self.telescope_panel)

        # Additional design-tab-specific controls
        extra_group = QGroupBox("Source & Display")
        extra_layout = QGridLayout()
        row = 0

        # Source
        extra_layout.addWidget(QLabel("Source:"), row, 0); row += 1
        self.source_combo = QComboBox()
        self.source_combo.addItems([
            "Jupiter", "Saturn", "Moon", "Star Field",
            "Point Source (Star)", "None"
        ])
        self.source_combo.setCurrentText("Jupiter")
        extra_layout.addWidget(self.source_combo, row, 0); row += 1

        # Seeing
        extra_layout.addWidget(QLabel("Seeing:"), row, 0); row += 1
        self.seeing_combo = QComboBox()
        self.seeing_combo.addItems(["Excellent", "Good", "Average", "Poor", "None"])
        self.seeing_combo.setCurrentText("Good")
        extra_layout.addWidget(self.seeing_combo, row, 0); row += 1

        # Eyepiece controls
        self.eyepiece_check = QCheckBox("Use Eyepiece")
        self.eyepiece_check.setChecked(False)
        self.eyepiece_check.toggled.connect(self.toggle_eyepiece)
        extra_layout.addWidget(self.eyepiece_check, row, 0); row += 1

        extra_layout.addWidget(QLabel("Eyepiece FL (mm):"), row, 0); row += 1
        self.eyepiece_spin = QDoubleSpinBox()
        self.eyepiece_spin.setRange(3.0, 40.0)
        self.eyepiece_spin.setSingleStep(1.0)
        self.eyepiece_spin.setValue(10.0)
        self.eyepiece_spin.setEnabled(False)
        extra_layout.addWidget(self.eyepiece_spin, row, 0); row += 1

        extra_layout.addWidget(QLabel("Apparent FOV (\u00b0):"), row, 0); row += 1
        self.afov_spin = QDoubleSpinBox()
        self.afov_spin.setRange(30.0, 100.0)
        self.afov_spin.setSingleStep(5.0)
        self.afov_spin.setValue(50.0)  # Plössl standard
        self.afov_spin.setEnabled(False)
        self.afov_spin.setToolTip(
            "Apparent FOV of the eyepiece design.\n"
            "Higher = larger visual 'window' through the eyepiece.\n"
            "(50\u00b0 Pl\u00f6ssl, 68\u00b0 wide-angle, 82\u00b0 ultra-wide)"
        )
        extra_layout.addWidget(self.afov_spin, row, 0); row += 1

        # Polychromatic ray trace toggle
        self.polychromatic_check = QCheckBox("Polychromatic Ray Trace")
        self.polychromatic_check.setToolTip(
            "Show R/G/B colored rays to visualize chromatic aberration.\n"
            "Most useful for refractors (singlet, achromat, etc)."
        )
        extra_layout.addWidget(self.polychromatic_check, row, 0); row += 1
        self.polychromatic_desc = QLabel("(R/G/B rays — chromatic aberration)")
        self.polychromatic_desc.setWordWrap(True)
        self.polychromatic_desc.setStyleSheet("font-size: 8pt; color: #666;")
        extra_layout.addWidget(self.polychromatic_desc, row, 0); row += 1

        # Update button
        self.update_button = QPushButton("Update View")
        self.update_button.clicked.connect(self.update_view)
        extra_layout.addWidget(self.update_button, row, 0)

        extra_group.setLayout(extra_layout)
        sidebar_layout.addWidget(extra_group)
        sidebar_layout.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setWidget(sidebar)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumWidth(200)
        scroll_area.setMaximumWidth(280)

        # ── Assemble three columns: controls | ray trace | image ──
        main_layout.addWidget(scroll_area, stretch=0)
        main_layout.addWidget(self.ray_trace_canvas, stretch=1)
        main_layout.addLayout(image_column, stretch=2)

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
        self.eyepiece_view_button.setChecked(False)
        self.refresh_image_display()

    def show_eyepiece_view(self):
        """Switch to eyepiece view display mode."""
        self.display_mode = "eyepiece_view"
        self.eyepiece_view_button.setChecked(True)
        self.true_size_button.setChecked(False)
        self.scaled_button.setChecked(False)
        self.refresh_image_display()

    def show_scaled(self):
        """Switch to standardized size display mode."""
        self.display_mode = "scaled"
        self.true_size_button.setChecked(False)
        self.scaled_button.setChecked(False)
        self.eyepiece_view_button.setChecked(False)
        self.scaled_button.setChecked(True)
        self.refresh_image_display()

    def refresh_image_display(self):
        """Refresh the image canvas based on current display mode."""
        if self.display_mode == "true_size" and self.true_size_figure is not None:
            self.image_canvas.set_figure(self.true_size_figure)
        elif self.display_mode == "eyepiece_view" and self.eyepiece_view_figure is not None:
            self.image_canvas.set_figure(self.eyepiece_view_figure)
        elif self.current_figure is not None:
            self.image_canvas.set_figure(self.current_figure)
        else:
            self.image_canvas.figure.clear()
            self.image_canvas.canvas.draw()

    def calculate_diffraction_limit(self, aperture_mm, wavelength_nm=550.0):
        """Calculate diffraction limit in arcseconds."""
        wavelength_m = wavelength_nm * 1e-9
        aperture_m = aperture_mm * 1e-3
        theta_rad = 1.22 * wavelength_m / aperture_m
        theta_arcsec = theta_rad * 206265
        return theta_arcsec

    def update_performance_label(self, telescope, seeing_arcsec):
        """Update the performance info label with full resolution breakdown."""
        wavelength_m = 550.0 * 1e-9
        aperture_m = telescope.primary_diameter * 1e-3
        obstruction_ratio = getattr(telescope, 'obstruction_ratio', 0.0)

        # Pure aperture diffraction
        rayleigh_base = rayleigh_criterion_arcsec(wavelength_m, aperture_m, 0.0)
        # With obstruction
        rayleigh_with_obs = rayleigh_criterion_arcsec(wavelength_m, aperture_m, obstruction_ratio)
        obstruction_effect = rayleigh_base - rayleigh_with_obs

        # Geometric aberrations
        primary_type = getattr(telescope, 'primary_type', 'parabolic')
        spherical_blur_arcsec = 0.0
        if primary_type == 'spherical':
            f_ratio = telescope.focal_ratio
            spherical_blur_arcsec = 1000.0 / (f_ratio ** 3)

        # Combine resolution contributors (add in quadrature)
        # Note: Approximate - real aberrations don't simply add in quadrature
        combined_geometric = np.sqrt(rayleigh_with_obs**2 + spherical_blur_arcsec**2)

        # Build breakdown text
        breakdown_parts = [f"Diffraction (aperture): {rayleigh_base:.2f}\""]
        if obstruction_ratio > 0:
            sign = "+" if obstruction_effect >= 0 else ""
            breakdown_parts.append(
                f"Obstruction: {obstruction_ratio*100:.0f}% ({sign}{obstruction_effect:.2f}\" narrower core)"
            )
        if spherical_blur_arcsec > 0.1:
            breakdown_parts.append(f"Spherical: {spherical_blur_arcsec:.2f}\"")
            breakdown_parts.append(f"Combined: {combined_geometric:.2f}\"")

        if seeing_arcsec is None:
            effective_resolution = combined_geometric
            self.performance_label.setText(
                f"Resolution: {effective_resolution:.2f}\" ({' \u2022 '.join(breakdown_parts)}) \u2014 No atmosphere"
            )
            self.performance_label.setStyleSheet(
                "font-weight: bold; padding: 5px; color: green;"
            )
        elif seeing_arcsec > combined_geometric:
            self.performance_label.setText(
                f"\u26a0 Seeing-limited: {seeing_arcsec:.1f}\" resolution "
                f"(optics capable of {combined_geometric:.2f}\" [{' \u2022 '.join(breakdown_parts)}] "
                f"but atmosphere limits performance)"
            )
            self.performance_label.setStyleSheet(
                "font-weight: bold; padding: 5px; color: #cc6600;"
            )
        else:
            effective_resolution = combined_geometric
            self.performance_label.setText(
                f"\u2713 Optics-limited: {effective_resolution:.2f}\" resolution "
                f"({' \u2022 '.join(breakdown_parts)}) \u2014 "
                f"Seeing is {seeing_arcsec:.1f}\", better than optics"
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
                f"Eyepiece: {eyepiece.focal_length_mm:.0f}mm ({eyepiece.apparent_fov_deg:.0f}\u00b0 AFOV) \u2192 "
                f"{mag:.0f}\u00d7 magnification, {exit_pupil:.1f}mm exit pupil, {true_fov:.2f}\u00b0 true FOV"
            )
        else:
            self.eyepiece_label.setText("Direct focal plane view (no eyepiece)")

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

    def popout_image(self):
        """Pop out the simulated image based on current display mode."""
        if self.display_mode == "true_size" and self.true_size_figure is not None:
            figure_to_show = self.true_size_figure
        elif self.display_mode == "eyepiece_view" and self.eyepiece_view_figure is not None:
            figure_to_show = self.eyepiece_view_figure
        else:
            figure_to_show = self.current_figure

        if figure_to_show is None:
            return

        telescope = self.telescope_panel.build()
        eyepiece = self.get_eyepiece(telescope)

        # Build title
        title = f"{telescope.primary_diameter:.0f}mm f/{telescope.focal_ratio:.1f}"
        if eyepiece:
            mag = telescope.focal_length / eyepiece.focal_length_mm
            title += f" with {eyepiece.focal_length_mm:.0f}mm eyepiece ({mag:.0f}\u00d7 magnification)"
        else:
            title += " \u2014 Direct Focal Plane"

        window = ImagePopoutWindow(
            figure_to_show,
            title=title,
            display_mode=self.display_mode,
            parent=self
        )
        window.exec()

    def update_view(self):
        """Update both ray trace and simulated image."""
        try:
            # Build telescope and source using shared components
            telescope = self.telescope_panel.build()
            source = get_source(self.source_combo.currentText())
            seeing = get_seeing(self.seeing_combo.currentText())
            eyepiece = self.get_eyepiece(telescope)

            # Update effective f/ratio display
            self.telescope_panel.update_effective_fratio(telescope)

            # Update performance label
            self.update_performance_label(telescope, seeing)

            # Update eyepiece label
            self.update_eyepiece_label(telescope, eyepiece)

            # Update ray trace
            telescope_type = self.telescope_panel.type_combo.currentText()

            if self.polychromatic_check.isChecked():
                fig_ray_trace = plot_polychromatic_ray_trace(
                    telescope, num_display_rays=11
                )
            else:
                rays = create_parallel_rays(
                    num_rays=11,
                    aperture_diameter=telescope.primary_diameter,
                    entry_height=telescope.tube_length * 1.15,
                )
                telescope.trace_rays(rays)
                components = telescope.get_components_for_plotting()
                title = f"{telescope.primary_diameter:.0f}mm f/{telescope.focal_ratio:.1f} (FL: {telescope.focal_length:.0f}mm) {telescope_type} \u2014 Ray Trace"
                fig_ray_trace = plot_ray_trace(rays, components, title=title)

            self.ray_trace_canvas.set_figure(fig_ray_trace)
            plt.close(fig_ray_trace)

            # Update simulated image (if source selected)
            if source is not None:
                # Close old figures to prevent memory leak
                if self.current_figure is not None:
                    plt.close(self.current_figure)
                if self.true_size_figure is not None:
                    plt.close(self.true_size_figure)
                if self.eyepiece_view_figure is not None:
                    plt.close(self.eyepiece_view_figure)

                result = plot_source_image(
                    telescope,
                    source,
                    seeing_arcsec=seeing,
                    eyepiece=eyepiece,
                    eyepiece_view_figsize=(8, 8) if eyepiece is not None else None,
                )

                if isinstance(result, list):
                    self.current_figure = result[0]
                    self.true_size_figure = result[1] if len(result) > 1 else None
                    self.eyepiece_view_figure = result[2] if len(result) > 2 else None
                else:
                    self.current_figure = result
                    self.true_size_figure = None
                    self.eyepiece_view_figure = None

                # Enable buttons
                self.scaled_button.setEnabled(True)
                self.popout_button.setEnabled(True)

                has_eyepiece_figs = self.true_size_figure is not None
                self.true_size_button.setEnabled(has_eyepiece_figs)
                self.eyepiece_view_button.setEnabled(self.eyepiece_view_figure is not None)

                if not has_eyepiece_figs and self.display_mode == "true_size":
                    self.display_mode = "scaled"
                    self.scaled_button.setChecked(True)
                    self.true_size_button.setChecked(False)
                    self.eyepiece_view_button.setChecked(False)

                if self.eyepiece_view_figure is None and self.display_mode == "eyepiece_view":
                    self.display_mode = "scaled"
                    self.scaled_button.setChecked(True)
                    self.eyepiece_view_button.setChecked(False)

                self.refresh_image_display()

            else:
                self.image_canvas.figure.clear()
                self.image_canvas.canvas.draw()
                self.current_figure = None
                self.true_size_figure = None
                self.eyepiece_view_figure = None
                self.scaled_button.setEnabled(False)
                self.true_size_button.setEnabled(False)
                self.eyepiece_view_button.setEnabled(False)
                self.popout_button.setEnabled(False)

            self.config_changed.emit()

        except Exception as e:
            print(f"Error updating view: {e}")
            import traceback
            traceback.print_exc()

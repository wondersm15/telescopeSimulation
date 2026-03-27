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
from telescope_sim.geometry import (
    NewtonianTelescope, CassegrainTelescope, RefractingTelescope,
    MaksutovCassegrainTelescope, SchmidtCassegrainTelescope
)
from telescope_sim.plotting import (
    plot_psf_2d, plot_psf_profile, plot_spot_diagram,
    plot_coma_field_analysis, plot_vignetting_curve
)
from telescope_sim.physics.diffraction import rayleigh_criterion_arcsec
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

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout()

        # Top section: Plots + Info sidebar
        top_layout = QHBoxLayout()

        # Left: PSF
        self.psf_widget = QWidget()
        psf_container = QVBoxLayout()
        psf_container.setContentsMargins(0, 0, 0, 0)
        self.psf_label_header = QLabel("Point Spread Function (PSF)")
        self.psf_label_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.psf_label_header.setStyleSheet("font-weight: bold; font-size: 12pt;")
        psf_container.addWidget(self.psf_label_header)

        self.psf_canvas = MatplotlibCanvas(figsize=(6, 6))
        psf_container.addWidget(self.psf_canvas)
        self.psf_widget.setLayout(psf_container)
        top_layout.addWidget(self.psf_widget)

        # Center: Spot Diagram
        self.spot_widget = QWidget()
        spot_container = QVBoxLayout()
        spot_container.setContentsMargins(0, 0, 0, 0)
        self.spot_label_header = QLabel("Spot Diagram")
        self.spot_label_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spot_label_header.setStyleSheet("font-weight: bold; font-size: 12pt;")
        spot_container.addWidget(self.spot_label_header)

        self.spot_canvas = MatplotlibCanvas(figsize=(6, 6))
        spot_container.addWidget(self.spot_canvas)
        self.spot_widget.setLayout(spot_container)
        top_layout.addWidget(self.spot_widget)

        # Right: Info sidebar
        sidebar = QVBoxLayout()
        sidebar_widget = QWidget()
        sidebar_widget.setMaximumWidth(260)

        # Analysis View dropdown
        analysis_group = QGroupBox("Analysis View")
        analysis_layout = QVBoxLayout()
        self.analysis_combo = QComboBox()
        self.analysis_combo.addItems([
            "PSF + Spot Diagram",
            "Coma Field Analysis",
            "Vignetting Curve"
        ])
        self.analysis_combo.currentTextChanged.connect(self.on_analysis_view_changed)
        analysis_layout.addWidget(self.analysis_combo)
        analysis_group.setLayout(analysis_layout)
        sidebar.addWidget(analysis_group)

        # Metrics display
        self.metrics_label = QLabel("Click 'Update Analysis' to compute performance metrics")
        self.metrics_label.setWordWrap(True)
        self.metrics_label.setStyleSheet("font-size: 10pt; padding: 6px; background-color: #f0f0f0; color: #222;")
        sidebar.addWidget(self.metrics_label)

        # Explanation label
        explanation = QLabel(
            "<b>PSF</b>: How a point source appears "
            "due to <i>diffraction</i> (wave optics).<br>"
            "<b>Spot Diagram</b>: Where rays converge due to <i>geometry</i> "
            "(geometric optics).<br>"
            "<b>Combined</b>: image = spot \u2297 PSF."
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet("font-size: 8pt; padding: 4px; background-color: #e8f4f8; color: #004488;")
        sidebar.addWidget(explanation)

        # Physics info panel
        physics_info = QLabel(
            "<b>Included:</b><ul style='margin:2px 0px; padding-left:16px;'>"
            "<li>Diffraction</li>"
            "<li>Obstruction</li>"
            "<li>Spider vanes</li>"
            "<li>Chromatic aberration</li>"
            "<li>Coma</li>"
            "<li>Spherical aberration</li>"
            "</ul>"
            "<b>Not Included:</b><ul style='margin:2px 0px; padding-left:16px;'>"
            "<li>Astigmatism</li>"
            "<li>Field curvature</li>"
            "<li>Seeing</li>"
            "</ul>"
        )
        physics_info.setWordWrap(True)
        physics_info.setStyleSheet("font-size: 8pt; padding: 4px; background-color: #f5f5f5; color: #222;")
        sidebar.addWidget(physics_info)

        # PSF Display Options (stacked vertically in sidebar)
        self.psf_options_group = QGroupBox("PSF Display Options")
        psf_options_layout = QVBoxLayout()
        psf_options_layout.setSpacing(2)

        # PSF Mode (1D vs 2D)
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Type:"))
        self.psf_1d_radio = QRadioButton("1D")
        self.psf_2d_radio = QRadioButton("2D")
        self.psf_2d_radio.setChecked(True)
        self.psf_mode_group = QButtonGroup()
        self.psf_mode_group.addButton(self.psf_1d_radio)
        self.psf_mode_group.addButton(self.psf_2d_radio)
        mode_row.addWidget(self.psf_1d_radio)
        mode_row.addWidget(self.psf_2d_radio)
        mode_row.addStretch()
        psf_options_layout.addLayout(mode_row)

        # Scale (log vs linear)
        scale_row = QHBoxLayout()
        scale_row.addWidget(QLabel("Scale:"))
        self.psf_log_radio = QRadioButton("Log")
        self.psf_linear_radio = QRadioButton("Linear")
        self.psf_log_radio.setChecked(True)
        self.psf_scale_group = QButtonGroup()
        self.psf_scale_group.addButton(self.psf_log_radio)
        self.psf_scale_group.addButton(self.psf_linear_radio)
        scale_row.addWidget(self.psf_log_radio)
        scale_row.addWidget(self.psf_linear_radio)
        scale_row.addStretch()
        psf_options_layout.addLayout(scale_row)

        # Checkboxes
        self.lock_axes_check = QCheckBox("Lock PSF Axes")
        self.lock_axes_check.setToolTip("Keep PSF plot axes fixed when updating parameters")
        psf_options_layout.addWidget(self.lock_axes_check)

        self.autoscale_psf_check = QCheckBox("Auto-scale Intensity")
        self.autoscale_psf_check.setToolTip("Automatically adjust color scale to show full dynamic range")
        self.autoscale_psf_check.setChecked(False)
        self.autoscale_psf_check.toggled.connect(self.on_psf_options_changed)
        psf_options_layout.addWidget(self.autoscale_psf_check)

        self.psf_options_group.setLayout(psf_options_layout)
        sidebar.addWidget(self.psf_options_group)

        sidebar.addStretch()
        sidebar_widget.setLayout(sidebar)
        top_layout.addWidget(sidebar_widget)

        main_layout.addLayout(top_layout)

        # Connect PSF option changes to auto-update
        self.psf_1d_radio.toggled.connect(self.on_psf_options_changed)
        self.psf_2d_radio.toggled.connect(self.on_psf_options_changed)
        self.psf_log_radio.toggled.connect(self.on_psf_options_changed)
        self.psf_linear_radio.toggled.connect(self.on_psf_options_changed)

        # Bottom: Controls (compact layout)
        controls_group = QGroupBox("Controls")
        controls_layout = QGridLayout()
        controls_layout.setVerticalSpacing(2)
        controls_layout.setHorizontalSpacing(4)

        row = 0

        # Row 0: Telescope type + Aperture
        controls_layout.addWidget(QLabel("Type:"), row, 0)
        self.telescope_combo = QComboBox()
        self.telescope_combo.addItems(["Newtonian", "Cassegrain", "Refractor", "Maksutov-Cassegrain", "Schmidt-Cassegrain"])
        self.telescope_combo.setCurrentText("Newtonian")
        self.telescope_combo.currentTextChanged.connect(self.on_telescope_type_changed)
        controls_layout.addWidget(self.telescope_combo, row, 1)

        controls_layout.addWidget(QLabel("Aperture (mm):"), row, 2)
        self.aperture_spin = QDoubleSpinBox()
        self.aperture_spin.setRange(50.0, 500.0)
        self.aperture_spin.setSingleStep(10.0)
        self.aperture_spin.setValue(200.0)
        controls_layout.addWidget(self.aperture_spin, row, 3)

        row += 1

        # Row 1: Primary/Objective type
        self.primary_label = QLabel("Primary:")
        controls_layout.addWidget(self.primary_label, row, 0)
        self.primary_combo = QComboBox()
        self.primary_combo.addItems(["Parabolic", "Spherical"])
        self.primary_combo.setCurrentText("Parabolic")
        controls_layout.addWidget(self.primary_combo, row, 1)

        self.objective_label = QLabel("Objective:")
        controls_layout.addWidget(self.objective_label, row, 0)
        self.objective_combo = QComboBox()
        self.objective_combo.addItems(["Singlet", "Achromat", "APO Doublet", "APO Triplet (air-spaced)"])
        self.objective_combo.setCurrentText("Singlet")
        controls_layout.addWidget(self.objective_combo, row, 1)

        self.objective_label.hide()
        self.objective_combo.hide()

        # Secondary magnification (for Cassegrain variants)
        self.sec_mag_label = QLabel("Sec. Mag:")
        self.sec_mag_label.setToolTip("System focal length = primary FL × this value")
        controls_layout.addWidget(self.sec_mag_label, row, 2)
        self.sec_mag_spin = QDoubleSpinBox()
        self.sec_mag_spin.setRange(1.5, 6.0)
        self.sec_mag_spin.setSingleStep(0.5)
        self.sec_mag_spin.setValue(3.0)
        self.sec_mag_spin.setToolTip("System focal length = primary FL × this value")
        controls_layout.addWidget(self.sec_mag_spin, row, 3)
        self.sec_mag_label.hide()
        self.sec_mag_spin.hide()

        row += 1

        # Row 2: f-ratio + lock
        controls_layout.addWidget(QLabel("f-ratio:"), row, 0)
        self.fratio_spin = QDoubleSpinBox()
        self.fratio_spin.setRange(3.0, 15.0)
        self.fratio_spin.setSingleStep(0.1)
        self.fratio_spin.setValue(5.0)
        controls_layout.addWidget(self.fratio_spin, row, 1)

        self.lock_fratio_check = QCheckBox("Lock f-ratio")
        self.lock_fratio_check.setToolTip("Lock f-ratio when changing aperture")
        self.lock_fratio_check.setChecked(True)
        controls_layout.addWidget(self.lock_fratio_check, row, 2, 1, 2)

        row += 1

        # Row 3: Focal length + lock + effective f/ratio
        controls_layout.addWidget(QLabel("FL (mm):"), row, 0)
        self.focal_length_spin = QDoubleSpinBox()
        self.focal_length_spin.setRange(150.0, 3000.0)
        self.focal_length_spin.setSingleStep(10.0)
        self.focal_length_spin.setValue(1000.0)
        controls_layout.addWidget(self.focal_length_spin, row, 1)

        self.lock_focal_length_check = QCheckBox("Lock FL")
        self.lock_focal_length_check.setToolTip("Lock focal length when changing aperture")
        controls_layout.addWidget(self.lock_focal_length_check, row, 2)

        self.effective_fratio_label = QLabel("Eff. f/ratio: --")
        self.effective_fratio_label.setStyleSheet("font-style: italic; color: #666; font-size: 9pt;")
        controls_layout.addWidget(self.effective_fratio_label, row, 3)

        row += 1

        # Row 4: Wavelength + Obstruction
        controls_layout.addWidget(QLabel("\u03bb (nm):"), row, 0)
        self.wavelength_spin = QDoubleSpinBox()
        self.wavelength_spin.setRange(400.0, 700.0)
        self.wavelength_spin.setSingleStep(10.0)
        self.wavelength_spin.setValue(550.0)
        controls_layout.addWidget(self.wavelength_spin, row, 1)

        self.obstruction_label = QLabel("Obstruction:")
        self.enable_obstruction_check = QCheckBox("Enable")
        self.enable_obstruction_check.setChecked(True)
        self.enable_obstruction_check.setToolTip(
            "Enable/disable secondary mirror obstruction effects on PSF and resolution"
        )
        obstruction_enable_layout = QHBoxLayout()
        obstruction_enable_layout.setSpacing(2)
        obstruction_enable_layout.addWidget(self.obstruction_label)
        obstruction_enable_layout.addWidget(self.enable_obstruction_check)
        controls_layout.addLayout(obstruction_enable_layout, row, 2)

        self.obstruction_spin = QDoubleSpinBox()
        self.obstruction_spin.setRange(0.0, 0.5)
        self.obstruction_spin.setSingleStep(0.01)
        self.obstruction_spin.setValue(0.20)
        self.obstruction_spin.setDecimals(2)
        self.obstruction_spin.setToolTip(
            "Secondary diameter / Primary diameter (0.2 = 20% obstruction)"
        )
        controls_layout.addWidget(self.obstruction_spin, row, 3)

        row += 1

        # Row 5: Spider vanes + Update button
        controls_layout.addWidget(QLabel("Spider Vanes:"), row, 0)
        self.spider_vanes_spin = QDoubleSpinBox()
        self.spider_vanes_spin.setRange(0, 4)
        self.spider_vanes_spin.setDecimals(0)
        self.spider_vanes_spin.setValue(0)
        controls_layout.addWidget(self.spider_vanes_spin, row, 1)

        controls_layout.addWidget(QLabel("Vane Width (mm):"), row, 2)
        self.vane_width_spin = QDoubleSpinBox()
        self.vane_width_spin.setRange(0.5, 5.0)
        self.vane_width_spin.setSingleStep(0.5)
        self.vane_width_spin.setValue(2.0)
        controls_layout.addWidget(self.vane_width_spin, row, 3)

        row += 1

        # Meniscus thickness (Maksutov-Cassegrain only)
        self.meniscus_label = QLabel("Meniscus (mm):")
        self.meniscus_label.setToolTip("Meniscus corrector thickness. Default = aperture/10.")
        controls_layout.addWidget(self.meniscus_label, row, 2)
        self.meniscus_spin = QDoubleSpinBox()
        self.meniscus_spin.setRange(5.0, 50.0)
        self.meniscus_spin.setSingleStep(1.0)
        self.meniscus_spin.setValue(self.aperture_spin.value() / 10.0)
        self.meniscus_spin.setToolTip("Meniscus corrector thickness. Default = aperture/10.")
        controls_layout.addWidget(self.meniscus_spin, row, 3)
        self.meniscus_label.hide()
        self.meniscus_spin.hide()

        row += 1

        # Update button
        self.update_button = QPushButton("Update Analysis")
        self.update_button.clicked.connect(self.update_view)
        controls_layout.addWidget(self.update_button, row, 0, 1, 4)

        controls_group.setLayout(controls_layout)
        main_layout.addWidget(controls_group)

        self.setLayout(main_layout)

        # Connect focal length synchronization signals
        self.aperture_spin.valueChanged.connect(self.on_aperture_changed)
        self.fratio_spin.valueChanged.connect(self.on_fratio_changed)
        self.focal_length_spin.valueChanged.connect(self.on_focal_length_changed)
        self.lock_fratio_check.toggled.connect(self.on_lock_fratio_toggled)
        self.lock_focal_length_check.toggled.connect(self.on_lock_focal_length_toggled)

        # Connect lock axes checkbox
        self.lock_axes_check.toggled.connect(self.on_lock_axes_toggled)

        # Initial render
        self.update_view()

    def on_lock_axes_toggled(self, checked):
        """Handle lock axes checkbox toggle."""
        # Note: Axis locking is now handled by MatplotlibCanvas.set_figure()
        pass

    def on_analysis_view_changed(self, view_name):
        """Show/hide canvases based on selected analysis view."""
        is_default = view_name == "PSF + Spot Diagram"

        # Show/hide spot diagram and PSF options (only in default view)
        self.spot_widget.setVisible(is_default)
        self.psf_options_group.setVisible(is_default)

        # Update header label for PSF canvas
        if is_default:
            self.psf_label_header.setText("Point Spread Function (PSF)")
        elif view_name == "Coma Field Analysis":
            self.psf_label_header.setText("Coma Field Analysis")
        elif view_name == "Vignetting Curve":
            self.psf_label_header.setText("Vignetting Curve")

        # Trigger re-render
        self.update_view()

    def on_psf_options_changed(self):
        """Handle PSF display option changes - auto-update view."""
        # Only update if we have a valid configuration
        if hasattr(self, 'update_button'):
            self.update_view()

    def on_telescope_type_changed(self, telescope_type):
        """Show/hide appropriate controls based on telescope type."""
        is_refractor = telescope_type == "Refractor"
        is_newtonian = telescope_type == "Newtonian"

        # Primary type (spherical/parabolic) only for Newtonian
        self.primary_label.setVisible(is_newtonian)
        self.primary_combo.setVisible(is_newtonian)

        # Objective type only for refractors
        self.objective_label.setVisible(is_refractor)
        self.objective_combo.setVisible(is_refractor)

        # Obstruction controls only for reflectors
        self.obstruction_label.setVisible(not is_refractor)
        self.enable_obstruction_check.setVisible(not is_refractor)
        self.obstruction_spin.setVisible(not is_refractor)

        # Secondary magnification only for Cassegrain variants
        is_cassegrain_variant = telescope_type in ("Cassegrain", "Maksutov-Cassegrain", "Schmidt-Cassegrain")
        self.sec_mag_label.setVisible(is_cassegrain_variant)
        self.sec_mag_spin.setVisible(is_cassegrain_variant)

        # Meniscus thickness only for Maksutov-Cassegrain
        is_mak = telescope_type == "Maksutov-Cassegrain"
        self.meniscus_label.setVisible(is_mak)
        self.meniscus_spin.setVisible(is_mak)

        # Set default obstruction ratios by type
        if telescope_type == "Newtonian":
            self.obstruction_spin.setValue(0.20)  # 20% typical
        elif telescope_type == "Cassegrain":
            self.obstruction_spin.setValue(0.30)  # 30% typical
        elif telescope_type == "Maksutov-Cassegrain":
            self.obstruction_spin.setValue(0.33)  # 33% typical
        elif telescope_type == "Schmidt-Cassegrain":
            self.obstruction_spin.setValue(0.35)  # 35% typical

    def on_lock_fratio_toggled(self, checked):
        """Ensure only one lock is active at a time."""
        if checked:
            self.lock_focal_length_check.setChecked(False)

    def on_lock_focal_length_toggled(self, checked):
        """Ensure only one lock is active at a time."""
        if checked:
            self.lock_fratio_check.setChecked(False)

    def on_aperture_changed(self, aperture):
        """Update f/ratio or focal length when aperture changes."""
        if self.lock_fratio_check.isChecked():
            # Lock f/ratio, update focal length
            fratio = self.fratio_spin.value()
            new_focal_length = aperture * fratio
            self.focal_length_spin.blockSignals(True)
            self.focal_length_spin.setValue(new_focal_length)
            self.focal_length_spin.blockSignals(False)
        elif self.lock_focal_length_check.isChecked():
            # Lock focal length, update f/ratio
            focal_length = self.focal_length_spin.value()
            new_fratio = focal_length / aperture if aperture > 0 else 5.0
            self.fratio_spin.blockSignals(True)
            self.fratio_spin.setValue(new_fratio)
            self.fratio_spin.blockSignals(False)
        else:
            # Default: lock f/ratio, update focal length
            fratio = self.fratio_spin.value()
            new_focal_length = aperture * fratio
            self.focal_length_spin.blockSignals(True)
            self.focal_length_spin.setValue(new_focal_length)
            self.focal_length_spin.blockSignals(False)

        # Update meniscus thickness default (aperture/10)
        if self.meniscus_spin.isVisible():
            self.meniscus_spin.setValue(aperture / 10.0)

    def on_fratio_changed(self, fratio):
        """Update focal length when f/ratio changes."""
        aperture = self.aperture_spin.value()
        new_focal_length = aperture * fratio
        self.focal_length_spin.blockSignals(True)
        self.focal_length_spin.setValue(new_focal_length)
        self.focal_length_spin.blockSignals(False)

    def on_focal_length_changed(self, focal_length):
        """Update f/ratio when focal length changes."""
        aperture = self.aperture_spin.value()
        new_fratio = focal_length / aperture if aperture > 0 else 5.0
        self.fratio_spin.blockSignals(True)
        self.fratio_spin.setValue(new_fratio)
        self.fratio_spin.blockSignals(False)

    def build_telescope(self):
        """Build telescope object from current configuration."""
        telescope_type = self.telescope_combo.currentText().lower().replace("-", "")
        primary_diameter = self.aperture_spin.value()
        f_ratio = self.fratio_spin.value()
        focal_length = self.focal_length_spin.value()  # Use spinner value directly

        # Get primary type for reflectors (string: "parabolic" or "spherical")
        primary_type_str = self.primary_combo.currentText().lower()

        # Get obstruction settings (for reflectors)
        enable_obstruction = self.enable_obstruction_check.isChecked()
        obstruction_ratio = self.obstruction_spin.value()
        secondary_diameter = primary_diameter * obstruction_ratio

        # Secondary magnification for Cassegrain variants
        sec_mag = self.sec_mag_spin.value()

        if telescope_type == "newtonian":
            telescope = NewtonianTelescope(
                primary_diameter=primary_diameter,
                focal_length=focal_length,
                primary_type=primary_type_str,
                spider_vanes=int(self.spider_vanes_spin.value()),
                spider_vane_width=self.vane_width_spin.value(),
                secondary_minor_axis=secondary_diameter,
                enable_obstruction=enable_obstruction
            )
        elif telescope_type == "cassegrain":
            # CassegrainTelescope is always parabolic by definition
            telescope = CassegrainTelescope(
                primary_diameter=primary_diameter,
                primary_focal_length=focal_length,
                secondary_magnification=sec_mag,
                secondary_minor_axis=secondary_diameter,
                enable_obstruction=enable_obstruction
            )
        elif telescope_type == "refractor":
            # Map GUI labels to objective_type values
            objective_map = {
                "singlet": "singlet",
                "achromat": "achromat",
                "apo doublet": "apo-doublet",
                "apo triplet (air-spaced)": "apo-triplet"
            }
            objective_type = objective_map.get(
                self.objective_combo.currentText().lower(),
                "singlet"
            )
            telescope = RefractingTelescope(
                primary_diameter=primary_diameter,
                focal_length=focal_length,
                objective_type=objective_type
            )
        elif telescope_type == "maksutovcassegrain":
            telescope = MaksutovCassegrainTelescope(
                primary_diameter=primary_diameter,
                primary_focal_length=focal_length,
                secondary_magnification=sec_mag,
                meniscus_thickness=self.meniscus_spin.value(),
                secondary_minor_axis=secondary_diameter,
                enable_obstruction=enable_obstruction
            )
        elif telescope_type == "schmidtcassegrain":
            telescope = SchmidtCassegrainTelescope(
                primary_diameter=primary_diameter,
                primary_focal_length=focal_length,
                secondary_magnification=sec_mag,
                secondary_minor_axis=secondary_diameter,
                enable_obstruction=enable_obstruction
            )
        else:
            telescope = NewtonianTelescope(
                primary_diameter=primary_diameter,
                focal_length=focal_length,
                secondary_minor_axis=secondary_diameter,
                enable_obstruction=enable_obstruction
            )

        return telescope

    def calculate_metrics(self, telescope):
        """Calculate performance metrics with breakdown of contributions."""
        wavelength_nm = self.wavelength_spin.value()
        wavelength_m = wavelength_nm * 1e-9
        aperture_m = telescope.primary_diameter * 1e-3
        plate_scale = 206265.0 / telescope.focal_length  # arcsec/mm

        # Diffraction limit — pure aperture (no obstruction)
        rayleigh_base = rayleigh_criterion_arcsec(wavelength_m, aperture_m, 0.0)

        # Diffraction limit — with obstruction
        obstruction_ratio = telescope.obstruction_ratio if hasattr(telescope, 'obstruction_ratio') else 0.0
        rayleigh_with_obs = rayleigh_criterion_arcsec(wavelength_m, aperture_m, obstruction_ratio)

        # Obstruction effect on resolution (narrower core)
        obstruction_effect = rayleigh_base - rayleigh_with_obs  # positive = narrower

        # Dawes limit (empirical for visual double stars)
        dawes_arcsec = 116.0 / telescope.primary_diameter

        # Airy disk diameter
        airy_disk_arcsec = 2.44 * wavelength_m / aperture_m * 206265

        # Spider vane metrics
        n_vanes = int(getattr(telescope, 'spider_vanes', 0))
        vane_width_mm = getattr(telescope, 'spider_vane_width', 0.0)
        radius_mm = telescope.primary_diameter / 2.0
        if n_vanes > 0 and radius_mm > 0:
            blocked_area = n_vanes * vane_width_mm * radius_mm
            total_area = np.pi * radius_mm ** 2
            spider_blocked_frac = blocked_area / total_area
            spider_strehl = (1 - spider_blocked_frac) ** 2
        else:
            spider_blocked_frac = 0.0
            spider_strehl = 1.0

        # Geometric aberrations
        primary_type = getattr(telescope, 'primary_type', 'parabolic')
        spherical_blur_arcsec = 0.0
        if primary_type == 'spherical':
            # Rough estimate: spherical aberration scales with (D/f)^3
            # For f/5 spherical, blur ~ 10-20 arcsec; for f/10, ~ 1-2 arcsec
            f_ratio = telescope.focal_ratio
            spherical_blur_arcsec = 1000.0 / (f_ratio ** 3)  # Approximate formula

        # Chromatic aberration (for refractors)
        chromatic_blur_arcsec = 0.0
        telescope_type = self.telescope_combo.currentText().lower()
        objective_type = getattr(telescope, 'objective_type', None)
        if telescope_type == "refractor" and objective_type == "singlet":
            # Singlet refractors have significant chromatic aberration
            # Approximate: ~2 arcsec at f/15, scales inversely with f-ratio
            chromatic_blur_arcsec = 30.0 / telescope.focal_ratio

        # Central obstruction impact
        obstruction_pct = 0.0
        if hasattr(telescope, 'obstruction_ratio'):
            obstruction_pct = telescope.obstruction_ratio * 100

        return {
            "rayleigh": rayleigh_with_obs,
            "rayleigh_base": rayleigh_base,
            "rayleigh_with_obs": rayleigh_with_obs,
            "obstruction_effect": obstruction_effect,
            "spider_blocked_frac": spider_blocked_frac,
            "spider_strehl": spider_strehl,
            "n_vanes": n_vanes,
            "dawes": dawes_arcsec,
            "airy_disk": airy_disk_arcsec,
            "wavelength": wavelength_nm,
            "aperture": telescope.primary_diameter,
            "fratio": telescope.focal_ratio,
            "spherical_blur": spherical_blur_arcsec,
            "chromatic_blur": chromatic_blur_arcsec,
            "obstruction_pct": obstruction_pct,
            "primary_type": primary_type
        }

    def update_metrics_label(self, metrics):
        """Update the metrics display with resolution breakdown."""
        # Build breakdown text
        breakdown_parts = [f"Diffraction (aperture): {metrics['rayleigh_base']:.2f}\""]

        if metrics['obstruction_pct'] > 0:
            effect = metrics['obstruction_effect']
            sign = "+" if effect >= 0 else ""
            breakdown_parts.append(
                f"Obstruction: {metrics['obstruction_pct']:.0f}% "
                f"(resolution {sign}{effect:.2f}\" narrower core)"
            )

        if metrics['n_vanes'] > 0:
            breakdown_parts.append(
                f"Spider vanes: {metrics['spider_blocked_frac']*100:.1f}% blocked "
                f"(Strehl \u2248{metrics['spider_strehl']:.2f})"
            )

        if metrics['spherical_blur'] > 0.1:
            breakdown_parts.append(f"Spherical: {metrics['spherical_blur']:.2f}\"")

        if metrics['chromatic_blur'] > 0.1:
            breakdown_parts.append(f"Chromatic: {metrics['chromatic_blur']:.2f}\"")

        breakdown = " • ".join(breakdown_parts)

        tip = ""
        if metrics['obstruction_pct'] > 0:
            tip = "\nTip: Obstruction effect on extended objects is subtle (modeled in PSF convolution). Use Point Source to see it directly."

        text = (
            f"Current: D={metrics['aperture']:.0f}mm, f/{metrics['fratio']:.1f}, "
            f"\u03bb={metrics['wavelength']:.0f}nm, {metrics['primary_type']} | "
            f"Resolution Breakdown: {breakdown}{tip}"
        )
        self.metrics_label.setText(text)

    def update_view(self):
        """Update PSF, spot diagram, and metrics."""
        try:
            telescope = self.build_telescope()
            wavelength_nm = self.wavelength_spin.value()

            # Update effective f/ratio display
            actual_fratio = telescope.focal_ratio
            user_fratio = self.fratio_spin.value()

            if abs(actual_fratio - user_fratio) > 0.1:
                # Telescope overrode f/ratio (e.g., Maksutov with secondary magnification)
                self.effective_fratio_label.setText(
                    f"⚠ Effective f/ratio: f/{actual_fratio:.1f} "
                    f"(telescope uses {actual_fratio:.1f}, not input {user_fratio:.1f})"
                )
                self.effective_fratio_label.setStyleSheet("font-style: italic; color: #cc6600; font-weight: bold;")
            else:
                self.effective_fratio_label.setText(f"✓ Effective f/ratio: f/{actual_fratio:.1f}")
                self.effective_fratio_label.setStyleSheet("font-style: italic; color: #666;")

            # Calculate and display metrics
            metrics = self.calculate_metrics(telescope)
            self.update_metrics_label(metrics)

            # Determine analysis view mode
            analysis_view = self.analysis_combo.currentText()
            telescope_type = self.telescope_combo.currentText()
            include_obstruction = self.enable_obstruction_check.isChecked()

            if analysis_view == "Coma Field Analysis":
                # Coma field analysis on psf_canvas (spot hidden)
                fig_coma = plot_coma_field_analysis(
                    telescope,
                    wavelength_nm=wavelength_nm,
                    include_obstruction=include_obstruction,
                    figsize=(14, 7)
                )
                self.psf_canvas.set_figure(fig_coma)
                plt.close(fig_coma)

            elif analysis_view == "Vignetting Curve":
                # Vignetting curve on psf_canvas (spot hidden)
                fig_vig = plot_vignetting_curve(
                    telescope,
                    figsize=(9, 6)
                )
                self.psf_canvas.set_figure(fig_vig)
                plt.close(fig_vig)

            else:
                # Default: PSF + Spot Diagram
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
                        include_obstruction=include_obstruction,
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

                    # Add secondary x-axis in arcseconds
                    focal_length = telescope.focal_length
                    plate_scale = 206265.0 / focal_length  # arcsec/mm
                    def _um_to_arcsec(x_um, ps=plate_scale):
                        return x_um * ps / 1000.0
                    def _arcsec_to_um(x_arcsec, ps=plate_scale):
                        return x_arcsec * 1000.0 / ps
                    ax_top = ax.secondary_xaxis('top', functions=(_um_to_arcsec, _arcsec_to_um))
                    ax_top.set_xlabel("Angular distance (arcsec)", fontsize=8)

                    fig_psf.tight_layout()
                    plt.close(fig_full)  # Close the temporary full figure
                else:
                    # 2D image (plot_psf_2d uses log scale internally)
                    autoscale = self.autoscale_psf_check.isChecked()
                    fig_psf = plot_psf_2d(
                        telescope,
                        wavelength_nm=wavelength_nm,
                        include_obstruction=include_obstruction,
                        autoscale=autoscale,
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

                # Set figure with optional axis limit preservation
                self.psf_canvas.set_figure(fig_psf, preserve_limits=self.lock_axes_check.isChecked())
                plt.close(fig_psf)

                # Update spot diagram (requires traced rays)
                from telescope_sim.source.light_source import create_parallel_rays
                rays = create_parallel_rays(
                    num_rays=21,  # More rays for better spot diagram
                    aperture_diameter=telescope.primary_diameter,
                    entry_height=telescope.tube_length * 1.15,
                    wavelength_nm=wavelength_nm  # Pass wavelength for chromatic effects
                )
                telescope.trace_rays(rays)

                title = f"{telescope.primary_diameter:.0f}mm f/{telescope.focal_ratio:.1f} {telescope_type} — Spot Diagram"
                fig_spot = plot_spot_diagram(
                    rays,
                    title=title,
                    figsize=(9, 9)  # Increased from 6x6 to 9x9 inches for better visibility
                )
                self.spot_canvas.set_figure(fig_spot)
                plt.close(fig_spot)

        except Exception as e:
            print(f"Error updating performance view: {e}")
            import traceback
            traceback.print_exc()

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
from telescope_sim.geometry import (
    NewtonianTelescope, CassegrainTelescope, RefractingTelescope,
    MaksutovCassegrainTelescope, SchmidtCassegrainTelescope
)
from telescope_sim.geometry.eyepiece import Eyepiece
from telescope_sim.plotting import plot_ray_trace, plot_source_image, plot_polychromatic_ray_trace
from telescope_sim.source.sources import Jupiter, Moon, Saturn, StarField, PointSource
from telescope_sim.source.light_source import create_parallel_rays
from telescope_sim.physics.diffraction import rayleigh_criterion_arcsec


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

        # Controls — 2-column grid (label | widget), one control per row
        controls_group = QGroupBox("Controls")
        controls_layout = QGridLayout()

        row = 0

        # Telescope type
        controls_layout.addWidget(QLabel("Telescope Type:"), row, 0)
        row += 1
        self.telescope_combo = QComboBox()
        self.telescope_combo.addItems([
            "Newtonian", "Cassegrain", "Refractor",
            "Maksutov-Cassegrain", "Schmidt-Cassegrain"
        ])
        self.telescope_combo.setCurrentText("Newtonian")
        self.telescope_combo.currentTextChanged.connect(self.on_telescope_type_changed)
        controls_layout.addWidget(self.telescope_combo, row, 0)

        row += 1

        # Aperture
        controls_layout.addWidget(QLabel("Aperture (mm):"), row, 0)
        row += 1
        self.aperture_spin = QDoubleSpinBox()
        self.aperture_spin.setRange(50.0, 500.0)
        self.aperture_spin.setSingleStep(10.0)
        self.aperture_spin.setValue(200.0)
        controls_layout.addWidget(self.aperture_spin, row, 0)

        row += 1

        # Primary type (for reflectors)
        self.primary_label = QLabel("Primary Type:")
        controls_layout.addWidget(self.primary_label, row, 0)
        row += 1
        self.primary_combo = QComboBox()
        self.primary_combo.addItems(["Parabolic", "Spherical"])
        self.primary_combo.setCurrentText("Parabolic")
        controls_layout.addWidget(self.primary_combo, row, 0)

        # Objective type (for refractors) — shares same rows, toggled by visibility
        self.objective_label = QLabel("Objective Type:")
        controls_layout.addWidget(self.objective_label, row - 1, 0)
        self.objective_combo = QComboBox()
        self.objective_combo.addItems([
            "Singlet", "Achromat", "APO Doublet",
            "APO Triplet (air-spaced)"
        ])
        self.objective_combo.setCurrentText("Singlet")
        controls_layout.addWidget(self.objective_combo, row, 0)

        # Hide objective controls initially (shown when refractor selected)
        self.objective_label.hide()
        self.objective_combo.hide()

        row += 1

        # Secondary magnification (for Cassegrain variants)
        self.sec_mag_label = QLabel("Secondary Magnification:")
        self.sec_mag_label.setToolTip("System focal length = primary FL × this value")
        controls_layout.addWidget(self.sec_mag_label, row, 0)
        row += 1
        self.sec_mag_spin = QDoubleSpinBox()
        self.sec_mag_spin.setRange(1.5, 6.0)
        self.sec_mag_spin.setSingleStep(0.5)
        self.sec_mag_spin.setValue(3.0)
        self.sec_mag_spin.setToolTip("System focal length = primary FL × this value")
        controls_layout.addWidget(self.sec_mag_spin, row, 0)
        # Hidden by default (shown for Cassegrain variants)
        self.sec_mag_label.hide()
        self.sec_mag_spin.hide()

        row += 1

        # f-ratio
        controls_layout.addWidget(QLabel("f-ratio:"), row, 0)
        row += 1
        self.fratio_spin = QDoubleSpinBox()
        self.fratio_spin.setRange(3.0, 15.0)
        self.fratio_spin.setSingleStep(0.1)
        self.fratio_spin.setValue(5.0)
        controls_layout.addWidget(self.fratio_spin, row, 0)
        row += 1
        self.lock_fratio_check = QCheckBox("Lock f-ratio")
        self.lock_fratio_check.setToolTip("Lock f-ratio when changing aperture")
        self.lock_fratio_check.setChecked(True)  # Default to locking f-ratio
        controls_layout.addWidget(self.lock_fratio_check, row, 0)

        row += 1

        # Focal length
        controls_layout.addWidget(QLabel("Focal Length (mm):"), row, 0)
        row += 1
        self.focal_length_spin = QDoubleSpinBox()
        self.focal_length_spin.setRange(150.0, 3000.0)
        self.focal_length_spin.setSingleStep(10.0)
        self.focal_length_spin.setValue(1000.0)  # Default: 200mm × f/5
        controls_layout.addWidget(self.focal_length_spin, row, 0)
        row += 1
        self.lock_focal_length_check = QCheckBox("Lock focal length")
        self.lock_focal_length_check.setToolTip("Lock focal length when changing aperture")
        controls_layout.addWidget(self.lock_focal_length_check, row, 0)

        row += 1

        # Effective f/ratio display
        self.effective_fratio_label = QLabel("Effective f/ratio: (build telescope to see)")
        self.effective_fratio_label.setWordWrap(True)
        self.effective_fratio_label.setStyleSheet("font-style: italic; color: #666;")
        controls_layout.addWidget(self.effective_fratio_label, row, 0)

        row += 1

        # Secondary obstruction controls (for reflectors)
        self.obstruction_label = QLabel("Secondary Obstruction:")
        controls_layout.addWidget(self.obstruction_label, row, 0)
        row += 1
        self.enable_obstruction_check = QCheckBox("Enable")
        self.enable_obstruction_check.setChecked(True)
        self.enable_obstruction_check.setToolTip(
            "Enable/disable secondary mirror obstruction effects on PSF and resolution"
        )
        controls_layout.addWidget(self.enable_obstruction_check, row, 0)
        row += 1
        self.obstruction_ratio_label = QLabel("Obstruction Ratio:")
        controls_layout.addWidget(self.obstruction_ratio_label, row, 0)
        row += 1
        self.obstruction_spin = QDoubleSpinBox()
        self.obstruction_spin.setRange(0.0, 0.5)  # 0% to 50%
        self.obstruction_spin.setSingleStep(0.01)
        self.obstruction_spin.setValue(0.20)  # Default 20% for Newtonian
        self.obstruction_spin.setDecimals(2)
        self.obstruction_spin.setToolTip(
            "Secondary diameter / Primary diameter (0.2 = 20% obstruction)"
        )
        controls_layout.addWidget(self.obstruction_spin, row, 0)

        row += 1

        # Spider vanes (for reflectors)
        self.spider_vanes_label = QLabel("Spider Vanes:")
        controls_layout.addWidget(self.spider_vanes_label, row, 0)
        row += 1
        self.spider_vanes_spin = QDoubleSpinBox()
        self.spider_vanes_spin.setRange(0, 6)
        self.spider_vanes_spin.setDecimals(0)
        self.spider_vanes_spin.setValue(0)
        controls_layout.addWidget(self.spider_vanes_spin, row, 0)

        row += 1
        self.vane_width_label = QLabel("Vane Width (mm):")
        controls_layout.addWidget(self.vane_width_label, row, 0)
        row += 1
        self.vane_width_spin = QDoubleSpinBox()
        self.vane_width_spin.setRange(0.5, 5.0)
        self.vane_width_spin.setSingleStep(0.5)
        self.vane_width_spin.setValue(2.0)
        controls_layout.addWidget(self.vane_width_spin, row, 0)

        row += 1

        # Source
        controls_layout.addWidget(QLabel("Source:"), row, 0)
        row += 1
        self.source_combo = QComboBox()
        self.source_combo.addItems([
            "Jupiter", "Saturn", "Moon", "Star Field",
            "Point Source (Star)", "None"
        ])
        self.source_combo.setCurrentText("Jupiter")
        controls_layout.addWidget(self.source_combo, row, 0)

        row += 1

        # Seeing
        controls_layout.addWidget(QLabel("Seeing:"), row, 0)
        row += 1
        self.seeing_combo = QComboBox()
        self.seeing_combo.addItems(["Excellent", "Good", "Average", "Poor", "None"])
        self.seeing_combo.setCurrentText("Good")
        controls_layout.addWidget(self.seeing_combo, row, 0)

        row += 1

        # Meniscus thickness (Maksutov-Cassegrain only)
        self.meniscus_label = QLabel("Meniscus (mm):")
        self.meniscus_label.setToolTip("Meniscus corrector thickness. Default = aperture/10.")
        controls_layout.addWidget(self.meniscus_label, row, 0)
        row += 1
        self.meniscus_spin = QDoubleSpinBox()
        self.meniscus_spin.setRange(5.0, 50.0)
        self.meniscus_spin.setSingleStep(1.0)
        self.meniscus_spin.setValue(self.aperture_spin.value() / 10.0)
        self.meniscus_spin.setToolTip("Meniscus corrector thickness. Default = aperture/10.")
        controls_layout.addWidget(self.meniscus_spin, row, 0)
        self.meniscus_label.hide()
        self.meniscus_spin.hide()

        row += 1

        # Eyepiece controls
        self.eyepiece_check = QCheckBox("Use Eyepiece")
        self.eyepiece_check.setChecked(False)
        self.eyepiece_check.toggled.connect(self.toggle_eyepiece)
        controls_layout.addWidget(self.eyepiece_check, row, 0)

        row += 1
        controls_layout.addWidget(QLabel("Eyepiece FL (mm):"), row, 0)
        row += 1
        self.eyepiece_spin = QDoubleSpinBox()
        self.eyepiece_spin.setRange(3.0, 40.0)
        self.eyepiece_spin.setSingleStep(1.0)
        self.eyepiece_spin.setValue(10.0)
        self.eyepiece_spin.setEnabled(False)
        controls_layout.addWidget(self.eyepiece_spin, row, 0)

        row += 1
        controls_layout.addWidget(QLabel("Apparent FOV (\u00b0):"), row, 0)
        row += 1
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
        controls_layout.addWidget(self.afov_spin, row, 0)

        row += 1

        # Polychromatic ray trace toggle
        self.polychromatic_check = QCheckBox("Polychromatic Ray Trace")
        self.polychromatic_check.setToolTip(
            "Show R/G/B colored rays to visualize chromatic aberration.\n"
            "Most useful for refractors (singlet, achromat, etc)."
        )
        controls_layout.addWidget(self.polychromatic_check, row, 0)
        row += 1
        self.polychromatic_desc = QLabel("(R/G/B rays — chromatic aberration)")
        self.polychromatic_desc.setWordWrap(True)
        self.polychromatic_desc.setStyleSheet("font-size: 8pt; color: #666;")
        controls_layout.addWidget(self.polychromatic_desc, row, 0)

        row += 1

        # Update button
        self.update_button = QPushButton("Update View")
        self.update_button.clicked.connect(self.update_view)
        controls_layout.addWidget(self.update_button, row, 0)

        controls_group.setLayout(controls_layout)
        sidebar_layout.addWidget(controls_group)
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

        # Connect focal length synchronization signals
        self.aperture_spin.valueChanged.connect(self.on_aperture_changed)
        self.fratio_spin.valueChanged.connect(self.on_fratio_changed)
        self.focal_length_spin.valueChanged.connect(self.on_focal_length_changed)
        self.lock_fratio_check.toggled.connect(self.on_lock_fratio_toggled)
        self.lock_focal_length_check.toggled.connect(self.on_lock_focal_length_toggled)

        # Initial render
        self.update_view()

    def toggle_eyepiece(self, checked):
        """Enable/disable eyepiece controls."""
        self.eyepiece_spin.setEnabled(checked)
        self.afov_spin.setEnabled(checked)

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
        self.obstruction_ratio_label.setVisible(not is_refractor)
        self.obstruction_spin.setVisible(not is_refractor)

        # Spider vanes only for reflectors
        self.spider_vanes_label.setVisible(not is_refractor)
        self.spider_vanes_spin.setVisible(not is_refractor)
        self.vane_width_label.setVisible(not is_refractor)
        self.vane_width_spin.setVisible(not is_refractor)

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

    def build_telescope(self):
        """Build telescope object from current configuration."""
        telescope_type = self.telescope_combo.currentText().lower().replace("-", "")
        primary_diameter = self.aperture_spin.value()
        f_ratio = self.fratio_spin.value()
        focal_length = self.focal_length_spin.value()  # Use spinner value directly

        # Get obstruction settings (for reflectors)
        enable_obstruction = self.enable_obstruction_check.isChecked()
        obstruction_ratio = self.obstruction_spin.value()
        secondary_diameter = primary_diameter * obstruction_ratio

        # Secondary magnification for Cassegrain variants
        sec_mag = self.sec_mag_spin.value()

        # Spider vane settings
        spider_vanes = int(self.spider_vanes_spin.value())
        spider_vane_width = self.vane_width_spin.value()

        if telescope_type == "newtonian":
            primary_type = self.primary_combo.currentText().lower()
            telescope = NewtonianTelescope(
                primary_diameter=primary_diameter,
                focal_length=focal_length,
                primary_type=primary_type,
                spider_vanes=spider_vanes,
                spider_vane_width=spider_vane_width,
                secondary_minor_axis=secondary_diameter,
                enable_obstruction=enable_obstruction
            )
        elif telescope_type == "cassegrain":
            telescope = CassegrainTelescope(
                primary_diameter=primary_diameter,
                primary_focal_length=focal_length,
                secondary_magnification=sec_mag,
                spider_vanes=spider_vanes,
                spider_vane_width=spider_vane_width,
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
                spider_vanes=spider_vanes,
                spider_vane_width=spider_vane_width,
                secondary_minor_axis=secondary_diameter,
                enable_obstruction=enable_obstruction
            )
        elif telescope_type == "schmidtcassegrain":
            telescope = SchmidtCassegrainTelescope(
                primary_diameter=primary_diameter,
                primary_focal_length=focal_length,
                secondary_magnification=sec_mag,
                spider_vanes=spider_vanes,
                spider_vane_width=spider_vane_width,
                secondary_minor_axis=secondary_diameter,
                enable_obstruction=enable_obstruction
            )
        else:
            # Default to Newtonian
            telescope = NewtonianTelescope(
                primary_diameter=primary_diameter,
                focal_length=focal_length,
                spider_vanes=spider_vanes,
                spider_vane_width=spider_vane_width,
                secondary_minor_axis=secondary_diameter,
                enable_obstruction=enable_obstruction
            )

        return telescope

    def build_source(self):
        """Build source object from current configuration."""
        source_type = self.source_combo.currentText().lower().replace(" ", "")

        if source_type == "jupiter":
            return Jupiter()
        elif source_type == "saturn":
            return Saturn()
        elif source_type == "moon":
            return Moon()
        elif source_type == "starfield":
            return StarField()
        elif source_type == "pointsource(star)":
            return PointSource()
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
                f"Eyepiece: {eyepiece.focal_length_mm:.0f}mm ({eyepiece.apparent_fov_deg:.0f}° AFOV) → "
                f"{mag:.0f}× magnification, {exit_pupil:.1f}mm exit pupil, {true_fov:.2f}° true FOV"
            )
        else:
            self.eyepiece_label.setText("Direct focal plane view (no eyepiece)")

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

        telescope = self.build_telescope()
        eyepiece = self.get_eyepiece(telescope)

        # Build title
        title = f"{telescope.primary_diameter:.0f}mm f/{telescope.focal_ratio:.1f}"
        if eyepiece:
            mag = telescope.focal_length / eyepiece.focal_length_mm
            title += f" with {eyepiece.focal_length_mm:.0f}mm eyepiece ({mag:.0f}× magnification)"
        else:
            title += " — Direct Focal Plane"

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
            # Build telescope and source
            telescope = self.build_telescope()
            source = self.build_source()
            seeing = self.get_seeing_value()
            eyepiece = self.get_eyepiece(telescope)

            # Update performance label
            self.update_performance_label(telescope, seeing)

            # Update eyepiece label
            self.update_eyepiece_label(telescope, eyepiece)

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

            # Update ray trace
            telescope_type = self.telescope_combo.currentText()

            if self.polychromatic_check.isChecked():
                # Polychromatic ray trace (R/G/B colored rays)
                fig_ray_trace = plot_polychromatic_ray_trace(
                    telescope, num_display_rays=11
                )
            else:
                # Standard monochromatic ray trace
                rays = create_parallel_rays(
                    num_rays=11,
                    aperture_diameter=telescope.primary_diameter,
                    entry_height=telescope.tube_length * 1.15,
                )
                telescope.trace_rays(rays)
                components = telescope.get_components_for_plotting()
                title = f"{telescope.primary_diameter:.0f}mm f/{telescope.focal_ratio:.1f} (FL: {telescope.focal_length:.0f}mm) {telescope_type} — Ray Trace"
                fig_ray_trace = plot_ray_trace(rays, components, title=title)

            self.ray_trace_canvas.set_figure(fig_ray_trace)
            plt.close(fig_ray_trace)  # Close to free memory

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

                # plot_source_image returns a list if eyepiece is used, single figure otherwise
                if isinstance(result, list):
                    # With eyepiece: [normal_view, true_angular_size_view, eyepiece_view]
                    self.current_figure = result[0]  # Standardized size
                    self.true_size_figure = result[1] if len(result) > 1 else None
                    self.eyepiece_view_figure = result[2] if len(result) > 2 else None
                else:
                    # Without eyepiece: single figure
                    self.current_figure = result
                    self.true_size_figure = None
                    self.eyepiece_view_figure = None

                # Enable buttons
                self.scaled_button.setEnabled(True)
                self.popout_button.setEnabled(True)

                # Enable eyepiece-dependent buttons
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

                # Display based on current mode
                self.refresh_image_display()

                # Don't close these - we need them for display/pop-out
            else:
                # Clear image canvas
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

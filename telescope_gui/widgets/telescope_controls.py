"""
Shared TelescopeControlPanel widget.

A composite QWidget containing all telescope configuration controls:
type, aperture, f-ratio, focal length (with bidirectional sync),
primary type, objective type, secondary magnification, meniscus thickness,
spider vanes, vane width, and obstruction ratio.

Used by all 5 GUI tabs (single-mode and comparison-mode) to eliminate
code duplication.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout,
    QLabel, QComboBox, QDoubleSpinBox, QCheckBox, QGroupBox,
)
from PyQt6.QtCore import pyqtSignal

from telescope_gui.telescope_builder import build_telescope


# Default obstruction ratios by telescope type
DEFAULT_OBSTRUCTION = {
    "Newtonian": 0.20,
    "Cassegrain": 0.30,
    "Maksutov-Cassegrain": 0.33,
    "Schmidt-Cassegrain": 0.35,
}


class TelescopeControlPanel(QWidget):
    """Composite widget with all telescope configuration controls.

    Supports two layout modes:
    - ``layout_mode="sidebar"`` — single-column vertical (label on its own row,
      widget on the next row). Used by design_tab and ray_traces_tab sidebars.
    - ``layout_mode="grid"`` — compact multi-column grid (label and widget on
      the same row). Used by performance_tab bottom bar and comparison
      images/analytics horizontal controls.

    Signals:
        config_changed: Emitted whenever any control value changes.
    """

    config_changed = pyqtSignal()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, number=1, layout_mode="sidebar", show_group_box=True,
                 default_type="Newtonian", default_fratio=5.0, parent=None):
        """
        Args:
            number: Telescope number (1 or 2) — used for header label.
            layout_mode: "sidebar" for vertical layout, "grid" for horizontal.
            show_group_box: Wrap controls in a QGroupBox titled "Controls".
            default_type: Initial telescope type selection.
            default_fratio: Initial f-ratio value.
            parent: Parent QWidget.
        """
        super().__init__(parent)
        self._number = number
        self._layout_mode = layout_mode
        self._guard = False  # Reentrancy guard for focal-length sync

        self._build_ui(show_group_box, default_type, default_fratio)
        self._connect_signals()
        self.update_controls_visibility()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_config(self):
        """Return a dict of all current control values.

        The dict keys match the ``build_telescope()`` keyword arguments so
        callers can do ``build_telescope(**panel.get_config())``.
        """
        return {
            "telescope_type": self.type_combo.currentText(),
            "diameter": self.aperture_spin.value(),
            "focal_length": self.focal_length_spin.value(),
            "primary_type": self.primary_combo.currentText().lower(),
            "objective_type": self.objective_combo.currentText(),
            "secondary_magnification": self.sec_mag_spin.value(),
            "meniscus_thickness": self.meniscus_spin.value(),
            "spider_vanes": int(self.spider_vanes_spin.value()),
            "spider_vane_width": self.vane_width_spin.value(),
            "obstruction_ratio": self.obstruction_spin.value(),
            "enable_obstruction": self.enable_obstruction_check.isChecked(),
        }

    def build(self):
        """Convenience: build a telescope from the current config."""
        return build_telescope(**self.get_config())

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self, show_group_box, default_type, default_fratio):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        if self._layout_mode == "sidebar":
            self._build_sidebar(outer, show_group_box, default_type, default_fratio)
        else:
            self._build_grid(outer, show_group_box, default_type, default_fratio)

    # ---- Sidebar (vertical, label-above-widget) layout ----

    def _build_sidebar(self, outer, show_group_box, default_type, default_fratio):
        group = QGroupBox("Controls") if show_group_box else QWidget()
        grid = QGridLayout()
        grid.setContentsMargins(4, 8, 4, 4)
        grid.setVerticalSpacing(2)
        row = 0

        # Telescope type
        grid.addWidget(QLabel("Telescope Type:"), row, 0); row += 1
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Newtonian", "Cassegrain", "Refractor",
            "Maksutov-Cassegrain", "Schmidt-Cassegrain",
        ])
        self.type_combo.setCurrentText(default_type)
        grid.addWidget(self.type_combo, row, 0); row += 1

        # Aperture
        grid.addWidget(QLabel("Aperture (mm):"), row, 0); row += 1
        self.aperture_spin = QDoubleSpinBox()
        self.aperture_spin.setRange(50.0, 500.0)
        self.aperture_spin.setSingleStep(10.0)
        self.aperture_spin.setValue(200.0)
        grid.addWidget(self.aperture_spin, row, 0); row += 1

        # Primary type (Newtonian only)
        self.primary_label = QLabel("Primary Type:")
        grid.addWidget(self.primary_label, row, 0); row += 1
        self.primary_combo = QComboBox()
        self.primary_combo.addItems(["Parabolic", "Spherical"])
        grid.addWidget(self.primary_combo, row, 0)

        # Objective type (Refractor only) — shares same rows
        self.objective_label = QLabel("Objective Type:")
        grid.addWidget(self.objective_label, row - 1, 0)
        self.objective_combo = QComboBox()
        self.objective_combo.addItems([
            "Singlet", "Achromat", "APO Doublet",
            "APO Triplet (air-spaced)",
        ])
        grid.addWidget(self.objective_combo, row, 0)
        self.objective_label.hide()
        self.objective_combo.hide()
        row += 1

        # Secondary magnification (Cassegrain variants)
        self.sec_mag_label = QLabel("Secondary Magnification:")
        self.sec_mag_label.setToolTip("System focal length = primary FL × this value")
        grid.addWidget(self.sec_mag_label, row, 0); row += 1
        self.sec_mag_spin = QDoubleSpinBox()
        self.sec_mag_spin.setRange(1.5, 6.0)
        self.sec_mag_spin.setSingleStep(0.5)
        self.sec_mag_spin.setValue(3.0)
        self.sec_mag_spin.setToolTip("System focal length = primary FL × this value")
        grid.addWidget(self.sec_mag_spin, row, 0)
        self.sec_mag_label.hide()
        self.sec_mag_spin.hide()
        row += 1

        # f-ratio
        grid.addWidget(QLabel("f-ratio:"), row, 0); row += 1
        self.fratio_spin = QDoubleSpinBox()
        self.fratio_spin.setRange(3.0, 15.0)
        self.fratio_spin.setSingleStep(0.1)
        self.fratio_spin.setValue(default_fratio)
        grid.addWidget(self.fratio_spin, row, 0); row += 1

        self.lock_fratio_check = QCheckBox("Lock f-ratio")
        self.lock_fratio_check.setToolTip("Lock f-ratio when changing aperture")
        self.lock_fratio_check.setChecked(True)
        grid.addWidget(self.lock_fratio_check, row, 0); row += 1

        # Focal length
        grid.addWidget(QLabel("Focal Length (mm):"), row, 0); row += 1
        self.focal_length_spin = QDoubleSpinBox()
        self.focal_length_spin.setRange(150.0, 7500.0)
        self.focal_length_spin.setSingleStep(10.0)
        self.focal_length_spin.setDecimals(1)
        initial_fl = self.aperture_spin.value() * self.fratio_spin.value()
        self.focal_length_spin.setValue(initial_fl)
        grid.addWidget(self.focal_length_spin, row, 0); row += 1

        self.lock_focal_length_check = QCheckBox("Lock focal length")
        self.lock_focal_length_check.setToolTip("Lock focal length when changing aperture")
        grid.addWidget(self.lock_focal_length_check, row, 0); row += 1

        # Effective f/ratio display
        self.effective_fratio_label = QLabel("Effective f/ratio: (build telescope to see)")
        self.effective_fratio_label.setWordWrap(True)
        self.effective_fratio_label.setStyleSheet("font-style: italic; color: #666;")
        grid.addWidget(self.effective_fratio_label, row, 0); row += 1

        # Obstruction controls
        self.obstruction_label = QLabel("Secondary Obstruction:")
        grid.addWidget(self.obstruction_label, row, 0); row += 1
        self.enable_obstruction_check = QCheckBox("Enable")
        self.enable_obstruction_check.setChecked(True)
        self.enable_obstruction_check.setToolTip(
            "Enable/disable secondary mirror obstruction effects on PSF and resolution"
        )
        grid.addWidget(self.enable_obstruction_check, row, 0); row += 1

        self.obstruction_ratio_label = QLabel("Obstruction Ratio:")
        grid.addWidget(self.obstruction_ratio_label, row, 0); row += 1
        self.obstruction_spin = QDoubleSpinBox()
        self.obstruction_spin.setRange(0.0, 0.5)
        self.obstruction_spin.setSingleStep(0.01)
        self.obstruction_spin.setValue(DEFAULT_OBSTRUCTION.get(default_type, 0.20))
        self.obstruction_spin.setDecimals(2)
        self.obstruction_spin.setToolTip(
            "Secondary diameter / Primary diameter (0.2 = 20% obstruction)"
        )
        grid.addWidget(self.obstruction_spin, row, 0); row += 1

        # Spider vanes
        self.spider_vanes_label = QLabel("Spider Vanes:")
        grid.addWidget(self.spider_vanes_label, row, 0); row += 1
        self.spider_vanes_spin = QDoubleSpinBox()
        self.spider_vanes_spin.setRange(0, 6)
        self.spider_vanes_spin.setDecimals(0)
        self.spider_vanes_spin.setValue(0)
        grid.addWidget(self.spider_vanes_spin, row, 0); row += 1

        self.vane_width_label = QLabel("Vane Width (mm):")
        grid.addWidget(self.vane_width_label, row, 0); row += 1
        self.vane_width_spin = QDoubleSpinBox()
        self.vane_width_spin.setRange(0.5, 5.0)
        self.vane_width_spin.setSingleStep(0.5)
        self.vane_width_spin.setValue(2.0)
        grid.addWidget(self.vane_width_spin, row, 0); row += 1

        # Meniscus thickness (Maksutov only)
        self.meniscus_label = QLabel("Meniscus (mm):")
        self.meniscus_label.setToolTip("Meniscus corrector thickness. Default = aperture/10.")
        grid.addWidget(self.meniscus_label, row, 0); row += 1
        self.meniscus_spin = QDoubleSpinBox()
        self.meniscus_spin.setRange(5.0, 50.0)
        self.meniscus_spin.setSingleStep(1.0)
        self.meniscus_spin.setValue(self.aperture_spin.value() / 10.0)
        self.meniscus_spin.setToolTip("Meniscus corrector thickness. Default = aperture/10.")
        grid.addWidget(self.meniscus_spin, row, 0)
        self.meniscus_label.hide()
        self.meniscus_spin.hide()
        row += 1

        group.setLayout(grid)
        outer.addWidget(group)

    # ---- Grid (horizontal, compact multi-column) layout ----

    def _build_grid(self, outer, show_group_box, default_type, default_fratio):
        group = QGroupBox("Controls") if show_group_box else QWidget()
        grid = QGridLayout()
        grid.setVerticalSpacing(2)
        grid.setHorizontalSpacing(4)
        row = 0

        # Row 0: type + aperture
        grid.addWidget(QLabel("Type:"), row, 0)
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Newtonian", "Cassegrain", "Refractor",
            "Maksutov-Cassegrain", "Schmidt-Cassegrain",
        ])
        self.type_combo.setCurrentText(default_type)
        grid.addWidget(self.type_combo, row, 1)

        grid.addWidget(QLabel("Aperture (mm):"), row, 2)
        self.aperture_spin = QDoubleSpinBox()
        self.aperture_spin.setRange(50.0, 500.0)
        self.aperture_spin.setSingleStep(10.0)
        self.aperture_spin.setValue(200.0)
        grid.addWidget(self.aperture_spin, row, 3)
        row += 1

        # Row 1: primary/objective + sec mag
        self.primary_label = QLabel("Primary:")
        grid.addWidget(self.primary_label, row, 0)
        self.primary_combo = QComboBox()
        self.primary_combo.addItems(["Parabolic", "Spherical"])
        grid.addWidget(self.primary_combo, row, 1)

        self.objective_label = QLabel("Objective:")
        grid.addWidget(self.objective_label, row, 0)
        self.objective_combo = QComboBox()
        self.objective_combo.addItems([
            "Singlet", "Achromat", "APO Doublet",
            "APO Triplet (air-spaced)",
        ])
        grid.addWidget(self.objective_combo, row, 1)
        self.objective_label.hide()
        self.objective_combo.hide()

        self.sec_mag_label = QLabel("Sec. Mag:")
        self.sec_mag_label.setToolTip("System focal length = primary FL × this value")
        grid.addWidget(self.sec_mag_label, row, 2)
        self.sec_mag_spin = QDoubleSpinBox()
        self.sec_mag_spin.setRange(1.5, 6.0)
        self.sec_mag_spin.setSingleStep(0.5)
        self.sec_mag_spin.setValue(3.0)
        self.sec_mag_spin.setToolTip("System focal length = primary FL × this value")
        grid.addWidget(self.sec_mag_spin, row, 3)
        self.sec_mag_label.hide()
        self.sec_mag_spin.hide()
        row += 1

        # Row 2: f-ratio + focal length on same row
        grid.addWidget(QLabel("f/:"), row, 0)
        self.fratio_spin = QDoubleSpinBox()
        self.fratio_spin.setRange(3.0, 15.0)
        self.fratio_spin.setSingleStep(0.1)
        self.fratio_spin.setValue(default_fratio)
        grid.addWidget(self.fratio_spin, row, 1)

        grid.addWidget(QLabel("FL:"), row, 2)
        self.focal_length_spin = QDoubleSpinBox()
        self.focal_length_spin.setRange(150.0, 7500.0)
        self.focal_length_spin.setSingleStep(10.0)
        self.focal_length_spin.setDecimals(1)
        initial_fl = self.aperture_spin.value() * self.fratio_spin.value()
        self.focal_length_spin.setValue(initial_fl)
        grid.addWidget(self.focal_length_spin, row, 3)
        row += 1

        # Row 3: lock checkboxes + effective f/ratio
        self.lock_fratio_check = QCheckBox("Lock f/")
        self.lock_fratio_check.setToolTip("Lock f-ratio when changing aperture")
        self.lock_fratio_check.setChecked(True)
        grid.addWidget(self.lock_fratio_check, row, 0, 1, 2)

        self.lock_focal_length_check = QCheckBox("Lock FL")
        self.lock_focal_length_check.setToolTip("Lock focal length when changing aperture")
        grid.addWidget(self.lock_focal_length_check, row, 2)

        self.effective_fratio_label = QLabel("Eff. f/ratio: --")
        self.effective_fratio_label.setStyleSheet("font-style: italic; color: #666; font-size: 9pt;")
        grid.addWidget(self.effective_fratio_label, row, 3)
        row += 1

        # Row 4: obstruction
        from PyQt6.QtWidgets import QHBoxLayout
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
        grid.addLayout(obstruction_enable_layout, row, 0, 1, 2)

        self.obstruction_ratio_label = QLabel()  # Hidden in grid mode
        self.obstruction_ratio_label.hide()

        self.obstruction_spin = QDoubleSpinBox()
        self.obstruction_spin.setRange(0.0, 0.5)
        self.obstruction_spin.setSingleStep(0.01)
        self.obstruction_spin.setValue(DEFAULT_OBSTRUCTION.get(default_type, 0.20))
        self.obstruction_spin.setDecimals(2)
        self.obstruction_spin.setToolTip(
            "Secondary diameter / Primary diameter (0.2 = 20% obstruction)"
        )
        grid.addWidget(self.obstruction_spin, row, 2, 1, 2)
        row += 1

        # Row 5: spider vanes + vane width
        self.spider_vanes_label = QLabel("Spider Vanes:")
        grid.addWidget(self.spider_vanes_label, row, 0)
        self.spider_vanes_spin = QDoubleSpinBox()
        self.spider_vanes_spin.setRange(0, 6)
        self.spider_vanes_spin.setDecimals(0)
        self.spider_vanes_spin.setValue(0)
        grid.addWidget(self.spider_vanes_spin, row, 1)

        self.vane_width_label = QLabel("Vane Width (mm):")
        grid.addWidget(self.vane_width_label, row, 2)
        self.vane_width_spin = QDoubleSpinBox()
        self.vane_width_spin.setRange(0.5, 5.0)
        self.vane_width_spin.setSingleStep(0.5)
        self.vane_width_spin.setValue(2.0)
        grid.addWidget(self.vane_width_spin, row, 3)
        row += 1

        # Row 6: meniscus (Maksutov only)
        self.meniscus_label = QLabel("Meniscus (mm):")
        self.meniscus_label.setToolTip("Meniscus corrector thickness. Default = aperture/10.")
        grid.addWidget(self.meniscus_label, row, 2)
        self.meniscus_spin = QDoubleSpinBox()
        self.meniscus_spin.setRange(5.0, 50.0)
        self.meniscus_spin.setSingleStep(1.0)
        self.meniscus_spin.setValue(self.aperture_spin.value() / 10.0)
        self.meniscus_spin.setToolTip("Meniscus corrector thickness. Default = aperture/10.")
        grid.addWidget(self.meniscus_spin, row, 3)
        self.meniscus_label.hide()
        self.meniscus_spin.hide()

        group.setLayout(grid)
        outer.addWidget(group)

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self):
        self.type_combo.currentTextChanged.connect(self._on_telescope_type_changed)
        self.aperture_spin.valueChanged.connect(self._on_aperture_changed)
        self.fratio_spin.valueChanged.connect(self._on_fratio_changed)
        self.focal_length_spin.valueChanged.connect(self._on_focal_length_changed)
        self.lock_fratio_check.toggled.connect(self._on_lock_fratio_toggled)
        self.lock_focal_length_check.toggled.connect(self._on_lock_focal_length_toggled)

    # ------------------------------------------------------------------
    # Visibility
    # ------------------------------------------------------------------

    def update_controls_visibility(self):
        """Show/hide controls based on the current telescope type."""
        telescope_type = self.type_combo.currentText()
        is_refractor = telescope_type == "Refractor"
        is_newtonian = telescope_type == "Newtonian"
        is_cassegrain_variant = telescope_type in (
            "Cassegrain", "Maksutov-Cassegrain", "Schmidt-Cassegrain",
        )
        is_mak = telescope_type == "Maksutov-Cassegrain"

        # Primary type — Newtonian only
        self.primary_label.setVisible(is_newtonian)
        self.primary_combo.setVisible(is_newtonian)

        # Objective type — Refractor only
        self.objective_label.setVisible(is_refractor)
        self.objective_combo.setVisible(is_refractor)

        # Obstruction — reflectors only (non-refractor)
        self.obstruction_label.setVisible(not is_refractor)
        self.enable_obstruction_check.setVisible(not is_refractor)
        self.obstruction_ratio_label.setVisible(not is_refractor)
        self.obstruction_spin.setVisible(not is_refractor)

        # Spider vanes — reflectors only
        self.spider_vanes_label.setVisible(not is_refractor)
        self.spider_vanes_spin.setVisible(not is_refractor)
        self.vane_width_label.setVisible(not is_refractor)
        self.vane_width_spin.setVisible(not is_refractor)

        # Secondary magnification — Cassegrain variants only
        self.sec_mag_label.setVisible(is_cassegrain_variant)
        self.sec_mag_spin.setVisible(is_cassegrain_variant)

        # Meniscus — Maksutov only
        self.meniscus_label.setVisible(is_mak)
        self.meniscus_spin.setVisible(is_mak)

    # ------------------------------------------------------------------
    # Focal-length / f-ratio synchronization
    # ------------------------------------------------------------------

    def _on_telescope_type_changed(self, telescope_type):
        self.update_controls_visibility()
        # Set default obstruction ratio
        default_obs = DEFAULT_OBSTRUCTION.get(telescope_type)
        if default_obs is not None:
            self.obstruction_spin.setValue(default_obs)
        self.config_changed.emit()

    def _on_lock_fratio_toggled(self, checked):
        if checked:
            self.lock_focal_length_check.setChecked(False)

    def _on_lock_focal_length_toggled(self, checked):
        if checked:
            self.lock_fratio_check.setChecked(False)

    def _on_aperture_changed(self, aperture):
        if self._guard:
            return
        self._guard = True

        if self.lock_fratio_check.isChecked() or not self.lock_focal_length_check.isChecked():
            fratio = self.fratio_spin.value()
            self.focal_length_spin.blockSignals(True)
            self.focal_length_spin.setValue(aperture * fratio)
            self.focal_length_spin.blockSignals(False)
        else:
            focal_length = self.focal_length_spin.value()
            new_fratio = focal_length / aperture if aperture > 0 else 5.0
            self.fratio_spin.blockSignals(True)
            self.fratio_spin.setValue(new_fratio)
            self.fratio_spin.blockSignals(False)

        # Update meniscus default
        if self.meniscus_spin.isVisible():
            self.meniscus_spin.setValue(aperture / 10.0)

        self._guard = False
        self.config_changed.emit()

    def _on_fratio_changed(self, fratio):
        if self._guard:
            return
        self._guard = True
        aperture = self.aperture_spin.value()
        self.focal_length_spin.blockSignals(True)
        self.focal_length_spin.setValue(aperture * fratio)
        self.focal_length_spin.blockSignals(False)
        self._guard = False
        self.config_changed.emit()

    def _on_focal_length_changed(self, focal_length):
        if self._guard:
            return
        self._guard = True
        aperture = self.aperture_spin.value()
        new_fratio = focal_length / aperture if aperture > 0 else 5.0
        self.fratio_spin.blockSignals(True)
        self.fratio_spin.setValue(new_fratio)
        self.fratio_spin.blockSignals(False)
        self._guard = False
        self.config_changed.emit()

    # ------------------------------------------------------------------
    # Effective f/ratio display helper
    # ------------------------------------------------------------------

    def update_effective_fratio(self, telescope):
        """Update the effective f/ratio label after building a telescope."""
        actual_fratio = telescope.focal_ratio
        user_fratio = self.fratio_spin.value()

        if abs(actual_fratio - user_fratio) > 0.1:
            self.effective_fratio_label.setText(
                f"\u26a0 Effective f/ratio: f/{actual_fratio:.1f} "
                f"(telescope uses {actual_fratio:.1f}, not input {user_fratio:.1f})"
            )
            self.effective_fratio_label.setStyleSheet(
                "font-style: italic; color: #cc6600; font-weight: bold;"
            )
        else:
            self.effective_fratio_label.setText(f"\u2713 Effective f/ratio: f/{actual_fratio:.1f}")
            self.effective_fratio_label.setStyleSheet("font-style: italic; color: #666;")

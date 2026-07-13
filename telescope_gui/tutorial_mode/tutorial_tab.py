"""Main Tutorial & Testing tab widget.

Assembles the scenario sidebar, before/after canvases, description panel,
theory readout, tweakable controls, effect toggles, and terminal panel
into a single QWidget registered as a GUI mode.
"""

from __future__ import annotations

import traceback
from dataclasses import replace

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QGroupBox, QSizePolicy, QDoubleSpinBox,
    QSpinBox, QComboBox, QFrame, QCheckBox, QSlider,
)
from PyQt6.QtCore import Qt

from telescope_gui.tutorial_mode.scenario_registry import (
    ScenarioDefinition, TelescopeConfig, SourceConfig,
    SCENARIOS, get_scenario_by_id, get_first_implemented,
)
from telescope_gui.tutorial_mode.scenario_runner import (
    run_scenario_side, compute_theory_for_scenario,
    apply_theory_overlay, build_terminal_command,
    _telescope_kwargs, build_source,
)
from telescope_gui.tutorial_mode.widgets.scenario_sidebar import ScenarioSidebar
from telescope_gui.tutorial_mode.widgets.before_after_panel import BeforeAfterPanel
from telescope_gui.tutorial_mode.widgets.theory_readout import TheoryReadoutPanel
from telescope_gui.tutorial_mode.widgets.terminal_panel import TerminalPanel
from telescope_gui.tutorial_mode.widgets.effect_toggles import EffectTogglesPanel
from telescope_gui.tutorial_mode.widgets.source_code_panel import SourceCodePanel

# Source-level imports for the source code viewer
from telescope_sim.plotting.ray_trace_plot import (
    plot_psf_2d, plot_psf_profile, plot_source_image,
    _render_source_through_telescope, _compute_psf_at_field_angle,
    plot_coma_field_analysis, plot_polychromatic_ray_trace,
)
from telescope_sim.physics.fft_psf import compute_fft_psf
from telescope_sim.physics.diffraction import compute_psf
from telescope_sim.physics.aberrations import compute_coma_spot, coma_free_field


class TutorialTab(QWidget):
    """Tutorial & Testing mode: guided optical physics scenarios.

    Layout:
        [Scenario Sidebar (240px)] | [Main Content Area]
                                     - Description + learn more
                                     - Before/After canvases
                                     - Theory readout bar
                                     - Tweakable controls + Update/Reset
                                     - Effect toggles (Act 3 only)
                                     - Terminal panel
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_scenario: ScenarioDefinition | None = None
        self._current_after_config: TelescopeConfig | None = None
        self._current_seeing: float | None = None
        self._tweak_widgets: dict[str, QWidget] = {}
        # Independent before-side widgets (only populated when scenario sets
        # tweakable_params_before); empty otherwise.
        self._tweak_widgets_before: dict[str, QWidget] = {}
        # Per-axis (xlim, ylim) captured from the before-side figure
        self._before_axis_limits: list[tuple] | None = None
        self._psf_view_combo: QComboBox | None = None
        # log/linear PSF scale toggle (for scenarios that render a PSF)
        self._psf_scale_combo: QComboBox | None = None
        # Overlay-visibility toggle (e.g. spider vanes, theory rings)
        self._show_overlay_check: QCheckBox | None = None
        # Focus-wavelength toggle (for chromatic-aberration scenarios)
        self._focus_wavelength_combo: QComboBox | None = None
        # Display-stretch toggle (linear / log) for source-image scenarios
        self._display_stretch_combo: QComboBox | None = None
        # Exposure-level slider (log-scaled) for source-image scenarios.
        # Default per-scenario via ScenarioDefinition.default_exposure.
        self._exposure_slider: QSlider | None = None
        self._exposure_value_label: QLabel | None = None
        # Filter combo (ND / colour). Only shown when the scenario
        # opts in via show_filter_combo (e.g. Act 3 filter scenarios).
        self._filter_combo: QComboBox | None = None
        # Exit-pupil combo (Phase 1.4). Shown for extended-source image
        # scenarios; drives the Eye-view surface-brightness model
        # (∝ (exit_pupil / 7 mm)², capped at naked-eye). Irrelevant in
        # Detector view (where exposure drives brightness instead).
        self._exit_pupil_combo: QComboBox | None = None
        # Focal-zoom combo (Phase B4). Shown for the chromatic scenario;
        # switches the after-side focal-plane radial-profile x-axis between
        # a wide view (singlet halo off-panel) and a close view (resolves
        # achromat/APO differences).
        self._focal_zoom_combo: QComboBox | None = None
        # Eye-blur checkbox (R3.12). For fixed Eye-vs-Detector scenarios: when
        # checked, the Eye pane uses log_integrated (1″ eye-resolution blur)
        # instead of plain log.
        self._eye_blur_check: QCheckBox | None = None
        # Shared-normalisation reference peak (Phase 1.5): the before-side
        # (unobstructed) FFT raw peak, captured during _render_before and
        # applied as the after-side peak_reference so the central-
        # obstruction Strehl drop is visible. None = independent peaks.
        self._shared_psf_peak: float | None = None
        # Live ephemeris checkbox. When checked, the after-side source
        # is reconstructed with use_realtime=True so its angular size
        # (and Saturn ring tilt) come from skyfield/DE421 at the time
        # the user opened the scenario. Only shown on scenarios with
        # supports_realtime=True.
        self._realtime_check: QCheckBox | None = None
        self._build_ui()
        # Load the first implemented scenario automatically
        first = get_first_implemented()
        if first:
            self._load_scenario(first)
            self.sidebar.set_active(first.id)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Left sidebar
        self.sidebar = ScenarioSidebar()
        self.sidebar.scenario_selected.connect(self._on_scenario_selected)
        root.addWidget(self.sidebar)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #ccc;")
        root.addWidget(sep)

        # Main content area (scrollable)
        self.main_scroll = QScrollArea()
        self.main_scroll.setWidgetResizable(True)
        self.main_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(12, 8, 12, 8)
        self.main_layout.setSpacing(8)

        # Description area
        self.title_label = QLabel("Select a scenario from the sidebar")
        self.title_label.setStyleSheet(
            "font-size: 14pt; font-weight: bold; color: #2a2a2a;")
        self.main_layout.addWidget(self.title_label)

        self.description_label = QLabel("")
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("font-size: 10pt; color: #444; padding: 2px 0;")
        self.main_layout.addWidget(self.description_label)

        self.learn_more_label = QLabel("")
        self.learn_more_label.setStyleSheet(
            "font-size: 9pt; color: #2255cc; font-style: italic;")
        self.main_layout.addWidget(self.learn_more_label)

        # Before / After canvases
        self.before_after = BeforeAfterPanel()
        self.before_after.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_layout.addWidget(self.before_after, stretch=3)

        # Theory readout
        self.theory_readout = TheoryReadoutPanel()
        self.main_layout.addWidget(self.theory_readout)

        # Tweakable controls area. The controls live in a single horizontal
        # row; scenarios with many controls (planets: 6 tweakables + toggles +
        # view/exposure/exit-pupil/realtime) made that row ~1400px wide, which
        # forced the whole page wider than the viewport → horizontal page
        # scroll AND stretched the Expanding before/after canvases to that
        # width (planets rendered oversized, needing scroll to see the disk).
        # Wrapping the controls in their own horizontal scroll strip decouples
        # the control-row width from the page width: the row scrolls inside a
        # fixed-height strip, the page stays at the viewport width, and the
        # canvases keep a sane size.
        self.controls_group = QGroupBox("Adjust parameters")
        self.controls_group.setStyleSheet("font-weight: bold; font-size: 9pt;")
        self.controls_layout = QHBoxLayout(self.controls_group)
        self.controls_layout.setContentsMargins(8, 4, 8, 4)
        self.controls_layout.setSpacing(12)
        self.controls_scroll = QScrollArea()
        self.controls_scroll.setWidgetResizable(True)
        self.controls_scroll.setWidget(self.controls_group)
        self.controls_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.controls_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.controls_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Keep the strip from claiming the controls' full min width for the
        # page, and hold it to roughly one control-row tall.
        self.controls_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.controls_scroll.setMinimumWidth(200)
        self.controls_scroll.setMaximumHeight(120)
        self.main_layout.addWidget(self.controls_scroll)

        # Controls auto-update on edit; only a Reset is exposed.
        btn_row = QHBoxLayout()
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setStyleSheet(
            "padding: 4px 12px; color: #555; border: 1px solid #aaa; border-radius: 4px;")
        self.reset_btn.clicked.connect(self._on_reset_clicked)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 8pt;")

        self.lock_axes_check = QCheckBox("Lock axes")
        self.lock_axes_check.setChecked(True)
        self.lock_axes_check.setStyleSheet("font-size: 8pt; color: #555;")
        self.lock_axes_check.setToolTip(
            "Keep the after-side axes fixed to the before-side range,\n"
            "so size changes are visually apparent.")
        self.lock_axes_check.stateChanged.connect(self._on_update_clicked)

        btn_row.addWidget(self.reset_btn)
        btn_row.addWidget(self.lock_axes_check)
        btn_row.addWidget(self.status_label)
        btn_row.addStretch()
        self.main_layout.addLayout(btn_row)

        # Effect toggles (Act 3)
        self.effect_toggles = EffectTogglesPanel()
        self.effect_toggles.toggled.connect(self._on_update_clicked)
        self.main_layout.addWidget(self.effect_toggles)

        # Terminal panel
        self.terminal_panel = TerminalPanel()
        self.main_layout.addWidget(self.terminal_panel)

        # Source code viewer
        self.source_panel = SourceCodePanel()
        self.main_layout.addWidget(self.source_panel)

        self.main_layout.addStretch()
        self.main_scroll.setWidget(self.main_widget)
        root.addWidget(self.main_scroll, stretch=1)

    # ------------------------------------------------------------------
    # Scenario loading
    # ------------------------------------------------------------------

    def _on_scenario_selected(self, scenario_id: str):
        scenario = get_scenario_by_id(scenario_id)
        if scenario:
            self._load_scenario(scenario)

    def _load_scenario(self, scenario: ScenarioDefinition):
        self._current_scenario = scenario
        self._current_after_config = scenario.after_telescope
        self._current_seeing = scenario.after_seeing_arcsec

        # Update description area
        self.title_label.setText(scenario.title)
        applies_label = {
            "refractor": "Applies to: Refractors only",
            "reflector": "Applies to: Reflectors / catadioptric only",
            "both": "Applies to: Refractors and Reflectors",
        }.get(scenario.applies_to, "Applies to: Both")
        self.description_label.setText(
            f"{applies_label}\n\n{scenario.description}"
        )
        self.learn_more_label.setText(
            f"Learn more → Parameters & Physics: {scenario.learn_more_section}"
        )

        # Rebuild tweakable controls for this scenario
        self._rebuild_controls(scenario)

        # Update source code viewer
        self.source_panel.set_functions(
            self._get_source_functions(scenario.plot_function))

        # Show/hide effect toggles (Act 3 only)
        self.effect_toggles.set_visible_toggles(scenario.effect_toggles)

        # Clear old after canvas and reset axis limits for new scenario
        self._before_axis_limits = None
        # Reset the shared-normalisation reference; _render_before re-captures
        # it for scenarios that opt in (shared_psf_normalization).
        self._shared_psf_peak = None
        self.before_after.clear_after()
        self.theory_readout.clear()
        self.terminal_panel.clear()

        # Enable/disable the lock-axes checkbox based on scenario compatibility
        lock_safe = self._axis_lock_is_safe(scenario)
        self.lock_axes_check.setEnabled(lock_safe)
        if lock_safe:
            self.lock_axes_check.setToolTip(
                "Keep the after-side axes fixed to the before-side range,\n"
                "so size changes are visually apparent.")
        else:
            self.lock_axes_check.setToolTip(
                "Axis lock disabled — before/after panels use different plot\n"
                "types or sources with different fields of view, so the\n"
                "before-side range isn't physically comparable to the after-side.")

        # Render the static "before" side
        self._render_before(scenario)

        # Render the initial "after" side
        self._render_after()

    def _clear_layout(self, layout):
        """Recursively remove all widgets and sub-layouts from a layout."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            elif item.layout() is not None:
                self._clear_layout(item.layout())

    def _rebuild_controls(self, scenario: ScenarioDefinition):
        """Clear and rebuild the tweakable controls for the scenario."""
        self._clear_layout(self.controls_layout)
        self._tweak_widgets.clear()
        self._tweak_widgets_before.clear()
        self._psf_view_combo = None
        self._psf_scale_combo = None
        self._show_overlay_check = None
        self._focus_wavelength_combo = None
        self._display_stretch_combo = None
        self._exposure_slider = None
        self._exposure_value_label = None
        self._filter_combo = None
        self._exit_pupil_combo = None
        self._focal_zoom_combo = None
        self._eye_blur_check = None
        self._realtime_check = None

        params = scenario.tweakable_params
        params_before = scenario.tweakable_params_before
        # PSF scenarios always get the 1D/2D toggle even if no other tweakable params
        is_psf_scenario = scenario.plot_function == "plot_psf_2d"
        # Scenarios that benefit from a log/linear toggle (PSF maps and
        # 1D radial profiles).
        is_psf_profile_scenario = scenario.plot_function == "plot_psf_profile"
        wants_scale_toggle = is_psf_scenario or is_psf_profile_scenario
        # Source-image scenarios always need the controls panel for the
        # View / Exposure / Filter / Exit-pupil combos, even when they
        # expose no tweakable telescope params (e.g. a pure filter lesson).
        wants_display_combo = (
            scenario.plot_function == "plot_source_image"
            or scenario.secondary_plot_function == "plot_source_image"
        )
        if (not params and not is_psf_scenario and not params_before
                and not wants_display_combo):
            self.controls_scroll.setVisible(False)
            return

        self.controls_scroll.setVisible(True)

        # When tweakable_params_before is set, render TWO labelled groups
        if params_before is not None:
            before_box = self._build_group_box("Before:", "#888")
            self._populate_group(before_box, params_before,
                                  scenario.before_telescope,
                                  scenario.before_source,
                                  scenario.before_seeing_arcsec,
                                  self._tweak_widgets_before)
            self.controls_layout.addWidget(before_box)

            after_box = self._build_group_box("After:", "#2a6496")
            self._populate_group(after_box, params,
                                  scenario.after_telescope,
                                  scenario.after_source,
                                  scenario.after_seeing_arcsec,
                                  self._tweak_widgets)
            self.controls_layout.addWidget(after_box)
        else:
            # Single shared panel (existing behaviour)
            for param in params:
                self._add_param_widget(param, scenario.after_telescope,
                                        scenario.after_source,
                                        scenario.after_seeing_arcsec,
                                        self._tweak_widgets,
                                        target_layout=self.controls_layout)

        # PSF view toggle for scenarios that render a 2D PSF
        # (disabled for spider/obstruction scenarios where azimuthal pattern matters)
        if is_psf_scenario and scenario.show_psf_toggle:
            self._add_psf_view_combo()

        # Log/linear toggle for any PSF-rendering scenario
        if wants_scale_toggle:
            self._add_psf_scale_combo()

        # Overlay-visibility toggle for scenarios with informative overlays
        # (spider-vane lines, etc.)
        from telescope_gui.tutorial_mode.theory_computations import OVERLAY_FUNCTIONS
        if scenario.id in OVERLAY_FUNCTIONS:
            self._add_show_overlay_check()

        # Focus-wavelength toggle (for chromatic scenarios — both the
        # 1D radial-profile comparison and the polychromatic star-field
        # rendering use the same focus-wavelength concept).
        wants_focus_combo = (
            scenario.secondary_plot_function == "plot_chromatic_focal_planes"
            or (scenario.after_polychromatic
                and scenario.plot_function == "plot_source_image")
        )
        if wants_focus_combo:
            self._add_focus_wavelength_combo()
            self._sync_focus_combo_for_objective()

        # Focal-zoom toggle (B4) for the chromatic focal-plane image.
        if scenario.show_focal_zoom_combo:
            self._add_focal_zoom_combo()

        # Display-stretch toggle (linear / log) for any scenario whose
        # after-side renders a source image (so the toggle is available
        # for fratio_coma and spherical_aberration which use a different
        # plot_function but call plot_source_image via
        # secondary_plot_function). `wants_display_combo` computed above.
        if wants_display_combo:
            # When the After view is PINNED (fixed Eye-vs-Detector comparison),
            # hide the free View combo and instead offer an Eye-blur toggle.
            if scenario.after_display_stretch is None:
                self._add_display_stretch_combo(scenario.default_display_stretch)
            elif scenario.show_eye_blur_toggle:
                self._add_eye_blur_check()
            self._add_exposure_slider(scenario.default_exposure)
        if wants_display_combo and scenario.show_filter_combo:
            self._add_filter_combo(scenario.default_filter)
        # Exit-pupil control (Phase 1.4) — only for extended-source image
        # scenarios, where the Eye-view surface brightness is exit-pupil
        # driven. Stars are aperture-driven, so the control is meaningless
        # for point/double/field sources.
        if wants_display_combo and self._scenario_has_extended_source(scenario):
            self._add_exit_pupil_combo(scenario.default_exit_pupil_mm)
        if scenario.supports_realtime:
            self._add_realtime_check()

        # Initial exposure-slider enabled state (greyed in Eye view).
        self._sync_exposure_enabled()

        self.controls_layout.addStretch()

    def _build_group_box(self, title: str, accent: str) -> QGroupBox:
        """Inner group box used when independent before/after controls are shown."""
        box = QGroupBox(title)
        box.setStyleSheet(
            f"QGroupBox {{ font-weight: bold; font-size: 9pt; "
            f"color: {accent}; border: 1px solid #ccc; "
            f"border-radius: 3px; margin-top: 6px; padding: 8px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; "
            f"left: 6px; padding: 0 4px; }}"
        )
        h = QHBoxLayout(box)
        h.setContentsMargins(6, 4, 6, 4)
        h.setSpacing(10)
        return box

    def _populate_group(self, box: QGroupBox, params: tuple,
                         telescope_cfg: TelescopeConfig,
                         source_cfg: SourceConfig,
                         seeing: float | None,
                         widget_map: dict):
        """Populate a group box with widgets for the given params."""
        layout = box.layout()
        for param in params:
            self._add_param_widget(param, telescope_cfg, source_cfg, seeing,
                                    widget_map, target_layout=layout)
        layout.addStretch()

    def _add_param_widget(self, param: str,
                           telescope_cfg: TelescopeConfig,
                           source_cfg: SourceConfig,
                           seeing: float | None,
                           widget_map: dict,
                           target_layout):
        """Dispatch a single param to the right widget builder."""
        if param == "diameter":
            self._add_spin(param, "Aperture (mm)", telescope_cfg.diameter,
                           50.0, 1000.0, 10.0,
                           widget_map=widget_map, target_layout=target_layout)
        elif param == "focal_length":
            self._add_spin(param, "Focal length (mm)", telescope_cfg.focal_length,
                           200.0, 10000.0, 50.0,
                           widget_map=widget_map, target_layout=target_layout)
        elif param == "obstruction_ratio":
            self._add_spin(param, "Obstruction", telescope_cfg.obstruction_ratio,
                           0.0, 0.55, 0.01, decimals=2,
                           widget_map=widget_map, target_layout=target_layout)
        elif param == "spider_vanes":
            self._add_int_spin(param, "Spider vanes", telescope_cfg.spider_vanes,
                               0, 6,
                               widget_map=widget_map, target_layout=target_layout)
        elif param == "spider_vane_width":
            self._add_spin(param, "Vane width (mm)", telescope_cfg.spider_vane_width,
                           0.5, 10.0, 0.5,
                           widget_map=widget_map, target_layout=target_layout)
        elif param == "seeing":
            self._add_seeing_combo(seeing,
                                    widget_map=widget_map, target_layout=target_layout)
        elif param == "separation_arcsec":
            sep = source_cfg.kwargs.get("separation_arcsec", 1.0)
            self._add_spin(param, "Separation (\")", sep, 0.1, 10.0, 0.1,
                           widget_map=widget_map, target_layout=target_layout)
        elif param == "objective_type":
            self._add_objective_combo(telescope_cfg.objective_type,
                                       widget_map=widget_map, target_layout=target_layout)
        elif param == "primary_type":
            self._add_primary_type_combo(telescope_cfg.primary_type,
                                          widget_map=widget_map, target_layout=target_layout)

    def _add_spin(self, key: str, label: str, value: float,
                  minimum: float, maximum: float, step: float, decimals: int = 1,
                  widget_map: dict | None = None, target_layout=None):
        if widget_map is None:
            widget_map = self._tweak_widgets
        if target_layout is None:
            target_layout = self.controls_layout
        col = QVBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 8pt; font-weight: normal; color: #555;")
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setDecimals(decimals)
        spin.setValue(value)
        spin.setFixedWidth(90)
        # Auto-update on Enter / focus-out so changes propagate without
        # the user needing to press an Update button (which we removed).
        spin.editingFinished.connect(self._on_update_clicked)
        col.addWidget(lbl)
        col.addWidget(spin)
        target_layout.addLayout(col)
        widget_map[key] = spin

    def _add_int_spin(self, key: str, label: str, value: int,
                       minimum: int, maximum: int,
                       widget_map: dict | None = None, target_layout=None):
        if widget_map is None:
            widget_map = self._tweak_widgets
        if target_layout is None:
            target_layout = self.controls_layout
        col = QVBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 8pt; font-weight: normal; color: #555;")
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setFixedWidth(70)
        spin.editingFinished.connect(self._on_update_clicked)
        col.addWidget(lbl)
        col.addWidget(spin)
        target_layout.addLayout(col)
        widget_map[key] = spin

    def _add_seeing_combo(self, current_seeing: float | None,
                           widget_map: dict | None = None, target_layout=None):
        if widget_map is None:
            widget_map = self._tweak_widgets
        if target_layout is None:
            target_layout = self.controls_layout
        col = QVBoxLayout()
        lbl = QLabel("Seeing")
        lbl.setStyleSheet("font-size: 8pt; font-weight: normal; color: #555;")
        combo = QComboBox()
        options = [
            ("None (space)", None),
            ("Excellent (0.8\")", 0.8),
            ("Good (1.5\")", 1.5),
            ("Average (2.5\")", 2.5),
            ("Poor (4.0\")", 4.0),
        ]
        for text, val in options:
            combo.addItem(text, val)
        for i, (_, val) in enumerate(options):
            if val == current_seeing:
                combo.setCurrentIndex(i)
                break
        combo.currentIndexChanged.connect(self._on_update_clicked)
        col.addWidget(lbl)
        col.addWidget(combo)
        target_layout.addLayout(col)
        widget_map["seeing"] = combo

    def _add_objective_combo(self, current: str,
                              widget_map: dict | None = None, target_layout=None):
        if widget_map is None:
            widget_map = self._tweak_widgets
        if target_layout is None:
            target_layout = self.controls_layout
        col = QVBoxLayout()
        lbl = QLabel("Objective type")
        lbl.setStyleSheet("font-size: 8pt; font-weight: normal; color: #555;")
        combo = QComboBox()
        options = ["singlet", "achromat", "apo-doublet", "apo-triplet"]
        for opt in options:
            combo.addItem(opt)
        idx = options.index(current) if current in options else 0
        combo.setCurrentIndex(idx)
        # Keep the F=C focus option enabled/disabled in sync as the
        # user toggles objective (F=C only meaningful for achromat/apo).
        combo.currentIndexChanged.connect(self._sync_focus_combo_for_objective)
        combo.currentIndexChanged.connect(self._on_update_clicked)
        col.addWidget(lbl)
        col.addWidget(combo)
        target_layout.addLayout(col)
        widget_map["objective_type"] = combo

    def _add_primary_type_combo(self, current: str,
                                 widget_map: dict | None = None, target_layout=None):
        if widget_map is None:
            widget_map = self._tweak_widgets
        if target_layout is None:
            target_layout = self.controls_layout
        col = QVBoxLayout()
        lbl = QLabel("Primary type")
        lbl.setStyleSheet("font-size: 8pt; font-weight: normal; color: #555;")
        combo = QComboBox()
        options = ["spherical", "parabolic"]
        for opt in options:
            combo.addItem(opt)
        idx = options.index(current) if current in options else 0
        combo.setCurrentIndex(idx)
        combo.currentIndexChanged.connect(self._on_update_clicked)
        col.addWidget(lbl)
        col.addWidget(combo)
        target_layout.addLayout(col)
        widget_map["primary_type"] = combo

    def _add_psf_view_combo(self):
        col = QVBoxLayout()
        lbl = QLabel("PSF view")
        lbl.setStyleSheet("font-size: 8pt; font-weight: normal; color: #555;")
        combo = QComboBox()
        combo.addItem("2D PSF")
        combo.addItem("1D Profile")
        combo.setCurrentIndex(0)
        combo.currentIndexChanged.connect(self._on_psf_view_changed)
        col.addWidget(lbl)
        col.addWidget(combo)
        self.controls_layout.addLayout(col)
        self._psf_view_combo = combo

    def _add_psf_scale_combo(self):
        """Linear/log toggle for PSF plots (2D or 1D radial profile)."""
        col = QVBoxLayout()
        lbl = QLabel("Scale")
        lbl.setStyleSheet("font-size: 8pt; font-weight: normal; color: #555;")
        combo = QComboBox()
        combo.addItem("Log")
        combo.addItem("Linear")
        combo.setCurrentIndex(0)
        combo.currentIndexChanged.connect(self._on_psf_view_changed)
        col.addWidget(lbl)
        col.addWidget(combo)
        self.controls_layout.addLayout(col)
        self._psf_scale_combo = combo

    def _add_display_stretch_combo(self, default_stretch: str = "log"):
        """View toggle: Detector / Eye / Eye + integration.

        Three display mappings of the same underlying simulation:
        - Detector: linear per-pixel intensity (what a CCD records).
        - Eye: asinh intensity response (eye's log magnitude response).
        - Eye + integration: asinh + ~1″ spatial blur (eye's spatial
          resolution at moderate eyepiece magnification).

        The simulated data is identical in all three; only the screen
        mapping changes.
        """
        col = QVBoxLayout()
        lbl = QLabel("View")
        lbl.setStyleSheet("font-size: 8pt; font-weight: normal; color: #555;")
        combo = QComboBox()
        combo.addItem("Detector (linear)", "linear")
        combo.addItem("Eye (logarithmic)", "log")
        combo.addItem("Eye + integration (log + spatial)", "log_integrated")
        # Default per-scenario: "log" (Eye) for most; "linear" (Detector)
        # for exposure / saturation lessons where the exposure slider and
        # saturation clipping need to be live. Eye view ignores exposure.
        _default_idx = combo.findData(default_stretch)
        combo.setCurrentIndex(_default_idx if _default_idx >= 0 else 1)
        combo.setToolTip(
            "Detector: linear per-pixel intensity (calibrated CCD pixel\n"
            "  response — bright cores dominate, dim features clipped).\n"
            "Eye: asinh intensity response (eye's logarithmic magnitude\n"
            "  response — dim stars visible alongside bright ones).\n"
            "Eye + integration: Eye plus 1″ spatial integration (eye's\n"
            "  ~1″ resolution at moderate eyepiece magnification —\n"
            "  chromatic-disk light mixes into the perceived core)."
        )
        combo.currentIndexChanged.connect(self._on_update_clicked)
        # Keep the exposure slider's enabled state in sync with the view:
        # exposure is a detector concept, so it's greyed out in Eye view.
        combo.currentIndexChanged.connect(self._sync_exposure_enabled)
        col.addWidget(lbl)
        col.addWidget(combo)
        self.controls_layout.addLayout(col)
        self._display_stretch_combo = combo

    def _sync_exposure_enabled(self):
        """Grey out the exposure slider in Eye view (exposure = detector-only).

        Exposure is integration time — a detector concept. In the Eye views
        (log / log_integrated) brightness is optics-driven (aperture² for
        stars, exit-pupil for extended objects), so the slider has no effect.
        Disabling it makes that explicit rather than leaving an inert-looking
        live control (per the user's feedback)."""
        if self._exposure_slider is None:
            return
        scn = self._current_scenario
        if (scn is not None and self._display_stretch_combo is None
                and scn.after_display_stretch is not None):
            # Fixed Eye-vs-Detector layout: exposure acts on the Detector pane,
            # which is present as long as one side is "linear".
            is_eye = "linear" not in (scn.after_display_stretch,
                                      scn.before_display_stretch)
        else:
            stretch = (self._display_stretch_combo.currentData()
                       if self._display_stretch_combo is not None else "linear")
            is_eye = stretch in ("log", "log_integrated")
        self._exposure_slider.setEnabled(not is_eye)
        if self._exposure_value_label is not None:
            if is_eye:
                self._exposure_value_label.setText("N/A (Eye)")
                self._exposure_value_label.setStyleSheet(
                    "font-size: 8pt; font-weight: bold; color: #999;")
            else:
                self._exposure_value_label.setText(
                    f"{self._slider_to_exposure(self._exposure_slider.value()):.2f}×")
                self._exposure_value_label.setStyleSheet(
                    "font-size: 8pt; font-weight: bold; color: #333;")

    # Exposure slider — log-scaled, internal range 0..200 maps to
    # 10^((slider-100)/50) = 0.01× → 1× → 100×. Default position 100
    # is overridden by ScenarioDefinition.default_exposure.
    _EXPOSURE_SLIDER_MIN = 0
    _EXPOSURE_SLIDER_MAX = 200
    _EXPOSURE_SLIDER_CENTER = 100

    @classmethod
    def _slider_to_exposure(cls, pos: int) -> float:
        return 10.0 ** ((pos - cls._EXPOSURE_SLIDER_CENTER) / 50.0)

    @classmethod
    def _exposure_to_slider(cls, exposure: float) -> int:
        import math
        return int(round(cls._EXPOSURE_SLIDER_CENTER
                          + 50.0 * math.log10(max(exposure, 1e-9))))

    def _add_exposure_slider(self, default_exposure: float):
        """Exposure-level slider for source-image scenarios.

        Log-scaled: a one-decade move on the slider corresponds to a
        10× change in collected flux. Default position is read from
        the scenario's `default_exposure` so Acts 1+2 can preset
        whatever exposure makes their lesson read clearly without
        forcing the user to fiddle.
        """
        col = QVBoxLayout()
        header = QHBoxLayout()
        lbl = QLabel("Exposure")
        lbl.setStyleSheet(
            "font-size: 8pt; font-weight: normal; color: #555;")
        value_lbl = QLabel(f"{default_exposure:.2f}×")
        value_lbl.setStyleSheet(
            "font-size: 8pt; font-weight: bold; color: #333;")
        header.addWidget(lbl)
        header.addStretch()
        header.addWidget(value_lbl)
        col.addLayout(header)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(self._EXPOSURE_SLIDER_MIN)
        slider.setMaximum(self._EXPOSURE_SLIDER_MAX)
        slider.setValue(self._exposure_to_slider(default_exposure))
        slider.setToolTip(
            "Collected flux ∝ exposure. Higher = brighter image.\n"
            "1.0× is the photometric anchor (mag-0 star, 100 mm,\n"
            "no seeing → just-below-saturation). Bright sources or\n"
            "large apertures will saturate at lower exposure; faint\n"
            "sources need higher exposure to lift above the noise.\n"
            "Range: 0.01× to 100×, log-scaled."
        )

        def _on_change(v):
            value_lbl.setText(f"{self._slider_to_exposure(v):.2f}×")

        def _on_release():
            self._on_update_clicked()

        slider.valueChanged.connect(_on_change)
        slider.sliderReleased.connect(_on_release)

        col.addWidget(slider)
        self.controls_layout.addLayout(col)
        self._exposure_slider = slider
        self._exposure_value_label = value_lbl

    def _add_realtime_check(self):
        """Checkbox to swap the after-side source for the live ephemeris.

        When checked, the after-side source is reconstructed with
        ``use_realtime=True``. That triggers a skyfield query for the
        current Jupiter/Saturn/Moon geometry (angular size + Saturn
        ring tilt + Moon phase) so the rendered image matches what
        the user would actually see through a telescope *tonight*.
        """
        col = QVBoxLayout()
        lbl = QLabel("Source data")
        lbl.setStyleSheet(
            "font-size: 8pt; font-weight: normal; color: #555;")
        check = QCheckBox("Use live ephemeris")
        check.setToolTip(
            "Default: fixed reference angular size (representative\n"
            "values near opposition). Check this to override with the\n"
            "current Earth–target geometry from skyfield + DE421:\n"
            "  • Jupiter / Saturn / Moon angular diameters\n"
            "  • Saturn ring tilt (relevant near 2025 ring-plane\n"
            "    crossing — rings nearly invisible at low tilt).\n"
            "  • Moon phase / sub-observer longitude.\n"
            "First-time use downloads the JPL DE421 ephemeris\n"
            "(~16 MB) into ~/.skyfield."
        )
        check.stateChanged.connect(self._on_update_clicked)
        col.addWidget(lbl)
        col.addWidget(check)
        self.controls_layout.addLayout(col)
        self._realtime_check = check

    def _add_filter_combo(self, default_filter: str):
        """ND/colour filter dropdown for brightness/saturation scenarios.

        Pulls the library from telescope_sim.physics.filters. Filters
        multiply per-channel flux before saturation clipping — so they
        physically reduce photons and shift colour balance, exactly
        like a real eyepiece filter.
        """
        from telescope_sim.physics.filters import FILTER_LIBRARY
        col = QVBoxLayout()
        lbl = QLabel("Filter")
        lbl.setStyleSheet(
            "font-size: 8pt; font-weight: normal; color: #555;")
        combo = QComboBox()
        for flt in FILTER_LIBRARY:
            combo.addItem(flt.name, flt.name)
            combo.setItemData(combo.count() - 1, flt.description,
                              Qt.ItemDataRole.ToolTipRole)
        idx = combo.findData(default_filter)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.setToolTip(
            "Optical filter applied before the detector. ND = neutral\n"
            "density (uniform dimming). W = Wratten colour filters that\n"
            "shift the RGB balance — useful for revealing low-contrast\n"
            "features on planets (red filter highlights Jupiter's GRS,\n"
            "blue brings out Venus cloud detail, etc.)."
        )
        combo.currentIndexChanged.connect(self._on_update_clicked)
        col.addWidget(lbl)
        col.addWidget(combo)
        self.controls_layout.addLayout(col)
        self._filter_combo = combo

    # Exit-pupil options (mm) for the Eye-view surface-brightness model.
    # Each maps to a representative observing magnification regime. The
    # surface-brightness factor (exit_pupil / 7 mm)² is shown so the user
    # sees how much dimmer-than-naked-eye each choice is.
    _EXIT_PUPIL_OPTIONS = [
        (7.0, "7.0 mm — max (naked-eye SB)"),
        (4.0, "4.0 mm — low power"),
        (2.0, "2.0 mm — planetary"),
        (1.0, "1.0 mm — high power"),
        (0.5, "0.5 mm — very high power"),
    ]

    def _add_exit_pupil_combo(self, default_exit_pupil_mm: float):
        """Exit-pupil dropdown driving the Eye-view extended-source brightness.

        Only shown for extended-source image scenarios (planets / Moon).
        In the Eye view, a telescope cannot raise an extended object's
        surface brightness above the naked-eye level; at higher
        magnification (smaller exit pupil) it falls as (p / 7 mm)². This
        control picks the observing exit pupil. It has NO effect in the
        Detector view (where exposure drives brightness) or on stars
        (point sources are aperture-driven, magnification-independent).
        """
        col = QVBoxLayout()
        lbl = QLabel("Exit pupil")
        lbl.setStyleSheet(
            "font-size: 8pt; font-weight: normal; color: #555;")
        combo = QComboBox()
        for p_mm, text in self._EXIT_PUPIL_OPTIONS:
            combo.addItem(text, p_mm)
        idx = combo.findData(default_exit_pupil_mm)
        combo.setCurrentIndex(idx if idx >= 0 else 2)  # 2.0 mm planetary
        combo.setToolTip(
            "Eye-view surface-brightness model (extended objects):\n"
            "a telescope can't exceed naked-eye surface brightness, and\n"
            "at higher magnification (smaller exit pupil) it falls as\n"
            "(exit pupil / 7 mm)². Exit pupil = aperture / magnification.\n"
            "No effect in Detector view (exposure drives brightness there)\n"
            "or on point-like stars (aperture-driven). Perceptual model."
        )
        combo.currentIndexChanged.connect(self._on_update_clicked)
        col.addWidget(lbl)
        col.addWidget(combo)
        self.controls_layout.addLayout(col)
        self._exit_pupil_combo = combo

    def _add_eye_blur_check(self):
        """Eye-blur toggle for fixed Eye-vs-Detector scenarios (R3.12).

        Switches the Eye pane between plain asinh (log) and asinh + 1″ spatial
        integration (log_integrated) — the eye's finite spatial resolution at
        a moderate eyepiece magnification."""
        col = QVBoxLayout()
        lbl = QLabel("Eye pane")
        lbl.setStyleSheet("font-size: 8pt; font-weight: normal; color: #555;")
        check = QCheckBox("Eye blur (1″)")
        check.setChecked(False)
        check.setToolTip(
            "Add the eye's ~1″ spatial integration to the Eye pane\n"
            "(log → log_integrated). Models finite eye resolution at a\n"
            "moderate eyepiece; softens fine structure the same way the\n"
            "eye would.")
        check.stateChanged.connect(self._on_update_clicked)
        col.addWidget(lbl)
        col.addWidget(check)
        self.controls_layout.addLayout(col)
        self._eye_blur_check = check

    def _eye_stretch(self) -> str:
        """The Eye pane's stretch: log, or log_integrated when eye-blur is on."""
        if (self._eye_blur_check is not None
                and self._eye_blur_check.isChecked()):
            return "log_integrated"
        return "log"

    # Focal-zoom options (arcsec x-range) for the chromatic focal-plane
    # radial-profile panel. Wide shows the singlet halo off-panel; Close
    # resolves the achromat / APO-doublet / APO-triplet differences.
    _FOCAL_ZOOM_OPTIONS = [
        (120.0, "Wide (±120″) — singlet halo"),
        (10.0, "Close (±10″) — achromat/APO"),
    ]

    def _add_focal_zoom_combo(self):
        """Zoom dropdown for the after-side chromatic focal-plane image (B4).

        Switches the radial-profile x-axis between a wide view (the singlet
        chromatic halo runs off-panel — the dramatic 'bad' case) and a close
        view (resolves the much smaller achromat / APO-doublet / APO-triplet
        residuals that are invisible at the wide scale)."""
        col = QVBoxLayout()
        lbl = QLabel("Focal zoom")
        lbl.setStyleSheet(
            "font-size: 8pt; font-weight: normal; color: #555;")
        combo = QComboBox()
        for arcsec, text in self._FOCAL_ZOOM_OPTIONS:
            combo.addItem(text, arcsec)
        combo.setCurrentIndex(0)  # Wide default
        combo.setToolTip(
            "Radial-profile x-axis range on the focal-plane panel.\n"
            "Wide: the singlet's chromatic halo runs off-panel.\n"
            "Close: zoom in to compare achromat vs APO residuals\n"
            "(too small to see at the wide scale)."
        )
        combo.currentIndexChanged.connect(self._on_update_clicked)
        col.addWidget(lbl)
        col.addWidget(combo)
        self.controls_layout.addLayout(col)
        self._focal_zoom_combo = combo

    def _current_focal_zoom(self, scenario: ScenarioDefinition):
        """Return the selected focal-zoom x-range (arcsec), or None."""
        if self._focal_zoom_combo is None:
            return None
        return self._focal_zoom_combo.currentData()

    # Index of the "F=C plane" item in the focus-wavelength combo (kept
    # as a constant so the sync logic doesn't drift from the addItem
    # order in _add_focus_wavelength_combo).
    _FOCUS_COMBO_FC_INDEX = 1
    _FOCUS_COMBO_G_INDEX = 0

    def _sync_focus_combo_for_objective(self):
        """Disable the F=C-plane focus item when objective is singlet.

        F and C share a focal plane in an achromat (and approximately in
        apo designs) — that's what 'achromatic' means. They lie on
        different planes in a singlet, so the F=C-plane option is
        meaningless for a singlet. If the user had F=C selected when
        they switched to singlet, auto-fall-back to G.
        """
        if self._focus_wavelength_combo is None:
            return
        obj_combo = self._tweak_widgets.get("objective_type")
        if obj_combo is None:
            return
        is_singlet = (obj_combo.currentText() == "singlet")
        from PyQt6.QtCore import Qt
        model = self._focus_wavelength_combo.model()
        if model is None:
            return
        fc_item = model.item(self._FOCUS_COMBO_FC_INDEX)
        if fc_item is None:
            return
        if is_singlet:
            fc_item.setFlags(fc_item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            if (self._focus_wavelength_combo.currentIndex()
                    == self._FOCUS_COMBO_FC_INDEX):
                # Auto-switch to G so we don't render an invalid
                # F=C choice on a singlet
                self._focus_wavelength_combo.setCurrentIndex(
                    self._FOCUS_COMBO_G_INDEX)
        else:
            fc_item.setFlags(fc_item.flags() | Qt.ItemFlag.ItemIsEnabled)

    def _add_focus_wavelength_combo(self):
        """Toggle for which focal plane the user has focused on.

        Default is the G / design wavelength (550 nm), peak human eye
        sensitivity. This is where amateur observers naturally focus an
        achromat (sharpest "snap to focus" at the brightness peak), and
        produces the classic violet/purple halo around bright stars
        from the defocused F and C wavelengths.

        Other options:
          R / B: focus shifted so the chosen channel is sharp at center.
          F=C plane: where F (486 nm) and C (656 nm) converge in an
            achromat — by construction chromatic_defocus(F) ==
            chromatic_defocus(C) for an achromat, so this option is
            *identical* to R or B on an achromat (and produces a green
            halo from the defocused d-line). For a singlet F and C lie
            at different planes, so this option picks the C-line plane.
        """
        col = QVBoxLayout()
        lbl = QLabel("Focus at")
        lbl.setStyleSheet("font-size: 8pt; font-weight: normal; color: #555;")
        combo = QComboBox()
        combo.addItem("G / design (550 nm)", 550.0)
        combo.addItem("F=C plane (achromat-natural)", 656.3)
        combo.addItem("R (656 nm)", 656.3)
        combo.addItem("B (486 nm)", 486.1)
        combo.setCurrentIndex(0)  # G default — typical observer focus, purple halos
        combo.setToolTip(
            "G / design: peak eye sensitivity; the focal plane a typical\n"
            "  observer 'snaps to' on an achromat. Produces the classic\n"
            "  violet/purple halo from defocused F and C light.\n"
            "F=C plane: where F (486) and C (656) converge in an achromat\n"
            "  — produces a green halo from defocused d-line.\n"
            "  Achromat: F=C ≡ R ≡ B (same plane by design).\n"
            "  Singlet: F and C are at different planes; this picks C.\n"
            "R / B: focus shifted so that channel is sharp at center."
        )
        combo.currentIndexChanged.connect(self._on_update_clicked)
        col.addWidget(lbl)
        col.addWidget(combo)
        self.controls_layout.addLayout(col)
        self._focus_wavelength_combo = combo

    def _add_show_overlay_check(self):
        """Toggle for scenario-specific theoretical overlays."""
        col = QVBoxLayout()
        lbl = QLabel("Overlay")
        lbl.setStyleSheet("font-size: 8pt; font-weight: normal; color: #555;")
        check = QCheckBox("Show")
        check.setChecked(True)
        check.stateChanged.connect(self._on_psf_view_changed)
        col.addWidget(lbl)
        col.addWidget(check)
        self.controls_layout.addLayout(col)
        self._show_overlay_check = check

    def _current_log_scale(self) -> bool | None:
        """Return the user-selected log/linear state, or None if no toggle."""
        if self._psf_scale_combo is None:
            return None
        return self._psf_scale_combo.currentIndex() == 0  # 0 = "Log"

    def _current_exposure(self, scenario: ScenarioDefinition) -> float:
        """Return the user-selected exposure level, or scenario default."""
        if self._exposure_slider is None:
            return scenario.default_exposure
        return self._slider_to_exposure(self._exposure_slider.value())

    def _current_filter(self, scenario: ScenarioDefinition) -> str:
        """Return the user-selected filter name, or scenario default."""
        if self._filter_combo is None:
            return scenario.default_filter
        return self._filter_combo.currentData() or scenario.default_filter

    def _current_exit_pupil(self, scenario: ScenarioDefinition) -> float:
        """Return the user-selected exit pupil (mm), or scenario default."""
        if self._exit_pupil_combo is None:
            return scenario.default_exit_pupil_mm
        data = self._exit_pupil_combo.currentData()
        return float(data) if data is not None else scenario.default_exit_pupil_mm

    _EXTENDED_SOURCE_TYPES = ("Jupiter", "Saturn", "Moon")

    @classmethod
    def _scenario_has_extended_source(cls,
                                      scenario: ScenarioDefinition) -> bool:
        """True when the after-side source is an extended object (planet/Moon).

        Only extended sources use the exit-pupil surface-brightness model;
        point/double/field star sources are aperture-driven.
        """
        return scenario.after_source.source_type in cls._EXTENDED_SOURCE_TYPES

    def _before_display_settings(self, scenario: ScenarioDefinition) -> dict:
        """Resolve the Before-side display settings (Phase 1.2).

        The View / Filter / Exposure controls are live and live on the
        After side. By default the Before side mirrors them; when the
        scenario pins before_display_stretch / before_filter /
        before_exposure, the Before side uses those fixed values so the two
        panels form an honest comparison (e.g. Detector vs Eye, no-filter
        vs ND). Exit pupil and focus wavelength always mirror the live
        controls (no per-side pin needed so far).
        """
        stretch = scenario.before_display_stretch
        if stretch is None:
            stretch = (self._display_stretch_combo.currentData()
                       if self._display_stretch_combo is not None else "linear")
        # When the Before pane is the Eye ("log"), the eye-blur toggle may
        # promote it to log_integrated (R3.12 fixed Eye-vs-Detector layout).
        if stretch == "log":
            stretch = self._eye_stretch()
        flt = scenario.before_filter
        if flt is None:
            flt = self._current_filter(scenario)
        exposure = scenario.before_exposure
        if exposure is None:
            exposure = self._current_exposure(scenario)
        focus_wl = (self._focus_wavelength_combo.currentData()
                    if self._focus_wavelength_combo is not None else 550.0)
        return {
            "display_stretch": stretch,
            "filter_name": flt,
            "exposure_level": exposure,
            "focus_wavelength_nm": focus_wl,
            "exit_pupil_mm": self._current_exit_pupil(scenario),
        }

    @staticmethod
    def _axis_lock_is_safe(scenario: ScenarioDefinition) -> bool:
        """True when after-side axes can be safely clamped to before-side limits.

        Unsafe cases:
        - scenario uses different plot functions on each side (units / panel
          counts differ).
        - before/after sources are different types (typically very different
          fields of view, e.g. PointSource vs TutorialStarField).
        """
        if scenario.secondary_plot_function is not None:
            return False
        if scenario.before_source.source_type != scenario.after_source.source_type:
            return False
        return True

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_before(self, scenario: ScenarioDefinition):
        """Render and display the baseline image."""
        self.status_label.setText("Rendering baseline…")
        plot_fn = self._effective_plot_function(scenario, side="before")

        # Determine which widget set drives the before side and which params
        # to read. Three modes:
        #   - tweakable_params_before set: read from independent before widgets
        #   - both_sides_dynamic: read shared widgets (after-side panel)
        #   - default: before side is fully static
        before_source = scenario.before_source
        before_telescope = scenario.before_telescope
        before_seeing = scenario.before_seeing_arcsec

        if scenario.tweakable_params_before is not None:
            params = self._collect_before_params(scenario)
            before_source = self._params_to_source_config(scenario, params,
                                                           base=scenario.before_source)
            before_telescope = self._params_to_telescope_config(
                scenario, params, base=scenario.before_telescope)
            if "seeing" in params:
                before_seeing = params["seeing"]
        elif scenario.both_sides_dynamic and self._tweak_widgets:
            params = self._collect_params(scenario)
            before_source = self._params_to_source_config(
                scenario, params, base=scenario.before_source)
            if scenario.before_telescope_dynamic:
                before_telescope = self._params_to_telescope_config(
                    scenario, params, base=scenario.before_telescope)
            if scenario.before_telescope_dynamic and "seeing" in params:
                before_seeing = params["seeing"]

        # Per-side display settings (Phase 1.2): the Before side may pin its
        # own View / Filter / Exposure so before-vs-after is an honest
        # comparison (e.g. Detector vs Eye, no-filter vs ND).
        disp = self._before_display_settings(scenario)
        fig, info, err = run_scenario_side(
            before_telescope,
            before_source,
            plot_fn,
            wavelength_nm=scenario.before_wavelength_nm,
            seeing_arcsec=before_seeing,
            polychromatic=scenario.before_polychromatic,
            apply_vignetting=scenario.before_apply_vignetting,
            apply_coma=scenario.before_apply_coma,
            log_scale=self._current_log_scale(),
            display_stretch=disp["display_stretch"],
            focus_wavelength_nm=disp["focus_wavelength_nm"],
            exposure_level=disp["exposure_level"],
            filter_name=disp["filter_name"],
            exit_pupil_mm=disp["exit_pupil_mm"],
            idealize_sa=scenario.idealize_singlet_sa,
            focal_zoom_arcsec=self._current_focal_zoom(scenario),
        )
        if err:
            self.status_label.setText("Before render failed")
            print(f"[Tutorial] Before render error:\n{err}")
            return

        # Shared-normalisation reference (Phase 1.5): capture the before-side
        # (unobstructed) on-axis FFT raw peak so the after side can display
        # its obstructed PSF relative to it, making the Strehl drop visible.
        if scenario.shared_psf_normalization:
            self._shared_psf_peak = info.get("psf_raw_peak")
            # Make the before figure self-documenting in the 2D view: it's the
            # reference the after side is normalised against. (The 1D view
            # states the per-side normalisation basis in its side column via
            # the obstruction overlay, so this in-plot note would be redundant
            # there — restrict it to the 2D PSF map.)
            if fig.axes and plot_fn == "plot_psf_2d":
                fig.axes[0].text(
                    0.02, 0.98,
                    "Reference: normalised to own peak (≡ 1.0)",
                    transform=fig.axes[0].transAxes, fontsize=7,
                    va="top", ha="left", color="white",
                    bbox=dict(boxstyle="round,pad=0.3",
                              facecolor="black", alpha=0.6))

        # Theory + scenario overlays. Theory provides numbers/circles; some
        # scenarios (spider_vanes, obstruction_plus_spiders) have no theory
        # function but still need overlays — call apply_theory_overlay
        # whether or not a theory result exists so scenario-id-keyed
        # overlays always fire.
        theory = None
        if scenario.theory_function and plot_fn != "plot_psf_profile":
            theory = compute_theory_for_scenario(
                scenario, info.get("telescope"),
                seeing_arcsec=before_seeing,
                wavelength_nm=scenario.before_wavelength_nm,
            )
            if theory:
                self.theory_readout.update_theory(
                    theory["theory_value"],
                    unit=theory.get("unit", ""),
                    label=theory.get("label", ""),
                    formula=theory.get("formula", ""),
                )
        if (self._show_overlay_check is None
                or self._show_overlay_check.isChecked()):
            apply_theory_overlay(scenario, fig, theory or {},
                                 telescope=info.get("telescope"),
                                 seeing_arcsec=before_seeing,
                                 side="before")

        # Capture per-axis limits for locking the after-side (works for
        # single-plot and multi-subplot figures such as coma field analysis)
        if fig.axes:
            self._before_axis_limits = [
                (ax.get_xlim(), ax.get_ylim()) for ax in fig.axes
            ]
        else:
            self._before_axis_limits = None

        self.before_after.set_before(fig, scenario.before_label)
        plt.close(fig)
        self.status_label.setText("")

    def _render_after(self):
        """Render and display the live after image from current controls."""
        if self._current_scenario is None:
            return

        scenario = self._current_scenario
        params = self._collect_params(scenario)
        self.status_label.setText("Rendering…")

        # Build telescope config from current control values
        after_config = self._params_to_telescope_config(scenario, params)
        after_source_config = self._params_to_source_config(scenario, params)
        plot_fn = self._effective_plot_function(scenario, side="after")

        # Effect toggles (Act 3) — read all five and apply them to either
        # the rendering kwargs (coma, vignetting, seeing) or directly to
        # the telescope config (obstruction, spider_vanes). Previously
        # only coma / vignetting / seeing were honoured, so toggling
        # obstruction or spider_vanes off had no visible effect.
        active_effects = self.effect_toggles.get_active_effects()
        apply_coma = active_effects.get("coma", True)
        apply_vignetting = active_effects.get("vignetting", True)
        seeing = params.get("seeing", scenario.after_seeing_arcsec)
        if not active_effects.get("seeing", True):
            seeing = None
        if not active_effects.get("obstruction", True):
            after_config = replace(
                after_config,
                enable_obstruction=False,
                obstruction_ratio=0.0,
            )
        if not active_effects.get("spider_vanes", True):
            after_config = replace(after_config, spider_vanes=0)

        focus_wl = (self._focus_wavelength_combo.currentData()
                    if self._focus_wavelength_combo is not None else 550.0)
        # After-side stretch: a pinned view (fixed Eye-vs-Detector comparison)
        # takes precedence over the free View combo. When the pinned after view
        # is the Eye ("log"), the eye-blur toggle may promote it to
        # log_integrated.
        if scenario.after_display_stretch is not None:
            stretch = scenario.after_display_stretch
            if stretch == "log":
                stretch = self._eye_stretch()
        else:
            stretch = (self._display_stretch_combo.currentData()
                       if self._display_stretch_combo is not None else "linear")

        exposure = self._current_exposure(scenario)
        flt = self._current_filter(scenario)
        # Shared-normalisation reference (Phase 1.5): only for scenarios that
        # opt in (central_obstruction), and only relevant to the 2D PSF path.
        peak_ref = (self._shared_psf_peak
                    if scenario.shared_psf_normalization else None)
        fig, info, err = run_scenario_side(
            after_config,
            after_source_config,
            plot_fn,
            wavelength_nm=scenario.after_wavelength_nm,
            seeing_arcsec=seeing,
            polychromatic=scenario.after_polychromatic,
            apply_coma=apply_coma,
            apply_vignetting=apply_vignetting,
            log_scale=self._current_log_scale(),
            focus_wavelength_nm=focus_wl,
            display_stretch=stretch,
            exposure_level=exposure,
            filter_name=flt,
            exit_pupil_mm=self._current_exit_pupil(scenario),
            peak_reference=peak_ref,
            idealize_sa=scenario.idealize_singlet_sa,
            focal_zoom_arcsec=self._current_focal_zoom(scenario),
        )

        if err:
            self.status_label.setText("Render failed")
            print(f"[Tutorial] After render error:\n{err}")
            return

        telescope = info.get("telescope")

        # Theory + overlay. Decoupled: overlays fire whether or not a
        # theory function exists (some scenarios use overlays for spider
        # markers without computing a theoretical value).
        theory = None
        if scenario.theory_function and telescope:
            theory = compute_theory_for_scenario(
                scenario, telescope,
                seeing_arcsec=seeing,
                wavelength_nm=scenario.after_wavelength_nm,
                obstruction_ratio=params.get("obstruction_ratio",
                                              scenario.after_telescope.obstruction_ratio),
            )
            if theory:
                # Estimate sim value from figure metadata or theory placeholder
                sim_value = self._estimate_sim_value(scenario, info, theory)
                if sim_value is not None:
                    self.theory_readout.update_values(
                        theory["theory_value"], sim_value,
                        unit=theory.get("unit", ""),
                        label=theory.get("label", ""),
                        formula=theory.get("formula", ""),
                    )
                else:
                    self.theory_readout.update_theory(
                        theory["theory_value"],
                        unit=theory.get("unit", ""),
                        label=theory.get("label", ""),
                        formula=theory.get("formula", ""),
                    )
                # Show extra info for aperture vs seeing
                if scenario.id == "aperture_vs_seeing" and "is_seeing_limited" in theory:
                    if theory["is_seeing_limited"]:
                        self.theory_readout.show_extra("⚠ Seeing-limited")
        if (telescope
                and (self._show_overlay_check is None
                     or self._show_overlay_check.isChecked())):
            apply_theory_overlay(scenario, fig, theory or {},
                                 telescope=telescope,
                                 seeing_arcsec=seeing,
                                 side="after")

        # Apply per-axis limits from before-side for visual comparison.
        # Only safe when both sides use the same plot function AND the same
        # source type; otherwise the captured xlim/ylim are in mismatched
        # units (e.g. µm vs mm) or cover an incompatible FOV (e.g. 5″ point
        # source vs 200″ star field) and applying them clips the after-side
        # to garbage. See _axis_lock_is_safe.
        #
        # Additionally, even when statically safe, the after side may have
        # auto-determined a meaningfully wider/narrower range than the
        # captured before-side (e.g. polychromatic singlet auto-expands FOV
        # ~14× over achromat baseline). The runtime range-mismatch check
        # skips lock per-axis when this happens, so the after side shows
        # its real extent rather than being clipped back.
        if (self.lock_axes_check.isChecked()
                and self._axis_lock_is_safe(scenario)
                and self._before_axis_limits is not None
                and fig.axes):
            for i, ax in enumerate(fig.axes):
                if i < len(self._before_axis_limits):
                    xlim_before, ylim_before = self._before_axis_limits[i]
                    # Apply the before-side window. For PSF plots (mm axis)
                    # this is unconditional — the axis is a display scale
                    # (image_scale ∝ f-ratio), so a bigger aperture shrinks
                    # both the disk AND the auto-scaled axis; holding the axis
                    # fixed is the whole point (the Airy lesson).
                    #
                    # For SOURCE-IMAGE plots the axis IS the real angular FOV.
                    # When the after-side source's FOV genuinely differs from
                    # the before-side (e.g. live ephemeris shrinks Jupiter
                    # 60″→47″, or any size change), forcing the before window
                    # floats the smaller image inside an oversized frame with
                    # the axes background showing as a grey border. Skip the
                    # lock per-axis when the natural spans differ >5%, so the
                    # source is shown at its true angular size. Equal-FOV cases
                    # (aperture/seeing/filter changes; both_sides_dynamic
                    # separation) still lock cleanly.
                    if plot_fn == "plot_source_image":
                        nat_xlim = ax.get_xlim()
                        span_before = abs(xlim_before[1] - xlim_before[0])
                        span_nat = abs(nat_xlim[1] - nat_xlim[0])
                        if (span_before > 0
                                and abs(span_nat - span_before) / span_before
                                > 0.05):
                            continue  # FOV changed — don't clamp to before
                    ax.set_xlim(xlim_before)
                    ax.set_ylim(ylim_before)

        self.before_after.set_after(fig, scenario.after_label)
        plt.close(fig)

        # Update terminal panel
        cmd = build_terminal_command(scenario, {
            **_telescope_kwargs(after_config),
            "wavelength_nm": scenario.after_wavelength_nm,
            "seeing_arcsec": seeing,
            **params,
        })
        self.terminal_panel.set_command(cmd)
        self.status_label.setText("Done")

    def _estimate_sim_value(self, scenario: ScenarioDefinition, info: dict,
                             theory: dict) -> float | None:
        """Extract a simulation value to compare against theory.

        For most scenarios the plot function returns metadata we can use.
        Where we can't extract it, return None (shows theory only).
        """
        if scenario.id == "airy_disk":
            # airy_radius_arcsec is in the render info
            return info.get("airy_radius_arcsec")
        elif scenario.id == "central_obstruction":
            # With shared normalisation (Phase 1.5), the after-side 2D PSF
            # is displayed relative to the unobstructed before-side peak, so
            # the measured displayed peak IS the simulated Strehl ratio —
            # compare it directly against theory (1−ε²)². (psf_relative_peak
            # is only present for the 2D view; the 1D profile shows the
            # Strehl gap via the _obstruction_overlay instead.)
            return info.get("psf_relative_peak")
        elif scenario.id in ("aperture_vs_seeing", "fratio_coma"):
            # Show the theoretical effective resolution as "sim" value
            # (since the simulation matches by construction)
            return theory.get("theory_value")
        return None

    # ------------------------------------------------------------------
    # Control value collection
    # ------------------------------------------------------------------

    def _read_widget_map(self, widget_map: dict) -> dict:
        """Read current values from a widget dict."""
        params = {}
        for key, widget in widget_map.items():
            if isinstance(widget, QDoubleSpinBox):
                params[key] = widget.value()
            elif isinstance(widget, QSpinBox):
                params[key] = widget.value()
            elif isinstance(widget, QComboBox):
                if key == "seeing":
                    params[key] = widget.currentData()
                else:
                    params[key] = widget.currentText()
        return params

    def _collect_params(self, scenario: ScenarioDefinition) -> dict:
        """Read current values from the after-side (or shared) tweak widgets."""
        return self._read_widget_map(self._tweak_widgets)

    def _collect_before_params(self, scenario: ScenarioDefinition) -> dict:
        """Read current values from the independent before-side tweak widgets."""
        return self._read_widget_map(self._tweak_widgets_before)

    def _params_to_telescope_config(self, scenario: ScenarioDefinition,
                                     params: dict,
                                     base: TelescopeConfig | None = None,
                                     ) -> TelescopeConfig:
        """Merge tweak params over a TelescopeConfig base.

        When `base` is None, falls back to scenario.after_telescope so existing
        callers continue to work. Pass `scenario.before_telescope` explicitly
        when rebuilding the before side from live params.
        """
        if base is None:
            base = scenario.after_telescope
        return TelescopeConfig(
            telescope_type=base.telescope_type,
            diameter=params.get("diameter", base.diameter),
            focal_length=params.get("focal_length", base.focal_length),
            primary_type=params.get("primary_type", base.primary_type),
            objective_type=params.get("objective_type", base.objective_type),
            secondary_magnification=base.secondary_magnification,
            meniscus_thickness=base.meniscus_thickness,
            spider_vanes=params.get("spider_vanes", base.spider_vanes),
            spider_vane_width=params.get("spider_vane_width", base.spider_vane_width),
            obstruction_ratio=params.get("obstruction_ratio", base.obstruction_ratio),
            enable_obstruction=base.enable_obstruction if params.get("obstruction_ratio", base.obstruction_ratio) > 0 else False,
        )

    def _params_to_source_config(self, scenario: ScenarioDefinition,
                                   params: dict,
                                   base: SourceConfig | None = None,
                                   ) -> SourceConfig:
        """Build updated source config, merging any tweaked source params.

        When `base` is None, falls back to scenario.after_source. Pass
        `scenario.before_source` explicitly when rebuilding the before side.
        """
        if base is None:
            base = scenario.after_source
        kwargs = dict(base.kwargs)

        if base.source_type == "DoubleStar" and "separation_arcsec" in params:
            kwargs["separation_arcsec"] = params["separation_arcsec"]

        # Live ephemeris toggle (only applies to after-side, not before)
        if (scenario.supports_realtime
                and self._realtime_check is not None
                and self._realtime_check.isChecked()
                and base is scenario.after_source):
            kwargs["use_realtime"] = True

        if kwargs == base.kwargs:
            return base
        return SourceConfig(source_type=base.source_type, kwargs=kwargs)

    # ------------------------------------------------------------------
    # Source code viewer helpers
    # ------------------------------------------------------------------

    def _get_source_functions(self, plot_function_name: str) -> list:
        """Map a plot function name to the list of callables to show in the viewer."""
        mapping = {
            "plot_psf_2d": [plot_psf_2d, compute_fft_psf],
            "plot_psf_profile": [plot_psf_profile, compute_psf],
            "plot_source_image": [
                plot_source_image,
                _render_source_through_telescope,
                _compute_psf_at_field_angle,
            ],
            "plot_coma_field_analysis": [
                plot_coma_field_analysis,
                compute_coma_spot,
                coma_free_field,
            ],
            "plot_polychromatic_ray_trace": [plot_polychromatic_ray_trace],
        }
        return mapping.get(plot_function_name, [])

    # ------------------------------------------------------------------
    # PSF view helpers
    # ------------------------------------------------------------------

    def _effective_plot_function(self, scenario: ScenarioDefinition,
                                  side: str = "after") -> str:
        """Return the plot function to use for a given side.

        Honours the 1D/2D PSF toggle and `secondary_plot_function` (used to
        pair different visualisations on the two sides).
        """
        if (side == "after"
                and scenario.secondary_plot_function is not None):
            return scenario.secondary_plot_function
        if (scenario.plot_function == "plot_psf_2d"
                and self._psf_view_combo is not None
                and self._psf_view_combo.currentIndex() == 1):
            return "plot_psf_profile"
        return scenario.plot_function

    def _on_psf_view_changed(self):
        """Re-render both sides when the PSF view toggle changes."""
        if self._current_scenario is None:
            return
        self._before_axis_limits = None
        # Update source viewer to show 1D or 2D function as appropriate
        self.source_panel.set_functions(
            self._get_source_functions(
                self._effective_plot_function(self._current_scenario)))
        self._render_before(self._current_scenario)
        self._render_after()

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_update_clicked(self):
        # Re-render the before side first whenever it tracks live params:
        # either via shared widgets (both_sides_dynamic) or via independent
        # widgets (tweakable_params_before).
        scn = self._current_scenario
        if scn is not None and (
                scn.both_sides_dynamic
                or scn.tweakable_params_before is not None):
            self._render_before(scn)
        self._render_after()

    def _on_reset_clicked(self):
        if self._current_scenario:
            self._rebuild_controls(self._current_scenario)
            self._render_after()

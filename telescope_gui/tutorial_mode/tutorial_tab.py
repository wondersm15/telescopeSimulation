"""Main Tutorial & Testing tab widget.

Assembles the scenario sidebar, before/after canvases, description panel,
theory readout, tweakable controls, effect toggles, and terminal panel
into a single QWidget registered as a GUI mode.
"""

from __future__ import annotations

import traceback

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QGroupBox, QSizePolicy, QDoubleSpinBox,
    QSpinBox, QComboBox, QFrame, QCheckBox,
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

        # Tweakable controls area
        self.controls_group = QGroupBox("Adjust parameters")
        self.controls_group.setStyleSheet("font-weight: bold; font-size: 9pt;")
        self.controls_layout = QHBoxLayout(self.controls_group)
        self.controls_layout.setContentsMargins(8, 4, 8, 4)
        self.controls_layout.setSpacing(12)
        self.main_layout.addWidget(self.controls_group)

        # Update / Reset buttons
        btn_row = QHBoxLayout()
        self.update_btn = QPushButton("Update →")
        self.update_btn.setStyleSheet(
            "font-weight: bold; padding: 4px 16px; background: #2a6496; "
            "color: white; border-radius: 4px;")
        self.update_btn.clicked.connect(self._on_update_clicked)

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

        btn_row.addWidget(self.update_btn)
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
        self.description_label.setText(scenario.description)
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
        self.before_after.clear_after()
        self.theory_readout.clear()
        self.terminal_panel.clear()

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

        params = scenario.tweakable_params
        params_before = scenario.tweakable_params_before
        # PSF scenarios always get the 1D/2D toggle even if no other tweakable params
        is_psf_scenario = scenario.plot_function == "plot_psf_2d"
        if not params and not is_psf_scenario and not params_before:
            self.controls_group.setVisible(False)
            return

        self.controls_group.setVisible(True)

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

        fig, info, err = run_scenario_side(
            before_telescope,
            before_source,
            plot_fn,
            wavelength_nm=scenario.before_wavelength_nm,
            seeing_arcsec=before_seeing,
            polychromatic=scenario.before_polychromatic,
            apply_vignetting=scenario.before_apply_vignetting,
            apply_coma=scenario.before_apply_coma,
        )
        if err:
            self.status_label.setText("Before render failed")
            print(f"[Tutorial] Before render error:\n{err}")
            return

        # Theory overlay on the before figure — only for 2D PSF (circle overlay)
        if scenario.theory_function and plot_fn != "plot_psf_profile":
            theory = compute_theory_for_scenario(
                scenario, info.get("telescope"),
                seeing_arcsec=scenario.before_seeing_arcsec,
                wavelength_nm=scenario.before_wavelength_nm,
            )
            if theory:
                apply_theory_overlay(scenario, fig, theory,
                                     telescope=info.get("telescope"),
                                     seeing_arcsec=scenario.before_seeing_arcsec)
                self.theory_readout.update_theory(
                    theory["theory_value"],
                    unit=theory.get("unit", ""),
                    label=theory.get("label", ""),
                    formula=theory.get("formula", ""),
                )

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

        # Effect toggles (Act 3)
        active_effects = self.effect_toggles.get_active_effects()
        apply_coma = active_effects.get("coma", True)
        apply_vignetting = active_effects.get("vignetting", True)
        seeing = params.get("seeing", scenario.after_seeing_arcsec)
        if not active_effects.get("seeing", True):
            seeing = None

        fig, info, err = run_scenario_side(
            after_config,
            after_source_config,
            plot_fn,
            wavelength_nm=scenario.after_wavelength_nm,
            seeing_arcsec=seeing,
            polychromatic=scenario.after_polychromatic,
            apply_coma=apply_coma,
            apply_vignetting=apply_vignetting,
        )

        if err:
            self.status_label.setText("Render failed")
            print(f"[Tutorial] After render error:\n{err}")
            return

        telescope = info.get("telescope")

        # Theory computation + overlay (circle overlay only for 2D PSF)
        if scenario.theory_function and telescope:
            theory = compute_theory_for_scenario(
                scenario, telescope,
                seeing_arcsec=seeing,
                wavelength_nm=scenario.after_wavelength_nm,
                obstruction_ratio=params.get("obstruction_ratio",
                                              scenario.after_telescope.obstruction_ratio),
            )
            if theory:
                if plot_fn != "plot_psf_profile":
                    apply_theory_overlay(scenario, fig, theory,
                                         telescope=telescope,
                                         seeing_arcsec=seeing)
                # Estimate sim value from figure metadata or theory value placeholder
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

        # Apply per-axis limits from before-side for visual comparison.
        # Iterates all axes so multi-subplot figures (e.g. coma field analysis)
        # are locked correctly per subplot.
        if (self.lock_axes_check.isChecked()
                and self._before_axis_limits is not None
                and fig.axes):
            for i, ax in enumerate(fig.axes):
                if i < len(self._before_axis_limits):
                    xlim, ylim = self._before_axis_limits[i]
                    ax.set_xlim(xlim)
                    ax.set_ylim(ylim)

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
            # Estimate Strehl from the PSF peak ratio relative to unobstructed
            # (approximate: we don't have unobstructed reference in info)
            return None  # Show theory only for now
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
        if base.source_type == "DoubleStar" and "separation_arcsec" in params:
            return SourceConfig(
                source_type="DoubleStar",
                kwargs={"separation_arcsec": params["separation_arcsec"]},
            )
        return base

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

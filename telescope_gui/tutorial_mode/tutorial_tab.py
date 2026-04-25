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
        self._before_axis_limits: tuple | None = None
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
        self._psf_view_combo = None

        params = scenario.tweakable_params
        # PSF scenarios always get the 1D/2D toggle even if no other tweakable params
        is_psf_scenario = scenario.plot_function == "plot_psf_2d"
        if not params and not is_psf_scenario:
            self.controls_group.setVisible(False)
            return

        self.controls_group.setVisible(True)
        after = scenario.after_telescope

        for param in params:
            if param == "diameter":
                self._add_spin("diameter", "Aperture (mm)", after.diameter,
                               50.0, 1000.0, 10.0)
            elif param == "focal_length":
                self._add_spin("focal_length", "Focal length (mm)", after.focal_length,
                               200.0, 10000.0, 50.0)
            elif param == "obstruction_ratio":
                self._add_spin("obstruction_ratio", "Obstruction", after.obstruction_ratio,
                               0.0, 0.55, 0.01, decimals=2)
            elif param == "spider_vanes":
                self._add_int_spin("spider_vanes", "Spider vanes", after.spider_vanes,
                                   0, 6)
            elif param == "spider_vane_width":
                self._add_spin("spider_vane_width", "Vane width (mm)", after.spider_vane_width,
                               0.5, 10.0, 0.5)
            elif param == "seeing":
                self._add_seeing_combo(scenario.after_seeing_arcsec)
            elif param == "separation_arcsec":
                sep = scenario.after_source.kwargs.get("separation_arcsec", 1.0)
                self._add_spin("separation_arcsec", "Separation (\")", sep, 0.1, 10.0, 0.1)
            elif param == "objective_type":
                self._add_objective_combo(after.objective_type)

        # PSF view toggle for scenarios that render a 2D PSF
        if is_psf_scenario:
            self._add_psf_view_combo()

        self.controls_layout.addStretch()

    def _add_spin(self, key: str, label: str, value: float,
                  minimum: float, maximum: float, step: float, decimals: int = 1):
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
        self.controls_layout.addLayout(col)
        self._tweak_widgets[key] = spin

    def _add_int_spin(self, key: str, label: str, value: int, minimum: int, maximum: int):
        col = QVBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 8pt; font-weight: normal; color: #555;")
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setFixedWidth(70)
        col.addWidget(lbl)
        col.addWidget(spin)
        self.controls_layout.addLayout(col)
        self._tweak_widgets[key] = spin

    def _add_seeing_combo(self, current_seeing: float | None):
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
        # Set current selection
        for i, (_, val) in enumerate(options):
            if val == current_seeing:
                combo.setCurrentIndex(i)
                break
        col.addWidget(lbl)
        col.addWidget(combo)
        self.controls_layout.addLayout(col)
        self._tweak_widgets["seeing"] = combo

    def _add_objective_combo(self, current: str):
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
        self.controls_layout.addLayout(col)
        self._tweak_widgets["objective_type"] = combo

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
        """Render and display the static baseline image."""
        self.status_label.setText("Rendering baseline…")
        plot_fn = self._effective_plot_function(scenario)
        fig, info, err = run_scenario_side(
            scenario.before_telescope,
            scenario.before_source,
            plot_fn,
            wavelength_nm=scenario.before_wavelength_nm,
            seeing_arcsec=scenario.before_seeing_arcsec,
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
                apply_theory_overlay(scenario, fig, theory)
                self.theory_readout.update_theory(
                    theory["theory_value"],
                    unit=theory.get("unit", ""),
                    label=theory.get("label", ""),
                    formula=theory.get("formula", ""),
                )

        # Capture axis limits for locking the after-side axes
        if fig.axes:
            ax = fig.axes[0]
            self._before_axis_limits = (ax.get_xlim(), ax.get_ylim())
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
        plot_fn = self._effective_plot_function(scenario)

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
                    apply_theory_overlay(scenario, fig, theory)
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

        # Apply before-side axis limits to after-side for visual comparison
        if (self.lock_axes_check.isChecked()
                and self._before_axis_limits is not None
                and fig.axes):
            xlim, ylim = self._before_axis_limits
            fig.axes[0].set_xlim(xlim)
            fig.axes[0].set_ylim(ylim)

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

    def _collect_params(self, scenario: ScenarioDefinition) -> dict:
        """Read current values from all tweak widgets."""
        params = {}
        for key, widget in self._tweak_widgets.items():
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

    def _params_to_telescope_config(self, scenario: ScenarioDefinition,
                                     params: dict) -> TelescopeConfig:
        """Merge tweak params over the scenario's after telescope config."""
        base = scenario.after_telescope
        return TelescopeConfig(
            telescope_type=base.telescope_type,
            diameter=params.get("diameter", base.diameter),
            focal_length=params.get("focal_length", base.focal_length),
            primary_type=base.primary_type,
            objective_type=params.get("objective_type", base.objective_type),
            secondary_magnification=base.secondary_magnification,
            meniscus_thickness=base.meniscus_thickness,
            spider_vanes=params.get("spider_vanes", base.spider_vanes),
            spider_vane_width=params.get("spider_vane_width", base.spider_vane_width),
            obstruction_ratio=params.get("obstruction_ratio", base.obstruction_ratio),
            enable_obstruction=base.enable_obstruction if params.get("obstruction_ratio", base.obstruction_ratio) > 0 else False,
        )

    def _params_to_source_config(self, scenario: ScenarioDefinition,
                                   params: dict) -> SourceConfig:
        """Build updated source config, merging any tweaked source params."""
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

    def _effective_plot_function(self, scenario: ScenarioDefinition) -> str:
        """Return the plot function to use, accounting for the 1D/2D PSF toggle."""
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
        self._render_after()

    def _on_reset_clicked(self):
        if self._current_scenario:
            self._rebuild_controls(self._current_scenario)
            self._render_after()

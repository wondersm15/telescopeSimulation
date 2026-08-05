"""Tests for the shared TelescopeControlPanel and source_controls modules.

Requires a QApplication instance for widget creation. A session-scoped
fixture is created here to avoid polluting conftest.py (since no other
test module currently needs Qt).
"""

import pytest

from PyQt6.QtWidgets import QApplication

from telescope_gui.widgets.telescope_controls import (
    TelescopeControlPanel, DEFAULT_OBSTRUCTION,
)
from telescope_gui.widgets.source_controls import get_source, get_seeing, SEEING_PRESETS
from telescope_sim.source.sources import Jupiter, Moon, Saturn, StarField, PointSource


# ------------------------------------------------------------------
# QApplication fixture (session-scoped so it's created once)
# ------------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ------------------------------------------------------------------
# TelescopeControlPanel tests
# ------------------------------------------------------------------

class TestTelescopeControlPanelCreation:
    """Test that the panel can be created in both layout modes."""

    def test_create_sidebar_mode(self, qapp):
        panel = TelescopeControlPanel(number=1, layout_mode="sidebar")
        assert panel is not None

    def test_create_grid_mode(self, qapp):
        panel = TelescopeControlPanel(number=1, layout_mode="grid")
        assert panel is not None

    def test_create_without_group_box(self, qapp):
        panel = TelescopeControlPanel(
            number=1, layout_mode="grid", show_group_box=False
        )
        assert panel is not None

    def test_custom_defaults(self, qapp):
        panel = TelescopeControlPanel(
            number=2, layout_mode="sidebar",
            default_type="Cassegrain", default_fratio=10.0,
        )
        assert panel.type_combo.currentText() == "Cassegrain"
        assert panel.fratio_spin.value() == 10.0


class TestGetConfig:
    """Test that get_config() returns correct default values."""

    def test_default_newtonian_config(self, qapp):
        panel = TelescopeControlPanel(
            number=1, layout_mode="sidebar",
            default_type="Newtonian", default_fratio=5.0,
        )
        config = panel.get_config()

        assert config["telescope_type"] == "Newtonian"
        assert config["diameter"] == 200.0
        assert config["focal_length"] == 1000.0  # 200 * 5
        assert config["primary_type"] == "parabolic"
        assert config["spider_vanes"] == 0
        assert config["obstruction_ratio"] == 0.20
        assert config["enable_obstruction"] is True

    def test_default_cassegrain_config(self, qapp):
        panel = TelescopeControlPanel(
            number=1, layout_mode="grid",
            default_type="Cassegrain", default_fratio=10.0,
        )
        config = panel.get_config()

        assert config["telescope_type"] == "Cassegrain"
        assert config["secondary_magnification"] == 3.0
        assert config["obstruction_ratio"] == 0.30

    def test_config_keys_match_build_telescope(self, qapp):
        """get_config() keys should be valid build_telescope() kwargs."""
        from telescope_gui.telescope_builder import build_telescope
        import inspect

        panel = TelescopeControlPanel(number=1, layout_mode="sidebar")
        config = panel.get_config()

        sig = inspect.signature(build_telescope)
        valid_params = set(sig.parameters.keys())
        config_keys = set(config.keys())

        assert config_keys.issubset(valid_params), (
            f"Extra keys in get_config(): {config_keys - valid_params}"
        )


class TestBuildConvenience:
    """Test the build() convenience method."""

    def test_build_returns_telescope(self, qapp):
        panel = TelescopeControlPanel(number=1, layout_mode="sidebar")
        telescope = panel.build()
        assert telescope is not None
        assert telescope.primary_diameter == 200.0

    def test_build_all_types(self, qapp):
        types = [
            "Newtonian", "Cassegrain", "Refractor",
            "Maksutov-Cassegrain", "Schmidt-Cassegrain",
        ]
        for ttype in types:
            panel = TelescopeControlPanel(
                number=1, layout_mode="grid", default_type=ttype,
            )
            telescope = panel.build()
            assert telescope is not None, f"Failed to build {ttype}"


class TestControlsVisibility:
    """Test update_controls_visibility() for each telescope type."""

    def test_newtonian_shows_primary(self, qapp):
        panel = TelescopeControlPanel(
            number=1, layout_mode="sidebar", default_type="Newtonian",
        )
        # Use isHidden() instead of isVisible() — isVisible() requires
        # the widget to be shown in a window; isHidden() checks the
        # widget's own visibility flag.
        assert not panel.primary_label.isHidden()
        assert not panel.primary_combo.isHidden()
        assert panel.objective_label.isHidden()
        assert panel.objective_combo.isHidden()
        assert panel.sec_mag_label.isHidden()
        assert panel.meniscus_label.isHidden()

    def test_refractor_shows_objective(self, qapp):
        panel = TelescopeControlPanel(
            number=1, layout_mode="sidebar", default_type="Refractor",
        )
        assert not panel.objective_label.isHidden()
        assert not panel.objective_combo.isHidden()
        assert panel.primary_label.isHidden()
        assert panel.obstruction_label.isHidden()
        assert panel.spider_vanes_label.isHidden()

    def test_cassegrain_shows_sec_mag(self, qapp):
        panel = TelescopeControlPanel(
            number=1, layout_mode="sidebar", default_type="Cassegrain",
        )
        assert not panel.sec_mag_label.isHidden()
        assert not panel.sec_mag_spin.isHidden()
        assert panel.primary_label.isHidden()
        assert panel.objective_label.isHidden()

    def test_maksutov_shows_meniscus(self, qapp):
        panel = TelescopeControlPanel(
            number=1, layout_mode="sidebar", default_type="Maksutov-Cassegrain",
        )
        assert not panel.meniscus_label.isHidden()
        assert not panel.meniscus_spin.isHidden()
        assert not panel.sec_mag_label.isHidden()

    def test_schmidt_shows_sec_mag_no_meniscus(self, qapp):
        panel = TelescopeControlPanel(
            number=1, layout_mode="sidebar", default_type="Schmidt-Cassegrain",
        )
        assert not panel.sec_mag_label.isHidden()
        assert panel.meniscus_label.isHidden()

    def test_type_change_updates_visibility(self, qapp):
        panel = TelescopeControlPanel(
            number=1, layout_mode="sidebar", default_type="Newtonian",
        )
        assert not panel.primary_label.isHidden()

        panel.type_combo.setCurrentText("Refractor")
        assert panel.primary_label.isHidden()
        assert not panel.objective_label.isHidden()


class TestFocalLengthSync:
    """Test bidirectional focal length / f-ratio synchronization."""

    def test_initial_focal_length(self, qapp):
        panel = TelescopeControlPanel(
            number=1, layout_mode="sidebar",
            default_fratio=5.0,
        )
        # aperture=200, fratio=5 → FL=1000
        assert abs(panel.focal_length_spin.value() - 1000.0) < 0.1

    def test_fratio_change_updates_focal_length(self, qapp):
        panel = TelescopeControlPanel(
            number=1, layout_mode="sidebar",
            default_fratio=5.0,
        )
        panel.fratio_spin.setValue(8.0)
        # aperture=200, fratio=8 → FL=1600
        assert abs(panel.focal_length_spin.value() - 1600.0) < 0.1

    def test_focal_length_change_updates_fratio(self, qapp):
        panel = TelescopeControlPanel(
            number=1, layout_mode="sidebar",
            default_fratio=5.0,
        )
        panel.focal_length_spin.setValue(1500.0)
        # aperture=200, FL=1500 → fratio=7.5
        assert abs(panel.fratio_spin.value() - 7.5) < 0.1

    def test_aperture_change_with_locked_fratio(self, qapp):
        panel = TelescopeControlPanel(
            number=1, layout_mode="sidebar",
            default_fratio=5.0,
        )
        panel.lock_fratio_check.setChecked(True)
        panel.aperture_spin.setValue(300.0)
        # fratio stays 5, FL should be 1500
        assert abs(panel.fratio_spin.value() - 5.0) < 0.1
        assert abs(panel.focal_length_spin.value() - 1500.0) < 0.1

    def test_aperture_change_with_locked_focal_length(self, qapp):
        panel = TelescopeControlPanel(
            number=1, layout_mode="sidebar",
            default_fratio=5.0,
        )
        panel.lock_focal_length_check.setChecked(True)
        panel.aperture_spin.setValue(250.0)
        # FL stays 1000, fratio should be 4.0
        assert abs(panel.focal_length_spin.value() - 1000.0) < 0.1
        assert abs(panel.fratio_spin.value() - 4.0) < 0.1

    def test_lock_fratio_unchecks_lock_fl(self, qapp):
        panel = TelescopeControlPanel(number=1, layout_mode="sidebar")
        panel.lock_focal_length_check.setChecked(True)
        panel.lock_fratio_check.setChecked(True)
        assert not panel.lock_focal_length_check.isChecked()

    def test_lock_fl_unchecks_lock_fratio(self, qapp):
        panel = TelescopeControlPanel(number=1, layout_mode="sidebar")
        panel.lock_fratio_check.setChecked(True)
        panel.lock_focal_length_check.setChecked(True)
        assert not panel.lock_fratio_check.isChecked()


class TestDefaultObstruction:
    """Test that obstruction defaults are set per telescope type."""

    @pytest.mark.parametrize("ttype,expected", [
        ("Newtonian", 0.20),
        ("Cassegrain", 0.30),
        ("Maksutov-Cassegrain", 0.33),
        ("Schmidt-Cassegrain", 0.35),
    ])
    def test_default_obstruction_values(self, qapp, ttype, expected):
        panel = TelescopeControlPanel(
            number=1, layout_mode="sidebar", default_type=ttype,
        )
        assert abs(panel.obstruction_spin.value() - expected) < 0.001

    def test_type_change_updates_obstruction(self, qapp):
        panel = TelescopeControlPanel(
            number=1, layout_mode="sidebar", default_type="Newtonian",
        )
        assert abs(panel.obstruction_spin.value() - 0.20) < 0.001
        panel.type_combo.setCurrentText("Cassegrain")
        assert abs(panel.obstruction_spin.value() - 0.30) < 0.001


# ------------------------------------------------------------------
# Source controls tests
# ------------------------------------------------------------------

class TestGetSource:
    """Test the get_source() helper."""

    def test_jupiter(self):
        s = get_source("Jupiter")
        assert isinstance(s, Jupiter)

    def test_saturn(self):
        s = get_source("Saturn")
        assert isinstance(s, Saturn)

    def test_moon(self):
        s = get_source("Moon")
        assert isinstance(s, Moon)

    def test_star_field(self):
        s = get_source("Star Field")
        assert isinstance(s, StarField)

    def test_point_source(self):
        s = get_source("Point Source (Star)")
        assert isinstance(s, PointSource)

    def test_none(self):
        assert get_source("None") is None

    def test_unknown_returns_none(self):
        assert get_source("InvalidSource") is None


class TestGetSeeing:
    """Test the get_seeing() helper."""

    def test_excellent(self):
        assert get_seeing("Excellent") == 0.8

    def test_good(self):
        assert get_seeing("Good") == 1.5

    def test_average(self):
        assert get_seeing("Average") == 2.5

    def test_poor(self):
        assert get_seeing("Poor") == 4.0

    def test_none(self):
        assert get_seeing("None") is None

    def test_case_insensitive(self):
        assert get_seeing("good") == 1.5
        assert get_seeing("GOOD") == 1.5
        assert get_seeing("Good") == 1.5


# ------------------------------------------------------------------
# Parameters & Physics reference tab — vignetting diagram
# ------------------------------------------------------------------

class TestReferenceTabVignettingDiagram:
    """The static vignetting diagram (user-requested; vignetting can't be
    shown on the star field, so it's illustrated here instead)."""

    def test_diagram_builds_with_two_panels(self):
        import matplotlib
        matplotlib.use("Agg")
        from telescope_gui.reference_tab import _build_vignetting_diagram
        fig = _build_vignetting_diagram()
        # Side view + secondary-face panels.
        assert len(fig.axes) == 2
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_reference_tab_constructs_with_diagram(self, qapp):
        from telescope_gui.reference_tab import ParametersPhysicsTab
        tab = ParametersPhysicsTab()
        assert tab is not None

    def test_panel_a_source_star_and_focus_circle(self):
        """R4.6: Panel A marks the light SOURCE with a star and the
        convergence (prime focus) with an OPEN CIRCLE; caught rays stop at the
        secondary while missed rays continue to the focus."""
        import matplotlib
        matplotlib.use("Agg")
        from telescope_gui.reference_tab import _build_vignetting_diagram
        import matplotlib.pyplot as plt
        fig = _build_vignetting_diagram()
        axA = fig.axes[0]
        markers = [ln.get_marker() for ln in axA.get_lines()]
        assert "*" in markers          # source star
        assert "o" in markers          # prime-focus convergence circle
        # An open-circle marker (unfilled facecolor) for the focus.
        assert any(ln.get_marker() == "o"
                   and ln.get_markerfacecolor() in ("none", "None")
                   for ln in axA.get_lines())
        plt.close(fig)

    def test_caption_defines_clear_aperture(self):
        from telescope_gui.reference_tab import VIGNETTING_DIAGRAM_CAPTION_HTML
        html = VIGNETTING_DIAGRAM_CAPTION_HTML.lower()
        assert "clear aperture" in html
        assert "reflective face" in html          # what it IS
        assert "miss" in html                      # red rays miss the mirror


class TestReferenceTabRealismAudit:
    """R3.3: the Parameters & Physics tab carries a realism-audit section
    (approximations + how to improve them), including the eye-mode ring note."""

    def test_realism_section_present(self, qapp):
        from PyQt6.QtWidgets import QGroupBox
        from telescope_gui.reference_tab import ParametersPhysicsTab
        tab = ParametersPhysicsTab()
        titles = [gb.title() for gb in tab.findChildren(QGroupBox)]
        assert any("Realism audit" in t for t in titles)

    def test_covers_eye_ring_over_emphasis(self):
        from telescope_gui.reference_tab import REALISM_AUDIT_HTML
        h = REALISM_AUDIT_HTML.lower()
        assert "asinh" in h and "ring" in h
        # Names concrete idealisations with an improve/accept framing.
        assert "to improve" in h and "accepted" in h
        assert "seeing" in h and "procedural" in h


# ------------------------------------------------------------------
# Tutorial sidebar — every act must be reachable (regression: Act 4
# was hardcoded out, hiding Jupiter/Saturn/Star Field Showcase)
# ------------------------------------------------------------------

class TestScenarioSidebarActs:
    def test_all_acts_and_scenarios_listed(self, qapp):
        from PyQt6.QtWidgets import QLabel, QPushButton, QScrollArea
        from telescope_gui.tutorial_mode.widgets.scenario_sidebar import (
            ScenarioSidebar,
        )
        from telescope_gui.tutorial_mode.scenario_registry import (
            get_scenarios_by_act, SCENARIOS,
        )
        sb = ScenarioSidebar()

        # Every act present in the registry must have a heading in the sidebar.
        labels = [w.text() for w in sb.findChildren(QLabel)]
        acts = sorted(get_scenarios_by_act().keys())
        for act_num in acts:
            assert any(f"Act {act_num}" in t for t in labels), (
                f"Act {act_num} heading missing from sidebar")
        # Act 4 (Real Objects) specifically — the one that was dropped.
        assert any("Act 4" in t and "Real Objects" in t for t in labels)

        # Every implemented scenario must have a button.
        implemented = [s for s in SCENARIOS if s.implemented]
        assert len(sb._buttons) == len(implemented)
        for s in implemented:
            assert s.id in sb._buttons

    def test_act4_scenarios_are_reachable(self, qapp):
        from telescope_gui.tutorial_mode.widgets.scenario_sidebar import (
            ScenarioSidebar,
        )
        sb = ScenarioSidebar()
        for sid in ("saturn_rings", "starfield_resolution"):
            assert sid in sb._buttons, f"{sid} not reachable in sidebar"
            assert sb._buttons[sid].isEnabled()


# ------------------------------------------------------------------
# R3.13a — live ephemeris applies to BOTH sides
# ------------------------------------------------------------------

class TestRealtimeBothSides:
    def test_realtime_applies_to_before_and_after(self, qapp):
        """When the live-ephemeris box is checked, BOTH the Before and After
        Moon sources are rebuilt with use_realtime=True (R3.13a — previously
        only the After side got it)."""
        import telescope_gui.tutorial_mode.tutorial_tab as tt
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id

        calls = []
        orig = tt.run_scenario_side

        def spy(tel, src, plot_fn, **kw):
            calls.append(dict(src.kwargs))
            return orig(tel, src, plot_fn, **kw)

        tt.run_scenario_side = spy
        try:
            tab = tt.TutorialTab()
            s = get_scenario_by_id("nd_filter_moon")
            tab._load_scenario(s)
            assert tab._realtime_check is not None
            tab._realtime_check.setChecked(True)
            calls.clear()
            tab._render_before(s)
            tab._render_after()
            assert len(calls) == 2
            assert all(kw.get("use_realtime") is True for kw in calls)
        finally:
            tt.run_scenario_side = orig

    def test_realtime_off_leaves_sources_canned(self, qapp):
        """Unchecked → neither side sets use_realtime (default canned Moon)."""
        import telescope_gui.tutorial_mode.tutorial_tab as tt
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id

        calls = []
        orig = tt.run_scenario_side

        def spy(tel, src, plot_fn, **kw):
            calls.append(dict(src.kwargs))
            return orig(tel, src, plot_fn, **kw)

        tt.run_scenario_side = spy
        try:
            tab = tt.TutorialTab()
            s = get_scenario_by_id("nd_filter_moon")
            tab._load_scenario(s)
            tab._realtime_check.setChecked(False)
            calls.clear()
            tab._render_before(s)
            tab._render_after()
            assert all(not kw.get("use_realtime") for kw in calls)
        finally:
            tt.run_scenario_side = orig


# ------------------------------------------------------------------
# R5.3c: the Tutorial "Learn more →" line is a working deep link into
# the Parameters & Physics reference, not decorative blue text.
# ------------------------------------------------------------------

class TestLearnMoreDeepLink:
    """Every scenario's learn_more_section must land on a real heading."""

    def _ref(self):
        from telescope_gui.reference_tab import ParametersPhysicsTab
        return ParametersPhysicsTab()

    @staticmethod
    def _heading_of(widget):
        """Readable heading for an anchor widget (group-box title or <h3>)."""
        import re
        from PyQt6.QtWidgets import QGroupBox
        if isinstance(widget, QGroupBox):
            return widget.title()
        m = re.match(r"\A<h3>(.*?)</h3>", widget.text(), re.DOTALL)
        return re.sub(r"<[^>]+>", "", m.group(1)) if m else ""

    def test_every_scenario_hint_resolves(self, qapp):
        """A new scenario with an unmatched hint fails here, not silently."""
        from telescope_gui.tutorial_mode.scenario_registry import SCENARIOS
        ref = self._ref()
        unmatched = [s.learn_more_section for s in SCENARIOS
                     if ref.resolve_section(s.learn_more_section) is None]
        assert unmatched == []

    def test_ambiguous_hints_pick_the_physics_heading(self, qapp):
        """The two hints with more than one plausible target.

        "Diffraction" must not land on "3. Spider Vane Diffraction", and
        "Coma" must not land on the "Coma Field Analysis" plot description.
        """
        ref = self._ref()
        assert "1. Diffraction" in self._heading_of(
            ref.resolve_section("Diffraction"))
        assert "5. Coma" in self._heading_of(ref.resolve_section("Coma"))

    def test_plural_and_partial_hints_resolve(self, qapp):
        """Hints that differ from the heading in number or extra words."""
        ref = self._ref()
        assert "Spider Vane" in self._heading_of(
            ref.resolve_section("Spider Vanes"))
        assert "Photometry" in self._heading_of(
            ref.resolve_section("Photometry & Filters"))
        # Exact match beats the "Vignetting (diagram)" figure section.
        assert self._heading_of(ref.resolve_section("Vignetting")) \
            == "7. Vignetting"

    def test_unknown_hint_is_reported_not_guessed(self, qapp):
        ref = self._ref()
        assert ref.resolve_section("Quantum Chromodynamics") is None
        assert ref.scroll_to_section("Quantum Chromodynamics") is False

    def test_sections_scroll_to_distinct_places_in_document_order(self, qapp):
        """The link actually moves the view, and later sections scroll further."""
        ref = self._ref()
        ref.resize(1000, 800)
        ref.show()
        qapp.processEvents()
        ordered = ["Diffraction", "Central Obstruction", "Spider Vanes",
                   "Chromatic Aberration", "Coma", "Vignetting",
                   "Atmospheric Seeing", "Photometry & Filters"]
        positions = []
        for name in ordered:
            assert ref.scroll_to_section(name) is True
            positions.append(ref._scroll.verticalScrollBar().value())
        assert positions[0] > 0, "first jump did not move the scroll area"
        assert positions == sorted(positions), positions
        assert len(set(positions)) == len(positions), positions
        ref.hide()

    def test_split_registers_one_anchor_per_h3(self, qapp):
        """Splitting the body at <h3> is what makes subsections addressable."""
        from telescope_gui.reference_tab import PHYSICS_HTML
        ref = self._ref()
        assert len(ref._anchors) >= PHYSICS_HTML.count("\n<h3>")

    def test_tutorial_label_is_a_clickable_link_carrying_the_section(self, qapp):
        """The label renders an <a href> and emits the hint when activated."""
        from telescope_gui.tutorial_mode.tutorial_tab import TutorialTab
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        tab = TutorialTab()
        scenario = get_scenario_by_id("fratio_coma")
        tab._load_scenario(scenario)
        text = tab.learn_more_label.text()
        assert "<a href='reference:Coma'" in text

        emitted = []
        tab.learn_more_requested.connect(emitted.append)
        tab.learn_more_label.linkActivated.emit("reference:Coma")
        assert emitted == ["Coma"]

    def test_click_opens_reference_tab_beside_tutorial(self, qapp):
        """The jump must not destroy the scenario the reader is working in."""
        from telescope_gui.main_window import MainWindow
        from telescope_gui.reference_tab import ParametersPhysicsTab
        win = MainWindow()
        win.tutorial_mode_radio.setChecked(True)
        tutorial = win.tab_widget.widget(0)
        assert win.tab_widget.count() == 1          # built lazily

        tutorial.learn_more_requested.emit("Central Obstruction")
        qapp.processEvents()

        titles = [win.tab_widget.tabText(i)
                  for i in range(win.tab_widget.count())]
        assert titles == ["Tutorial", "Reference"]
        ref = win.tab_widget.widget(1)
        assert isinstance(ref, ParametersPhysicsTab)
        assert win.tab_widget.currentWidget() is ref
        # Tutorial tab survives, still holding its scenario.
        assert win.tab_widget.widget(0) is tutorial

        # A second click reuses the same tab rather than stacking duplicates.
        tutorial.learn_more_requested.emit("Vignetting")
        qapp.processEvents()
        assert win.tab_widget.count() == 2
        win.close()


# ------------------------------------------------------------------
# R5.5b/c/d — figure conventions: axis naming and pupil colour language
# ------------------------------------------------------------------

class TestPupilColourLanguage:
    """The pupil colour scale must distinguish which SIDE of the pupil a ray
    entered from (R5.5d). Colouring on |h| made a ray at -80 mm and one at
    +80 mm identical, on a figure whose whole point is that those two rays
    land on opposite sides of the focus.
    """

    def test_opposite_pupil_halves_get_different_colours(self):
        import numpy as np
        from telescope_sim.plotting.ray_trace_plot import _pupil_colormap_colors
        colors, _ = _pupil_colormap_colors(np.array([-80.0, 80.0]))
        assert colors[0] != colors[1]

    def test_colour_depends_only_on_signed_height(self):
        import numpy as np
        from telescope_sim.plotting.ray_trace_plot import _pupil_colormap_colors
        colors, _ = _pupil_colormap_colors(np.array([-40.0, 40.0, -40.0]))
        assert colors[0] == colors[2]      # same ray height -> same colour
        assert colors[0] != colors[1]      # mirrored ray    -> different

    def test_scale_is_centred_on_the_optical_axis(self):
        """h = 0 must sit at the middle of the colourbar, so the two wings are
        readable as 'below' and 'above' rather than an arbitrary split."""
        import numpy as np
        from telescope_sim.plotting.ray_trace_plot import _pupil_colormap_colors
        _, sm = _pupil_colormap_colors(np.array([-95.0, -10.0, 0.0, 95.0]))
        assert sm.norm.vmin == pytest.approx(-sm.norm.vmax)
        assert sm.norm.vmax == pytest.approx(95.0)

    def test_near_axis_rays_are_not_washed_out(self):
        """Both wings start part-way up their ramp; a paraxial ray must stay
        visible against the white panel background."""
        import numpy as np
        from telescope_sim.plotting.ray_trace_plot import _pupil_diverging_cmap
        cmap = _pupil_diverging_cmap()
        for v in (0.49, 0.51):
            r, g, b, _ = cmap(v)
            assert min(r, g, b) < 0.90     # not near-white

    def test_blue_wing_is_below_axis_and_orange_above(self):
        import numpy as np
        from telescope_sim.plotting.ray_trace_plot import _pupil_colormap_colors
        colors, _ = _pupil_colormap_colors(np.array([-95.0, 95.0]))
        neg_r, neg_g, neg_b, _ = colors[0]
        pos_r, pos_g, pos_b, _ = colors[1]
        assert neg_b > neg_r               # negative h reads blue
        assert pos_r > pos_b               # positive h reads orange

    def test_2d_spot_scale_stays_unsigned_and_shares_the_hue(self):
        """A 2D spot replicates every azimuth, so 'above/below' is undefined
        there — it keeps a magnitude ramp, deliberately the positive (orange)
        wing so both families speak one colour language."""
        from telescope_sim.plotting.ray_trace_plot import (
            _pupil_magnitude_cmap, _pupil_diverging_cmap)
        mag = _pupil_magnitude_cmap()
        div = _pupil_diverging_cmap()
        assert mag(0.0)[:3] == pytest.approx(div(0.5)[:3], abs=0.02)
        assert mag(1.0)[:3] == pytest.approx(div(1.0)[:3], abs=0.02)
        # Monotonically darkening, so "deep = edge" holds.
        assert sum(mag(1.0)[:3]) < sum(mag(0.0)[:3])

    def test_no_figure_still_advertises_an_unsigned_meridional_scale(self):
        """The old '|Pupil zone| (mm)' colourbar label claimed a magnitude
        scale on plots that are now signed."""
        from pathlib import Path
        src = Path("telescope_sim/plotting/ray_trace_plot.py").read_text()
        assert "|Pupil zone| (mm)" not in src


class TestFigureAxisConventions:
    """R5.5c: z is the optical axis, x/y are transverse — in every figure."""

    def _fig_labels(self, fig):
        return [(ax.get_xlabel(), ax.get_ylabel()) for ax in fig.axes]

    def test_side_views_name_the_optical_axis_z(self):
        import matplotlib.pyplot as plt
        from telescope_sim.plotting.ray_trace_plot import (
            plot_ray_trace_pupil_colored)
        from telescope_gui.telescope_builder import build_telescope
        t = build_telescope(telescope_type="Newtonian", diameter=200,
                            focal_length=800, primary_type="spherical",
                            enable_obstruction=False, spider_vanes=0)
        fig = plot_ray_trace_pupil_colored(t)
        xl, yl = self._fig_labels(fig)[0]
        assert xl == "x, transverse (mm)"
        assert "z" in yl and "optical axis" in yl
        plt.close(fig)

    def test_focal_plane_views_name_both_transverse_axes(self):
        """They used to read 'Position (mm)' on both axes, which named
        neither."""
        from pathlib import Path
        src = Path("telescope_sim/plotting/ray_trace_plot.py").read_text()
        assert 'set_xlabel("Position (mm)")' not in src
        assert 'set_ylabel("Position (mm)")' not in src
        assert 'set_xlabel("Position on focal plane (mm)")' not in src

    def test_no_side_view_calls_the_optical_axis_y(self):
        """'y (mm)' for the optical axis collided with the transverse y of the
        focal-plane views — the ambiguity R5.5c was raised about."""
        from pathlib import Path
        src = Path("telescope_sim/plotting/ray_trace_plot.py").read_text()
        assert '_ylabel("y (mm)")' not in src
        assert '_ylabel("y (mm)", fontsize=8)' not in src


class TestSphericalCausticOrientation:
    """R5.5b: the caustic used to be drawn with the optical axis HORIZONTAL,
    next to a ray trace drawn with it VERTICAL — the same picture rotated 90°,
    which is what read as 'on its side'.
    """

    def _analysis_fig(self):
        from telescope_sim.plotting.ray_trace_plot import (
            plot_spherical_focal_analysis)
        from telescope_gui.telescope_builder import build_telescope
        t = build_telescope(telescope_type="Newtonian", diameter=200,
                            focal_length=800, primary_type="spherical",
                            enable_obstruction=False, spider_vanes=0)
        return plot_spherical_focal_analysis(t)

    def test_caustic_optical_axis_is_vertical(self):
        import matplotlib.pyplot as plt
        fig = self._analysis_fig()
        ax_caustic = fig.axes[0]
        assert "Δz" in ax_caustic.get_ylabel()
        assert ax_caustic.get_xlabel().startswith("Transverse x")
        plt.close(fig)

    def test_caustic_and_ray_trace_agree_on_which_axis_is_optical(self):
        """Both panels the reader compares must put z on the same screen
        axis, or the comparison silently transposes."""
        import matplotlib.pyplot as plt
        from telescope_sim.plotting.ray_trace_plot import (
            plot_ray_trace_pupil_colored)
        from telescope_gui.telescope_builder import build_telescope
        t = build_telescope(telescope_type="Newtonian", diameter=200,
                            focal_length=800, primary_type="spherical",
                            enable_obstruction=False, spider_vanes=0)
        trace = plot_ray_trace_pupil_colored(t)
        analysis = self._analysis_fig()
        trace_y = trace.axes[0].get_ylabel()
        caustic_y = analysis.axes[0].get_ylabel()
        assert "z" in trace_y and "z" in caustic_y
        assert "x" in trace.axes[0].get_xlabel()
        assert "x" in analysis.axes[0].get_xlabel()
        plt.close(trace)
        plt.close(analysis)

    def test_marginal_rays_cross_below_the_paraxial_focus(self):
        """The physics the rotation has to preserve: with z up the page and
        light climbing, edge rays cross SHORT of the star, i.e. at Δz < 0."""
        import numpy as np
        import matplotlib.pyplot as plt
        from telescope_sim.plotting.ray_trace_plot import _trace_ray_fan
        from telescope_gui.telescope_builder import build_telescope
        t = build_telescope(telescope_type="Newtonian", diameter=200,
                            focal_length=800, primary_type="spherical",
                            enable_obstruction=False, spider_vanes=0)
        h, dx = _trace_ray_fan(t, 550.0, 21)
        marginal = int(np.argmax(np.abs(h)))
        z_cross = dx[marginal] * t.focal_length / h[marginal]
        assert z_cross < 0
        fig = self._analysis_fig()
        lo, hi = fig.axes[0].get_ylim()
        assert lo < z_cross < 0 < hi        # visible, below the star
        # And the vertical axis really is the Δz axis (mm, a few times the
        # marginal crossing), not the transverse one (µm, ~100× larger). This
        # is what fails if the panel is ever rotated back on its side.
        assert hi < 5.0 * abs(z_cross)
        plt.close(fig)


class TestCausticInTheCorrectedState:
    """The primary_type dropdown's OTHER value. With a parabolic primary
    every ray crosses at Δz = 0, and the panel used to collapse: the axis
    floored at ±1 µm of numerical noise and every ray was drawn as the same
    vertical line, under a title that still claimed a caustic existed.
    """

    def _fig(self, primary_type):
        from telescope_sim.plotting.ray_trace_plot import (
            plot_spherical_focal_analysis)
        from telescope_gui.telescope_builder import build_telescope
        t = build_telescope(telescope_type="Newtonian", diameter=200,
                            focal_length=800, primary_type=primary_type,
                            enable_obstruction=False, spider_vanes=0)
        return plot_spherical_focal_analysis(t), t

    def test_corrected_panel_is_scaled_to_the_depth_of_focus(self):
        """Not to numerical noise: the visible Δz range must be a physical
        tolerance the reader can compare the crossing against."""
        import matplotlib.pyplot as plt
        fig, t = self._fig("parabolic")
        lo, hi = fig.axes[0].get_ylim()
        dof_half = 2.0 * (550.0 * 1e-6) * t.focal_ratio ** 2
        assert hi >= dof_half          # the band itself has to fit
        assert hi <= 10.0 * dof_half   # but not be lost in a huge window
        plt.close(fig)

    def test_corrected_panel_draws_a_converging_cone_not_one_line(self):
        """Every ray crosses at Δz = 0, but they still ARRIVE at different
        angles — the cone must be visible, not collapsed onto the axis."""
        import matplotlib.pyplot as plt
        fig, _t = self._fig("parabolic")
        ax = fig.axes[0]
        spans = [abs(ln.get_xdata()[1] - ln.get_xdata()[0])
                 for ln in ax.lines if len(ln.get_xdata()) == 2]
        assert max(spans) > 1.0        # µm of transverse travel across the box
        plt.close(fig)

    def test_corrected_title_does_not_claim_a_caustic(self):
        import matplotlib.pyplot as plt
        fig, _t = self._fig("parabolic")
        title = fig.axes[0].get_title().lower()
        assert "no caustic" in title
        assert "marginal rays cross below" not in title
        plt.close(fig)

    def test_aberrated_title_quantifies_the_error_against_that_tolerance(self):
        import matplotlib.pyplot as plt
        fig, _t = self._fig("spherical")
        title = fig.axes[0].get_title().lower()
        assert "marginal rays cross below" in title
        assert "depth of focus" in title   # the yardstick, not a bare mm
        plt.close(fig)

    def test_depth_of_focus_band_is_drawn_in_both_states(self):
        import matplotlib.pyplot as plt
        for primary_type in ("spherical", "parabolic"):
            fig, _t = self._fig(primary_type)
            labels = [t.get_text() for t in fig.axes[0].get_legend().get_texts()]
            assert any("depth of focus" in s.lower() for s in labels), \
                primary_type
            plt.close(fig)


class TestSphericalNarrativeMatchesTheFigures:
    """R5.5a: the description still described a single right-hand plot and an
    inset that R4.7 had already removed."""

    def _scenario(self):
        from telescope_gui.tutorial_mode.scenario_registry import (
            get_scenario_by_id)
        return get_scenario_by_id("spherical_aberration")

    def test_narrative_describes_both_right_hand_panels(self):
        desc = self._scenario().description.lower()
        assert "caustic" in desc
        assert "ray fan" in desc
        assert "top" in desc and "bottom" in desc

    def test_narrative_does_not_promise_a_removed_inset(self):
        desc = self._scenario().description.lower()
        assert "inset" not in desc

    def test_narrative_states_the_axis_and_colour_conventions(self):
        desc = self._scenario().description.lower()
        assert "optical axis" in desc
        assert "blue" in desc and "orange" in desc

    def test_side_label_mentions_both_panels(self):
        label = self._scenario().after_label.lower()
        assert "caustic" in label and "fan" in label



# ------------------------------------------------------------------
# R5.7: square kernel-support ("box around every star") artifacts
# ------------------------------------------------------------------

def _chebyshev_ring(img, cy, cx, r):
    """Values on the square ring max(|dy|, |dx|) == r, or None if off-frame."""
    import numpy as np
    h, w = img.shape
    if cy - r < 0 or cx - r < 0 or cy + r >= h or cx + r >= w:
        return None
    return np.concatenate([
        img[cy - r, cx - r:cx + r + 1],
        img[cy + r, cx - r:cx + r + 1],
        img[cy - r + 1:cy + r, cx - r],
        img[cy - r + 1:cy + r, cx + r],
    ])


def box_score_at(img, cy, cx, r_min=4, floor_frac=3e-5):
    """Score how strongly a SQUARE outline is present around (cy, cx).

    The discriminator is which metric the feature is constant along. A square
    kernel support is flat along a CHEBYSHEV ring and then cliffs to the next
    ring out; an Airy ring is flat along a EUCLIDEAN ring and varies wildly
    along a Chebyshev one, because the corners sit 1.41x further from centre.
    So score = (drop from ring r to ring r+1) / (variation around ring r):
    only a square support scores both terms at once. An earlier attempt that
    compared corner brightness to axis brightness fired on every Airy pattern.
    """
    import numpy as np
    peak = float(img.max())
    if peak <= 0:
        return 0.0
    r_max = min(cy, cx, img.shape[0] - cy - 2, img.shape[1] - cx - 2)
    best = 0.0
    for r in range(r_min, max(r_min + 1, r_max - 1)):
        a = _chebyshev_ring(img, cy, cx, r)
        b = _chebyshev_ring(img, cy, cx, r + 1)
        if a is None or b is None:
            continue
        ma, mb = float(a.mean()), float(b.mean())
        if ma < floor_frac * peak:      # below display visibility
            continue
        cv = float(a.std()) / max(ma, 1e-30)
        if cv > 0.6:                    # not flat -> a ring, not a box edge
            continue
        step = ma / max(mb, 1e-30)
        if step < 2.0:                  # no cliff -> smooth falloff
            continue
        best = max(best, step / max(cv, 0.02))
    return best


def worst_box_score(img, n_peaks=6, min_sep=30):
    """Worst box score over the brightest sources plus the frame centre."""
    import numpy as np
    from scipy.ndimage import maximum_filter
    mx = maximum_filter(img, size=min_sep)
    cand = np.argwhere((img == mx) & (img > 0.05 * img.max()))
    order = np.argsort(img[cand[:, 0], cand[:, 1]])[::-1]
    centres, worst = [], 0.0
    for i in order:
        y, x = int(cand[i, 0]), int(cand[i, 1])
        if any(abs(y - py) < min_sep and abs(x - px) < min_sep
               for py, px in centres):
            continue
        centres.append((y, x))
        if len(centres) >= n_peaks:
            break
    centres.append((img.shape[0] // 2, img.shape[1] // 2))
    for cy, cx in centres:
        worst = max(worst, box_score_at(img, cy, cx))
    return worst


BOX_THRESHOLD = 100.0
"""Above this a square outline is unambiguously present.

Calibrated by `test_detector_fires_on_the_untapered_star_field`: with the taper
removed the coma field scores ~1e27, while the same field rendered with it
scores single digits. A well-sampled Airy ring can reach ~9 (measured on a
300mm f/2 with no seeing), so the threshold sits an order of magnitude above
the worst legitimate feature and far below the artifact.
"""


@pytest.fixture(scope="module")
def _coma_telescope():
    from telescope_gui.telescope_builder import build_telescope
    return build_telescope(telescope_type="Newtonian", diameter=200,
                           focal_length=600, primary_type="parabolic",
                           enable_obstruction=True, obstruction_ratio=0.2,
                           spider_vanes=0)


def _capture_source_image(monkeypatch, telescope, source, **kwargs):
    """Render through plot_source_image and return the array actually drawn."""
    import numpy as np
    import matplotlib.pyplot as plt
    import telescope_sim.plotting.ray_trace_plot as rtp

    captured = {}
    original = rtp._draw_source_on_axes

    def spy(ax, display_image, display_rgb, half_fov, log_scale, colormap,
            fig):
        if "img" not in captured:
            captured["img"] = (None if display_image is None
                               else np.array(display_image))
            captured["rgb"] = (None if display_rgb is None
                               else np.array(display_rgb))
        return original(ax, display_image, display_rgb, half_fov, log_scale,
                        colormap, fig)

    monkeypatch.setattr(rtp, "_draw_source_on_axes", spy)
    figures = rtp.plot_source_image(telescope, source, **kwargs)
    for fig in (figures if isinstance(figures, list) else [figures]):
        plt.close(fig)
    img = captured.get("img")
    if img is None and captured.get("rgb") is not None:
        img = captured["rgb"].max(axis=2)
    return img


class TestCircularTaperRemovesSquareKernelSupport:
    """R5.7: "the stars again seem like they have clear rectangular outlines".

    Root cause: an Airy convolution kernel is a SQUARE crop only ~5 Airy radii
    wide, and the Airy wings fall as r^-3, so the kernel is still ~1e-4 of its
    peak where it stops DISCONTINUOUSLY. Convolution stamps that support onto
    every star and an asinh stretch lifts 1e-4 into visible grey.

    Each pair of tests below first shows the detector FIRING with the taper
    disabled, so the passing assertion is load-bearing rather than vacuous.
    """

    def test_taper_zeroes_the_corners_and_keeps_the_core(self):
        import numpy as np
        from telescope_sim.plotting.ray_trace_plot import _apply_circular_taper
        flat = np.ones((65, 65))
        out = _apply_circular_taper(flat)
        assert out[0, 0] == 0.0 and out[0, -1] == 0.0
        assert out[-1, 0] == 0.0 and out[-1, -1] == 0.0
        # Everything inside 85% of the inscribed radius is untouched.
        assert out[32, 32] == 1.0
        assert out[32, 32 + 20] == 1.0        # 20 < 0.85 * 32
        assert out.min() >= 0.0 and out.max() <= 1.0

    def test_detector_fires_on_the_untapered_star_field(
            self, monkeypatch, _coma_telescope):
        import telescope_sim.plotting.ray_trace_plot as rtp
        from telescope_sim.source.sources import ComaDemoField
        monkeypatch.setattr(rtp, "_apply_circular_taper", lambda k: k)
        img = _capture_source_image(
            monkeypatch, _coma_telescope,
            ComaDemoField(field_radius_arcsec=150.0),
            display_stretch="asinh", apply_coma=True, seeing_arcsec=None)
        assert worst_box_score(img) > BOX_THRESHOLD

    def test_stars_have_no_square_outline(self, monkeypatch, _coma_telescope):
        """Guards the whole-PSF taper on the star path.

        Scope note: this pair is only sensitive to a HARD square edge — it
        needs a >2x cliff between adjacent Chebyshev rings. Measured, it scores
        the same 5.4 with and without the *inner* kernel taper, because that
        square is softened by the convolution. So it does NOT cover the
        off-axis kernel; `test_offaxis_kernel_corners_are_zeroed` does.
        """
        from telescope_sim.source.sources import ComaDemoField
        img = _capture_source_image(
            monkeypatch, _coma_telescope,
            ComaDemoField(field_radius_arcsec=150.0),
            display_stretch="asinh", apply_coma=True, seeing_arcsec=None)
        assert worst_box_score(img) < BOX_THRESHOLD

    @staticmethod
    def _capture_offaxis_kernel(monkeypatch, telescope):
        """The kernel `_compute_psf_at_field_angle` actually convolves with."""
        import scipy.signal
        import telescope_sim.plotting.ray_trace_plot as rtp
        captured = []
        original = scipy.signal.fftconvolve

        def spy(a, b, *args, **kwargs):
            captured.append(b)
            return original(a, b, *args, **kwargs)

        # The function imports fftconvolve locally, so patch it at the source.
        monkeypatch.setattr(scipy.signal, "fftconvolve", spy)
        rtp._compute_psf_at_field_angle(telescope, 60.0, 550.0, 121, 0.05,
                                        True, True)
        assert captured, "no convolution happened on the off-axis path"
        return captured[0]

    def test_untapered_offaxis_kernel_stops_while_still_visible(
            self, monkeypatch, _coma_telescope):
        """Calibration: the square support is real and above visibility.

        An asinh display stretch lifts anything above ~1e-4 of peak into
        visible grey, so a kernel that is still that bright where it stops
        stamps its square outline onto every star it is convolved with.
        """
        import telescope_sim.plotting.ray_trace_plot as rtp
        monkeypatch.setattr(rtp, "_apply_circular_taper", lambda k: k)
        kernel = self._capture_offaxis_kernel(monkeypatch, _coma_telescope)
        peak = kernel.max()
        assert kernel[0, 0] / peak > 1e-4          # corner
        assert kernel[kernel.shape[0] // 2, 0] / peak > 1e-5   # edge midpoint

    def test_offaxis_kernel_corners_are_zeroed(self, monkeypatch,
                                               _coma_telescope):
        """R5.7's actual fix: the off-axis Airy kernel is tapered.

        Verified visually as well — zoomed montages of the coma-demo field
        show square-cornered halos before this and round stars after.
        """
        import numpy as np
        kernel = self._capture_offaxis_kernel(monkeypatch, _coma_telescope)
        n = kernel.shape[0]
        for corner in ((0, 0), (0, n - 1), (n - 1, 0), (n - 1, n - 1)):
            assert kernel[corner] == 0.0
        # The core survives: still normalised, still peaked at the centre.
        assert kernel[n // 2, n // 2] == kernel.max()
        assert np.isclose(kernel.sum(), 1.0)

    @staticmethod
    def _taper_spy(monkeypatch):
        """Record every kernel that goes through the taper, still tapering."""
        import telescope_sim.plotting.ray_trace_plot as rtp
        calls = []
        original = rtp._apply_circular_taper

        def spy(kernel):
            calls.append(kernel.shape)
            return original(kernel)

        monkeypatch.setattr(rtp, "_apply_circular_taper", spy)
        return calls

    def test_coma_spot_diagram_tapers_its_kernel(self, monkeypatch,
                                                 _coma_telescope):
        """plot_coma_spot's kernel is tapered as defence-in-depth.

        No box is VISIBLE in this figure: measured, the box score is 0 with
        the taper both on and off, because the geometric coma comet is far
        wider than the kernel and smears its square edge out. So the guard has
        to be structural — assert the path tapers, not that a box vanished.
        Claiming a behavioural fix here would overstate what was measured.
        """
        import matplotlib.pyplot as plt
        import telescope_sim.plotting.ray_trace_plot as rtp
        calls = self._taper_spy(monkeypatch)
        plt.close(rtp.plot_coma_spot(_coma_telescope, 300.0))
        assert calls, "plot_coma_spot did not taper its Airy kernel"

    def test_focal_image_tapers_its_analytic_kernel(self, monkeypatch):
        """Same situation as plot_coma_spot: structural guard, no visible box.

        Here the geometric spot is ~10x wider than the kernel (measured: RMS
        25.5 um against an 8.5 px kernel half-width), so the square edge never
        survives the convolution.
        """
        import telescope_sim.plotting.ray_trace_plot as rtp
        from telescope_gui.telescope_builder import build_telescope
        spherical = build_telescope(telescope_type="Newtonian", diameter=200,
                                    focal_length=800, primary_type="spherical",
                                    enable_obstruction=False, spider_vanes=0)
        calls = self._taper_spy(monkeypatch)
        rtp._compute_focal_image(spherical, num_pixels=256,
                                 method="analytical")
        assert calls, "_compute_focal_image did not taper its Airy kernel"

    def test_extended_sources_keep_their_spider_spikes(self):
        """The documented exception: tapering the extended-source kernel would
        clip diffraction spikes, which are real and must reach the frame."""
        import numpy as np
        from telescope_gui.telescope_builder import build_telescope
        from telescope_sim.source.sources import Jupiter
        import telescope_sim.plotting.ray_trace_plot as rtp
        spider = build_telescope(telescope_type="Newtonian", diameter=200,
                                 focal_length=1200, primary_type="parabolic",
                                 enable_obstruction=True,
                                 obstruction_ratio=0.25, spider_vanes=4,
                                 spider_vane_width=2.0)
        image, _rgb, info = rtp._render_source_through_telescope(
            Jupiter(), spider, seeing_arcsec=None)
        assert np.isfinite(image).all() and image.max() > 0


class TestAnnotationBoxesStayInsideTheirAxes:
    """Batch P: the source-image info box and title both overran the axes.

    Seen in a real GUI capture of the coma module: the info box's long lines
    ("Display: asinh stretch (boosts dim features; data unchanged)") ran out
    past the right axis edge, and the one-line title ran under the colourbar
    ("...f/3.0 Para|bolic"). Both are now wrapped.
    """

    def _figure(self, **kwargs):
        import matplotlib.pyplot as plt
        from telescope_gui.telescope_builder import build_telescope
        from telescope_sim.plotting.ray_trace_plot import plot_source_image
        from telescope_sim.source.sources import ComaDemoField
        telescope = build_telescope(telescope_type="Newtonian", diameter=200,
                                    focal_length=600, primary_type="parabolic",
                                    enable_obstruction=True,
                                    obstruction_ratio=0.2, spider_vanes=0)
        fig = plot_source_image(telescope,
                                ComaDemoField(field_radius_arcsec=150.0),
                                seeing_arcsec=1.5, **kwargs)
        fig.canvas.draw()
        try:
            yield_fig = fig
            return yield_fig
        finally:
            pass

    def test_wrap_preserves_content_and_bounds_the_width(self):
        from telescope_sim.plotting.ray_trace_plot import (
            _wrap_annotation, _ANNOTATION_WIDTH)
        lines = [
            "FOV: 300\" x 300\"",
            "Eye view (perceptual): exposure N/A - star brightness is "
            "proportional to aperture squared (until it saturates)",
            "  (concentric rings = Airy diffraction pattern; atmosphere "
            "normally blurs them)",
        ]
        out = _wrap_annotation(lines)
        assert all(len(ln) <= _ANNOTATION_WIDTH for ln in out.split("\n"))
        # No word is lost or mangled.
        assert " ".join(out.split()) == " ".join(" ".join(lines).split())
        # A sub-note stays visually subordinate to the line above it.
        wrapped_sub = [ln for ln in out.split("\n") if "concentric" in ln][0]
        assert wrapped_sub.startswith("  ")

    def test_info_box_does_not_overrun_the_axes(self):
        import matplotlib.pyplot as plt
        fig = self._figure(display_stretch="log_integrated")
        ax = fig.axes[0]
        boxes = [t for t in ax.texts if t.get_bbox_patch() is not None]
        assert boxes, "the source image lost its info box"
        ax_bb = ax.get_window_extent()
        for t in boxes:
            assert t.get_window_extent().x1 <= ax_bb.x1 + 2.0
        plt.close(fig)

    def test_title_does_not_overrun_the_axes(self):
        import matplotlib.pyplot as plt
        fig = self._figure()
        ax = fig.axes[0]
        title = ax.title
        assert title.get_text()
        ax_bb = ax.get_window_extent()
        tb = title.get_window_extent()
        assert tb.x0 >= ax_bb.x0 - 2.0 and tb.x1 <= ax_bb.x1 + 2.0
        plt.close(fig)


class TestComaReferenceCircleLabelsDoNotCollide:
    """Batch P: at f/3, cff is 2.1" in a +/-150" frame, so the old NE-diagonal
    placement dropped "cff = 2.1"" straight onto the "0"" and "30"" star
    labels. Both circle labels now go below the axis, where the stars aren't.
    """

    def _overlay_figure(self):
        import matplotlib.pyplot as plt
        from telescope_gui.telescope_builder import build_telescope
        from telescope_gui.tutorial_mode.theory_computations import (
            _coma_starfield_overlay)
        from telescope_sim.plotting.ray_trace_plot import plot_source_image
        from telescope_sim.source.sources import ComaDemoField
        telescope = build_telescope(telescope_type="Newtonian", diameter=200,
                                    focal_length=600, primary_type="parabolic",
                                    enable_obstruction=True,
                                    obstruction_ratio=0.2, spider_vanes=0)
        fig = plot_source_image(telescope,
                                ComaDemoField(field_radius_arcsec=150.0),
                                seeing_arcsec=1.5)
        _coma_starfield_overlay(fig, {}, telescope)
        fig.canvas.draw()
        return fig, plt

    def test_circle_labels_do_not_overlap_the_star_labels(self):
        fig, plt = self._overlay_figure()
        ax = fig.axes[0]
        circle_labels, star_labels = [], []
        for t in ax.texts:
            text = t.get_text()
            if "cff" in text:
                circle_labels.append(t)
            elif text.endswith("″"):
                star_labels.append(t)
        assert len(circle_labels) == 2 and star_labels
        for c in circle_labels:
            for s in star_labels:
                assert not c.get_window_extent().overlaps(
                    s.get_window_extent()), (
                    f"{c.get_text()!r} overlaps {s.get_text()!r}")
        plt.close(fig)

    def test_circle_labels_stay_inside_the_axes(self):
        fig, plt = self._overlay_figure()
        ax = fig.axes[0]
        ax_bb = ax.get_window_extent()
        for t in ax.texts:
            if "cff" not in t.get_text():
                continue
            tb = t.get_window_extent()
            assert tb.y0 >= ax_bb.y0 - 2.0 and tb.x0 >= ax_bb.x0 - 2.0
        plt.close(fig)

    def test_circle_labels_clear_the_stars_themselves(self):
        """The stars, not just their text labels.

        The first below-axis placement put each label at its own circle's
        radius. At f/3 the cff circle is 2.1″ inside a ±150″ frame, so
        "cff = 2.1″" landed on top of the central star it describes — and
        10× cff, only 18″ further down, landed on top of *that*.
        """
        fig, plt = self._overlay_figure()
        ax = fig.axes[0]
        circle_labels = [t for t in ax.texts if "cff" in t.get_text()]
        assert len(circle_labels) == 2
        # The stars all sit on y = 0 in data coordinates, and their own
        # labels stand 4 % of the y-span above them. Require at least that
        # much clearance below — a label 2″ under the axis is nominally
        # "below the stars" and still drawn on top of them.
        star_row_px = ax.transData.transform((0.0, 0.0))[1]
        clearance = 0.04 * ax.get_window_extent().height
        for t in circle_labels:
            tb = t.get_window_extent()
            assert tb.y1 < star_row_px - clearance, (
                f"{t.get_text()!r} is drawn on the stars "
                f"(top {tb.y1:.1f} px, needs to clear "
                f"{star_row_px - clearance:.1f} px)")
        a, b = (t.get_window_extent() for t in circle_labels)
        assert not a.overlaps(b), "the two circle labels overlap each other"
        plt.close(fig)


class TestMetricsPanelFitsItsAxes:
    """R5.7 sweep fallout: the PSF-profile side panel overran the FIGURE.

    `plot_psf_profile`'s metrics block is monospace at fontsize 9 and ~218 px
    wide; the panel it sits in was 124 px of a 500 px tutorial canvas, so 50 px
    fell off the right-hand edge of the figure and was clipped away — the user
    lost the right ~23 % of every metrics line on the two Act-1 modules that
    use this figure. All four formula lines overran the panel too.
    """

    @staticmethod
    def _profile_figure(**kwargs):
        import matplotlib.pyplot as plt
        from telescope_gui.telescope_builder import build_telescope
        from telescope_sim.plotting.ray_trace_plot import plot_psf_profile
        params = dict(telescope_type="Newtonian", diameter=200,
                      focal_length=1000, primary_type="parabolic",
                      enable_obstruction=True, obstruction_ratio=0.3,
                      spider_vanes=0)
        params.update(kwargs)
        telescope = build_telescope(**params)
        # figsize/log_scale as the tutorial tab drives it.
        fig = plot_psf_profile(telescope, figsize=(5, 5), log_scale=True)
        fig.canvas.draw()
        return fig, plt

    @staticmethod
    def _panel(fig):
        """The axis-off metrics/formula panel."""
        for ax in fig.axes:
            if not ax.axison and ax.texts:
                return ax
        raise AssertionError("no metrics panel found")

    def test_metrics_block_stays_inside_the_figure(self):
        fig, plt = self._profile_figure()
        fig_right = fig.get_window_extent().x1
        panel = self._panel(fig)
        boxed = [t for t in panel.texts if t.get_bbox_patch() is not None]
        assert boxed, "metrics box not found"
        for t in boxed:
            tb = t.get_window_extent()
            assert tb.x1 <= fig_right, (
                f"metrics box is clipped by the figure edge "
                f"({tb.x1 - fig_right:.0f} px lost)")
        plt.close(fig)

    def test_every_panel_text_stays_inside_the_panel(self):
        fig, plt = self._profile_figure()
        panel = self._panel(fig)
        panel_bb = panel.get_window_extent()
        for t in panel.texts:
            tb = t.get_window_extent()
            assert tb.x1 <= panel_bb.x1 + 1.0, (
                f"{t.get_text().splitlines()[0]!r} overruns the panel by "
                f"{tb.x1 - panel_bb.x1:.0f} px")
        plt.close(fig)

    def test_char_budget_tracks_the_panel_width(self):
        """The wrap width is measured, not hard-coded.

        A hard-coded width fits one figsize and clips at every other, which
        is how the original box came to be 218 px wide in a 124 px panel.
        """
        import matplotlib.pyplot as plt
        from telescope_sim.plotting.ray_trace_plot import _panel_char_budget
        fig = plt.figure(figsize=(5, 5))
        narrow = fig.add_axes((0.0, 0.0, 0.2, 1.0))
        wide = fig.add_axes((0.0, 0.0, 0.6, 1.0))
        assert (_panel_char_budget(wide, 8.0)
                > 2 * _panel_char_budget(narrow, 8.0))
        # Smaller type fits more characters in the same panel.
        assert _panel_char_budget(wide, 6.0) > _panel_char_budget(wide, 8.0)
        plt.close(fig)

    def test_single_panel_mode_has_no_title_under_the_suptitle(self):
        """The panel title is only meaningful as one of a contrasting pair.

        Alone it is redundant (the y-label already names the scale) and the
        secondary top axis pushes it up into the suptitle, where the two
        overprinted — "Log scale" written through "Point Spread Function".
        """
        fig, plt = self._profile_figure()
        sup = fig._suptitle
        assert sup is not None and sup.get_text()
        sup_bb = sup.get_window_extent()
        for ax in fig.axes:
            if not ax.title.get_text():
                continue
            assert not sup_bb.overlaps(ax.title.get_window_extent()), (
                f"{ax.title.get_text()!r} overprints the suptitle")
        plt.close(fig)


class TestStrehlOnlyWhereItApplies:
    """R4.4b — 'Airy disc seems to have Strehl/obstruction formulas that
    don't belong there.'

    It did. `plot_psf_profile` printed the Strehl metric and the Marechal
    formula unconditionally, so a perfect parabola with obstruction disabled
    reported "Strehl ≈ 1.000" and a formula in σ and r₁ that the Airy module
    never introduces. The earlier round could not reproduce it because it
    checked the theory readout and the scenario overlays — the offending text
    is inside this figure's own metrics/formula panel.
    """

    @staticmethod
    def _panel_text(**kwargs):
        import matplotlib.pyplot as plt
        from telescope_gui.telescope_builder import build_telescope
        from telescope_sim.plotting.ray_trace_plot import plot_psf_profile
        params = dict(telescope_type="Newtonian", diameter=200,
                      focal_length=1000, primary_type="parabolic",
                      enable_obstruction=False, obstruction_ratio=0.0,
                      spider_vanes=0)
        params.update(kwargs)
        include = params.pop("include_obstruction", True)
        fig = plot_psf_profile(build_telescope(**params), figsize=(5, 5),
                               log_scale=True,
                               include_obstruction=include)
        text = "\n".join(t.get_text() for ax in fig.axes for t in ax.texts)
        plt.close(fig)
        return text

    def test_perfect_unobstructed_optics_show_no_strehl(self):
        text = self._panel_text(include_obstruction=False)
        assert "Strehl" not in text, (
            "Strehl has nothing to say about a perfect unobstructed "
            f"aperture:\n{text}")
        # The Airy content it SHOULD carry is still there.
        assert "Airy radius" in text and "Rayleigh" in text

    def test_obstruction_brings_strehl_back(self):
        text = self._panel_text(enable_obstruction=True,
                                obstruction_ratio=0.3)
        assert "Strehl" in text, (
            "a 30 % obstruction costs real Strehl — the metric belongs here")
        assert "(1-ε²)²" in text

    def test_an_aberrated_primary_brings_strehl_back(self):
        text = self._panel_text(primary_type="spherical",
                                include_obstruction=False)
        assert "Strehl" in text, (
            "a spherical primary has a real Strehl deficit")

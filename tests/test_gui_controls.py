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

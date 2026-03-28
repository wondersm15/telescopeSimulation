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

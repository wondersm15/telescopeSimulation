"""Tests for the single-mode Design tab and Comparison Images tab image path.

Regression guard for the "Jupiter is completely washed out" bug: the Design
and Comparison tabs called `plot_source_image` with the library defaults
(Detector view, exposure 1.0). For any aperture above 100 mm that saturates
every extended source, and neither tab had a control to change it. The
Tutorial tab never exercised those defaults, so its validation could not
catch the problem.

These tests drive the real widgets and spy on the real render, so they fail
if a tab stops forwarding the shared `ImageDisplayControls` settings.
"""

import numpy as np
import pytest

from PyQt6.QtWidgets import QApplication

import telescope_sim.plotting.ray_trace_plot as rtp
from telescope_sim.plotting.ray_trace_plot import (
    EYE_PUPIL_MM,
    SATURATION_LEVEL,
    resolve_exit_pupil_mm,
    saturated_area_fraction,
    _saturation_warning_text,
)
from telescope_sim.geometry.eyepiece import Eyepiece
from telescope_gui.widgets.display_controls import (
    DEFAULT_EXIT_PUPIL_MM,
    ImageDisplayControls,
    exposure_to_slider,
    slider_to_exposure,
)


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def render_spy(monkeypatch):
    """Record the `info` dict of every real render.

    `plot_source_image` looks `_render_source_through_telescope` up as a
    module global, so patching the module attribute intercepts every caller
    (Design, Comparison and Tutorial alike) without changing the result.
    """
    infos = []
    real_render = rtp._render_source_through_telescope

    def spy(*args, **kwargs):
        result = real_render(*args, **kwargs)
        infos.append(result[2])
        return result

    monkeypatch.setattr(rtp, "_render_source_through_telescope", spy)
    return infos


# ------------------------------------------------------------------
# Pure helpers
# ------------------------------------------------------------------

class TestResolveExitPupil:
    def test_default_is_naked_eye_pupil(self):
        assert resolve_exit_pupil_mm(telescope=None) == EYE_PUPIL_MM

    def test_explicit_value_used_without_eyepiece(self):
        assert resolve_exit_pupil_mm(telescope=None, exit_pupil_mm=2.0) == 2.0

    def test_eyepiece_overrides_explicit_value(self):
        """With an eyepiece the exit pupil is derived (D / magnification),
        never chosen: a stale combo value must not leak through."""
        class Scope:
            primary_diameter = 200.0
            focal_length = 1000.0
        eyepiece = Eyepiece(focal_length_mm=25.0)
        expected = eyepiece.exit_pupil_mm(200.0, 1000.0)
        assert expected == pytest.approx(5.0)
        assert resolve_exit_pupil_mm(Scope(), eyepiece, 0.5) == expected


class TestSaturatedAreaFraction:
    def test_blank_image_is_zero(self):
        assert saturated_area_fraction(np.zeros((8, 8))) == 0.0

    def test_unclipped_disc_is_zero(self):
        img = np.zeros((10, 10))
        img[2:8, 2:8] = 0.9 * SATURATION_LEVEL
        assert saturated_area_fraction(img) == 0.0

    def test_fraction_measured_over_object_not_frame(self):
        """Dark sky must not dilute the fraction: half the object clipped
        reads 50 % however much empty frame surrounds it."""
        img = np.zeros((100, 100))
        img[0:2, 0:4] = SATURATION_LEVEL
        img[2:4, 0:4] = 0.5 * SATURATION_LEVEL
        assert saturated_area_fraction(img) == pytest.approx(0.5)

    def test_rgb_uses_brightest_channel(self):
        img = np.zeros((4, 4, 3))
        img[..., 0] = SATURATION_LEVEL  # red channel clipped everywhere
        img[..., 1] = 0.2
        assert saturated_area_fraction(img) == 1.0


class TestSaturationWarningText:
    def test_silent_below_threshold(self):
        assert _saturation_warning_text({"saturated_fraction": 0.0}) is None
        assert _saturation_warning_text({}) is None

    def test_detector_remedy_mentions_exposure(self):
        text = _saturation_warning_text(
            {"saturated_fraction": 0.89, "is_eye_view": False})
        assert "89%" in text and "Exposure" in text

    def test_eye_remedy_does_not_mention_exposure(self):
        """Exposure is disabled in Eye view, so suggesting it is useless."""
        text = _saturation_warning_text(
            {"saturated_fraction": 0.5, "is_eye_view": True})
        assert "Exposure" not in text and "exit pupil" in text


# ------------------------------------------------------------------
# Shared display-controls widget
# ------------------------------------------------------------------

class TestImageDisplayControls:
    def test_defaults_are_eye_view(self, qapp):
        controls = ImageDisplayControls()
        kwargs = controls.plot_kwargs()
        assert kwargs["display_stretch"] == "log"
        assert kwargs["exit_pupil_mm"] == DEFAULT_EXIT_PUPIL_MM
        assert controls.filter_name() == "None"
        assert not controls.exposure_slider.isEnabled()

    def test_detector_view_enables_exposure(self, qapp):
        controls = ImageDisplayControls()
        controls.view_combo.setCurrentIndex(
            controls.view_combo.findData("linear"))
        assert controls.exposure_slider.isEnabled()
        assert not controls.exit_pupil_combo.isEnabled()

    def test_exposure_slider_round_trip(self):
        for exposure in (0.1, 0.25, 1.0, 4.0):
            assert slider_to_exposure(exposure_to_slider(exposure)) == \
                pytest.approx(exposure, rel=0.05)

    def test_stars_disable_exit_pupil(self, qapp):
        controls = ImageDisplayControls()
        controls.set_context(is_extended_source=False,
                             eyepiece_exit_pupil_mm=None)
        assert not controls.exit_pupil_combo.isEnabled()
        assert "Stars" in controls.exit_pupil_note.text()

    def test_eyepiece_locks_exit_pupil(self, qapp):
        controls = ImageDisplayControls()
        controls.set_context(is_extended_source=True,
                             eyepiece_exit_pupil_mm=5.0)
        assert not controls.exit_pupil_combo.isEnabled()
        assert "5.0 mm" in controls.exit_pupil_note.text()


# ------------------------------------------------------------------
# Design tab end to end
# ------------------------------------------------------------------

@pytest.fixture
def design_tab(qapp):
    from telescope_gui.single_mode.design_tab import DesignTab
    return DesignTab()


class TestDesignTabNotWashedOut:
    @pytest.mark.parametrize("source_name", ["Jupiter", "Saturn", "Moon"])
    def test_defaults_do_not_saturate(self, design_tab, render_spy,
                                      source_name):
        """The original bug: at the tab's defaults the planet clipped to a
        white disc (89 % of Jupiter at 200 mm). Fails if the tab stops
        passing the display controls to `plot_source_image`."""
        design_tab.source_combo.setCurrentText(source_name)
        design_tab.update_view()
        info = render_spy[-1]
        assert info["display_stretch"] == "log"
        assert info["saturated_fraction"] < rtp.SATURATION_WARNING_FRACTION

    def test_detector_view_at_unit_exposure_flags_saturation(
            self, design_tab, render_spy):
        """Detector view at exposure 1.0 through 200 mm still saturates —
        that is real — but now the figure says so."""
        controls = design_tab.display_controls
        controls.view_combo.setCurrentIndex(
            controls.view_combo.findData("linear"))
        design_tab.source_combo.setCurrentText("Jupiter")
        design_tab.update_view()
        assert _saturation_warning_text(render_spy[-1]) is not None

    def test_exposure_control_reaches_render(self, design_tab, render_spy):
        controls = design_tab.display_controls
        controls.view_combo.setCurrentIndex(
            controls.view_combo.findData("linear"))
        controls.exposure_slider.setValue(exposure_to_slider(0.25))
        design_tab.source_combo.setCurrentText("Jupiter")
        design_tab.update_view()
        assert render_spy[-1]["saturated_fraction"] == 0.0

    def test_eyepiece_drives_eye_view_exit_pupil(self, design_tab,
                                                 render_spy):
        """The eyepiece used to set the washout but not the surface
        brightness, so the two used different exit pupils."""
        design_tab.source_combo.setCurrentText("Jupiter")
        design_tab.eyepiece_check.setChecked(True)
        design_tab.eyepiece_spin.setValue(25.0)
        telescope = design_tab.telescope_panel.build()
        expected = Eyepiece(focal_length_mm=25.0).exit_pupil_mm(
            telescope.primary_diameter, telescope.focal_length)
        design_tab.update_view()
        assert render_spy[-1]["exit_pupil_mm"] == pytest.approx(expected)
        assert f"{expected:.1f} mm" in \
            design_tab.display_controls.exit_pupil_note.text()

    def test_star_source_disables_exit_pupil(self, design_tab):
        design_tab.source_combo.setCurrentText("Point Source (Star)")
        assert not design_tab.display_controls.exit_pupil_combo.isEnabled()


class TestComparisonImagesTab:
    def test_both_panels_use_display_controls(self, qapp, render_spy):
        from telescope_gui.comparison_mode.images_tab import ImagesTab
        tab = ImagesTab()
        tab.source_combo.setCurrentText("Jupiter")
        tab.update_view()
        assert len(render_spy) >= 2  # at least one render per panel
        for info in render_spy:
            assert info["display_stretch"] == "log"
            assert info["saturated_fraction"] < \
                rtp.SATURATION_WARNING_FRACTION

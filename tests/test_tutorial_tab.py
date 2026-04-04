"""Tests for the Tutorial & Testing tab components.

Covers:
- DoubleStar source rendering
- Scenario registry structure and integrity
- Theory computation functions
- Scenario runner (rendering + theory)
- apply_coma / apply_vignetting toggle parameters
"""

import numpy as np
import pytest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# DoubleStar source
# ---------------------------------------------------------------------------

class TestDoubleStar:
    def test_renders_two_peaks(self):
        from telescope_sim.source.sources import DoubleStar
        ds = DoubleStar(separation_arcsec=2.0)
        img = ds.render_ideal(half_fov_arcsec=10.0, num_pixels=100)
        assert img.shape == (100, 100)
        # Two non-zero pixels
        nonzero = np.count_nonzero(img)
        assert nonzero == 2

    def test_normalized_to_one(self):
        from telescope_sim.source.sources import DoubleStar
        ds = DoubleStar(separation_arcsec=1.0)
        img = ds.render_ideal(half_fov_arcsec=10.0, num_pixels=100)
        assert pytest.approx(img.max(), abs=1e-9) == 1.0

    def test_field_extent_minimum(self):
        from telescope_sim.source.sources import DoubleStar
        ds = DoubleStar(separation_arcsec=0.5)
        assert ds.field_extent_arcsec >= 10.0

    def test_field_extent_scales_with_separation(self):
        from telescope_sim.source.sources import DoubleStar
        ds = DoubleStar(separation_arcsec=20.0)
        assert ds.field_extent_arcsec == pytest.approx(200.0)

    def test_magnitude_ratio(self):
        from telescope_sim.source.sources import DoubleStar
        # Primary brighter (mag 0) vs secondary (mag 2.5 = 10x dimmer)
        ds = DoubleStar(separation_arcsec=4.0, magnitude_primary=0.0,
                        magnitude_secondary=2.5)
        img = ds.render_ideal(half_fov_arcsec=20.0, num_pixels=200)
        nonzero_vals = img[img > 0]
        assert len(nonzero_vals) == 2
        assert nonzero_vals.max() == pytest.approx(1.0)
        ratio = nonzero_vals.max() / nonzero_vals.min()
        assert ratio == pytest.approx(10.0 ** (0.4 * 2.5), rel=0.01)

    def test_exported_from_source_init(self):
        from telescope_sim.source import DoubleStar
        ds = DoubleStar()
        assert ds.separation_arcsec == 1.0


# ---------------------------------------------------------------------------
# Scenario registry
# ---------------------------------------------------------------------------

class TestScenarioRegistry:
    def test_thirteen_scenarios_total(self):
        from telescope_gui.tutorial_mode.scenario_registry import SCENARIOS
        assert len(SCENARIOS) == 13

    def test_acts_populated(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenarios_by_act
        by_act = get_scenarios_by_act()
        assert len(by_act[1]) == 6
        assert len(by_act[2]) == 4
        assert len(by_act[3]) == 3

    def test_five_implemented(self):
        from telescope_gui.tutorial_mode.scenario_registry import SCENARIOS
        implemented = [s for s in SCENARIOS if s.implemented]
        assert len(implemented) == 5
        ids = {s.id for s in implemented}
        assert ids == {"airy_disk", "central_obstruction", "aperture_vs_seeing",
                       "fratio_coma", "jupiter_full"}

    def test_get_scenario_by_id(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        s = get_scenario_by_id("airy_disk")
        assert s is not None
        assert s.title == "Airy Disk"

    def test_get_nonexistent_returns_none(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        assert get_scenario_by_id("nonexistent") is None

    def test_get_first_implemented(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_first_implemented
        first = get_first_implemented()
        assert first is not None
        assert first.implemented is True

    def test_all_implemented_have_terminal_template(self):
        from telescope_gui.tutorial_mode.scenario_registry import SCENARIOS
        for s in SCENARIOS:
            if s.implemented:
                assert s.terminal_template, f"{s.id} has no terminal template"

    def test_all_scenarios_have_before_after(self):
        from telescope_gui.tutorial_mode.scenario_registry import SCENARIOS
        for s in SCENARIOS:
            assert s.before_telescope is not None
            assert s.after_telescope is not None
            assert s.before_source is not None
            assert s.after_source is not None


# ---------------------------------------------------------------------------
# Theory computations
# ---------------------------------------------------------------------------

class TestTheoryComputations:
    @pytest.fixture
    def telescope_200mm(self):
        from telescope_sim.geometry import NewtonianTelescope
        return NewtonianTelescope(200.0, 1000.0, enable_obstruction=False)

    def test_airy_disk_formula(self, telescope_200mm):
        from telescope_gui.tutorial_mode.theory_computations import compute_airy_disk_theory
        result = compute_airy_disk_theory(telescope_200mm, wavelength_nm=550.0)
        # theta = 1.22 * 550e-9 / 0.2 * 206265 = 0.692 arcsec
        assert result["theory_value"] == pytest.approx(0.692, rel=0.01)
        assert result["unit"] == "arcsec"
        assert result["label"] == "Airy radius"

    def test_airy_disk_scales_with_aperture(self, telescope_200mm):
        from telescope_gui.tutorial_mode.theory_computations import compute_airy_disk_theory
        from telescope_sim.geometry import NewtonianTelescope
        t400 = NewtonianTelescope(400.0, 2000.0, enable_obstruction=False)
        r200 = compute_airy_disk_theory(telescope_200mm)["theory_value"]
        r400 = compute_airy_disk_theory(t400)["theory_value"]
        assert r200 == pytest.approx(2 * r400, rel=0.01)

    def test_central_obstruction_no_obstruction(self, telescope_200mm):
        from telescope_gui.tutorial_mode.theory_computations import compute_central_obstruction_theory
        result = compute_central_obstruction_theory(telescope_200mm, obstruction_ratio=0.0)
        assert result["theory_value"] == pytest.approx(1.0)

    def test_central_obstruction_30_percent(self, telescope_200mm):
        from telescope_gui.tutorial_mode.theory_computations import compute_central_obstruction_theory
        result = compute_central_obstruction_theory(telescope_200mm, obstruction_ratio=0.30)
        # (1 - 0.09)^2 = 0.8281
        assert result["theory_value"] == pytest.approx((1 - 0.09) ** 2, rel=0.001)

    def test_aperture_vs_seeing_seeing_limited(self, telescope_200mm):
        from telescope_gui.tutorial_mode.theory_computations import compute_aperture_vs_seeing_theory
        result = compute_aperture_vs_seeing_theory(
            telescope_200mm, seeing_arcsec=2.5, wavelength_nm=550.0)
        assert result["is_seeing_limited"] is True
        assert result["theory_value"] == pytest.approx(2.5)

    def test_aperture_vs_seeing_diffraction_limited(self):
        from telescope_gui.tutorial_mode.theory_computations import compute_aperture_vs_seeing_theory
        from telescope_sim.geometry import NewtonianTelescope
        # Small aperture: diffraction limit > 2.5" seeing
        t = NewtonianTelescope(50.0, 250.0, enable_obstruction=False)
        result = compute_aperture_vs_seeing_theory(
            t, seeing_arcsec=0.1, wavelength_nm=550.0)
        assert result["is_seeing_limited"] is False

    def test_coma_fratio_theory_returns_positive(self, telescope_200mm):
        from telescope_gui.tutorial_mode.theory_computations import compute_coma_fratio_theory
        result = compute_coma_fratio_theory(telescope_200mm)
        assert result["theory_value"] > 0
        assert result["unit"] == "arcsec"

    def test_theory_functions_registry_complete(self):
        from telescope_gui.tutorial_mode.theory_computations import THEORY_FUNCTIONS
        from telescope_gui.tutorial_mode.scenario_registry import SCENARIOS
        for s in SCENARIOS:
            if s.theory_function is not None:
                assert s.theory_function in THEORY_FUNCTIONS, (
                    f"Scenario {s.id} references unknown theory function {s.theory_function!r}")


# ---------------------------------------------------------------------------
# Scenario runner
# ---------------------------------------------------------------------------

class TestScenarioRunner:
    def test_run_airy_disk_before(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("airy_disk")
        fig, info, err = run_scenario_side(
            s.before_telescope, s.before_source, s.plot_function)
        assert err is None
        assert fig is not None
        plt.close(fig)

    def test_run_central_obstruction_after(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("central_obstruction")
        fig, info, err = run_scenario_side(
            s.after_telescope, s.after_source, s.plot_function)
        assert err is None
        plt.close(fig)

    def test_run_aperture_vs_seeing(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("aperture_vs_seeing")
        fig, info, err = run_scenario_side(
            s.after_telescope, s.after_source, s.plot_function,
            seeing_arcsec=s.after_seeing_arcsec)
        assert err is None
        plt.close(fig)

    def test_run_fratio_coma(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("fratio_coma")
        fig, info, err = run_scenario_side(
            s.after_telescope, s.after_source, s.plot_function)
        assert err is None
        plt.close(fig)

    def test_run_jupiter_full(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("jupiter_full")
        fig, info, err = run_scenario_side(
            s.after_telescope, s.after_source, s.plot_function,
            seeing_arcsec=s.after_seeing_arcsec)
        assert err is None
        plt.close(fig)

    def test_build_terminal_command(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import build_terminal_command
        s = get_scenario_by_id("airy_disk")
        cmd = build_terminal_command(s, {
            "diameter": 200.0, "focal_length": 1000.0,
            "wavelength_nm": 550.0, "telescope_type": "Newtonian",
            "enable_obstruction": False,
        })
        assert "NewtonianTelescope" in cmd
        assert "200.0" in cmd


# ---------------------------------------------------------------------------
# apply_coma / apply_vignetting toggles
# ---------------------------------------------------------------------------

class TestEffectToggles:
    @pytest.fixture
    def telescope_and_source(self):
        from telescope_sim.geometry import NewtonianTelescope
        from telescope_sim.source.sources import PointSource
        t = NewtonianTelescope(200.0, 1000.0, enable_obstruction=False)
        s = PointSource(field_angle_arcsec=60.0)
        return t, s

    def test_apply_coma_false_returns_symmetric_psf(self, telescope_and_source):
        """With apply_coma=False, off-axis PSF should be diffraction-only (on-axis)."""
        from telescope_sim.plotting import plot_source_image
        t, s = telescope_and_source
        fig_coma = plot_source_image(t, s, apply_coma=True)
        fig_no_coma = plot_source_image(t, s, apply_coma=False)
        # Both should render without error
        assert fig_coma is not None
        assert fig_no_coma is not None
        plt.close(fig_coma)
        plt.close(fig_no_coma)

    def test_apply_vignetting_false(self, telescope_and_source):
        """apply_vignetting=False should render without error."""
        from telescope_sim.plotting import plot_source_image
        t, s = telescope_and_source
        fig = plot_source_image(t, s, apply_vignetting=False)
        assert fig is not None
        plt.close(fig)

    def test_defaults_unchanged(self, telescope_and_source):
        """Existing calls without the new params should still work (defaults=True)."""
        from telescope_sim.plotting import plot_source_image
        t, _ = telescope_and_source
        from telescope_sim.source.sources import PointSource
        s = PointSource()  # on-axis
        fig = plot_source_image(t, s)
        assert fig is not None
        plt.close(fig)

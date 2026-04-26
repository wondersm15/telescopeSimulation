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
    def test_fourteen_scenarios_total(self):
        from telescope_gui.tutorial_mode.scenario_registry import SCENARIOS
        assert len(SCENARIOS) == 14

    def test_acts_populated(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenarios_by_act
        by_act = get_scenarios_by_act()
        assert len(by_act[1]) == 7
        assert len(by_act[2]) == 4
        assert len(by_act[3]) == 3

    def test_all_scenarios_implemented(self):
        from telescope_gui.tutorial_mode.scenario_registry import SCENARIOS
        implemented = [s for s in SCENARIOS if s.implemented]
        assert len(implemented) == 14
        ids = {s.id for s in implemented}
        assert ids == {
            "airy_disk", "rayleigh_criterion", "central_obstruction",
            "spider_vanes", "chromatic_aberration", "vignetting",
            "spherical_aberration",
            "obstruction_plus_spiders", "chromatic_plus_seeing",
            "aperture_vs_seeing", "fratio_coma",
            "jupiter_full", "saturn_rings", "starfield_resolution",
        }

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

    def test_vignetting_theory_returns_positive(self):
        from telescope_gui.tutorial_mode.theory_computations import compute_vignetting_theory
        from telescope_gui.telescope_builder import build_telescope
        t = build_telescope("Newtonian", 200.0, 1000.0, obstruction_ratio=0.20,
                            enable_obstruction=True)
        result = compute_vignetting_theory(t)
        assert result["theory_value"] > 0
        assert result["unit"] == "arcsec"
        assert result["label"] == "Fully illuminated field"

    def test_spherical_aberration_theory_spherical(self):
        from telescope_gui.tutorial_mode.theory_computations import (
            compute_spherical_aberration_theory)
        from telescope_gui.telescope_builder import build_telescope
        t = build_telescope("Newtonian", 200.0, 800.0, primary_type="spherical",
                            enable_obstruction=False)
        result = compute_spherical_aberration_theory(t)
        assert result["theory_value"] > 0
        assert result["unit"] == "arcsec"

    def test_spherical_aberration_theory_parabolic_is_zero(self):
        from telescope_gui.tutorial_mode.theory_computations import (
            compute_spherical_aberration_theory)
        from telescope_gui.telescope_builder import build_telescope
        t = build_telescope("Newtonian", 200.0, 800.0, primary_type="parabolic",
                            enable_obstruction=False)
        result = compute_spherical_aberration_theory(t)
        assert result["theory_value"] == 0.0

    def test_spherical_aberration_scales_with_fratio(self):
        from telescope_gui.tutorial_mode.theory_computations import (
            compute_spherical_aberration_theory)
        from telescope_gui.telescope_builder import build_telescope
        t_f4 = build_telescope("Newtonian", 200.0, 800.0, primary_type="spherical",
                               enable_obstruction=False)
        t_f8 = build_telescope("Newtonian", 200.0, 1600.0, primary_type="spherical",
                               enable_obstruction=False)
        sa_f4 = compute_spherical_aberration_theory(t_f4)["theory_value"]
        sa_f8 = compute_spherical_aberration_theory(t_f8)["theory_value"]
        # Blur ∝ D³/f³ — f/4 → f/8 doubles f, so blur should be ~8× less
        assert sa_f4 / sa_f8 == pytest.approx(8.0, rel=0.01)

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

    def test_run_rayleigh_criterion(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("rayleigh_criterion")
        fig, info, err = run_scenario_side(
            s.after_telescope, s.after_source, s.plot_function)
        assert err is None
        plt.close(fig)

    def test_run_spider_vanes(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("spider_vanes")
        fig, info, err = run_scenario_side(
            s.after_telescope, s.after_source, s.plot_function)
        assert err is None
        plt.close(fig)

    def test_run_chromatic_aberration(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("chromatic_aberration")
        fig, info, err = run_scenario_side(
            s.after_telescope, s.after_source, s.plot_function,
            polychromatic=s.after_polychromatic)
        assert err is None
        plt.close(fig)

    def test_run_vignetting(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("vignetting")
        fig, info, err = run_scenario_side(
            s.after_telescope, s.after_source, s.plot_function)
        assert err is None
        plt.close(fig)

    def test_run_vignetting_before_no_vignetting(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("vignetting")
        fig, info, err = run_scenario_side(
            s.before_telescope, s.before_source, s.plot_function,
            apply_vignetting=False)
        assert err is None
        plt.close(fig)

    def test_run_obstruction_plus_spiders(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("obstruction_plus_spiders")
        fig, info, err = run_scenario_side(
            s.after_telescope, s.after_source, s.plot_function)
        assert err is None
        plt.close(fig)

    def test_run_chromatic_plus_seeing(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("chromatic_plus_seeing")
        fig, info, err = run_scenario_side(
            s.after_telescope, s.after_source, s.plot_function,
            seeing_arcsec=s.after_seeing_arcsec,
            polychromatic=s.after_polychromatic)
        assert err is None
        plt.close(fig)

    def test_run_saturn_rings(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("saturn_rings")
        fig, info, err = run_scenario_side(
            s.after_telescope, s.after_source, s.plot_function,
            seeing_arcsec=s.after_seeing_arcsec)
        assert err is None
        plt.close(fig)

    def test_run_starfield_resolution(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("starfield_resolution")
        fig, info, err = run_scenario_side(
            s.after_telescope, s.after_source, s.plot_function,
            seeing_arcsec=s.after_seeing_arcsec)
        assert err is None
        plt.close(fig)

    def test_run_spherical_aberration_before(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("spherical_aberration")
        fig, info, err = run_scenario_side(
            s.before_telescope, s.before_source, s.plot_function)
        assert err is None
        plt.close(fig)

    def test_run_spherical_aberration_after_spot(self):
        # After side uses secondary_plot_function (spot diagram)
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("spherical_aberration")
        fig, info, err = run_scenario_side(
            s.after_telescope, s.after_source, s.secondary_plot_function)
        assert err is None
        plt.close(fig)

    def test_run_coma_secondary_starfield(self):
        # Coma after side is plot_source_image with TutorialStarField
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("fratio_coma")
        assert s.secondary_plot_function == "plot_source_image"
        fig, info, err = run_scenario_side(
            s.after_telescope, s.after_source, s.secondary_plot_function)
        assert err is None
        plt.close(fig)

    def test_run_vignetting_curve(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("vignetting")
        assert s.plot_function == "plot_vignetting_curve"
        fig, info, err = run_scenario_side(
            s.after_telescope, s.after_source, s.plot_function)
        assert err is None
        plt.close(fig)

    def test_objective_type_map_handles_hyphenated(self):
        # build_telescope must accept "apo-doublet" / "apo-triplet" as used by
        # TelescopeConfig — previously these silently fell back to singlet.
        from telescope_gui.telescope_builder import build_telescope
        from telescope_sim.geometry.apo_lenses import (
            ApochromaticDoublet, ApochromaticTriplet,
        )
        from telescope_sim.geometry.lenses import SphericalLens
        t_doublet = build_telescope("Refractor", 100.0, 500.0,
                                     objective_type="apo-doublet")
        assert isinstance(t_doublet.objective, ApochromaticDoublet), (
            "apo-doublet should build an ApochromaticDoublet")

        t_triplet = build_telescope("Refractor", 100.0, 500.0,
                                     objective_type="apo-triplet")
        assert isinstance(t_triplet.objective, ApochromaticTriplet), (
            "apo-triplet should build an ApochromaticTriplet")

        t_singlet = build_telescope("Refractor", 100.0, 500.0,
                                     objective_type="singlet")
        assert isinstance(t_singlet.objective, SphericalLens)

        # GUI label form (with space) must also still work
        t_gui = build_telescope("Refractor", 100.0, 500.0,
                                 objective_type="apo doublet")
        assert isinstance(t_gui.objective, ApochromaticDoublet)

    def test_chromatic_defocus_decreases_with_correction(self):
        # Defocus magnitudes at H-alpha (656nm) for a 100mm f/5: should
        # decrease in the order singlet > achromat > apo-doublet > apo-triplet.
        from telescope_sim.plotting.ray_trace_plot import chromatic_defocus
        from telescope_gui.telescope_builder import build_telescope
        wl = 656.0
        d_singlet = abs(chromatic_defocus(
            build_telescope("Refractor", 100.0, 500.0, objective_type="singlet"),
            wl))
        d_achromat = abs(chromatic_defocus(
            build_telescope("Refractor", 100.0, 500.0, objective_type="achromat"),
            wl))
        d_apo_d = abs(chromatic_defocus(
            build_telescope("Refractor", 100.0, 500.0, objective_type="apo-doublet"),
            wl))
        d_apo_t = abs(chromatic_defocus(
            build_telescope("Refractor", 100.0, 500.0, objective_type="apo-triplet"),
            wl))
        assert d_singlet > d_achromat > d_apo_d > d_apo_t > 0
        # Apo-triplet correction is roughly 8x tighter than achromat
        assert d_achromat / d_apo_t >= 7.5

    def test_tutorial_starfield_deterministic(self):
        from telescope_sim.source.sources import TutorialStarField
        a = TutorialStarField()
        b = TutorialStarField()
        # Same positions, magnitudes — no random seed dependence
        np.testing.assert_array_equal(a.star_x_arcsec, b.star_x_arcsec)
        np.testing.assert_array_equal(a.star_y_arcsec, b.star_y_arcsec)
        np.testing.assert_array_equal(a.star_magnitudes, b.star_magnitudes)
        # Has the on-axis star
        on_axis = ((a.star_x_arcsec == 0.0) & (a.star_y_arcsec == 0.0))
        assert on_axis.any()
        # Has at least one star at r >= 100″ (edge field for coma test)
        r = np.sqrt(a.star_x_arcsec ** 2 + a.star_y_arcsec ** 2)
        assert (r >= 100.0).any()

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

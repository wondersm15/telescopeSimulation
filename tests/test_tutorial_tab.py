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
    def test_seventeen_scenarios_total(self):
        # 17 after Jupiter Full Simulation was dropped (redundant with Saturn
        # with Rings + Colour Filters on Jupiter).
        from telescope_gui.tutorial_mode.scenario_registry import SCENARIOS
        assert len(SCENARIOS) == 17

    def test_acts_populated(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenarios_by_act
        by_act = get_scenarios_by_act()
        assert len(by_act[1]) == 7      # Isolated Effects
        assert len(by_act[2]) == 4      # Combined Effects
        assert len(by_act[3]) == 4      # Brightness, Saturation & Filters (J3)
        assert len(by_act[4]) == 2      # Real Objects (Saturn, Star Field)

    def test_all_scenarios_implemented(self):
        from telescope_gui.tutorial_mode.scenario_registry import SCENARIOS
        implemented = [s for s in SCENARIOS if s.implemented]
        assert len(implemented) == 17
        ids = {s.id for s in implemented}
        assert ids == {
            "airy_disk", "rayleigh_criterion", "central_obstruction",
            "spider_vanes", "chromatic_aberration", "vignetting",
            "spherical_aberration",
            "obstruction_plus_spiders", "chromatic_plus_seeing",
            "aperture_vs_seeing", "fratio_coma",
            "exposure_demo", "nd_filter_moon",
            "color_filter_jupiter", "saturation_demo",
            "saturn_rings", "starfield_resolution",
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

    def test_run_coma_ray_fan_is_default(self):
        """The coma scenario defaults to the ray-fan view (R3.11a): left
        panel titled 'Coma ray fan …', not the RMS curve."""
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("fratio_coma")
        assert s.show_coma_view_combo is True
        fig, info, err = run_scenario_side(
            s.before_telescope, s.before_source, s.plot_function)
        assert err is None
        assert "ray fan" in fig.axes[0].get_title().lower()
        plt.close(fig)

    def test_run_coma_spot_grid_switch(self):
        """Passing coma_view_mode='spot_grid' switches the left panel to the
        RMS-vs-field curve (the spot-grid view)."""
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("fratio_coma")
        fig, info, err = run_scenario_side(
            s.before_telescope, s.before_source, s.plot_function,
            coma_view_mode="spot_grid")
        assert err is None
        assert "rms coma" in fig.axes[0].get_title().lower()
        plt.close(fig)

    def test_theory_forwarding_ignores_unknown_kwargs(self):
        """compute_theory_for_scenario must not drop the whole theory dict
        when the caller passes a kwarg the theory fn doesn't accept (R3.10
        regression: obstruction_ratio nuked the aperture-vs-seeing Airy
        overlay because the swallowed TypeError returned None)."""
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import (
            compute_theory_for_scenario)
        from telescope_sim.geometry.telescope import NewtonianTelescope
        s = get_scenario_by_id("aperture_vs_seeing")
        tel = NewtonianTelescope(primary_diameter=200.0, focal_length=1000.0,
                                 enable_obstruction=False)
        th = compute_theory_for_scenario(
            s, tel, seeing_arcsec=2.5, wavelength_nm=550.0,
            obstruction_ratio=0.0)  # unknown kwarg for this theory fn
        assert th is not None
        assert th.get("diffraction_limit_arcsec", 0.0) > 0.0


class TestApertureDiffractionToggle:
    """R3.10: apply_aperture_diffraction=False renders the star as an ideal
    point (no diffraction), so only seeing blurs it."""

    def _spot_px(self, img):
        return int((img > 0.01 * img.max()).sum())

    def test_aperture_off_is_ideal_point_without_seeing(self):
        from telescope_sim.geometry.telescope import NewtonianTelescope
        from telescope_sim.source.sources import PointSource
        from telescope_sim.plotting.ray_trace_plot import (
            _render_source_through_telescope as render)
        tel = NewtonianTelescope(primary_diameter=200.0, focal_length=1000.0,
                                 enable_obstruction=False)
        on, _, _ = render(PointSource(), tel, num_pixels=256,
                          apply_aperture_diffraction=True)
        off, _, _ = render(PointSource(), tel, num_pixels=256,
                           apply_aperture_diffraction=False)
        # Ideal point collapses to essentially one pixel; the Airy disk fills
        # many. So aperture-off is dramatically more compact.
        assert self._spot_px(off) < self._spot_px(on) / 10

    def test_aperture_off_with_seeing_matches_brightness(self):
        """Toggling aperture changes sharpness, not total brightness: with
        seeing on, aperture-off (pure seeing disk) preserves the flux of
        aperture-on within a modest tolerance."""
        from telescope_sim.geometry.telescope import NewtonianTelescope
        from telescope_sim.source.sources import PointSource
        from telescope_sim.plotting.ray_trace_plot import (
            _render_source_through_telescope as render)
        tel = NewtonianTelescope(primary_diameter=200.0, focal_length=1000.0,
                                 enable_obstruction=False)
        on, _, _ = render(PointSource(), tel, num_pixels=256,
                          seeing_arcsec=2.5, apply_aperture_diffraction=True)
        off, _, _ = render(PointSource(), tel, num_pixels=256,
                           seeing_arcsec=2.5, apply_aperture_diffraction=False)
        assert off.sum() == pytest.approx(on.sum(), rel=0.1)

    def test_run_fratio_coma(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("fratio_coma")
        fig, info, err = run_scenario_side(
            s.after_telescope, s.after_source, s.plot_function)
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
        # Has at least one edge star at ≥ 70% of the field radius
        r = np.sqrt(a.star_x_arcsec ** 2 + a.star_y_arcsec ** 2)
        assert (r >= a.field_radius_arcsec * 0.7).any()

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


class TestSharedPSFNormalization:
    """Phase 1.5: shared-normalisation central-obstruction Strehl visibility."""

    def _newt(self, eps):
        from telescope_gui.telescope_builder import build_telescope
        return build_telescope(
            telescope_type="Newtonian", diameter=200.0, focal_length=1000.0,
            enable_obstruction=(eps > 0), obstruction_ratio=eps)

    def test_plot_psf_2d_exposes_peaks(self):
        """plot_psf_2d attaches raw + relative peak attributes to the figure."""
        from telescope_sim.plotting.ray_trace_plot import plot_psf_2d
        fig = plot_psf_2d(self._newt(0.0), figsize=(4, 4))
        assert getattr(fig, "_psf_raw_peak", None) is not None
        assert fig._psf_raw_peak > 0
        # No reference => displayed relative to its own peak (1.0).
        assert fig._psf_relative_peak == pytest.approx(1.0)
        plt.close(fig)

    def test_peak_reference_yields_strehl_drop(self):
        """With the unobstructed peak as reference, the obstructed PSF's
        relative peak equals the Strehl ratio (1-eps^2)^2."""
        from telescope_sim.plotting.ray_trace_plot import plot_psf_2d
        eps = 0.30
        fig_un = plot_psf_2d(self._newt(0.0), figsize=(4, 4))
        ref = fig_un._psf_raw_peak
        fig_ob = plot_psf_2d(self._newt(eps), figsize=(4, 4),
                             peak_reference=ref)
        assert fig_ob._psf_relative_peak == pytest.approx(
            (1.0 - eps ** 2) ** 2, abs=0.01)
        plt.close(fig_un)
        plt.close(fig_ob)

    def test_runner_threads_peak_reference(self):
        """scenario_runner surfaces psf_raw_peak and applies peak_reference."""
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
        s = get_scenario_by_id("central_obstruction")
        # Before side (unobstructed) — capture the reference.
        fig_b, info_b, err_b = run_scenario_side(
            s.before_telescope, s.before_source, s.plot_function)
        assert err_b is None
        ref = info_b["psf_raw_peak"]
        assert ref and ref > 0
        plt.close(fig_b)
        # After side (obstructed) relative to that reference.
        fig_a, info_a, err_a = run_scenario_side(
            s.after_telescope, s.after_source, s.plot_function,
            peak_reference=ref)
        assert err_a is None
        eps = s.after_telescope.obstruction_ratio
        assert info_a["psf_relative_peak"] == pytest.approx(
            (1.0 - eps ** 2) ** 2, abs=0.01)
        plt.close(fig_a)

    def test_scenario_opts_into_shared_normalization(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        assert get_scenario_by_id("central_obstruction").shared_psf_normalization
        # Other PSF scenarios must NOT (aperture/size lessons, not Strehl).
        assert not get_scenario_by_id("airy_disk").shared_psf_normalization


class TestExitPupilEyeModel:
    """Phase 1.4: exposure is detector-only; eye-view brightness is optics-driven."""

    def _render(self, source, **kw):
        from telescope_sim.geometry import NewtonianTelescope
        from telescope_sim.plotting.ray_trace_plot import (
            _render_source_through_telescope,
        )
        t = NewtonianTelescope(200.0, 1000.0, enable_obstruction=False)
        img, _half, _info = _render_source_through_telescope(
            source, t, num_pixels=96, **kw)
        return img

    def _jupiter(self):
        from telescope_sim.source.sources import Jupiter
        return Jupiter()

    def _star(self):
        from telescope_sim.source.sources import PointSource
        return PointSource(magnitude=2.0)  # not saturated, so exposure shows

    def test_eye_view_ignores_exposure_extended(self):
        """Eye view: exposure does not change an extended-source render."""
        lo = self._render(self._jupiter(), display_stretch="log",
                          exposure_level=0.1)
        hi = self._render(self._jupiter(), display_stretch="log",
                          exposure_level=10.0)
        assert np.allclose(lo, hi)

    def test_eye_view_ignores_exposure_star(self):
        """Eye view: exposure does not change a point-source render."""
        lo = self._render(self._star(), display_stretch="log",
                          exposure_level=0.1)
        hi = self._render(self._star(), display_stretch="log",
                          exposure_level=10.0)
        assert np.allclose(lo, hi)

    def test_detector_view_applies_exposure(self):
        """Detector view: higher exposure yields a brighter render."""
        lo = self._render(self._star(), display_stretch="linear",
                          exposure_level=0.2)
        hi = self._render(self._star(), display_stretch="linear",
                          exposure_level=1.0)
        assert hi.sum() > lo.sum() * 1.5

    def test_eye_view_extended_brightness_scales_with_exit_pupil(self):
        """Eye view: a larger exit pupil gives a brighter extended surface."""
        small = self._render(self._jupiter(), display_stretch="log",
                             exit_pupil_mm=1.0)
        large = self._render(self._jupiter(), display_stretch="log",
                             exit_pupil_mm=7.0)
        assert large.sum() > small.sum() * 1.5

    def test_detector_view_ignores_exit_pupil(self):
        """Detector view: exit pupil has no effect (exposure drives brightness)."""
        a = self._render(self._jupiter(), display_stretch="linear",
                         exit_pupil_mm=1.0)
        b = self._render(self._jupiter(), display_stretch="linear",
                         exit_pupil_mm=7.0)
        assert np.allclose(a, b)

    def test_eye_view_star_ignores_exit_pupil(self):
        """Eye view: a point source is aperture-driven, not exit-pupil-driven."""
        a = self._render(self._star(), display_stretch="log",
                         exit_pupil_mm=1.0)
        b = self._render(self._star(), display_stretch="log",
                         exit_pupil_mm=7.0)
        assert np.allclose(a, b)

    def test_plot_source_image_accepts_exit_pupil(self):
        """Public API smoke: plot_source_image accepts exit_pupil_mm."""
        from telescope_sim.geometry import NewtonianTelescope
        from telescope_sim.plotting import plot_source_image
        t = NewtonianTelescope(200.0, 1000.0, enable_obstruction=False)
        fig = plot_source_image(t, self._jupiter(), num_pixels=96,
                                display_stretch="log", exit_pupil_mm=2.0)
        assert fig is not None
        plt.close(fig)


class TestPerSideDisplayControls:
    """Phase 1.2: per-side display controls pin Before-side stretch/filter/exposure."""

    def _scn(self, sid):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        return get_scenario_by_id(sid)

    def test_saturation_demo_detector_vs_eye(self):
        # R3.15: fixed Detector-left / Eye-right layout with a wide-brightness
        # star field (dynamic range).
        s = self._scn("saturation_demo")
        assert s.before_display_stretch == "linear"     # Detector (left)
        assert s.after_display_stretch == "log"          # Eye (right, pinned)
        assert s.show_eye_blur_toggle is True
        assert s.before_source.source_type == "DynamicRangeField"
        assert s.both_sides_dynamic and s.before_telescope_dynamic

    def test_dynamic_range_field_spans_wide_magnitudes(self):
        from telescope_sim.source.sources import DynamicRangeField
        s = DynamicRangeField()
        assert s.num_stars >= 6
        span = s.star_magnitudes.max() - s.star_magnitudes.min()
        assert span >= 6.0   # ≥ 6 mag ≈ ≥ 250× flux range

    def test_nd_filter_moon_before_unfiltered(self):
        s = self._scn("nd_filter_moon")
        assert s.before_filter == "None"
        assert s.default_filter != "None"            # after applies a filter
        assert s.default_display_stretch == "linear"  # detector saturation lesson

    def test_exposure_demo_fixed_eye_left_detector_right(self):
        # R3.12: fixed Eye-vs-Detector layout — Eye left (pinned, eye-blur
        # toggle), Detector right (pinned linear, exposure acts). No View combo.
        s = self._scn("exposure_demo")
        assert s.before_display_stretch == "log"       # Eye (left)
        assert s.after_display_stretch == "linear"     # Detector (right, pinned)
        assert s.show_eye_blur_toggle is True
        assert s.before_exposure is None               # aperture drives both
        assert s.both_sides_dynamic

    def test_exposure_demo_star_is_coloured(self):
        # B8: a coloured star so saturation whiteout / cone desaturation
        # is demonstrable (a mag-0 white star showed no colour).
        s = self._scn("exposure_demo")
        assert s.after_source.kwargs.get("spectral_rgb") is not None

    def test_color_filter_jupiter_before_unfiltered(self):
        s = self._scn("color_filter_jupiter")
        assert s.before_filter == "None"
        assert s.default_filter != "None"

    def test_color_filter_jupiter_defaults_to_blue(self):
        """R3.14: blue (W80A) is the correct Jupiter contrast filter and is
        now the default — NOT red (which gives a near-uniform red disk)."""
        s = self._scn("color_filter_jupiter")
        assert "blue" in s.default_filter.lower()

    def test_default_display_stretch_defaults_to_log(self):
        """Scenarios that don't opt in keep the Eye (log) default."""
        assert self._scn("rayleigh_criterion").default_display_stretch == "log"


class TestRound2Batch1:
    """Round 2 Batch 1: ray-fan floor, axis-lock FOV skip, dropped controls."""

    def _scn(self, sid):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        return get_scenario_by_id(sid)

    def _telescope(self, primary_type):
        from telescope_gui.telescope_builder import build_telescope
        return build_telescope(
            telescope_type="Newtonian", diameter=200.0, focal_length=800.0,
            primary_type=primary_type, enable_obstruction=False, spider_vanes=0)

    # B6c — ray-fan y-axis is floored to a physical (diffraction) scale so a
    # corrected primary reads as flat, not a magnified floating-point zigzag.
    def test_ray_fan_parabolic_floored_not_noise(self):
        from telescope_sim.plotting.ray_trace_plot import plot_ray_fan_telescope
        fig = plot_ray_fan_telescope(self._telescope("parabolic"), figsize=(4, 4))
        ylo, yhi = fig.axes[0].get_ylim()
        # Floor ≈ 3 × Airy radius (µm); must be ~µm, not the ~1e-11 noise scale.
        airy_um = 1.22 * (550.0 * 1e-6) * 4.0 * 1000.0
        assert yhi == pytest.approx(3.0 * airy_um, rel=0.01)
        assert yhi > 1.0  # decisively above floating-point noise
        plt.close(fig)

    def test_ray_fan_spherical_autoscales_above_floor(self):
        from telescope_sim.plotting.ray_trace_plot import plot_ray_fan_telescope
        fig = plot_ray_fan_telescope(self._telescope("spherical"), figsize=(4, 4))
        _, yhi = fig.axes[0].get_ylim()
        # Real SA spans tens–hundreds of µm — well above the diffraction floor.
        assert yhi > 50.0
        plt.close(fig)

    # B5/B8/B9 — confounding controls dropped.
    def test_nd_filter_moon_drops_diameter(self):
        assert "diameter" not in self._scn("nd_filter_moon").tweakable_params

    def test_exposure_demo_drops_focal_length_keeps_diameter(self):
        params = self._scn("exposure_demo").tweakable_params
        assert "focal_length" not in params
        assert "diameter" in params

    # B3 — central-obstruction panes labelled with their normalisation.
    def test_central_obstruction_labels_mention_normalization(self):
        s = self._scn("central_obstruction")
        assert "reference" in s.before_label.lower()
        assert "strehl" in s.after_label.lower()


class TestRound2Batch2:
    """Round 2 Batch 2: chromatic idealisation/zoom, chroma asinh, coloured stars."""

    def _scn(self, sid):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        return get_scenario_by_id(sid)

    # B4 — chromatic scenario opts into SA idealisation + the focal-zoom combo.
    def test_chromatic_scenario_flags(self):
        s = self._scn("chromatic_aberration")
        assert s.idealize_singlet_sa is True
        assert s.show_focal_zoom_combo is True

    def test_idealize_sa_converges_rays_to_focus(self):
        """idealize_sa=True draws each colour converging to its focal point.

        With idealisation the per-colour rays meet at a point, so the spread
        of axis-crossing x-positions for one wavelength collapses toward 0.
        We assert the figure renders and is flagged; geometric convergence is
        validated visually (the ray bundles meet at the star markers)."""
        from telescope_sim.plotting.ray_trace_plot import (
            plot_polychromatic_ray_trace,
        )
        from telescope_gui.telescope_builder import build_telescope
        t = build_telescope(telescope_type="Refractor", diameter=100,
                            focal_length=500, objective_type="singlet")
        fig_ideal = plot_polychromatic_ray_trace(t, figsize=(4, 5),
                                                 idealize_sa=True,
                                                 show_inset=False)
        # The idealisation note is present on the axes (whitespace-normalised,
        # since the note may wrap across lines).
        texts = " ".join(t.get_text().lower() for t in fig_ideal.axes[0].texts)
        texts = " ".join(texts.split())
        assert "spherical aberration removed" in texts
        plt.close(fig_ideal)

    def test_focal_zoom_changes_xlim(self):
        from telescope_sim.plotting.ray_trace_plot import (
            plot_chromatic_focal_planes,
        )
        from telescope_gui.telescope_builder import build_telescope
        t = build_telescope(telescope_type="Refractor", diameter=100,
                            focal_length=500, objective_type="achromat")
        wide = plot_chromatic_focal_planes(t, fixed_xlim_arcsec=120.0)
        close = plot_chromatic_focal_planes(t, fixed_xlim_arcsec=12.0)
        # The 1D radial-profile panel is the one labelled in arcsec.
        def _profile_xmax(fig):
            for ax in fig.axes:
                if "radial distance" in (ax.get_xlabel() or "").lower():
                    return ax.get_xlim()[1]
            return None
        assert _profile_xmax(wide) == pytest.approx(120.0, rel=0.02)
        assert _profile_xmax(close) == pytest.approx(12.0, rel=0.02)
        plt.close(wide); plt.close(close)

    # B8 — coloured PointSource renders RGB even through a reflector
    # (intrinsic stellar colour, independent of chromatic aberration).
    def test_pointsource_spectral_rgb_renders_colour(self):
        from telescope_sim.geometry import NewtonianTelescope
        from telescope_sim.source.sources import PointSource
        from telescope_sim.plotting.ray_trace_plot import (
            _render_source_through_telescope as R,
        )
        t = NewtonianTelescope(100.0, 800.0, enable_obstruction=False)
        s = PointSource(magnitude=0.0, spectral_rgb=(1.0, 0.5, 0.2))
        assert hasattr(s, "star_spectral_rgb")
        # Reflector + non-polychromatic → still produces a tinted RGB image.
        _img, _half, info = R(s, t, num_pixels=128, display_stretch="linear")
        rgb = info["image_rgb"]
        assert rgb is not None
        # Peak pixel is red-dominant (matches the SED tint), not grey.
        flat = rgb.reshape(-1, 3)
        peak = flat[np.argmax(flat.sum(axis=1))]
        assert peak[0] > peak[1] > peak[2]

    def test_white_pointsource_stays_grayscale(self):
        """No regression: a plain (uncoloured) PointSource still renders on
        the grayscale path (no image_rgb) through a reflector."""
        from telescope_sim.geometry import NewtonianTelescope
        from telescope_sim.source.sources import PointSource
        from telescope_sim.plotting.ray_trace_plot import (
            _render_source_through_telescope as R,
        )
        t = NewtonianTelescope(100.0, 800.0, enable_obstruction=False)
        s = PointSource(magnitude=0.0)  # no spectral_rgb
        _img, _half, info = R(s, t, num_pixels=128, display_stretch="linear")
        assert info["image_rgb"] is None

    # B7/B10 — chroma-preserving asinh keeps hue in eye view.
    def test_chroma_preserving_asinh_keeps_hue(self):
        """A red-dominant linear image stays red-dominant after the eye-view
        asinh (per-channel asinh would lift G/B and wash it toward grey)."""
        from telescope_sim.geometry import NewtonianTelescope
        from telescope_sim.source.sources import Jupiter
        from telescope_sim.plotting.ray_trace_plot import (
            _render_source_through_telescope as R,
        )
        t = NewtonianTelescope(200.0, 1000.0, enable_obstruction=False)
        j = Jupiter()
        # W25 red filter → red-dominant; eye view must preserve that.
        _img, _half, info = R(j, t, num_pixels=128, display_stretch="log",
                              filter_name="W25 (red)")
        rgb = info["image_rgb"]
        disk = rgb.reshape(-1, 3)
        disk = disk[disk.sum(axis=1) > 0.1]
        assert len(disk) > 0
        mean = disk.mean(axis=0)
        assert mean[0] > 2.0 * mean[1]  # red ≫ green (hue preserved)


class TestShowcaseStarField:
    """B12: the flagship star-field showcase source + scenario."""

    def _tel(self, obs=True, spider=4, coma_ok=True):
        from telescope_gui.telescope_builder import build_telescope
        return build_telescope(
            telescope_type="Newtonian", diameter=200, focal_length=800,
            enable_obstruction=obs, obstruction_ratio=0.2 if obs else 0.0,
            spider_vanes=spider, spider_vane_width=2.5)

    def _render(self, tel, **kw):
        from telescope_sim.source.sources import ShowcaseStarField
        from telescope_sim.plotting.ray_trace_plot import (
            _render_source_through_telescope as R,
        )
        _img, _half, info = R(ShowcaseStarField(), tel, num_pixels=192,
                              display_stretch="log", **kw)
        return info["image_rgb"]

    def test_field_has_colour_and_population(self):
        from telescope_sim.source.sources import ShowcaseStarField
        s = ShowcaseStarField()
        assert s.num_stars > 40
        assert hasattr(s, "star_spectral_rgb")
        assert s.star_spectral_rgb.shape == (s.num_stars, 3)
        # Not all one colour: several distinct tints present.
        uniq = {tuple(np.round(c, 2)) for c in s.star_spectral_rgb}
        assert len(uniq) >= 4

    def test_faint_stars_more_desaturated_than_bright(self):
        """R3.20: colour is magnitude-dependent — bright stars carry a tint,
        faint stars trend white (chroma ≈ how far the tint is from grey)."""
        from telescope_sim.source.sources import ShowcaseStarField
        s = ShowcaseStarField()
        rgb = s.star_spectral_rgb
        chroma = rgb.max(axis=1) - rgb.min(axis=1)   # 0 = white/grey
        mags = s.star_magnitudes
        bright = chroma[mags < 0.0]
        faint = chroma[mags > 3.0]
        assert bright.size and faint.size
        # Brightest stars are meaningfully more saturated than the faintest.
        assert bright.mean() > faint.mean() + 0.1

    def test_renders_in_colour_through_reflector(self):
        rgb = self._render(self._tel())
        assert rgb is not None
        # Some pixels are meaningfully non-grey (chroma present).
        flat = rgb.reshape(-1, 3)
        lit = flat[flat.sum(axis=1) > 0.05]
        chroma = (lit.max(axis=1) - lit.min(axis=1))
        assert (chroma > 0.1).sum() > 20

    def _changed(self, a, b):
        d = np.abs(a - b)
        return int((d.sum(axis=2) > 0.02).sum())

    def test_each_effect_visibly_changes_field(self):
        """coma / spider / obstruction / seeing each change the render.
        (Vignetting is intentionally excluded — FIF ≫ field, see scenario.)"""
        base = self._render(self._tel(), apply_coma=True, seeing_arcsec=1.5)
        no_coma = self._render(self._tel(), apply_coma=False, seeing_arcsec=1.5)
        no_spider = self._render(self._tel(spider=0), apply_coma=True,
                                 seeing_arcsec=1.5)
        no_obs = self._render(self._tel(obs=False), apply_coma=True,
                              seeing_arcsec=1.5)
        no_seeing = self._render(self._tel(), apply_coma=True,
                                 seeing_arcsec=None)
        assert self._changed(base, no_coma) > 50
        assert self._changed(base, no_spider) > 50
        assert self._changed(base, no_obs) > 50
        assert self._changed(base, no_seeing) > 50

    def test_scenario_uses_showcase_and_drops_vignetting_toggle(self):
        from telescope_gui.tutorial_mode.scenario_registry import get_scenario_by_id
        s = get_scenario_by_id("starfield_resolution")
        assert s.after_source.source_type == "ShowcaseStarField"
        assert s.before_source.source_type == "ShowcaseStarField"
        # Vignetting omitted (dead toggle); the other four remain.
        assert "vignetting" not in s.effect_toggles
        assert set(s.effect_toggles) == {"obstruction", "spider_vanes",
                                         "coma", "seeing"}


class TestPlanetPipeline:
    """B14: planets render at full intrinsic resolution, then the telescope
    sim degrades them (sum-bin to display + PSF/seeing) — no premature cap,
    no double blur. Confirms the A5 answer."""

    def _tel(self):
        from telescope_gui.telescope_builder import build_telescope
        return build_telescope(telescope_type="Newtonian", diameter=200,
                               focal_length=1000, enable_obstruction=False)

    def test_texture_is_high_resolution(self):
        from telescope_sim.source.sources import Jupiter, Saturn, Moon
        for cls in (Jupiter, Saturn, Moon):
            s = cls()
            half = s.field_extent_arcsec / 2.0
            for n in (256, 1024):
                rgb = s.render_ideal_rgb(half, n)
                assert rgb.shape == (n, n, 3)  # renders at the requested res

    def test_extended_source_oversamples_then_sumbins(self):
        """Jupiter at a modest display size renders at higher internal
        resolution and sum-bins down (high-res-then-degrade)."""
        import telescope_sim.plotting.ray_trace_plot as rp
        from telescope_sim.source.sources import Jupiter
        seen = {}
        orig = rp._render_source_through_telescope

        def wrap(source, telescope, **kw):
            seen["eff"] = kw.get("num_pixels")
            seen["disp"] = kw.get("display_num_pixels")
            return orig(source, telescope, **kw)
        rp._render_source_through_telescope = wrap
        try:
            fig = rp.plot_source_image(self._tel(), Jupiter(), num_pixels=120,
                                       seeing_arcsec=None)
            plt.close(fig)
        finally:
            rp._render_source_through_telescope = orig
        assert seen["eff"] > seen["disp"]   # oversampled internally
        assert seen["disp"] == 120          # displayed at requested size

    def test_star_source_renders_at_display_resolution(self):
        """Stars are points — no benefit to internal oversampling; render ==
        display (a sub-pixel Airy → one bright pixel, what a CCD records)."""
        import telescope_sim.plotting.ray_trace_plot as rp
        from telescope_sim.source.sources import PointSource
        seen = {}
        orig = rp._render_source_through_telescope

        def wrap(source, telescope, **kw):
            seen["eff"] = kw.get("num_pixels")
            seen["disp"] = kw.get("display_num_pixels")
            return orig(source, telescope, **kw)
        rp._render_source_through_telescope = wrap
        try:
            fig = rp.plot_source_image(self._tel(), PointSource(),
                                       num_pixels=120, seeing_arcsec=None)
            plt.close(fig)
        finally:
            rp._render_source_through_telescope = orig
        assert seen["eff"] == seen["disp"] == 120

    def test_seeing_degrades_monotonically(self):
        """More seeing spreads flux → lower high-vs-median contrast."""
        from telescope_sim.source.sources import Jupiter
        from telescope_sim.plotting.ray_trace_plot import (
            _render_source_through_telescope as R,
        )
        t = self._tel()

        def contrast(seeing):
            img, _h, _i = R(Jupiter(), t, num_pixels=200,
                            seeing_arcsec=seeing, display_stretch="linear")
            return float(np.percentile(img, 99.5) - np.percentile(img, 50))
        sharp = contrast(None)
        blurred = contrast(6.0)
        assert blurred < sharp  # atmosphere softens the disk

    def test_colour_preserved_through_degradation(self):
        """Jupiter stays warm/tan (R>G>B) after PSF + seeing + eye view."""
        from telescope_sim.source.sources import Jupiter
        from telescope_sim.plotting.ray_trace_plot import (
            _render_source_through_telescope as R,
        )
        _img, _h, info = R(Jupiter(), self._tel(), num_pixels=200,
                           seeing_arcsec=1.5, display_stretch="log")
        rgb = info["image_rgb"]
        disk = rgb.reshape(-1, 3)
        disk = disk[disk.sum(axis=1) > 0.1]
        mean = disk.mean(axis=0)
        assert mean[0] > mean[1] > mean[2]  # warm tan


class TestBrightnessModelPropagation:
    """B13: the detector-vs-eye brightness model must hold for EVERY source
    type — eye view ignores exposure, detector view responds to it. This is a
    generic renderer invariant; verifying it across source types guards against
    a per-source-path regression."""

    def _sources(self):
        from telescope_sim.source.sources import (
            PointSource, DoubleStar, MultiColorStarField, ShowcaseStarField,
            Jupiter, Moon,
        )
        from telescope_gui.telescope_builder import build_telescope
        refl = build_telescope(telescope_type="Newtonian", diameter=150,
                               focal_length=1200, enable_obstruction=False)
        refr = build_telescope(telescope_type="Refractor", diameter=80,
                               focal_length=640, objective_type="achromat")
        return [
            (PointSource(magnitude=2.0), refl, {}),
            (DoubleStar(separation_arcsec=8.0, magnitude_primary=0.0,
                        magnitude_secondary=4.0), refl, {}),
            (MultiColorStarField(), refr, dict(polychromatic=True)),
            (ShowcaseStarField(), refl, {}),
            (Jupiter(), refl, dict(seeing_arcsec=1.5)),
            (Moon(), refl, dict(seeing_arcsec=1.5)),
        ]

    def test_eye_view_exposure_invariant_all_sources(self):
        from telescope_sim.plotting.ray_trace_plot import (
            _render_source_through_telescope as R,
        )
        for src, tel, extra in self._sources():
            e1, _h, _i = R(src, tel, num_pixels=96, display_stretch="log",
                           exposure_level=0.1, **extra)
            e2, _h, _i = R(src, tel, num_pixels=96, display_stretch="log",
                           exposure_level=10.0, **extra)
            assert np.allclose(e1, e2), (
                f"{type(src).__name__}: eye view changed with exposure")

    def test_detector_view_exposure_sensitive_all_sources(self):
        from telescope_sim.plotting.ray_trace_plot import (
            _render_source_through_telescope as R,
        )
        for src, tel, extra in self._sources():
            d1, _h, _i = R(src, tel, num_pixels=96, display_stretch="linear",
                           exposure_level=0.3, **extra)
            d2, _h, _i = R(src, tel, num_pixels=96, display_stretch="linear",
                           exposure_level=2.0, **extra)
            assert not np.allclose(d1, d2), (
                f"{type(src).__name__}: detector view ignored exposure")


class TestLegendsOutOfPlots:
    """R3.18 / R3.5c: legends must not sit on top of the plotted data. These
    two plots were the remaining offenders found by the legends-out sweep."""

    @staticmethod
    def _legend_data_overlap(ax, fig):
        """Count data-line vertices falling inside the axes legend box."""
        import numpy as np
        leg = ax.get_legend()
        if leg is None:
            return 0
        fig.canvas.draw()
        lb = leg.get_window_extent()
        hits = 0
        for ln in ax.get_lines():
            xd, yd = ln.get_data()
            if len(xd) == 0:
                continue
            pts = ax.transData.transform(np.column_stack([xd, yd]))
            hits += int(((pts[:, 0] >= lb.x0) & (pts[:, 0] <= lb.x1)
                         & (pts[:, 1] >= lb.y0) & (pts[:, 1] <= lb.y1)).sum())
        return hits

    def test_pupil_ray_trace_legend_not_over_rays(self):
        from telescope_sim.geometry.telescope import NewtonianTelescope
        from telescope_sim.plotting.ray_trace_plot import (
            plot_ray_trace_pupil_colored)
        tel = NewtonianTelescope(primary_diameter=200.0, focal_length=800.0,
                                 primary_type="spherical")
        fig = plot_ray_trace_pupil_colored(tel, figsize=(5, 5))
        # Legend was pulled to a FIGURE-level legend (bottom whitespace), so
        # the axes itself carries no legend on top of the rays.
        assert fig.axes[0].get_legend() is None
        assert len(fig.legends) >= 1
        plt.close(fig)

    def test_vignetting_curve_legend_clears_curve(self):
        from telescope_sim.geometry.telescope import NewtonianTelescope
        from telescope_sim.plotting.ray_trace_plot import plot_vignetting_curve
        tel = NewtonianTelescope(primary_diameter=200.0, focal_length=800.0)
        fig = plot_vignetting_curve(tel, figsize=(5, 5))
        # A few points from the θ_fif reference line may graze the frame, but
        # the legend must not sit on the illumination curve (was 64 pts).
        assert self._legend_data_overlap(fig.axes[0], fig) < 5
        plt.close(fig)

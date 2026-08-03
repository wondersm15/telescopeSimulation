"""Tests for spectrum → RGB colour science and the spectral star renderer.

Round 5 item R5.6a: the polychromatic star path sampled three delta
wavelengths and sent each into one RGB channel, which rendered every star's
core as pure green (hue 120°, R and B exactly zero) regardless of its spectral
type. These tests pin the colour science and assert the rendered symptom is
gone.
"""

import colorsys
import warnings

import numpy as np
import pytest

from telescope_sim.physics.colorimetry import (
    CMF_MAX_NM,
    CMF_MIN_NM,
    blackbody_linear_srgb,
    band_weights_for_source,
    cie_xyz_at,
    planck_spectral_radiance,
    spectral_bands,
    xyz_to_linear_srgb,
)


def _hue_sat(rgb):
    """Hue in degrees and HSV saturation, with brightness normalised away."""
    rgb = np.asarray(rgb, dtype=float)
    peak = float(rgb.max())
    if peak <= 1e-12:
        return None
    h, s, _ = colorsys.rgb_to_hsv(*(rgb / peak))
    return h * 360.0, s


class TestColourMatchingFunctions:

    def test_luminous_efficiency_peaks_near_555nm(self):
        """y_bar IS the photopic luminous efficiency curve; it peaks at 555 nm."""
        wl = np.arange(400.0, 700.0, 1.0)
        y_bar = cie_xyz_at(wl)[:, 1]
        assert 550.0 <= wl[int(np.argmax(y_bar))] <= 560.0

    def test_zero_outside_the_visible_band(self):
        for wl in (200.0, 379.0, 781.0, 2000.0):
            assert np.allclose(cie_xyz_at(wl), 0.0)

    def test_z_bar_vanishes_at_long_wavelengths(self):
        """The short-wavelength primary carries no red response."""
        assert cie_xyz_at(650.0)[2] == pytest.approx(0.0, abs=1e-6)

    def test_scalar_and_array_shapes(self):
        assert cie_xyz_at(550.0).shape == (3,)
        assert cie_xyz_at([450.0, 550.0, 650.0]).shape == (3, 3)

    def test_table_covers_the_visible_band(self):
        assert CMF_MIN_NM <= 400.0 and CMF_MAX_NM >= 700.0


class TestPlanck:

    def test_wien_displacement_law(self):
        """Peak wavelength must follow lambda_max * T = 2.898e6 nm*K."""
        for temperature in (3000.0, 5800.0, 10000.0):
            wl = np.arange(50.0, 4000.0, 0.5)
            peak_wl = wl[int(np.argmax(planck_spectral_radiance(wl, temperature)))]
            assert peak_wl == pytest.approx(2.897771e6 / temperature, rel=0.01)

    def test_hotter_is_brighter_at_every_wavelength(self):
        wl = np.arange(400.0, 700.0, 10.0)
        assert np.all(planck_spectral_radiance(wl, 6000.0)
                      > planck_spectral_radiance(wl, 4000.0))

    def test_non_positive_temperature_is_dark(self):
        assert np.allclose(planck_spectral_radiance([500.0], 0.0), 0.0)

    def test_no_overflow_at_low_temperature(self):
        """The exponent is clipped; a cool source must not produce inf/nan."""
        out = planck_spectral_radiance(np.arange(380.0, 780.0, 5.0), 300.0)
        assert np.all(np.isfinite(out))


class TestSpectralBands:

    def test_flat_spectrum_is_neutral(self):
        """The white balance: equal energy per band must sum to (1, 1, 1).

        This is what keeps a featureless "white star" white, so any colour in
        the rendered output is attributable to the source or to chromatic
        aberration, never to the choice of sampling.
        """
        for n_bands in (3, 9, 21):
            _, rgb_weights = spectral_bands(n_bands)
            assert np.allclose(rgb_weights.sum(axis=0), 1.0)

    def test_band_centres_ordered_and_in_range(self):
        centres, weights = spectral_bands(9, 400.0, 700.0)
        assert centres.shape == (9,)
        assert weights.shape == (9, 3)
        assert np.all(np.diff(centres) > 0)
        assert centres[0] > 400.0 and centres[-1] < 700.0

    def test_short_bands_are_blue_and_long_bands_are_red(self):
        centres, weights = spectral_bands(9)
        blue_band = int(np.argmin(np.abs(centres - 450.0)))
        red_band = int(np.argmin(np.abs(centres - 620.0)))
        assert weights[blue_band, 2] > weights[blue_band, 0]
        assert weights[red_band, 0] > weights[red_band, 2]

    def test_weights_never_negative(self):
        """Out-of-gamut spectral colours are clipped, not left negative."""
        _, weights = spectral_bands(15)
        assert np.all(weights >= 0.0)

    def test_rejects_zero_bands(self):
        with pytest.raises(ValueError):
            spectral_bands(0)

    def test_nine_bands_is_converged(self):
        """21 bands must not move a blackbody colour materially versus 9.

        Justifies the default: more bands cost linear time for no gain.
        """
        for temperature in (3500.0, 5800.0, 22400.0):
            coarse = blackbody_linear_srgb(temperature, n_bands=9)
            fine = blackbody_linear_srgb(temperature, n_bands=21)
            assert np.allclose(coarse, fine, atol=0.05)


class TestBlackbodyColour:

    def test_hotter_stars_are_bluer(self):
        """Blue/red ratio must rise monotonically with temperature."""
        ratios = []
        for temperature in (3000.0, 4300.0, 5800.0, 9900.0, 22400.0):
            rgb = blackbody_linear_srgb(temperature)
            ratios.append(rgb[2] / max(rgb[0], 1e-9))
        assert np.all(np.diff(ratios) > 0), ratios

    def test_solar_temperature_is_near_white(self):
        """A ~5800 K blackbody under a D65 white point is almost neutral."""
        hue_sat = _hue_sat(blackbody_linear_srgb(5800.0))
        assert hue_sat is not None
        assert hue_sat[1] < 0.15, f"Sun-like star too saturated: {hue_sat}"

    def test_cool_star_is_orange_not_red(self):
        """R5.1: a 3500 K star is a pale amber, not a saturated red."""
        hue, sat = _hue_sat(blackbody_linear_srgb(3500.0))
        assert 15.0 < hue < 60.0, f"hue {hue} is not in the orange band"
        assert sat < 0.75, f"saturation {sat} is implausibly deep"

    def test_peak_channel_is_unity(self):
        for temperature in (3000.0, 5800.0, 30000.0):
            assert blackbody_linear_srgb(temperature).max() == pytest.approx(1.0)

    def test_non_positive_temperature_is_black(self):
        assert np.allclose(blackbody_linear_srgb(0.0), 0.0)


class TestXYZConversion:

    def test_equal_energy_white_is_warm_before_balancing(self):
        """Illuminant E is NOT neutral in sRGB, because sRGB is D65-referenced.

        Raw integration gives roughly (1.00, 0.79, 0.75) — a warm cast. This
        is correct colorimetry, and it is exactly why `spectral_bands` applies
        a per-channel white balance; see the companion test below.
        """
        wl = np.arange(380.0, 781.0, 1.0)
        xyz = np.trapezoid(cie_xyz_at(wl), wl, axis=0)
        rgb = xyz_to_linear_srgb(xyz)
        rgb = rgb / rgb.max()
        assert rgb[0] == pytest.approx(1.0)
        assert rgb[2] < 0.85, f"expected a warm cast, got {rgb}"

    def test_band_weights_neutralise_equal_energy_white(self):
        """After balancing, a flat spectrum is exactly neutral by construction."""
        _, weights = spectral_bands(9)
        assert np.allclose(weights.sum(axis=0), 1.0)

    def test_negative_channels_can_be_kept(self):
        """Monochromatic 550 nm is outside the sRGB gamut — R goes negative.

        Documents why band weights are clipped: this is a real gamut limit,
        not a bug, and it is why 550 nm alone renders as pure green.
        """
        rgb = xyz_to_linear_srgb(cie_xyz_at(550.0), clip_negative=False)
        assert rgb[0] < 0.0
        assert np.all(xyz_to_linear_srgb(cie_xyz_at(550.0)) >= 0.0)


class TestBandWeightsForSource:

    def test_peak_channel_normalised_to_one(self):
        centres, weights = spectral_bands(9)
        for temperature in (3500.0, 5800.0, 22400.0):
            _, _, source_rgb = band_weights_for_source(
                centres, weights, temperature_k=temperature)
            assert source_rgb.max() == pytest.approx(1.0)

    def test_flat_spectrum_with_tint_reproduces_the_tint(self):
        """Sources without a temperature keep their tabulated colour exactly."""
        centres, weights = spectral_bands(9)
        tint = (1.0, 0.7, 0.3)
        _, _, source_rgb = band_weights_for_source(
            centres, weights, temperature_k=None, tint_rgb=tint)
        assert np.allclose(source_rgb, tint, atol=1e-9)

    def test_temperature_matches_the_blackbody_colour(self):
        centres, weights = spectral_bands(9)
        _, _, source_rgb = band_weights_for_source(
            centres, weights, temperature_k=4300.0)
        assert np.allclose(source_rgb, blackbody_linear_srgb(4300.0), atol=1e-9)


class TestSpectralStarRendering:
    """End-to-end: the R5.6a symptom must be gone from the rendered image."""

    @staticmethod
    def _render(objective_type):
        from telescope_gui.telescope_builder import build_telescope
        from telescope_sim.source.sources import MultiColorStarField
        from telescope_sim.plotting.ray_trace_plot import (
            _render_source_through_telescope)
        source = MultiColorStarField()
        scope = build_telescope(telescope_type="Refractor", diameter=80,
                                focal_length=640, objective_type=objective_type)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _, half_fov, info = _render_source_through_telescope(
                source, scope, wavelength_nm=550.0, num_pixels=512,
                seeing_arcsec=None, polychromatic=True,
                display_stretch="log", exposure_level=0.15)
        rgb = np.asarray(info["image_rgb"], dtype=float)
        pixel_scale = 2.0 * half_fov / rgb.shape[0]
        cores = []
        for x_as, y_as in zip(source.star_x_arcsec, source.star_y_arcsec):
            cx = int(round(rgb.shape[1] / 2 + x_as / pixel_scale))
            cy = int(round(rgb.shape[0] / 2 + y_as / pixel_scale))
            if 0 <= cx < rgb.shape[1] and 0 <= cy < rgb.shape[0]:
                cores.append(rgb[cy, cx])
        return source, rgb, np.asarray(cores)

    @pytest.mark.parametrize("objective_type",
                             ["achromat", "apo_doublet", "apo_triplet"])
    def test_star_cores_are_not_pure_green(self, objective_type):
        """The defect signature: hue exactly 120° with R and B both zero."""
        _, _, cores = self._render(objective_type)
        assert len(cores) > 0
        for core in cores:
            assert core[0] > 1e-6, f"red channel empty: {core}"
            assert core[2] > 1e-6, f"blue channel empty: {core}"
            hue, _ = _hue_sat(core)
            assert abs(hue - 120.0) > 5.0, f"still pure green: hue {hue}"

    @pytest.mark.parametrize("objective_type",
                             ["achromat", "apo_doublet", "apo_triplet"])
    def test_stars_do_not_all_share_one_hue(self, objective_type):
        """Before the fix every star rendered the same hue to within 0.5°."""
        _, _, cores = self._render(objective_type)
        hues = np.array([_hue_sat(c)[0] for c in cores])
        assert hues.max() - hues.min() > 10.0, f"hues collapsed: {hues}"

    def test_corrected_objective_tracks_star_temperature(self):
        """On an APO triplet the coolest star must render redder than the hottest."""
        source, _, cores = self._render("apo_triplet")
        temps = np.asarray(source.star_temperatures_K, dtype=float)
        coolest = cores[int(np.argmin(temps))]
        hottest = cores[int(np.argmax(temps))]
        assert coolest[0] / max(coolest[2], 1e-9) > hottest[0] / max(hottest[2], 1e-9)

    def test_channels_stay_registered(self):
        """R5.6c: per-channel centroids must coincide (no colour fringing)."""
        source, rgb, _ = self._render("apo_triplet")
        lum = rgb.sum(axis=2)
        cy, cx = np.unravel_index(int(np.argmax(lum)), lum.shape)
        box = 12
        sub = rgb[cy - box:cy + box + 1, cx - box:cx + box + 1]
        yy, xx = np.mgrid[:sub.shape[0], :sub.shape[1]]
        centroids = []
        for channel in range(3):
            plane = sub[:, :, channel]
            total = plane.sum()
            assert total > 0
            centroids.append(((xx * plane).sum() / total,
                              (yy * plane).sum() / total))
        spread = max(np.hypot(a[0] - b[0], a[1] - b[1])
                     for a in centroids for b in centroids)
        assert spread < 0.05, f"channel centroids spread {spread:.3f} px"

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
    apply_mesopic_desaturation,
    band_weights_for_source,
    cie_xyz_at,
    mesopic_chroma_gain,
    planck_spectral_radiance,
    spectral_bands,
    srgb_decode,
    srgb_encode,
    tone_map_gamma,
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


class TestMesopicVision:
    """R5.1: human colour vision is band-pass in luminance, not monotonic."""

    def test_gain_is_zero_in_the_dark(self):
        """Rods are a single receptor class, so scotopic vision is
        achromatic — no colour survives at very low flux."""
        assert mesopic_chroma_gain(0.0) == 0.0
        assert mesopic_chroma_gain(1e-4) < 0.01

    def test_gain_falls_off_again_when_bleached(self):
        """Cone photopigment bleaches at high flux and the percept whitens."""
        assert mesopic_chroma_gain(100.0) < 0.05

    def test_gain_peaks_between_the_two_thresholds(self):
        """Full colour is only available in the middle of the range."""
        from telescope_sim.physics.colorimetry import (
            CONE_BLEACH_FLUX, CONE_THRESHOLD_FLUX)
        mid = np.sqrt(CONE_THRESHOLD_FLUX * CONE_BLEACH_FLUX)
        assert mesopic_chroma_gain(mid) > mesopic_chroma_gain(
            CONE_THRESHOLD_FLUX / 10.0)
        assert mesopic_chroma_gain(mid) > mesopic_chroma_gain(
            CONE_BLEACH_FLUX * 10.0)

    def test_gain_is_bounded(self):
        flux = np.logspace(-6, 3, 200)
        gain = mesopic_chroma_gain(flux)
        assert np.all(gain >= 0.0) and np.all(gain < 1.0)

    def test_bright_end_matches_the_previous_model(self):
        """The old one-sided model used w = I/(I+0.5) toward grey; the bleach
        term must reproduce it so R4-era behaviour is unchanged at high flux."""
        from telescope_sim.physics.colorimetry import CONE_BLEACH_FLUX
        for flux in (0.5, 1.0, 4.0):
            expected = 1.0 - flux / (flux + CONE_BLEACH_FLUX)
            cone_on = flux / (flux + 0.05)
            assert mesopic_chroma_gain(flux) == pytest.approx(
                cone_on * expected, rel=1e-9)

    def test_desaturation_preserves_luminance(self):
        """Blending toward grey must not change how bright a pixel looks."""
        rng = np.random.default_rng(0)
        img = rng.uniform(0.0, 2.0, (16, 16, 3))
        out = apply_mesopic_desaturation(img)

        def _lum(a):
            return (0.2126 * a[..., 0] + 0.7152 * a[..., 1]
                    + 0.0722 * a[..., 2])

        assert np.allclose(_lum(out), _lum(img))

    def test_desaturation_does_not_mutate_input(self):
        img = np.full((4, 4, 3), 0.3)
        img[..., 0] = 0.9
        before = img.copy()
        apply_mesopic_desaturation(img)
        assert np.array_equal(img, before)


class TestEyeVersusDetectorColour:
    """R5.1 end-to-end: the two panes must disagree, in the right direction."""

    @staticmethod
    def _render(stretch):
        from telescope_gui.telescope_builder import build_telescope
        from telescope_sim.source.sources import PointSource
        from telescope_sim.plotting.ray_trace_plot import (
            _render_source_through_telescope)
        scope = build_telescope(telescope_type="reflector", diameter=100.0,
                               focal_length=800.0, primary_type="parabolic",
                               enable_obstruction=False, spider_vanes=0)
        star = PointSource(magnitude=0.0, temperature_k=4300.0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _, _, info = _render_source_through_telescope(
                star, scope, num_pixels=256, seeing_arcsec=None,
                display_stretch=stretch)
        return np.asarray(info["image_rgb"], dtype=float)

    @staticmethod
    def _ring_sat(rgb, radius_px):
        # The renderer emits sRGB CODE VALUES (R5.8), but chromaticity is a
        # property of linear light — the encode is a per-channel power law,
        # so it changes (max-min)/max even when the colour has not changed
        # at all. Decode first, or this measures the transfer function
        # instead of the colour.
        from telescope_sim.physics.colorimetry import srgb_decode
        rgb = srgb_decode(rgb)
        lum = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1]
               + 0.0722 * rgb[..., 2])
        cy, cx = np.unravel_index(int(np.argmax(lum)), lum.shape)
        yy, xx = np.mgrid[:rgb.shape[0], :rgb.shape[1]]
        ring = np.abs(np.hypot(yy - cy, xx - cx) - radius_px) < 1.0
        mean = rgb[ring].mean(axis=0)
        return (mean.max() - mean.min()) / max(mean.max(), 1e-12)

    def test_detector_records_the_same_colour_everywhere(self):
        """A camera has no cones: chromaticity is flux-independent."""
        rgb = self._render("linear")
        core = self._ring_sat(rgb, 4)
        halo = self._ring_sat(rgb, 20)
        assert core == pytest.approx(halo, abs=0.02)

    def test_eye_drains_colour_from_the_faint_halo(self):
        """R5.1: the halo is ~1% of the peak — far below the cone threshold —
        so an observer sees grey there, not the vivid orange the chroma-
        preserving asinh stretch used to display."""
        rgb = self._render("log")
        assert self._ring_sat(rgb, 20) < 0.10

    def test_eye_whitens_the_blazing_core(self):
        """The bright end (cone bleaching) must still work."""
        rgb = self._render("log")
        assert self._ring_sat(rgb, 0.0) < 0.15

    def test_eye_keeps_colour_in_the_middle(self):
        """Between the two limits the star's amber must survive, otherwise
        the fix has simply thrown all colour away."""
        rgb = self._render("log")
        assert self._ring_sat(rgb, 10) > self._ring_sat(rgb, 20)


class TestSRGBTransferFunction:
    """R5.8: the encode that cancels the monitor's own ~2.2 decode.

    `imshow` writes float RGB straight into the display buffer, so its input
    is an sRGB CODE VALUE, not a radiance. These tests pin the curve itself;
    `TestPhotometricFidelity` below checks that the renderer actually uses it.
    """

    def test_endpoints_are_exact(self):
        assert float(srgb_encode(0.0)) == pytest.approx(0.0)
        assert float(srgb_encode(1.0)) == pytest.approx(1.0)

    def test_round_trip_is_lossless(self):
        lin = np.linspace(0.0, 1.0, 2001)
        assert np.abs(srgb_decode(srgb_encode(lin)) - lin).max() < 1e-12

    def test_matches_the_published_curve(self):
        # Reference points from IEC 61966-2-1. Mid-grey is the one that
        # matters pedagogically: 18% reflectance sits near code 0.46, which
        # is why handing raw radiance to imshow looks ~2.3x too dark.
        assert float(srgb_encode(0.18)) == pytest.approx(0.4613, abs=5e-4)
        assert float(srgb_encode(0.5)) == pytest.approx(0.7354, abs=5e-4)
        assert float(srgb_decode(0.5)) == pytest.approx(0.2140, abs=5e-4)

    def test_is_monotonic(self):
        lin = np.linspace(0.0, 1.0, 500)
        assert np.all(np.diff(srgb_encode(lin)) > 0)

    def test_lifts_a_one_percent_feature_out_of_black(self):
        """The R5.2 arithmetic, pinned.

        A 1st Airy ring at 1.75% of peak used to be written into the image as
        the raw value 0.0175 -> level 4 of 255, and the monitor then emitted
        0.0175**2.2 = 0.017% of peak light, i.e. black. Encoded, it lands at
        level 36 and is visible.
        """
        assert float(srgb_encode(0.0175)) * 255 == pytest.approx(36, abs=1)
        assert float(srgb_encode(0.0042)) * 255 == pytest.approx(13, abs=1)
        assert float(srgb_encode(0.054)) * 255 == pytest.approx(66, abs=1)

    def test_clamps_out_of_range_input(self):
        assert float(srgb_encode(-0.5)) == pytest.approx(0.0)
        assert float(srgb_encode(1.5)) == pytest.approx(1.0)


class TestToneMapGamma:
    """The exponent that squeezes an over-range scene onto the display.

    This is a statement about the SCREEN, not a model of vision, and it must
    stay switched off wherever the scene already fits.
    """

    def test_scene_that_fits_is_left_alone(self):
        assert tone_map_gamma(2.0) == 1.0            # the Moon
        assert tone_map_gamma(200.0) == 1.0          # exactly the display
        assert tone_map_gamma(1.0) == 1.0            # a single star

    def test_planets_need_no_compression(self):
        # Jupiter ~203:1, Saturn ~484:1 measured. Jupiter must be exact;
        # Saturn is allowed to compress, but only slightly.
        assert tone_map_gamma(203.0) > 0.99
        assert tone_map_gamma(484.0) > 0.85

    def test_maps_the_scene_exactly_onto_the_display(self):
        """The defining property: an S:1 scene must come out D:1."""
        for scene in (1000.0, 1e4, 1e6):
            g = tone_map_gamma(scene, 200.0)
            assert scene ** g == pytest.approx(200.0, rel=1e-9)

    def test_star_field_compresses(self):
        # saturation_demo spans mag -1..6.5 = 1000:1.
        assert tone_map_gamma(1000.0) == pytest.approx(0.767, abs=0.002)

    def test_degenerate_input_is_safe(self):
        assert tone_map_gamma(0.0) == 1.0
        assert tone_map_gamma(-5.0) == 1.0


class TestPhotometricFidelity:
    """R5.8: does the RENDERER actually put simulated light on the screen?

    Every assertion here decodes what the renderer emits back to screen
    luminance -- what the monitor emits and the observer's eye receives --
    and compares it to the physics. Measuring in code-value space instead
    would silently pass a broken pipeline, which is how this went unnoticed.
    """

    _PROBE = 0.02          # low enough that Jupiter's disk does not clip
    _EXPOSURE = 0.3        # the scenario default; at 1.0 the disk saturates
                           # and every contrast measurement reads zero

    @staticmethod
    def _lum(rgb):
        from telescope_sim.physics.colorimetry import srgb_decode
        rgb = srgb_decode(np.asarray(rgb, dtype=float))
        return (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1]
                + 0.0722 * rgb[..., 2])

    @staticmethod
    def _contrast(v):
        p10, p50, p90 = np.percentile(v, [10, 50, 90])
        return (p90 - p10) / max(p50, 1e-12)

    def _render(self, diameter=200.0, **kw):
        import dataclasses
        from telescope_gui.tutorial_mode.scenario_registry import (
            get_scenario_by_id)
        from telescope_gui.tutorial_mode.scenario_runner import build_source
        from telescope_gui.telescope_builder import build_telescope
        from telescope_sim.plotting.ray_trace_plot import (
            _render_source_through_telescope)

        sc = get_scenario_by_id("color_filter_jupiter")
        src = build_source(sc.after_source)
        cfg = dataclasses.replace(sc.after_telescope, diameter=diameter)
        tel = build_telescope(**dataclasses.asdict(cfg))
        kw.setdefault("exit_pupil_mm", 7.0)
        _, _, info = _render_source_through_telescope(
            src, tel, filter_name="None", **kw)
        return info

    @pytest.fixture(scope="class")
    def _truth(self):
        """Unclipped linear render + the disk mask, defined ONCE.

        Both views must be measured over the SAME pixels; letting each pick
        its own threshold compares different pixel sets and manufactures a
        difference that is not there.
        """
        info = self._render(display_stretch="linear",
                            exposure_level=self._PROBE)
        lum = self._lum(info["image_rgb"]) / self._PROBE
        assert (np.asarray(info["image_rgb"]) < 0.999).all(), (
            "probe exposure clipped; contrast would read as zero")
        disk = lum > 0.25 * lum.max()
        return lum, disk, self._contrast(lum[disk])

    def test_detector_view_reproduces_real_contrast(self, _truth):
        """Was 2.15x too punchy: linear radiance went straight to imshow,
        so the monitor emitted radiance**2.2."""
        _, disk, true_c = _truth
        info = self._render(display_stretch="linear",
                            exposure_level=self._EXPOSURE)
        # Guard the measurement, not the image: a percentile contrast is
        # meaningless once a large share of the disk saturates to a flat
        # 1.0. At exposure 1.0 essentially all of it does, and this test
        # would then read 0.0 and look like a transfer-function bug.
        # The highest percentile this contrast measure reads is p90, so the
        # bound that matters is 10% -- take half of it for margin. (At the
        # scenario default ~1.8% of the disk saturates and the contrast is
        # still exact; at exposure 1.0 nearly all of it does and the
        # measurement collapses to 0.0, which would look like a
        # transfer-function bug rather than a saturated frame.)
        clipped = (np.asarray(info["image_rgb"]).max(axis=2)[disk] > 0.999)
        assert clipped.mean() < 0.05, (
            f"{clipped.mean():.1%} of the disk is saturated; p90 is no "
            f"longer measurable, so this test cannot mean what it says")
        got = self._contrast(self._lum(info["image_rgb"])[disk])
        assert got == pytest.approx(true_c, rel=0.10)

    def test_eye_view_reproduces_real_contrast(self, _truth):
        """Was 2.1x too flat: an asinh stretch compressed a scene that the
        observer's own eye was about to compress again."""
        _, disk, true_c = _truth
        info = self._render(display_stretch="log",
                            exposure_level=self._EXPOSURE)
        got = self._contrast(self._lum(info["image_rgb"])[disk])
        assert got == pytest.approx(true_c, rel=0.10)

    def test_both_views_agree_on_contrast(self, _truth):
        """The Detector-vs-Eye comparison is only honest if neither side is
        secretly rendered through a different curve."""
        _, disk, _ = _truth
        d = self._contrast(self._lum(
            self._render(display_stretch="linear",
                         exposure_level=self._EXPOSURE)["image_rgb"])[disk])
        e = self._contrast(self._lum(
            self._render(display_stretch="log",
                         exposure_level=self._EXPOSURE)["image_rgb"])[disk])
        assert d == pytest.approx(e, rel=0.10)

    def test_exit_pupil_moves_surface_brightness_as_the_square(self, _truth):
        """R5.8b. Surface brightness goes as (p/7mm)^2, so 1mm -> 7mm is
        49x. The asinh stretch squashed that to 2.56x, which is why the
        control appeared dead."""
        _, disk, _ = _truth
        ref = None
        for p in (1.0, 3.0, 7.0):
            info = self._render(display_stretch="log",
                                exposure_level=self._EXPOSURE,
                                exit_pupil_mm=p)
            med = np.percentile(self._lum(info["image_rgb"])[disk], 50)
            if ref is None:
                ref, sb_ref = med, info["eye_surface_brightness_factor"]
                continue
            expected = info["eye_surface_brightness_factor"] / sb_ref
            assert med / ref == pytest.approx(expected, rel=0.05)

    def test_detector_brightness_scales_as_aperture_squared(self, _truth):
        """Doubling the aperture must put 4x the light on the screen.

        Exposure 1.0 is deliberate. sRGB has a LINEAR toe below 0.0031
        (code 0.04), where encode and decode are just a factor of 12.92 and
        an unencoded pipeline scales identically to an encoded one. At the
        probe exposure Jupiter's whole disk sits inside that toe, and this
        test could not tell a correct renderer from a broken one -- it
        passed against the pre-R5.8 code. Here the disk lands at 0.15 and
        0.59 of full scale: above the toe, below saturation.
        """
        _, disk, _ = _truth
        med = {}
        for d in (50.0, 100.0):
            info = self._render(diameter=d, display_stretch="linear",
                                exposure_level=1.0)
            code = np.asarray(info["image_rgb"]).max(axis=2)[disk]
            assert (code > 0.999).mean() < 0.01, "saturated; ratio is capped"
            assert np.percentile(code, 50) > 0.04, "in the sRGB linear toe"
            med[d] = np.percentile(self._lum(info["image_rgb"])[disk], 50)
        assert med[100.0] / med[50.0] == pytest.approx(4.0, rel=0.05)

    def test_planets_are_rendered_without_compression(self):
        """Jupiter fits a screen, so the tone map must stay switched off --
        otherwise every planetary module quietly stops being photometric."""
        info = self._render(display_stretch="linear",
                            exposure_level=self._EXPOSURE)
        assert info["tone_gamma"] == 1.0


class TestGreyscaleDisplayPath:
    """R5.8: the colormapped path needs the same transfer function -- but it
    also carries a numeric colorbar, so the ARRAY must stay linear.

    Encoding the array itself would turn ticks labelled "Normalized
    intensity" into sRGB code values without changing the label. A third of
    the tutorial's source renders take this path.
    """

    def test_renderer_leaves_the_greyscale_array_linear(self):
        """Regression guard: `image` must not be encoded in place."""
        import dataclasses
        from telescope_gui.tutorial_mode.scenario_registry import (
            get_scenario_by_id)
        from telescope_gui.tutorial_mode.scenario_runner import build_source
        from telescope_gui.telescope_builder import build_telescope
        from telescope_sim.plotting.ray_trace_plot import (
            _render_source_through_telescope)

        sc = get_scenario_by_id("saturation_demo")
        src = build_source(sc.after_source)
        tel = build_telescope(**dataclasses.asdict(sc.after_telescope))
        image, _, info = _render_source_through_telescope(
            src, tel, display_stretch=sc.default_display_stretch,
            exposure_level=sc.default_exposure, filter_name="None")
        assert info["image_rgb"] is None, "expected the greyscale path"

        # Discriminate by PHYSICS, not by shape. "An encoded array would
        # look different" is not a test -- encoding twice moves values just
        # as much as encoding once, so a shape check passes either way (it
        # did). What only a linear array can do is obey Pogson's law: one
        # magnitude of difference is a flux ratio of exactly 2.512, and any
        # display encode destroys that.
        peaks = self._star_peaks(image, src, half_fov=info["half_fov_arcsec"])
        usable = [(m, p) for m, p in peaks if 0.001 < p < 0.99]
        assert len(usable) >= 3, "need unsaturated, above-noise stars"
        mags = np.array([m for m, _ in usable])
        inst = -2.5 * np.log10([p for _, p in usable])
        # inst_mag should track true mag one-for-one.
        slope = np.polyfit(mags, inst, 1)[0]
        assert slope == pytest.approx(1.0, abs=0.06), (
            f"flux ratios follow slope {slope:.3f}, not Pogson's 1.0 -- the "
            f"greyscale array is not linear radiance")

    @staticmethod
    def _star_peaks(image, src, half_fov):
        n = image.shape[0]
        px = 2.0 * half_fov / n
        out = []
        for x, y, m in zip(src.star_x_arcsec, src.star_y_arcsec,
                           src.star_magnitudes):
            cx, cy = int(round(n / 2 + x / px)), int(round(n / 2 + y / px))
            if not (0 <= cx < n and 0 <= cy < n):
                continue
            box = image[max(cy - 6, 0):cy + 7, max(cx - 6, 0):cx + 7]
            if box.size:
                out.append((float(m), float(box.max())))
        return out

    def test_norm_round_trips_so_colorbar_ticks_are_truthful(self):
        from telescope_sim.plotting.ray_trace_plot import _DisplayNorm
        for gamma in (1.0, 0.767, 0.5):
            norm = _DisplayNorm(gamma)
            data = np.array([0.0, 0.05, 0.1, 0.25, 0.5, 0.75, 1.0])
            back = norm.inverse(np.asarray(norm(data)))
            assert np.abs(back - data).max() < 1e-12

    def test_norm_makes_the_picture_photometric(self):
        """decode(what the colormap receives) must be proportional to the
        linear data -- the same guarantee the RGB path gets."""
        from telescope_sim.plotting.ray_trace_plot import _DisplayNorm
        from telescope_sim.physics.colorimetry import srgb_decode
        data = np.array([0.05, 0.1, 0.2, 0.4, 0.8, 1.0])
        screen = srgb_decode(np.asarray(_DisplayNorm(1.0)(data)))
        ratio = screen / data
        assert ratio.max() / ratio.min() == pytest.approx(1.0, abs=1e-9)

    def test_colorbar_keeps_intensity_units(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from telescope_sim.plotting.ray_trace_plot import (
            _draw_source_on_axes)

        fig, ax = plt.subplots()
        img = np.linspace(0.0, 1.0, 64 * 64).reshape(64, 64)
        _draw_source_on_axes(ax, img, None, 10.0, False, "gray", fig,
                             tone_gamma=1.0)
        cbar_ax = [a for a in fig.axes if a is not ax][0]
        assert cbar_ax.get_ylabel() == "Normalized intensity"
        lo, hi = cbar_ax.get_ylim()
        assert (lo, hi) == pytest.approx((0.0, 1.0))
        plt.close(fig)


class TestToneMapDisclosure:
    """CLAUDE.md physics policy: where the render is not real physics, the
    FIGURE has to say so -- not just a code comment.

    `saturation_demo` is the only scenario whose scene (1000:1) exceeds what
    a screen can emit, so it is the only one that may carry the notice, and
    it must.
    """

    @staticmethod
    def _annotation(scenario_id):
        import dataclasses
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from telescope_gui.tutorial_mode.scenario_registry import (
            get_scenario_by_id)
        from telescope_gui.tutorial_mode.scenario_runner import build_source
        from telescope_gui.telescope_builder import build_telescope
        from telescope_sim.plotting.ray_trace_plot import plot_source_image

        sc = get_scenario_by_id(scenario_id)
        src = build_source(sc.after_source)
        tel = build_telescope(**dataclasses.asdict(sc.after_telescope))
        figs = plot_source_image(
            tel, src, display_stretch=sc.default_display_stretch,
            exposure_level=sc.default_exposure)
        figs = figs if isinstance(figs, list) else [figs]
        text = " ".join(t.get_text() for f in figs for a in f.axes
                        for t in a.texts)
        for f in figs:
            plt.close(f)
        return text

    def test_compressed_scene_says_so_on_the_figure(self):
        text = self._annotation("saturation_demo")
        assert "tone-mapped" in text
        assert "not photometric" in text
        assert "0.77" in text, "the actual exponent must be stated"

    def test_faithful_scene_claims_no_compression(self):
        text = self._annotation("color_filter_jupiter")
        assert "tone-mapped" not in text
        assert "sRGB encoded" in text

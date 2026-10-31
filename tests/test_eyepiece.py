"""Tests for Eyepiece dataclass and presets."""

import numpy as np
import pytest

from telescope_sim.geometry.eyepiece import Eyepiece, EYEPIECE_PRESETS
from telescope_sim.plotting.ray_trace_plot import _apply_exit_pupil_washout


class TestEyepiece:
    """Tests for Eyepiece calculations."""

    def setup_method(self):
        self.eyepiece = Eyepiece(focal_length_mm=25.0, apparent_fov_deg=50.0)
        self.telescope_fl = 1000.0  # mm
        self.primary_diameter = 200.0  # mm

    def test_magnification(self):
        """1000mm / 25mm = 40x."""
        mag = self.eyepiece.magnification(self.telescope_fl)
        assert mag == pytest.approx(40.0)

    def test_true_fov(self):
        """50 deg AFOV / 40x = 1.25 deg = 4500 arcsec."""
        tfov = self.eyepiece.true_fov_arcsec(self.telescope_fl)
        assert tfov == pytest.approx(4500.0)

    def test_true_fov_arcmin(self):
        """4500 arcsec = 75 arcmin."""
        tfov = self.eyepiece.true_fov_arcmin(self.telescope_fl)
        assert tfov == pytest.approx(75.0)

    def test_exit_pupil(self):
        """200mm / 40x = 5.0mm."""
        ep = self.eyepiece.exit_pupil_mm(self.primary_diameter,
                                         self.telescope_fl)
        assert ep == pytest.approx(5.0)

    def test_high_magnification(self):
        """5mm eyepiece with 1000mm scope = 200x."""
        ep = Eyepiece(focal_length_mm=5.0, apparent_fov_deg=82.0)
        assert ep.magnification(self.telescope_fl) == pytest.approx(200.0)

    def test_from_preset(self):
        """Load plossl_25mm preset and verify values."""
        ep = Eyepiece.from_preset("plossl_25mm")
        assert ep.focal_length_mm == pytest.approx(25.0)
        assert ep.apparent_fov_deg == pytest.approx(50.0)

    def test_from_preset_wide(self):
        """Load wide_20mm preset."""
        ep = Eyepiece.from_preset("wide_20mm")
        assert ep.focal_length_mm == pytest.approx(20.0)
        assert ep.apparent_fov_deg == pytest.approx(68.0)

    def test_unknown_preset_raises(self):
        """Unknown preset name should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown eyepiece preset"):
            Eyepiece.from_preset("nonexistent_99mm")

    def test_all_presets_loadable(self):
        """All entries in EYEPIECE_PRESETS should create valid Eyepiece."""
        for name in EYEPIECE_PRESETS:
            ep = Eyepiece.from_preset(name)
            assert ep.focal_length_mm > 0
            assert ep.apparent_fov_deg > 0


class TestTrueFieldOfViewBasis:
    """R5.9/S1: TFOV has two formulas and the caller must know which ran.

    `Eyepiece` is shared code — `main.py` and the single-telescope Design tab
    consume it as much as the tutorial does — so these are unit tests on the
    model rather than on any GUI, per the physics-propagation rule.
    """

    def test_field_stop_gives_the_exact_plate_scale_answer(self):
        """A field stop is a real aperture: TFOV = 206265 * d / f_tel."""
        ep = Eyepiece(focal_length_mm=25.0, apparent_fov_deg=50.0,
                      field_stop_mm=21.2)
        assert ep.tfov_is_exact
        assert ep.true_fov_arcsec(1000.0) == pytest.approx(
            206265.0 * 21.2 / 1000.0)

    def test_field_stop_answer_is_independent_of_stated_afov(self):
        """The exact formula must not consult AFOV at all.

        This is the whole reason the field stop is better: it bypasses the
        eyepiece's internal mapping. If a caller mislabels the apparent
        field, the field-stop TFOV should be unmoved.
        """
        a = Eyepiece(25.0, 50.0, field_stop_mm=21.2).true_fov_arcsec(1000.0)
        b = Eyepiece(25.0, 82.0, field_stop_mm=21.2).true_fov_arcsec(1000.0)
        assert a == pytest.approx(b)

    def test_afov_fallback_is_flagged_not_silent(self):
        ep = Eyepiece(focal_length_mm=25.0, apparent_fov_deg=50.0)
        assert not ep.tfov_is_exact
        assert ep.true_fov_arcsec(1000.0) == pytest.approx(4500.0)
        assert "approx" in ep.summary(1000.0, 200.0).lower()

    def test_summary_states_the_basis_when_exact(self):
        ep = Eyepiece(25.0, 50.0, field_stop_mm=21.2)
        assert "field stop" in ep.summary(1000.0, 200.0)

    def test_afov_over_mag_is_optimistic_against_a_real_field_stop(self):
        """The approximation admits more sky than the real eyepiece does.

        A 25 mm Plossl's published field stop (~21.2 mm) is under the 23.3 mm
        a distortion-free design would need, so AFOV/M overstates the true
        field by a few percent. Pinning the SIGN and the rough SIZE of that
        error is what makes the disclosure meaningful.
        """
        approx = Eyepiece(25.0, 50.0).true_fov_arcsec(1000.0)
        exact = Eyepiece(25.0, 50.0, field_stop_mm=21.2).true_fov_arcsec(1000.0)
        assert exact < approx
        assert (approx - exact) / exact < 0.05

    def test_nominal_field_stop_is_not_used_as_a_default(self):
        """The geometric estimate must not silently become the answer.

        `nominal_field_stop_mm` is offered for comparison; wiring it in as a
        default would swap an honest approximation for a confident wrong
        number, since real eyepieces run under it.
        """
        ep = Eyepiece(25.0, 50.0)
        assert ep.field_stop_mm is None
        assert not ep.tfov_is_exact
        assert ep.nominal_field_stop_mm() == pytest.approx(
            2.0 * 25.0 * np.tan(np.radians(50.0) / 2.0))
        # and it is indeed larger than the real published stop
        assert ep.nominal_field_stop_mm() > 21.2


class TestUsefulMagnificationIsDerived:
    """R5.9/S1: the magnification limits come from pupils, not from lore."""

    def test_max_useful_reproduces_the_two_times_aperture_rule(self):
        """D / 0.5mm == 2 * D. The rule of thumb IS the exit-pupil criterion.

        Deriving it has to give the same number, or the derivation is wrong
        rather than the rule. This is the load-bearing check that S1 changed
        the explanation without changing the physics.
        """
        ep = Eyepiece(10.0, 50.0)
        for d in (60.0, 100.0, 200.0, 355.6):
            assert ep.max_useful_magnification(d) == pytest.approx(2.0 * d)

    def test_max_useful_lands_at_the_threshold_exit_pupil(self):
        from telescope_sim.geometry.eyepiece import MIN_USEFUL_EXIT_PUPIL_MM
        d = 200.0
        m = Eyepiece(10.0, 50.0).max_useful_magnification(d)
        assert d / m == pytest.approx(MIN_USEFUL_EXIT_PUPIL_MM)

    def test_threshold_actually_drives_the_limit(self, monkeypatch):
        """Changing the exit-pupil threshold must move the limit.

        The two tests above assert D/0.5 == 2*D, which is true of the derived
        form AND of a hard-coded `* 2.0` — they pin the agreement, not the
        derivation. This one pins the derivation: if the empirical threshold
        is ever revised (it is a physiological estimate, not a constant of
        nature), the maximum useful magnification has to follow it rather than
        keeping a stale doubled aperture.
        """
        from telescope_sim.geometry import eyepiece as eyepiece_mod

        ep = Eyepiece(10.0, 50.0)
        monkeypatch.setattr(eyepiece_mod, "MIN_USEFUL_EXIT_PUPIL_MM", 1.0)
        assert ep.max_useful_magnification(200.0) == pytest.approx(200.0)

    def test_min_useful_tracks_the_observers_pupil(self):
        """An older observer's smaller pupil raises the minimum magnification.

        The default 7 mm is a young dark-adapted eye; ~5 mm by middle age
        raises the limit 40%. This is an observer property, so it must not be
        frozen into the telescope model.
        """
        young = Eyepiece(25.0, 50.0, eye_pupil_mm=7.0)
        older = Eyepiece(25.0, 50.0, eye_pupil_mm=5.0)
        assert young.min_useful_magnification(200.0) == pytest.approx(200 / 7)
        assert older.min_useful_magnification(200.0) == pytest.approx(40.0)
        assert older.min_useful_magnification(200.0) > \
            young.min_useful_magnification(200.0)

    def test_default_eye_pupil_preserves_legacy_behaviour(self):
        """Existing consumers (main.py, design_tab) must not shift.

        The pre-S1 code hard-coded D/7. Anything else here would silently
        change what the Design tab reports, and single-mode rendering is
        deliberately unverified right now.
        """
        assert Eyepiece(25.0, 50.0).min_useful_magnification(200.0) == \
            pytest.approx(200.0 / 7.0)

    def test_renderer_and_eyepiece_share_one_eye_pupil(self):
        """One observer, one pupil — the renderer must not keep its own copy.

        S1 briefly defined the dark-adapted pupil twice: `EYE_PUPIL_MM` in
        `ray_trace_plot` (eye-view surface brightness, which falls as
        (p/7mm)^2) and `DEFAULT_EYE_PUPIL_MM` here (minimum useful
        magnification). They are the same physical quantity. Two independent
        literals means a later correction to one leaves the brightness model
        and the eyepiece model describing different eyes, silently.

        Identity, not equality: `==` would still pass if someone re-typed the
        literal, which is exactly the regression this guards.
        """
        from telescope_sim.geometry.eyepiece import DEFAULT_EYE_PUPIL_MM
        from telescope_sim.plotting import ray_trace_plot

        assert ray_trace_plot.EYE_PUPIL_MM is DEFAULT_EYE_PUPIL_MM


class TestPaddingMatchesTheSkyLevel:
    """R5.9/S2: padding a washed-out image with zero drew a bright square.

    `_apply_exit_pupil_washout` blends the frame toward its mean, so black
    sky comes out at a pedestal rather than at zero. `_crop_or_pad_to_fov`
    then padded with hard zeros, leaving a step at the edge of the simulated
    field — visible as a brighter square inside the circular eyepiece field
    whenever the true field is wider than the source's rendered field.
    """

    def test_pad_uses_the_image_floor_not_zero(self):
        from telescope_sim.plotting.ray_trace_plot import _crop_or_pad_to_fov

        # A frame whose darkest pixel is well above zero, exactly as the
        # washout leaves it.
        img = np.full((64, 64), 0.9)
        img[16:48, 16:48] = 1.0
        out, _, half = _crop_or_pad_to_fov(img, None, 1000.0, 2000.0)
        assert half == pytest.approx(2000.0)
        assert out.min() == pytest.approx(0.9), (
            "padded region is darker than any real sky in the frame")

    def test_pad_still_black_when_the_sky_is_black(self):
        """The fix must not brighten ordinary un-washed renders."""
        from telescope_sim.plotting.ray_trace_plot import _crop_or_pad_to_fov

        img = np.zeros((64, 64))
        img[24:40, 24:40] = 1.0
        out, _, _ = _crop_or_pad_to_fov(img, None, 1000.0, 2000.0)
        assert out.min() == pytest.approx(0.0)

    def test_rgb_padding_matches_per_channel(self):
        from telescope_sim.plotting.ray_trace_plot import _crop_or_pad_to_fov

        img = np.full((64, 64), 0.5)
        rgb = np.zeros((64, 64, 3))
        rgb[..., 0] = 0.4
        rgb[..., 1] = 0.3
        rgb[..., 2] = 0.2
        rgb[16:48, 16:48] = 1.0
        _, out_rgb, _ = _crop_or_pad_to_fov(img, rgb, 1000.0, 2000.0)
        for c, floor in enumerate((0.4, 0.3, 0.2)):
            assert out_rgb[0, 0, c] == pytest.approx(floor)

    def test_eyepiece_view_has_no_square_edge(self):
        """End-to-end, through the same detector the GUI sweep uses.

        The unit tests above pin the helper; this one pins the thing the
        user would actually see, at the eyepiece where the bug appeared: a
        32 mm on a 200 mm f/5 gives a 5760" true field around the Moon's
        2431" rendered field, so the padding is more than half the frame.
        """
        import matplotlib.pyplot as plt
        from tests.test_gui_controls import worst_box_score, BOX_THRESHOLD
        from telescope_gui.telescope_builder import build_telescope
        from telescope_sim.geometry.eyepiece import Eyepiece
        from telescope_sim.plotting.ray_trace_plot import plot_source_image
        from telescope_sim.source.sources import Moon

        telescope = build_telescope(
            telescope_type="Newtonian", diameter=200.0, focal_length=1000.0,
            primary_type="parabolic", enable_obstruction=True,
            obstruction_ratio=0.20, spider_vanes=4)
        ep = Eyepiece(focal_length_mm=32.0, apparent_fov_deg=50.0)
        figs = plot_source_image(
            telescope, Moon(), seeing_arcsec=2.0, figsize=(5, 5),
            display_stretch="log", eyepiece=ep,
            eyepiece_view_figsize=(5, 5),
            exit_pupil_mm=ep.exit_pupil_mm(telescope.primary_diameter,
                                           telescope.focal_length))
        assert isinstance(figs, list) and len(figs) == 3
        arr = np.asarray(figs[2].axes[0].get_images()[0].get_array(),
                         dtype=float)
        if arr.ndim == 3:
            arr = arr.max(axis=2)
        score = worst_box_score(arr)
        assert score <= BOX_THRESHOLD, (
            f"square edge at the padding boundary, box score {score:.1f}")
        for f in figs:
            plt.close(f)


class TestEyepieceFiguresKeepTheirBrightness:
    """The true-size and Eyepiece View figures must not re-normalise.

    The image reaching the eyepiece figures is already on the shared display
    scale (in the Detector view, set by the exposure). Both figures used to
    divide by their own max after `_crop_or_pad_to_fov`, which stretched a
    dim exposure back to full white in the very figures meant to match the
    standard view (single-mode follow-up, issue 2). Reverting that fix makes
    the dim Detector cases below read 1.0.
    """

    @staticmethod
    def _figure_peaks(source, eyepiece, stretch, exposure):
        import matplotlib.pyplot as plt
        from telescope_gui.telescope_builder import build_telescope
        from telescope_sim.plotting.ray_trace_plot import plot_source_image

        telescope = build_telescope(
            telescope_type="Newtonian", diameter=200.0, focal_length=1000.0,
            primary_type="parabolic", enable_obstruction=True,
            obstruction_ratio=0.20, spider_vanes=4)
        figs = plot_source_image(
            telescope, source, seeing_arcsec=2.0, num_pixels=256,
            figsize=(5, 5), display_stretch=stretch, exposure_level=exposure,
            eyepiece=eyepiece, eyepiece_view_figsize=(5, 5))
        peaks = []
        for f in figs:
            arr = np.asarray(f.axes[0].get_images()[0].get_array(),
                             dtype=float)
            peaks.append(float(arr.max()))
            plt.close(f)
        return peaks

    # A 5 mm eyepiece on 200 mm f/5: 200×, 1 mm exit pupil, 900" true field.
    # That crops the Moon (2431" field) and pads Jupiter (60" field), so both
    # branches of `_crop_or_pad_to_fov` are covered.
    @pytest.mark.parametrize("source_name", ["Moon", "Jupiter"])
    @pytest.mark.parametrize("stretch,exposure",
                             [("log", 1.0), ("linear", 0.2)])
    def test_all_three_figures_share_one_peak(self, source_name, stretch,
                                              exposure):
        from telescope_sim.source import sources

        source = getattr(sources, source_name)()
        enhanced, true_size, eyepiece_view = self._figure_peaks(
            source, Eyepiece(5.0, 50.0), stretch, exposure)

        # Dim to begin with — otherwise the comparison cannot tell a
        # re-normalised figure from a correct one. (The Eye view shows the
        # object near its naked-eye level, so only Detector is dim here.)
        if stretch == "linear":
            assert enhanced < 0.9
        assert true_size == pytest.approx(eyepiece_view)
        # Padding resamples the source with bilinear zoom, which can shave
        # a few percent off a small disk's peak; re-normalising would add
        # far more than 10 % here (up to ~7×).
        assert true_size == pytest.approx(enhanced, rel=0.10), (
            f"{source_name} {stretch}: true-size peak {true_size:.3f} vs "
            f"standardized {enhanced:.3f} — eyepiece figure re-normalised?")

    def test_eye_view_not_dimmed_by_small_exit_pupil(self):
        """A 1 mm exit pupil is 1/49 of naked-eye surface brightness in
        cd/m², but the adapted eye still sees a well-lit Moon — rendering
        the 1/49 literally left these figures near black (peak ~0.15)."""
        from telescope_sim.source.sources import Moon

        peaks = self._figure_peaks(Moon(), Eyepiece(5.0, 50.0), "log", 1.0)
        assert min(peaks) > 0.5, f"eyepiece figures dimmed: {peaks}"


class TestWashoutFunction:
    """Unit tests for _apply_exit_pupil_washout."""

    def test_small_exit_pupil_no_washout(self):
        """Exit pupil 1.0mm should produce near-zero washout."""
        image = np.random.default_rng(42).random((32, 32))
        original = image.copy()
        result, _, washout = _apply_exit_pupil_washout(image, None, 1.0)
        assert washout < 0.05
        # Image should be nearly unchanged
        np.testing.assert_allclose(result, original, atol=0.05)

    def test_large_exit_pupil_strong_washout(self):
        """Exit pupil 5.0mm should produce washout > 0.9."""
        image = np.random.default_rng(42).random((32, 32))
        _, _, washout = _apply_exit_pupil_washout(image, None, 5.0)
        assert washout > 0.9

    def test_medium_exit_pupil_moderate_washout(self):
        """Exit pupil 3.0mm should produce ~0.5 washout."""
        image = np.random.default_rng(42).random((32, 32))
        _, _, washout = _apply_exit_pupil_washout(image, None, 3.0)
        assert 0.3 < washout < 0.7

    def test_contrast_reduced_at_large_pupil(self):
        """Large exit pupil should reduce image contrast (std dev)."""
        rng = np.random.default_rng(42)
        image = rng.random((64, 64))
        original_std = image.std()
        result, _, _ = _apply_exit_pupil_washout(image, None, 5.0)
        assert result.std() < original_std * 0.5

    def test_all_zero_image(self):
        """All-zero input should produce all-zero output, no NaN/inf."""
        image = np.zeros((32, 32))
        result, _, washout = _apply_exit_pupil_washout(image, None, 5.0)
        assert np.all(np.isfinite(result))
        np.testing.assert_allclose(result, 0.0, atol=1e-12)

    def test_uniform_image(self):
        """Constant 0.5 image should stay uniform (std ~ 0) after washout."""
        image = np.full((32, 32), 0.5)
        result, _, _ = _apply_exit_pupil_washout(image, None, 5.0)
        assert result.std() < 1e-10

    def test_rgb_none_passthrough(self):
        """When image_rgb is None, returned rgb should also be None."""
        image = np.random.default_rng(42).random((32, 32))
        _, result_rgb, _ = _apply_exit_pupil_washout(image, None, 5.0)
        assert result_rgb is None

    def test_no_inplace_mutation(self):
        """Input arrays should not be modified by the function."""
        rng = np.random.default_rng(42)
        image = rng.random((32, 32))
        image_rgb = rng.random((32, 32, 3))
        image_orig = image.copy()
        rgb_orig = image_rgb.copy()
        _apply_exit_pupil_washout(image, image_rgb, 5.0)
        np.testing.assert_array_equal(image, image_orig)
        np.testing.assert_array_equal(image_rgb, rgb_orig)

    def test_empty_sky_stays_dark(self):
        """Washout must not light up sky that has no light in it.

        R5.9/S2: blending toward the FRAME mean lifted black sky to
        mean*(1-contrast_factor) — 0.68 for the Moon at a 6.4 mm exit pupil,
        so the night sky inside the eyepiece field rendered bright grey.
        Contrast reduction is a statement about detail on the object, not a
        licence to add light where none was collected.
        """
        image = np.zeros((128, 128))
        image[40:88, 40:88] = 1.0          # bright object, dark surround
        result, _, _ = _apply_exit_pupil_washout(image, None, 6.4)
        corner = result[:16, :16]
        assert corner.max() < 0.02, (
            f"empty sky lit to {corner.max():.3f} by the washout")

    def test_light_elsewhere_does_not_change_this_objects_contrast(self):
        """Washout must be local: distant light is not this object's business.

        R5.9/S2. Blending toward the FRAME mean coupled every pixel to every
        other one, so how washed-out an object looked depended on what else
        happened to be in the frame — and, in the eyepiece view, on how much
        empty sky the field of view included. Adding a bright patch in the
        far corner must leave this object's rendered contrast alone.

        (The blur scale is deliberately a fraction of the FRAME, not a fixed
        pixel count: the field maps to the eyepiece's fixed apparent field,
        so a constant fraction of the frame is a constant apparent angle to
        the observer, which is the scale the eye's response is defined on.)
        """
        alone = np.zeros((128, 128))
        alone[48:80, 48:80] = np.linspace(0.4, 1.0, 32)

        with_company = alone.copy()
        with_company[8:24, 100:120] = 1.0      # unrelated bright patch

        a_out, _, _ = _apply_exit_pupil_washout(alone, None, 6.4)
        b_out, _, _ = _apply_exit_pupil_washout(with_company, None, 6.4)

        # Compare the rendered object pixel by pixel, not by their range: the
        # frame-mean defect shifts the whole object by a constant, and a range
        # is blind to a constant offset. The claim is that the object renders
        # *identically*, so that is what gets asserted.
        a_patch = a_out[48:80, 48:80]
        b_patch = b_out[48:80, 48:80]
        worst = float(np.abs(a_patch - b_patch).max())
        assert worst < 0.005, (
            f"light elsewhere in the frame changed this object by up to "
            f"{worst:.3f}; washout is not local (object mean {a_patch.mean():.3f} "
            f"alone vs {b_patch.mean():.3f} with a bright patch in the corner)")

    def test_rgb_desaturated_at_large_pupil(self):
        """Large exit pupil should desaturate RGB toward luminance."""
        rng = np.random.default_rng(42)
        image = rng.random((32, 32))
        image_rgb = rng.random((32, 32, 3))
        # Measure color spread before
        lum_before = (0.2126 * image_rgb[..., 0]
                      + 0.7152 * image_rgb[..., 1]
                      + 0.0722 * image_rgb[..., 2])
        color_spread_before = sum(
            np.std(image_rgb[..., c] - lum_before) for c in range(3))
        _, result_rgb, _ = _apply_exit_pupil_washout(image, image_rgb, 5.0)
        lum_after = (0.2126 * result_rgb[..., 0]
                     + 0.7152 * result_rgb[..., 1]
                     + 0.0722 * result_rgb[..., 2])
        color_spread_after = sum(
            np.std(result_rgb[..., c] - lum_after) for c in range(3))
        assert color_spread_after < color_spread_before * 0.5

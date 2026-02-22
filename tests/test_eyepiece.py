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

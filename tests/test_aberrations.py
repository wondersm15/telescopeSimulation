"""Tests for the aberrations (coma) physics module."""

import numpy as np
import pytest

from telescope_sim.physics.aberrations import (
    compute_coma_spot,
    compute_coma_rms,
    coma_free_field,
)
from telescope_sim.plotting.ray_trace_plot import _build_coma_spot_2d


class TestComputeComaSpot:
    """Tests for the coma spot computation."""

    def test_on_axis_zero(self):
        """On-axis (0 arcsec) should produce zero offsets."""
        x, y = compute_coma_spot(0.0, 1000.0, 200.0)
        assert np.allclose(x, 0.0, atol=1e-15)
        assert np.allclose(y, 0.0, atol=1e-15)

    def test_increases_with_field_angle(self):
        """Coma should increase with field angle."""
        x1, y1 = compute_coma_spot(30.0, 1000.0, 200.0)
        x2, y2 = compute_coma_spot(60.0, 1000.0, 200.0)
        rms1 = np.sqrt(np.mean(x1 ** 2 + y1 ** 2))
        rms2 = np.sqrt(np.mean(x2 ** 2 + y2 ** 2))
        assert rms2 > rms1

    def test_linear_in_field_angle(self):
        """Coma RMS should scale linearly with field angle."""
        rms1 = compute_coma_rms(30.0, 1000.0, 200.0)
        rms2 = compute_coma_rms(60.0, 1000.0, 200.0)
        # Should be close to 2:1 ratio
        assert rms2 / rms1 == pytest.approx(2.0, rel=0.05)

    def test_output_shape(self):
        """Output arrays should have expected shape."""
        n_zones = 20
        n_azimuth = 36
        x, y = compute_coma_spot(60.0, 1000.0, 200.0,
                                  num_pupil_zones=n_zones,
                                  num_azimuthal=n_azimuth)
        assert x.shape == (n_zones * n_azimuth,)
        assert y.shape == (n_zones * n_azimuth,)

    def test_tangential_larger_than_sagittal(self):
        """Max x offset should be ~3x the max y offset (sagittal coma).

        For Seidel coma: x ranges from C_s to 3*C_s (all positive),
        y ranges from -C_s to +C_s.  So max(x) / max(|y|) ~ 3.
        """
        x, y = compute_coma_spot(60.0, 1000.0, 200.0,
                                  num_pupil_zones=100,
                                  num_azimuthal=144)
        max_y = np.max(np.abs(y))
        max_x = np.max(x)
        # Tangential max should be ~3x sagittal max
        if max_y > 1e-15:
            ratio = max_x / max_y
            assert 2.0 < ratio < 4.0


class TestComputeComaRMS:
    """Tests for the coma RMS computation."""

    def test_on_axis_zero(self):
        """On-axis should have zero RMS coma."""
        rms = compute_coma_rms(0.0, 1000.0, 200.0)
        assert rms == pytest.approx(0.0)

    def test_positive_off_axis(self):
        """Off-axis should have positive RMS coma."""
        rms = compute_coma_rms(60.0, 1000.0, 200.0)
        assert rms > 0


class TestComaFreeField:
    """Tests for the coma-free field computation."""

    def test_positive_value(self):
        """Should return a positive field angle."""
        cff = coma_free_field(1000.0, 200.0, 550e-6)
        assert cff > 0

    def test_increases_with_f_ratio(self):
        """Higher f-ratio (slower) should have larger coma-free field.

        Coma scales as 1/f^2, while Airy radius scales as f, so
        the coma-free field should increase strongly with f-ratio.
        """
        # f/5 (200mm, 1000mm)
        cff_f5 = coma_free_field(1000.0, 200.0, 550e-6)
        # f/8 (200mm, 1600mm)
        cff_f8 = coma_free_field(1600.0, 200.0, 550e-6)
        assert cff_f8 > cff_f5

    def test_reasonable_value(self):
        """Coma-free field for f/5 200mm should be a few arcminutes."""
        cff = coma_free_field(1000.0, 200.0, 550e-6)
        # For a 200mm f/5, coma-free field is typically ~200-400 arcsec
        assert 50.0 < cff < 1000.0


class TestBuildComaSpot2D:
    """Tests for the 2D coma spot image builder."""

    def test_output_shape(self):
        """Output should have the requested shape."""
        x = np.array([0.0, 0.001, 0.002])
        y = np.array([0.0, 0.0005, -0.0005])
        image = _build_coma_spot_2d(x, y, 0.01, 64)
        assert image.shape == (64, 64)

    def test_nonzero_output(self):
        """Image should have nonzero content."""
        x = np.array([0.0, 0.001, 0.002])
        y = np.array([0.0, 0.0005, -0.0005])
        image = _build_coma_spot_2d(x, y, 0.01, 64)
        assert image.sum() > 0

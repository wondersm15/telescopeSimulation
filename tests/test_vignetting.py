"""Tests for the vignetting physics module."""

import numpy as np
import pytest

from telescope_sim.physics.vignetting import (
    circle_overlap_fraction,
    compute_vignetting,
    fully_illuminated_field,
)
from telescope_sim.geometry.telescope import NewtonianTelescope


class TestCircleOverlapFraction:
    """Tests for the circle-circle overlap computation."""

    def test_concentric_equal_radii(self):
        """Concentric circles of equal size: 100% overlap."""
        assert circle_overlap_fraction(10.0, 10.0, 0.0) == pytest.approx(1.0)

    def test_concentric_larger_secondary(self):
        """Secondary larger than beam: 100% overlap."""
        assert circle_overlap_fraction(5.0, 10.0, 0.0) == pytest.approx(1.0)

    def test_concentric_smaller_secondary(self):
        """Secondary smaller than beam: fraction = (r2/r1)^2."""
        frac = circle_overlap_fraction(10.0, 5.0, 0.0)
        assert frac == pytest.approx(0.25)

    def test_no_overlap(self):
        """Circles separated beyond sum of radii: zero overlap."""
        assert circle_overlap_fraction(5.0, 5.0, 20.0) == pytest.approx(0.0)

    def test_partial_overlap(self):
        """Partially overlapping circles should be between 0 and 1."""
        frac = circle_overlap_fraction(5.0, 5.0, 5.0)
        assert 0.0 < frac < 1.0

    def test_circle1_inside_circle2(self):
        """Circle 1 entirely inside circle 2."""
        frac = circle_overlap_fraction(3.0, 10.0, 2.0)
        assert frac == pytest.approx(1.0)


class TestComputeVignetting:
    """Tests for the vignetting computation."""

    def test_on_axis_full_illumination(self):
        """On-axis (0 arcsec) should have full illumination."""
        result = compute_vignetting(0.0, 200.0, 1000.0, 900.0, 40.0)
        assert result == pytest.approx(1.0)

    def test_monotonically_decreasing(self):
        """Illumination should decrease with increasing field angle."""
        angles = np.linspace(0, 600, 50)
        illumination = compute_vignetting(angles, 200.0, 1000.0, 900.0, 40.0)
        # Should be non-increasing (allow for floating point tolerance)
        diffs = np.diff(illumination)
        assert np.all(diffs <= 1e-10)

    def test_large_angle_zero_illumination(self):
        """At a very large angle, illumination should drop to zero."""
        result = compute_vignetting(10000.0, 200.0, 1000.0, 900.0, 40.0)
        assert result == pytest.approx(0.0)

    def test_array_input(self):
        """Should accept array input and return array output."""
        angles = np.array([0.0, 100.0, 200.0])
        result = compute_vignetting(angles, 200.0, 1000.0, 900.0, 40.0)
        assert isinstance(result, np.ndarray)
        assert result.shape == (3,)

    def test_scalar_input(self):
        """Should accept scalar input and return scalar output."""
        result = compute_vignetting(0.0, 200.0, 1000.0, 900.0, 40.0)
        assert isinstance(result, float)


class TestFullyIlluminatedField:
    """Tests for the fully illuminated field computation."""

    def test_positive_value(self):
        """Should return a positive value for typical geometry."""
        fif = fully_illuminated_field(200.0, 1000.0, 900.0, 40.0)
        assert fif > 0

    def test_larger_secondary_gives_wider_field(self):
        """A larger secondary should give a wider fully-illuminated field."""
        fif_small = fully_illuminated_field(200.0, 1000.0, 900.0, 30.0)
        fif_large = fully_illuminated_field(200.0, 1000.0, 900.0, 50.0)
        assert fif_large > fif_small

    def test_matches_vignetting_boundary(self):
        """At the fully-illuminated field angle, illumination should be ~1."""
        fif = fully_illuminated_field(200.0, 1000.0, 900.0, 40.0)
        # Just inside should be 1.0
        v = compute_vignetting(fif * 0.99, 200.0, 1000.0, 900.0, 40.0)
        assert v == pytest.approx(1.0, abs=0.01)


class TestTelescopeVignettingDelegation:
    """Tests that NewtonianTelescope delegates to the physics module."""

    def test_compute_vignetting_method(self):
        """Telescope.compute_vignetting should delegate correctly."""
        tel = NewtonianTelescope(200.0, 1000.0)
        result = tel.compute_vignetting(0.0)
        assert result == pytest.approx(1.0)

    def test_fully_illuminated_field_method(self):
        """Telescope.fully_illuminated_field should return positive."""
        tel = NewtonianTelescope(200.0, 1000.0)
        fif = tel.fully_illuminated_field()
        assert fif >= 0

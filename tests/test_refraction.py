"""Tests for refraction physics (Snell's law and dispersion)."""

import numpy as np
import pytest

from telescope_sim.physics.refraction import (
    GLASS_CATALOG,
    refract_direction,
    refractive_index_cauchy,
)


class TestRefractDirection:
    def test_normal_incidence_passes_straight_through(self):
        """A ray hitting a surface head-on should pass straight through
        (no bending at normal incidence)."""
        d = np.array([0.0, -1.0])
        n = np.array([0.0, 1.0])
        result = refract_direction(d, n, 1.0, 1.5)
        assert result is not None
        np.testing.assert_allclose(result, [0.0, -1.0], atol=1e-10)

    def test_snell_law_known_angle(self):
        """Check refracted angle matches Snell's law for 30° incidence,
        air (n=1) to glass (n=1.5)."""
        theta1 = np.radians(30.0)
        d = np.array([np.sin(theta1), -np.cos(theta1)])
        n = np.array([0.0, 1.0])

        result = refract_direction(d, n, 1.0, 1.5)
        assert result is not None

        # Expected angle from Snell's law
        sin_theta2 = np.sin(theta1) / 1.5
        theta2 = np.arcsin(sin_theta2)

        # Refracted direction should have sin(theta2) as x-component magnitude
        assert abs(abs(result[0]) - np.sin(theta2)) < 1e-10

    def test_total_internal_reflection_returns_none(self):
        """Glass to air at a steep angle should produce total internal
        reflection (returns None)."""
        # Critical angle for n=1.5 -> n=1.0 is arcsin(1/1.5) ≈ 41.8°
        # Use 50° — well above critical angle.
        theta = np.radians(50.0)
        d = np.array([np.sin(theta), -np.cos(theta)])
        n = np.array([0.0, 1.0])

        result = refract_direction(d, n, 1.5, 1.0)
        assert result is None

    def test_glass_to_air_bends_away_from_normal(self):
        """When going from glass (n=1.5) to air (n=1.0), the refracted
        ray should bend away from the normal (larger angle)."""
        theta1 = np.radians(20.0)
        d = np.array([np.sin(theta1), -np.cos(theta1)])
        n = np.array([0.0, 1.0])

        result = refract_direction(d, n, 1.5, 1.0)
        assert result is not None

        # Angle should be larger than incident angle
        theta2 = np.arcsin(abs(result[0]))
        assert theta2 > theta1

    def test_equal_indices_no_bending(self):
        """Same refractive index on both sides — no refraction."""
        theta1 = np.radians(30.0)
        d = np.array([np.sin(theta1), -np.cos(theta1)])
        n = np.array([0.0, 1.0])

        result = refract_direction(d, n, 1.5, 1.5)
        assert result is not None
        np.testing.assert_allclose(result, d, atol=1e-10)


class TestCauchyDispersion:
    def test_blue_higher_index_than_red(self):
        """Shorter wavelengths (blue) should have higher refractive
        index than longer wavelengths (red) — normal dispersion."""
        coeffs = GLASS_CATALOG["BK7"]
        n_blue = refractive_index_cauchy(450.0, coeffs["B"], coeffs["C"])
        n_red = refractive_index_cauchy(650.0, coeffs["B"], coeffs["C"])
        assert n_blue > n_red

    def test_known_bk7_values(self):
        """BK7 refractive index at 550nm should be approximately 1.518."""
        coeffs = GLASS_CATALOG["BK7"]
        n = refractive_index_cauchy(550.0, coeffs["B"], coeffs["C"])
        assert abs(n - 1.518) < 0.02  # approximate Cauchy fit

    def test_flint_higher_dispersion(self):
        """F2 flint glass should have higher dispersion (larger index
        difference between blue and red) than BK7 crown glass."""
        bk7 = GLASS_CATALOG["BK7"]
        f2 = GLASS_CATALOG["F2"]

        disp_bk7 = (refractive_index_cauchy(450.0, bk7["B"], bk7["C"])
                     - refractive_index_cauchy(650.0, bk7["B"], bk7["C"]))
        disp_f2 = (refractive_index_cauchy(450.0, f2["B"], f2["C"])
                    - refractive_index_cauchy(650.0, f2["B"], f2["C"]))
        assert disp_f2 > disp_bk7

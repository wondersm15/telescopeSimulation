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

    def test_return_pupil_radius_shape_and_range(self):
        """With return_pupil_radius, a third normalized-radius array is
        returned: same shape, spanning obstruction..1.0 (edge)."""
        n_zones, n_azimuth = 20, 36
        x, y, pr = compute_coma_spot(60.0, 1000.0, 200.0,
                                     obstruction_ratio=0.2,
                                     num_pupil_zones=n_zones,
                                     num_azimuthal=n_azimuth,
                                     return_pupil_radius=True)
        assert pr.shape == (n_zones * n_azimuth,)
        # Normalized pupil radius: inner edge = obstruction ratio, outer = 1.
        assert np.isclose(pr.min(), 0.2, atol=1e-6)
        assert np.isclose(pr.max(), 1.0, atol=1e-6)
        # Marginal (edge) rays land farthest out along the comet tail.
        edge = pr >= 0.99
        assert np.max(x[edge]) >= np.max(x[~edge]) - 1e-12

    def test_return_pupil_radius_backward_compatible(self):
        """Default call still returns exactly two arrays (no radius)."""
        result = compute_coma_spot(60.0, 1000.0, 200.0)
        assert len(result) == 2

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


# ---------------------------------------------------------------------------
# PSF kernel centring (R5.6 regression)
# ---------------------------------------------------------------------------

def _centroid_offset(kernel):
    """Centroid of a 2D kernel measured from its TRUE centre, in pixels."""
    n = kernel.shape[0]
    c = (n - 1) / 2.0
    yy, xx = np.mgrid[:n, :n]
    total = kernel.sum()
    return ((xx * kernel).sum() / total - c,
            (yy * kernel).sum() / total - c)


class TestPSFKernelCentring:
    """Guards against the R5.6 per-channel misregistration bug.

    `chromatic_psf_kernel` built its defocus disk around the integer index
    `n // 2` rather than the array's true centre `(n-1)/2`. Combined with
    `fftconvolve(..., mode="same")` that produced a measured +1 px diagonal
    shift — but ONLY for channels that actually reached the convolution
    branch. The in-focus channel returns early for sub-pixel defocus, so R
    and B were displaced a full pixel relative to G and every star acquired a
    directional colour fringe (pink upper-right, yellow lower-left). It was
    WORST for the best optics, where a near-zero residual put different
    wavelengths on opposite sides of the 0.5 px early-return threshold.
    """

    OBJECTIVES = ["singlet", "achromat", "apo_doublet", "apo_triplet"]
    CHANNELS = [450.0, 550.0, 650.0]

    def _scope(self, objective):
        from telescope_gui.telescope_builder import build_telescope
        return build_telescope(telescope_type="Refractor", diameter=100,
                               focal_length=800, objective_type=objective)

    @pytest.mark.parametrize("objective", OBJECTIVES)
    def test_each_channel_is_centred(self, objective):
        """Every wavelength's kernel must be centred on the array centre."""
        from telescope_sim.plotting.ray_trace_plot import chromatic_psf_kernel
        for wl in self.CHANNELS:
            kernel = chromatic_psf_kernel(
                self._scope(objective), wl, 256, 0.05, True,
                focus_wavelength_nm=550.0,
            )
            dx, dy = _centroid_offset(kernel)
            assert abs(dx) < 0.05, f"{objective} {wl}nm x-centroid {dx:+.4f} px"
            assert abs(dy) < 0.05, f"{objective} {wl}nm y-centroid {dy:+.4f} px"

    @pytest.mark.parametrize("objective", OBJECTIVES)
    def test_channels_are_mutually_registered(self, objective):
        """R/G/B must land on each other — misregistration IS colour fringing.

        This is the assertion that actually fails on the pre-fix code: the
        spread was ~1.00 px for the achromat and both APO designs.
        """
        from telescope_sim.plotting.ray_trace_plot import chromatic_psf_kernel
        scope = self._scope(objective)
        centroids = [
            _centroid_offset(chromatic_psf_kernel(
                scope, wl, 256, 0.05, True, focus_wavelength_nm=550.0))
            for wl in self.CHANNELS
        ]
        spread_x = max(c[0] for c in centroids) - min(c[0] for c in centroids)
        spread_y = max(c[1] for c in centroids) - min(c[1] for c in centroids)
        assert spread_x < 0.05, f"{objective} inter-channel x spread {spread_x:.4f} px"
        assert spread_y < 0.05, f"{objective} inter-channel y spread {spread_y:.4f} px"

    def test_defocus_disk_never_empty(self):
        """A symmetric grid can produce an EMPTY binary disk (min r = 0.707).

        Centring the disk correctly is not enough: with a hard binary mask on
        a symmetric even grid, a radius between 0.5 and 0.707 selects no
        pixels at all, which would zero the PSF. The anti-aliased edge keeps
        the disk populated at every radius past the early-return threshold.
        """
        from telescope_sim.plotting.ray_trace_plot import chromatic_psf_kernel
        for objective in self.OBJECTIVES:
            scope = self._scope(objective)
            for wl in self.CHANNELS:
                kernel = chromatic_psf_kernel(
                    scope, wl, 256, 0.05, True, focus_wavelength_nm=550.0)
                assert kernel.sum() > 0, f"{objective} {wl}nm produced an empty PSF"
                assert np.all(np.isfinite(kernel))

    def test_on_axis_psf_centred_for_both_primary_types(self):
        """The spherical-aberration convolution must not shift the PSF.

        Same latent idiom as the chromatic bug: the SA spot was stamped around
        `num_pixels // 2` and used as an even-sized convolution kernel.
        """
        import warnings
        from telescope_gui.telescope_builder import build_telescope
        from telescope_sim.plotting.ray_trace_plot import _compute_psf_at_field_angle
        for primary_type in ("parabolic", "spherical"):
            scope = build_telescope(telescope_type="Newtonian", diameter=200,
                                    focal_length=1200, primary_type=primary_type)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                psf = _compute_psf_at_field_angle(scope, 0.0, 550.0, 256, 0.05, True)
            dx, dy = _centroid_offset(psf)
            assert abs(dx) < 0.05, f"{primary_type} x-centroid {dx:+.4f} px"
            assert abs(dy) < 0.05, f"{primary_type} y-centroid {dy:+.4f} px"


class TestCenteredPixelCoords:
    """The shared helper that encodes the centring convention."""

    def test_symmetric_for_even_and_odd(self):
        from telescope_sim.plotting.ray_trace_plot import _centered_pixel_coords
        for n in (64, 65, 256, 257):
            coords = _centered_pixel_coords(n)
            assert len(coords) == n
            # Symmetric about zero — this is the whole point.
            assert np.allclose(coords, -coords[::-1])
            assert abs(coords.sum()) < 1e-9

    def test_even_centre_is_half_integer(self):
        """Documents WHY `n // 2` is wrong: for even n the centre is x.5."""
        from telescope_sim.plotting.ray_trace_plot import _centered_pixel_coords
        coords = _centered_pixel_coords(256)
        assert coords[128] == 0.5   # the old `n // 2` origin — off by half
        assert coords[127] == -0.5

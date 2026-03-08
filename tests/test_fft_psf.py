"""Tests for the FFT-based PSF module."""

import numpy as np
import pytest

from telescope_sim.physics.fft_psf import build_pupil_mask, compute_fft_psf
from telescope_sim.physics.diffraction import compute_psf


class TestBuildPupilMask:
    """Tests for the pupil mask construction."""

    def test_filled_circle_no_vanes(self):
        """With no obstruction or vanes, mask should be a filled circle."""
        mask = build_pupil_mask(256, 200.0, obstruction_ratio=0.0,
                                spider_vanes=0)
        # Center should be open
        assert mask[128, 128] == 1.0
        # Corners should be blocked
        assert mask[0, 0] == 0.0
        # Total open area should approximate pi*r^2 / total_area
        open_fraction = mask.sum() / mask.size
        expected = np.pi / 4.0  # circle in square
        assert open_fraction == pytest.approx(expected, abs=0.02)

    def test_central_hole_with_obstruction(self):
        """Central obstruction should block the center."""
        mask = build_pupil_mask(256, 200.0, obstruction_ratio=0.3,
                                spider_vanes=0)
        # Center should be blocked
        assert mask[128, 128] == 0.0
        # Some pixels between obstruction and edge should be open
        # (at ~60% of radius)
        idx_60 = int(128 + 0.6 * 128)
        assert mask[128, idx_60] == 1.0

    def test_vanes_reduce_area(self):
        """Adding spider vanes should reduce the open area."""
        mask_no_vanes = build_pupil_mask(256, 200.0, spider_vanes=0)
        mask_4_vanes = build_pupil_mask(256, 200.0, spider_vanes=4,
                                         spider_vane_width=2.0)
        assert mask_4_vanes.sum() < mask_no_vanes.sum()

    def test_more_vanes_less_area(self):
        """More vanes should block more area."""
        mask_3 = build_pupil_mask(256, 200.0, spider_vanes=3,
                                   spider_vane_width=2.0)
        mask_6 = build_pupil_mask(256, 200.0, spider_vanes=6,
                                   spider_vane_width=2.0)
        assert mask_6.sum() < mask_3.sum()

    def test_mask_shape(self):
        """Mask should have the requested shape."""
        mask = build_pupil_mask(512, 200.0)
        assert mask.shape == (512, 512)

    def test_mask_binary(self):
        """Mask values should be 0 or 1."""
        mask = build_pupil_mask(128, 200.0, obstruction_ratio=0.2,
                                spider_vanes=4)
        unique_vals = np.unique(mask)
        assert set(unique_vals) <= {0.0, 1.0}


class TestComputeFFTPSF:
    """Tests for the FFT-based PSF computation."""

    def test_peak_at_center(self):
        """PSF peak should be at the center."""
        psf, _ = compute_fft_psf(200.0, 1000.0, 550e-6,
                                  grid_size=256)
        center = psf.shape[0] // 2
        assert psf[center, center] == pytest.approx(1.0)

    def test_normalized(self):
        """PSF peak should be 1.0."""
        psf, _ = compute_fft_psf(200.0, 1000.0, 550e-6,
                                  grid_size=256)
        assert psf.max() == pytest.approx(1.0)

    def test_positive_half_size(self):
        """Half-size should be positive."""
        _, half_size = compute_fft_psf(200.0, 1000.0, 550e-6,
                                        grid_size=256)
        assert half_size > 0

    def test_matches_analytical_airy_no_vanes(self):
        """Without vanes, FFT PSF azimuthal average should match Airy.

        This validates the FFT approach against the known analytical result.
        """
        D = 200.0
        f = 1000.0
        wl = 550e-6
        grid_size = 512

        psf_fft, half_size = compute_fft_psf(D, f, wl, grid_size=grid_size)

        # Compute azimuthal average of FFT PSF
        center = grid_size // 2
        coords = np.linspace(-half_size, half_size, grid_size)
        xx, yy = np.meshgrid(coords, coords)
        rr = np.sqrt(xx ** 2 + yy ** 2)

        # Sample at several radii and compare to analytical
        airy_radius = 1.22 * wl * (f / D)
        test_radii = np.linspace(0, airy_radius * 3, 20)

        for r_test in test_radii[1:]:  # skip r=0 (always 1.0)
            # Average FFT PSF in an annulus around r_test
            dr = airy_radius * 0.3
            annulus = (rr > r_test - dr) & (rr < r_test + dr)
            if annulus.sum() < 5:
                continue
            fft_avg = psf_fft[annulus].mean()

            # Analytical value
            r_arr = np.array([r_test])
            analytical = compute_psf(r_arr, D, f, wl)[0]

            # Allow generous tolerance due to discrete sampling
            assert fft_avg == pytest.approx(analytical, abs=0.15), \
                f"Mismatch at r={r_test:.6f}mm: FFT={fft_avg:.4f}, " \
                f"analytical={analytical:.4f}"

    def test_4_vanes_produce_spikes(self):
        """4 spider vanes should produce power at 4 spike angles.

        Spikes are perpendicular to each vane. For 4 vanes at 0/90 degrees,
        spikes appear at 0/90/180/270 degrees.
        """
        psf, half_size = compute_fft_psf(
            200.0, 1000.0, 550e-6,
            spider_vanes=4, spider_vane_width=2.0,
            grid_size=256,
        )

        center = psf.shape[0] // 2
        # Check that there's significant power along the spike directions
        # (horizontal and vertical lines through center)
        spike_h = psf[center, center + 20:center + 50].mean()
        spike_v = psf[center + 20:center + 50, center].mean()
        # Check power at 45-degree diagonal (should be lower)
        diag_indices = np.arange(20, 50)
        diag_vals = [psf[center + i, center + i] for i in diag_indices]
        diag_avg = np.mean(diag_vals)

        # Spikes should have more power than diagonals
        assert spike_h > diag_avg
        assert spike_v > diag_avg

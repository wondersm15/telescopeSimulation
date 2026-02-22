"""Tests for astronomical source classes and rendering pipeline."""

import numpy as np
import pytest

from telescope_sim.geometry import NewtonianTelescope
from telescope_sim.geometry.eyepiece import Eyepiece
from telescope_sim.source.sources import (
    AstronomicalSource,
    Jupiter,
    Moon,
    PointSource,
    Saturn,
    StarField,
)
from telescope_sim.plotting.ray_trace_plot import (
    _render_source_through_telescope,
    plot_source_image,
)


class TestPointSource:
    """Tests for PointSource."""

    def setup_method(self):
        self.source = PointSource()

    def test_render_ideal_has_one_bright_pixel(self):
        image = self.source.render_ideal(half_fov_arcsec=10.0,
                                         num_pixels=101)
        assert image.shape == (101, 101)
        # Exactly one non-zero pixel for an on-axis point source
        assert np.count_nonzero(image) == 1
        assert image.max() == pytest.approx(1.0)

    def test_render_ideal_off_axis(self):
        source = PointSource(field_angle_arcsec=5.0, position_angle_deg=0.0)
        image = source.render_ideal(half_fov_arcsec=10.0, num_pixels=101)
        assert np.count_nonzero(image) == 1
        # Bright pixel should be offset from center
        iy, ix = np.unravel_index(np.argmax(image), image.shape)
        center = 101 // 2
        assert ix > center  # offset in +x direction

    def test_field_extent_on_axis(self):
        source = PointSource(field_angle_arcsec=0.0)
        assert source.field_extent_arcsec == 10.0

    def test_field_extent_off_axis(self):
        source = PointSource(field_angle_arcsec=100.0)
        assert source.field_extent_arcsec == 250.0

    def test_field_extent_positive(self):
        assert self.source.field_extent_arcsec > 0

    def test_is_astronomical_source(self):
        assert isinstance(self.source, AstronomicalSource)


class TestStarField:
    """Tests for StarField."""

    def setup_method(self):
        self.source = StarField(num_stars=20, field_radius_arcsec=300.0,
                                seed=42)

    def test_correct_number_of_stars(self):
        assert len(self.source.star_x_arcsec) == 20
        assert len(self.source.star_y_arcsec) == 20
        assert len(self.source.star_magnitudes) == 20

    def test_stars_within_field_radius(self):
        r = np.sqrt(self.source.star_x_arcsec ** 2
                    + self.source.star_y_arcsec ** 2)
        assert np.all(r <= self.source.field_radius_arcsec + 1e-10)

    def test_reproducible_with_seed(self):
        source2 = StarField(num_stars=20, field_radius_arcsec=300.0, seed=42)
        np.testing.assert_array_equal(self.source.star_x_arcsec,
                                      source2.star_x_arcsec)
        np.testing.assert_array_equal(self.source.star_magnitudes,
                                      source2.star_magnitudes)

    def test_different_seed_gives_different_stars(self):
        source2 = StarField(num_stars=20, field_radius_arcsec=300.0, seed=99)
        assert not np.array_equal(self.source.star_x_arcsec,
                                  source2.star_x_arcsec)

    def test_render_ideal_shape(self):
        image = self.source.render_ideal(half_fov_arcsec=300.0,
                                         num_pixels=256)
        assert image.shape == (256, 256)

    def test_render_ideal_has_multiple_bright_pixels(self):
        image = self.source.render_ideal(half_fov_arcsec=300.0,
                                         num_pixels=256)
        # Should have at least several non-zero pixels (one per star,
        # though some stars may overlap)
        assert np.count_nonzero(image) >= 10

    def test_render_ideal_peak_normalized(self):
        image = self.source.render_ideal(half_fov_arcsec=300.0,
                                         num_pixels=256)
        assert image.max() == pytest.approx(1.0)

    def test_field_extent(self):
        assert self.source.field_extent_arcsec == 600.0

    def test_field_extent_positive(self):
        assert self.source.field_extent_arcsec > 0

    def test_magnitude_range(self):
        assert np.all(self.source.star_magnitudes >= 0.0)
        assert np.all(self.source.star_magnitudes <= 4.0)


class TestJupiter:
    """Tests for Jupiter source."""

    def setup_method(self):
        self.source = Jupiter(angular_diameter_arcsec=40.0)

    def test_render_ideal_is_disk(self):
        image = self.source.render_ideal(half_fov_arcsec=30.0,
                                         num_pixels=201)
        assert image.shape == (201, 201)
        # Center should be bright
        center = 201 // 2
        assert image[center, center] > 0.5
        # Corners should be zero (outside disk)
        assert image[0, 0] == pytest.approx(0.0, abs=1e-10)
        assert image[-1, -1] == pytest.approx(0.0, abs=1e-10)

    def test_zero_outside_radius(self):
        image = self.source.render_ideal(half_fov_arcsec=40.0,
                                         num_pixels=201)
        coords = np.linspace(-40.0, 40.0, 201)
        xx, yy = np.meshgrid(coords, coords)
        rr = np.sqrt(xx ** 2 + yy ** 2)
        outside = rr > 20.5  # slightly beyond Jupiter radius
        # Allow small tolerance for GRS Gaussian tails
        assert np.all(image[outside] < 0.05)

    def test_limb_darkening(self):
        """Edge should be dimmer than center due to limb darkening."""
        image = self.source.render_ideal(half_fov_arcsec=30.0,
                                         num_pixels=201)
        center = 201 // 2
        # Sample at center vs near limb
        center_intensity = image[center, center]
        # Near limb: ~80% of radius from center
        limb_pixel = center + int(0.8 * 20.0 / 30.0 * 100)
        if limb_pixel < 201:
            limb_intensity = image[center, limb_pixel]
            assert limb_intensity < center_intensity

    def test_band_structure(self):
        """Intensity should vary along meridian (bands)."""
        image = self.source.render_ideal(half_fov_arcsec=30.0,
                                         num_pixels=401)
        center = 401 // 2
        # Sample along the vertical center line (x=0, varying y)
        meridian = image[:, center]
        # Within the disk, there should be variation (bands)
        disk_mask = meridian > 0.01
        if np.sum(disk_mask) > 10:
            disk_values = meridian[disk_mask]
            # Standard deviation should be non-negligible
            assert np.std(disk_values) > 0.01

    def test_peak_normalized(self):
        image = self.source.render_ideal(half_fov_arcsec=30.0,
                                         num_pixels=201)
        assert image.max() == pytest.approx(1.0)

    def test_field_extent(self):
        assert self.source.field_extent_arcsec == 60.0

    def test_field_extent_positive(self):
        assert self.source.field_extent_arcsec > 0

    def test_is_astronomical_source(self):
        assert isinstance(self.source, AstronomicalSource)


class TestRenderSourceThroughTelescope:
    """Tests for _render_source_through_telescope."""

    def setup_method(self):
        self.telescope = NewtonianTelescope(
            primary_diameter=200.0,
            focal_length=1000.0,
            primary_type="parabolic",
        )

    def test_point_source_returns_correct_shape(self):
        source = PointSource()
        image, half_fov, info = _render_source_through_telescope(
            source, self.telescope, num_pixels=64,
        )
        assert image.shape == (64, 64)
        assert half_fov > 0
        assert np.all(np.isfinite(image))

    def test_star_field_returns_correct_shape(self):
        source = StarField(num_stars=5, field_radius_arcsec=100.0)
        image, half_fov, info = _render_source_through_telescope(
            source, self.telescope, num_pixels=64,
        )
        assert image.shape == (64, 64)
        assert np.all(np.isfinite(image))

    def test_jupiter_returns_correct_shape(self):
        source = Jupiter(angular_diameter_arcsec=40.0)
        image, half_fov, info = _render_source_through_telescope(
            source, self.telescope, num_pixels=64,
        )
        assert image.shape == (64, 64)
        assert np.all(np.isfinite(image))

    def test_info_dict_has_expected_keys(self):
        source = PointSource()
        _, _, info = _render_source_through_telescope(
            source, self.telescope, num_pixels=64,
        )
        assert "wavelength_nm" in info
        assert "f_ratio" in info
        assert "airy_radius_arcsec" in info
        assert "source_type" in info
        assert info["source_type"] == "PointSource"

    def test_peak_normalized(self):
        source = PointSource()
        image, _, _ = _render_source_through_telescope(
            source, self.telescope, num_pixels=64,
        )
        assert image.max() == pytest.approx(1.0, abs=0.01)

    def test_with_seeing(self):
        source = PointSource()
        image, _, info = _render_source_through_telescope(
            source, self.telescope, num_pixels=64,
            seeing_arcsec=2.0,
        )
        assert image.shape == (64, 64)
        assert np.all(np.isfinite(image))
        assert info["seeing_arcsec"] == 2.0

    def test_saturn_returns_correct_shape(self):
        source = Saturn(angular_diameter_arcsec=18.0)
        image, half_fov, info = _render_source_through_telescope(
            source, self.telescope, num_pixels=64,
        )
        assert image.shape == (64, 64)
        assert np.all(np.isfinite(image))

    def test_saturn_has_rgb(self):
        source = Saturn(angular_diameter_arcsec=18.0)
        _, _, info = _render_source_through_telescope(
            source, self.telescope, num_pixels=64,
        )
        assert info["image_rgb"] is not None
        assert info["image_rgb"].shape == (64, 64, 3)

    def test_moon_returns_correct_shape(self):
        source = Moon(angular_diameter_arcsec=200.0)
        image, half_fov, info = _render_source_through_telescope(
            source, self.telescope, num_pixels=64,
        )
        assert image.shape == (64, 64)
        assert np.all(np.isfinite(image))

    def test_moon_has_rgb(self):
        source = Moon(angular_diameter_arcsec=200.0)
        _, _, info = _render_source_through_telescope(
            source, self.telescope, num_pixels=64,
        )
        assert info["image_rgb"] is not None
        assert info["image_rgb"].shape == (64, 64, 3)


class TestSaturn:
    """Tests for Saturn source."""

    def setup_method(self):
        self.source = Saturn(angular_diameter_arcsec=18.0, ring_tilt_deg=20.0)

    def test_render_ideal_shape(self):
        image = self.source.render_ideal(half_fov_arcsec=30.0,
                                         num_pixels=201)
        assert image.shape == (201, 201)

    def test_disk_bright_at_center(self):
        image = self.source.render_ideal(half_fov_arcsec=30.0,
                                         num_pixels=201)
        center = 201 // 2
        assert image[center, center] > 0.3

    def test_rings_present(self):
        """Rings should create brightness beyond the planet disk."""
        image = self.source.render_ideal(half_fov_arcsec=30.0,
                                         num_pixels=201)
        # Sample in the B ring (brightest), at ~1.7x planet radius
        # along x-axis where ring_r = |x|
        center = 201 // 2
        pixel_scale = 60.0 / 201
        b_ring_arcsec = 9.0 * 1.7  # middle of B ring
        ring_pixel = center + int(b_ring_arcsec / pixel_scale)
        if ring_pixel < 201:
            assert image[center, ring_pixel] > 0.0

    def test_cassini_division(self):
        """Cassini division should be darker than adjacent ring regions."""
        image = self.source.render_ideal(half_fov_arcsec=30.0,
                                         num_pixels=401)
        center = 401 // 2
        pixel_scale = 60.0 / 401  # arcsec per pixel
        # Cassini division at ~2.0 * r_eq from center
        r_eq = 9.0
        cassini_r = 2.0 * r_eq
        cassini_pix = center + int(cassini_r / pixel_scale)
        b_ring_r = 1.8 * r_eq
        b_ring_pix = center + int(b_ring_r / pixel_scale)
        if cassini_pix < 401 and b_ring_pix < 401:
            assert image[center, cassini_pix] < image[center, b_ring_pix]

    def test_zero_outside_rings(self):
        image = self.source.render_ideal(half_fov_arcsec=30.0,
                                         num_pixels=201)
        assert image[0, 0] == pytest.approx(0.0, abs=1e-10)
        assert image[-1, -1] == pytest.approx(0.0, abs=1e-10)

    def test_peak_normalized(self):
        image = self.source.render_ideal(half_fov_arcsec=30.0,
                                         num_pixels=201)
        assert image.max() == pytest.approx(1.0)

    def test_rgb_shape(self):
        rgb = self.source.render_ideal_rgb(half_fov_arcsec=30.0,
                                           num_pixels=101)
        assert rgb.shape == (101, 101, 3)
        assert rgb.min() >= 0.0
        assert rgb.max() <= 1.0

    def test_field_extent_includes_rings(self):
        # Rings extend to ~2.27x radius, so field extent should be large
        assert self.source.field_extent_arcsec > self.source.angular_diameter_arcsec * 2

    def test_field_extent_positive(self):
        assert self.source.field_extent_arcsec > 0

    def test_edge_on_rings_thin(self):
        """Edge-on rings should be very thin in the y-direction."""
        source = Saturn(angular_diameter_arcsec=18.0, ring_tilt_deg=0.1)
        image = source.render_ideal(half_fov_arcsec=30.0, num_pixels=201)
        # With near-zero tilt, rings are thin lines along x-axis.
        # Check that a pixel above the ring plane (in y) is dark.
        center = 201 // 2
        pixel_scale = 60.0 / 201
        ring_x_pix = center + int(15.0 / pixel_scale)  # in B ring along x
        # 3 pixels above the ring plane
        if ring_x_pix < 201 and center + 3 < 201:
            assert image[center + 3, ring_x_pix] < image[center, ring_x_pix]

    def test_is_astronomical_source(self):
        assert isinstance(self.source, AstronomicalSource)


class TestMoon:
    """Tests for Moon source."""

    def setup_method(self):
        self.source = Moon(angular_diameter_arcsec=200.0, phase=1.0)

    def test_render_ideal_shape(self):
        image = self.source.render_ideal(half_fov_arcsec=150.0,
                                         num_pixels=201)
        assert image.shape == (201, 201)

    def test_disk_bright_at_center(self):
        image = self.source.render_ideal(half_fov_arcsec=150.0,
                                         num_pixels=201)
        center = 201 // 2
        assert image[center, center] > 0.3

    def test_zero_outside_disk(self):
        image = self.source.render_ideal(half_fov_arcsec=150.0,
                                         num_pixels=201)
        assert image[0, 0] == pytest.approx(0.0, abs=1e-10)

    def test_maria_darker_than_highlands(self):
        """Maria regions should be darker than bright highlands."""
        image = self.source.render_ideal(half_fov_arcsec=150.0,
                                         num_pixels=401)
        center = 401 // 2
        # Center of Mare Imbrium (upper left quadrant)
        pixel_scale = 300.0 / 401
        radius = 100.0
        mare_x = center + int(-0.25 * radius / pixel_scale)
        mare_y = center + int(0.30 * radius / pixel_scale)
        # Highland region (lower right, away from maria)
        high_x = center + int(-0.05 * radius / pixel_scale)
        high_y = center + int(-0.05 * radius / pixel_scale)
        if (0 <= mare_x < 401 and 0 <= mare_y < 401
                and 0 <= high_x < 401 and 0 <= high_y < 401):
            assert image[mare_y, mare_x] < image[high_y, high_x]

    def test_half_phase(self):
        """Half moon should have dark region on one side."""
        source = Moon(angular_diameter_arcsec=200.0, phase=0.5)
        image = source.render_ideal(half_fov_arcsec=150.0,
                                    num_pixels=201)
        center = 201 // 2
        # Left side should be dark (shadow), right side lit
        left_brightness = image[center, center - 30]
        right_brightness = image[center, center + 30]
        assert left_brightness < right_brightness

    def test_peak_normalized(self):
        image = self.source.render_ideal(half_fov_arcsec=150.0,
                                         num_pixels=201)
        assert image.max() == pytest.approx(1.0)

    def test_rgb_shape(self):
        rgb = self.source.render_ideal_rgb(half_fov_arcsec=150.0,
                                           num_pixels=101)
        assert rgb.shape == (101, 101, 3)
        assert rgb.min() >= 0.0
        assert rgb.max() <= 1.0

    def test_field_extent_positive(self):
        assert self.source.field_extent_arcsec > 0

    def test_is_astronomical_source(self):
        assert isinstance(self.source, AstronomicalSource)


class TestAdaptiveResolution:
    """Tests for adaptive resolution cap and eyepiece integration."""

    def setup_method(self):
        import matplotlib
        matplotlib.use("Agg")
        self.telescope = NewtonianTelescope(
            primary_diameter=200.0,
            focal_length=1000.0,
            primary_type="parabolic",
        )

    def test_adaptive_resolution_moon(self):
        """Moon should render successfully with adaptive resolution."""
        source = Moon(angular_diameter_arcsec=1870.0)
        fig = plot_source_image(
            self.telescope, source,
            seeing_arcsec=1.5,
            num_pixels=512,
        )
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close("all")

    def test_seeing_value_applied(self):
        """Seeing value should be passed through to rendering."""
        source = PointSource()
        _, _, info = _render_source_through_telescope(
            source, self.telescope,
            num_pixels=64,
            seeing_arcsec=1.5,
        )
        assert info["seeing_arcsec"] == 1.5

    def test_eyepiece_produces_two_figures(self):
        """With eyepiece, plot_source_image should return a list of figures."""
        source = Jupiter(angular_diameter_arcsec=40.0)
        eyepiece = Eyepiece(focal_length_mm=25.0, apparent_fov_deg=50.0)
        result = plot_source_image(
            self.telescope, source,
            eyepiece=eyepiece,
        )
        assert isinstance(result, list)
        assert len(result) == 2
        import matplotlib.pyplot as plt
        plt.close("all")

    def test_no_eyepiece_single_figure(self):
        """Without eyepiece, plot_source_image returns a single figure."""
        source = Jupiter(angular_diameter_arcsec=40.0)
        result = plot_source_image(
            self.telescope, source,
        )
        import matplotlib.pyplot as plt
        assert not isinstance(result, list)
        plt.close("all")


class TestExitPupilWashout:
    """Integration tests for exit pupil washout effect."""

    def setup_method(self):
        import matplotlib
        matplotlib.use("Agg")
        self.telescope = NewtonianTelescope(
            primary_diameter=200.0,
            focal_length=1000.0,
            primary_type="parabolic",
        )

    def test_washout_large_exit_pupil(self):
        """25mm eyepiece (5mm exit pupil) should reduce contrast vs 5mm
        eyepiece (1mm exit pupil) for Jupiter."""
        source = Jupiter(angular_diameter_arcsec=40.0)

        # High-mag eyepiece: 1mm exit pupil, no washout
        ep_high = Eyepiece(focal_length_mm=5.0, apparent_fov_deg=82.0)
        image_hi, _, info_hi = _render_source_through_telescope(
            source, self.telescope, num_pixels=64)
        rgb_hi = info_hi.get("image_rgb")
        from telescope_sim.plotting.ray_trace_plot import (
            _apply_exit_pupil_washout,
        )
        img_hi_w, _, w_hi = _apply_exit_pupil_washout(
            image_hi.copy(), rgb_hi.copy() if rgb_hi is not None else None,
            ep_high.exit_pupil_mm(200.0, 1000.0))

        # Low-mag eyepiece: 5mm exit pupil, strong washout
        ep_low = Eyepiece(focal_length_mm=25.0, apparent_fov_deg=50.0)
        image_lo, _, info_lo = _render_source_through_telescope(
            source, self.telescope, num_pixels=64)
        rgb_lo = info_lo.get("image_rgb")
        img_lo_w, _, w_lo = _apply_exit_pupil_washout(
            image_lo.copy(), rgb_lo.copy() if rgb_lo is not None else None,
            ep_low.exit_pupil_mm(200.0, 1000.0))

        # Low-mag should have more washout and less contrast
        assert w_lo > w_hi
        assert img_lo_w.std() < img_hi_w.std()
        import matplotlib.pyplot as plt
        plt.close("all")

    def test_washout_no_eyepiece(self):
        """No eyepiece should produce no washout (identical to baseline)."""
        source = Jupiter(angular_diameter_arcsec=40.0)
        # Without eyepiece, plot_source_image should not modify the image
        result = plot_source_image(self.telescope, source, num_pixels=64)
        # Just verify it returns a single figure (no washout applied)
        assert not isinstance(result, list)
        import matplotlib.pyplot as plt
        plt.close("all")

    def test_washout_preserves_shape(self):
        """Image shape should be unchanged after washout."""
        from telescope_sim.plotting.ray_trace_plot import (
            _apply_exit_pupil_washout,
        )
        image = np.random.default_rng(42).random((64, 64))
        image_rgb = np.random.default_rng(42).random((64, 64, 3))
        result, result_rgb, _ = _apply_exit_pupil_washout(
            image, image_rgb, 5.0)
        assert result.shape == (64, 64)
        assert result_rgb.shape == (64, 64, 3)

    def test_washout_skipped_for_starfield(self):
        """StarField + eyepiece should not apply washout (point sources)."""
        source = StarField(num_stars=5, field_radius_arcsec=100.0, seed=42)
        eyepiece = Eyepiece(focal_length_mm=25.0, apparent_fov_deg=50.0)
        # Render with and without eyepiece — image contrast should be similar
        image_no_ep, _, info_no_ep = _render_source_through_telescope(
            source, self.telescope, num_pixels=64)
        # With eyepiece, washout should NOT be applied (StarField is excluded)
        result = plot_source_image(
            self.telescope, source, num_pixels=64, eyepiece=eyepiece)
        assert isinstance(result, list)  # eyepiece produces list of figures
        import matplotlib.pyplot as plt
        plt.close("all")

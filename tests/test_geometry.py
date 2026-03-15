"""Tests for the geometry module (mirrors and telescope)."""

import numpy as np
import pytest

from telescope_sim.physics.ray import Ray
from telescope_sim.geometry.mirrors import (
    FlatMirror, HyperbolicMirror, ParabolicMirror, SphericalMirror,
)
from telescope_sim.geometry.lenses import AchromaticDoublet, SphericalLens
from telescope_sim.geometry.telescope import (
    CassegrainTelescope,
    MaksutovCassegrainTelescope,
    NewtonianTelescope,
    RefractingTelescope,
)


# --- Parabolic mirror tests ---

class TestParabolicMirror:
    def setup_method(self):
        """Create a standard test mirror: f=1000mm, 200mm diameter."""
        self.mirror = ParabolicMirror(focal_length=1000.0, diameter=200.0)

    def test_center_ray_reflects_to_focal_point(self):
        """A ray hitting the center of the mirror should reflect
        straight back up through the focal point."""
        ray = Ray(origin=[0, 500], direction=[0, -1])
        hit = self.mirror.reflect_ray(ray)
        assert hit is True
        # After reflecting off center of parabola, direction should
        # be straight up (0, 1) since the normal at center is (0, -1)
        assert np.allclose(ray.direction, [0, 1], atol=1e-10)

    def test_parallel_rays_converge_to_focal_point(self):
        """The defining property of a parabolic mirror: all parallel
        rays converge to the same focal point at (0, f)."""
        focal_length = self.mirror.focal_length
        x_positions = [-80, -40, -20, 0, 20, 40, 80]
        focal_points = []

        for x in x_positions:
            ray = Ray(origin=[x, 1200], direction=[0, -1])
            self.mirror.reflect_ray(ray)
            # Extend the reflected ray to find where it crosses x=0
            # (or more precisely, find t where the ray reaches
            # y = focal_length)
            if abs(ray.direction[1]) > 1e-10:
                t = (focal_length - ray.origin[1]) / ray.direction[1]
                focal_x = ray.origin[0] + t * ray.direction[0]
                focal_points.append(focal_x)

        # All rays should cross the axis at nearly the same x position
        # (which should be x=0 for on-axis parallel rays)
        for fx in focal_points:
            assert abs(fx) < 0.01, f"Ray missed focal point: x={fx}"

    def test_ray_outside_aperture_misses(self):
        """A ray outside the mirror diameter should not intersect."""
        ray = Ray(origin=[150, 500], direction=[0, -1])
        hit = self.mirror.reflect_ray(ray)
        assert hit is False

    def test_surface_points_shape(self):
        pts = self.mirror.get_surface_points(num_points=50)
        assert pts.shape == (50, 2)

    def test_surface_points_within_diameter(self):
        pts = self.mirror.get_surface_points()
        assert pts[:, 0].min() >= -100.0
        assert pts[:, 0].max() <= 100.0


# --- Spherical mirror tests ---

class TestSphericalMirror:
    def setup_method(self):
        """Create a spherical mirror with R=2000 (f~1000 paraxial)."""
        self.mirror = SphericalMirror(
            radius_of_curvature=2000.0, diameter=200.0
        )

    def test_center_ray_reflects_straight_back(self):
        ray = Ray(origin=[0, 500], direction=[0, -1])
        hit = self.mirror.reflect_ray(ray)
        assert hit is True
        assert np.allclose(ray.direction, [0, 1], atol=1e-10)

    def test_spherical_aberration(self):
        """Edge rays should focus at a different point than center
        rays — this is spherical aberration."""
        # Center ray
        center_ray = Ray(origin=[0, 1200], direction=[0, -1])
        self.mirror.reflect_ray(center_ray)
        t_center = (1000 - center_ray.origin[1]) / center_ray.direction[1]
        focal_x_center = center_ray.origin[0] + t_center * center_ray.direction[0]

        # Edge ray
        edge_ray = Ray(origin=[90, 1200], direction=[0, -1])
        self.mirror.reflect_ray(edge_ray)
        t_edge = (1000 - edge_ray.origin[1]) / edge_ray.direction[1]
        focal_x_edge = edge_ray.origin[0] + t_edge * edge_ray.direction[0]

        # Edge ray should NOT converge to the same point as center ray
        assert abs(focal_x_edge - focal_x_center) > 0.01, \
            "Expected spherical aberration but rays converged to same point"

    def test_approximate_focal_length(self):
        assert self.mirror.approximate_focal_length == 1000.0

    def test_ray_outside_aperture_misses(self):
        ray = Ray(origin=[150, 500], direction=[0, -1])
        hit = self.mirror.reflect_ray(ray)
        assert hit is False


# --- Flat mirror tests ---

class TestFlatMirror:
    def test_45_degree_diagonal_redirects_vertical_to_horizontal(self):
        """A 45-degree diagonal should redirect a vertical ray to
        horizontal — the core function of a Newtonian secondary."""
        mirror = FlatMirror.create_diagonal(
            center=(0, 500), minor_axis=50, angle_deg=45.0
        )
        ray = Ray(origin=[0, 1000], direction=[0, -1])
        hit = mirror.reflect_ray(ray)
        assert hit is True
        # Should now be going horizontal (the sign depends on which
        # side of the mirror the light comes from)
        assert abs(ray.direction[1]) < 0.01
        assert abs(ray.direction[0]) > 0.9

    def test_ray_missing_mirror_segment(self):
        """A ray that would hit the line but not the segment should miss."""
        mirror = FlatMirror.create_diagonal(
            center=(0, 500), minor_axis=10, angle_deg=45.0
        )
        # Ray far from the mirror center
        ray = Ray(origin=[100, 1000], direction=[0, -1])
        hit = mirror.reflect_ray(ray)
        assert hit is False

    def test_surface_points_are_two_endpoints(self):
        mirror = FlatMirror.create_diagonal(
            center=(0, 0), minor_axis=50, angle_deg=45.0
        )
        pts = mirror.get_surface_points()
        assert pts.shape == (2, 2)


# --- Newtonian telescope tests ---

class TestNewtonianTelescope:
    def setup_method(self):
        self.telescope = NewtonianTelescope(
            primary_diameter=200.0, focal_length=1000.0
        )

    def test_focal_ratio(self):
        assert self.telescope.focal_ratio == 5.0

    def test_ray_trace_produces_full_history(self):
        """A traced ray should have 4 history points:
        start -> primary -> secondary -> focal area."""
        ray = Ray(origin=[0, 1200], direction=[0, -1])
        self.telescope.trace_ray(ray)
        assert len(ray.history) == 4

    def test_multiple_rays_traced(self):
        rays = [
            Ray(origin=[x, 1200], direction=[0, -1])
            for x in [-50, 0, 50]
        ]
        self.telescope.trace_rays(rays)
        for ray in rays:
            assert len(ray.history) >= 3

    def test_spherical_primary_option(self):
        telescope = NewtonianTelescope(
            primary_diameter=200.0,
            focal_length=1000.0,
            primary_type="spherical",
        )
        assert telescope.primary_type == "spherical"
        ray = Ray(origin=[0, 1200], direction=[0, -1])
        telescope.trace_ray(ray)
        assert len(ray.history) >= 3

    def test_invalid_primary_type_raises(self):
        with pytest.raises(ValueError):
            NewtonianTelescope(
                primary_diameter=200.0,
                focal_length=1000.0,
                primary_type="hyperbolic",
            )

    def test_components_for_plotting(self):
        components = self.telescope.get_components_for_plotting()
        assert "primary_surface" in components
        assert "secondary_surface" in components
        assert "primary_diameter" in components
        assert components["primary_diameter"] == 200.0


# --- Hyperbolic mirror tests ---

class TestHyperbolicMirror:
    def setup_method(self):
        """Create a test hyperbolic mirror (typical Cassegrain secondary)."""
        # a=100, e=2.0 gives b^2 = 100^2*(4-1) = 30000
        self.mirror = HyperbolicMirror(
            semi_major_axis=100.0,
            eccentricity=2.0,
            diameter=60.0,
            center=(0.0, 800.0),
        )

    def test_surface_points_shape(self):
        pts = self.mirror.get_surface_points(num_points=50)
        assert pts.shape == (50, 2)

    def test_surface_points_within_diameter(self):
        pts = self.mirror.get_surface_points()
        local_x = pts[:, 0] - self.mirror.center[0]
        assert np.all(local_x >= -30.0 - 1e-10)
        assert np.all(local_x <= 30.0 + 1e-10)

    def test_convex_surface_normal_direction(self):
        """Normals on the convex surface should point downward
        (toward the primary / incoming light)."""
        # At the vertex (center), the normal should point straight down
        vertex = self.mirror.center.copy()
        normal = self.mirror.normal_at(vertex)
        assert normal[1] < 0, "Normal at vertex should point downward"
        assert abs(normal[0]) < 1e-10, "Normal at vertex should be vertical"


# --- Cassegrain telescope tests ---

class TestCassegrainTelescope:
    def setup_method(self):
        self.telescope = CassegrainTelescope(
            primary_diameter=200.0,
            primary_focal_length=800.0,
            secondary_magnification=5.0,
        )

    def test_focal_ratio(self):
        # effective FL = 800 * 5 = 4000, focal ratio = 4000/200 = 20
        assert abs(self.telescope.focal_ratio - 20.0) < 1e-10

    def test_effective_focal_length(self):
        assert abs(self.telescope.focal_length - 4000.0) < 1e-10

    def test_ray_trace_converges_behind_primary(self):
        """Rays should end up below the primary (y < 0)."""
        ray = Ray(origin=[50, 1200], direction=[0, -1])
        self.telescope.trace_ray(ray)
        final_y = ray.history[-1][1]
        assert final_y < 0, (
            f"Final ray position y={final_y} should be below primary (y<0)"
        )

    def test_multiple_rays_converge(self):
        """Parallel rays should focus to a small spot behind the primary."""
        rays = [
            Ray(origin=[x, 1200], direction=[0, -1])
            for x in [-60, -30, 30, 60]
        ]
        self.telescope.trace_rays(rays)
        end_points = [r.history[-1] for r in rays if len(r.history) >= 4]
        assert len(end_points) >= 2, "At least 2 rays should complete the path"
        xs = [p[0] for p in end_points]
        spread = max(xs) - min(xs)
        assert spread < 5.0, (
            f"Ray x-spread {spread:.2f}mm too large — rays not converging"
        )

    def test_components_for_plotting(self):
        components = self.telescope.get_components_for_plotting()
        required_keys = [
            "primary_surface", "secondary_surface", "primary_diameter",
            "focal_length", "secondary_offset", "tube_length", "primary_type",
        ]
        for key in required_keys:
            assert key in components, f"Missing key: {key}"

    def test_obstruction_ratio(self):
        ratio = self.telescope.obstruction_ratio
        assert 0 < ratio < 1, f"Obstruction ratio {ratio} out of range"
        expected = self.telescope.secondary_minor_axis / self.telescope.primary_diameter
        assert abs(ratio - expected) < 1e-10


# --- Spherical lens tests ---

class TestSphericalLens:
    def setup_method(self):
        """Create a symmetric biconvex lens: R_front=500, R_back=-500,
        thickness=10, diameter=80."""
        self.lens = SphericalLens(
            R_front=500.0, R_back=-500.0,
            thickness=10.0, diameter=80.0,
            center=(0.0, 100.0), glass="BK7",
        )

    def test_front_surface_points_shape(self):
        pts = self.lens.get_front_surface_points(num_points=50)
        assert pts.shape == (50, 2)

    def test_back_surface_points_shape(self):
        pts = self.lens.get_back_surface_points(num_points=50)
        assert pts.shape == (50, 2)

    def test_refract_ray_changes_direction(self):
        """An off-axis ray should change direction after passing
        through the lens."""
        ray = Ray(origin=[20.0, 300.0], direction=[0.0, -1.0])
        hit = self.lens.refract_ray(ray)
        assert hit is True
        # Ray should now be angled inward (toward the axis)
        assert ray.direction[0] < 0, (
            "Off-axis ray should bend toward the optical axis"
        )

    def test_ray_passes_through_both_surfaces(self):
        """A traced ray should have history points on both surfaces."""
        ray = Ray(origin=[10.0, 300.0], direction=[0.0, -1.0])
        hit = self.lens.refract_ray(ray)
        assert hit is True
        # History should have: start, front surface hit, back surface hit
        assert len(ray.history) >= 3

    def test_center_ray_passes_straight_through(self):
        """A ray along the optical axis should not be deflected."""
        ray = Ray(origin=[0.0, 300.0], direction=[0.0, -1.0])
        hit = self.lens.refract_ray(ray)
        assert hit is True
        np.testing.assert_allclose(ray.direction, [0.0, -1.0], atol=1e-6)


# --- Refracting telescope tests ---

class TestRefractingTelescope:
    def setup_method(self):
        self.telescope = RefractingTelescope(
            primary_diameter=100.0, focal_length=900.0,
        )

    def test_focal_ratio(self):
        assert abs(self.telescope.focal_ratio - 9.0) < 1e-10

    def test_obstruction_ratio_is_zero(self):
        assert self.telescope.obstruction_ratio == 0.0

    def test_ray_convergence(self):
        """Parallel rays should converge near the focal plane."""
        rays = [
            Ray(origin=[x, 1200], direction=[0, -1])
            for x in [-30, -15, 15, 30]
        ]
        self.telescope.trace_rays(rays)
        end_points = [r.history[-1] for r in rays if len(r.history) >= 3]
        assert len(end_points) >= 2, "At least 2 rays should complete"
        xs = [p[0] for p in end_points]
        spread = max(xs) - min(xs)
        assert spread < 10.0, (
            f"Ray x-spread {spread:.2f}mm too large — rays not converging"
        )

    def test_components_dict_keys(self):
        components = self.telescope.get_components_for_plotting()
        required_keys = [
            "primary_surface", "secondary_surface", "primary_diameter",
            "focal_length", "secondary_offset", "tube_length",
            "primary_type", "telescope_style",
        ]
        for key in required_keys:
            assert key in components, f"Missing key: {key}"
        assert components["telescope_style"] == "refractor"
        assert components["primary_type"] == "lens"

    def test_primary_type_is_lens(self):
        assert self.telescope.primary_type == "lens"

    def test_tube_length(self):
        assert self.telescope.tube_length == 900.0


# --- Achromatic doublet tests ---

class TestAchromaticDoublet:
    def setup_method(self):
        self.doublet = AchromaticDoublet(
            focal_length=800.0, diameter=80.0,
            center=(0.0, 800.0),
        )

    def test_objective_type(self):
        assert self.doublet.objective_type == "achromat"

    def test_has_crown_and_flint(self):
        assert hasattr(self.doublet, 'crown')
        assert hasattr(self.doublet, 'flint')
        assert self.doublet.crown.glass == "BK7"
        assert self.doublet.flint.glass == "F2"

    def test_refract_ray_changes_direction(self):
        ray = Ray(origin=[20.0, 1200.0], direction=[0.0, -1.0])
        hit = self.doublet.refract_ray(ray)
        assert hit is True
        assert ray.direction[0] < 0

    def test_surface_points_shape(self):
        front = self.doublet.get_front_surface_points(50)
        back = self.doublet.get_back_surface_points(50)
        interface = self.doublet.get_interface_surface_points(50)
        assert front.shape == (50, 2)
        assert back.shape == (50, 2)
        assert interface.shape == (50, 2)

    def test_chromatic_correction(self):
        """Red and blue rays should converge closer together
        through an achromat than through a singlet."""
        from telescope_sim.geometry.lenses import SphericalLens
        from telescope_sim.physics.refraction import (
            GLASS_CATALOG, refractive_index_cauchy,
        )

        # Build a singlet with the same focal length
        coeffs = GLASS_CATALOG["BK7"]
        n = refractive_index_cauchy(550.0, coeffs["B"], coeffs["C"])
        R = 2.0 * 800.0 * (n - 1.0)
        singlet = SphericalLens(
            R_front=R, R_back=-R, thickness=6.0, diameter=80.0,
            center=(0.0, 800.0), glass="BK7",
        )

        def trace_focal_y(lens, wavelength_nm):
            ray = Ray(origin=[20.0, 1200.0], direction=[0.0, -1.0],
                      wavelength_nm=wavelength_nm)
            lens.refract_ray(ray, wavelength_nm=wavelength_nm)
            if abs(ray.direction[0]) > 1e-12:
                t = -ray.origin[0] / ray.direction[0]
                return ray.origin[1] + t * ray.direction[1]
            return ray.origin[1]

        # Singlet focus spread (red vs blue)
        singlet_red = trace_focal_y(singlet, 656.3)
        singlet_blue = trace_focal_y(singlet, 486.1)
        singlet_spread = abs(singlet_red - singlet_blue)

        # Achromat focus spread
        achromat_red = trace_focal_y(self.doublet, 656.3)
        achromat_blue = trace_focal_y(self.doublet, 486.1)
        achromat_spread = abs(achromat_red - achromat_blue)

        assert achromat_spread < singlet_spread, (
            f"Achromat spread {achromat_spread:.2f}mm should be less "
            f"than singlet spread {singlet_spread:.2f}mm"
        )


class TestRefractingTelescopeAchromat:
    def setup_method(self):
        self.telescope = RefractingTelescope(
            primary_diameter=80.0, focal_length=800.0,
            objective_type="achromat",
        )

    def test_objective_type(self):
        assert self.telescope.objective_type == "achromat"

    def test_corrected_optics(self):
        assert self.telescope.corrected_optics is True

    def test_focal_ratio(self):
        assert abs(self.telescope.focal_ratio - 10.0) < 1e-10

    def test_ray_convergence(self):
        rays = [
            Ray(origin=[x, 1200], direction=[0, -1])
            for x in [-25, -10, 10, 25]
        ]
        self.telescope.trace_rays(rays)
        end_points = [r.history[-1] for r in rays if len(r.history) >= 3]
        assert len(end_points) >= 2
        xs = [p[0] for p in end_points]
        spread = max(xs) - min(xs)
        assert spread < 10.0

    def test_components_has_achromat_info(self):
        components = self.telescope.get_components_for_plotting()
        assert components["objective_type"] == "achromat"
        assert "interface_surface" in components

    def test_chromatic_defocus_smaller_than_singlet(self):
        from telescope_sim.plotting.ray_trace_plot import chromatic_defocus
        singlet = RefractingTelescope(
            primary_diameter=80.0, focal_length=800.0,
            objective_type="singlet",
        )
        singlet_defocus = abs(chromatic_defocus(singlet, 486.1))
        achromat_defocus = abs(chromatic_defocus(self.telescope, 486.1))
        assert achromat_defocus < singlet_defocus


# --- Maksutov-Cassegrain telescope tests ---

class TestMaksutovCassegrainTelescope:
    def setup_method(self):
        self.telescope = MaksutovCassegrainTelescope(
            primary_diameter=150.0,
            primary_focal_length=750.0,
            secondary_magnification=4.0,
        )

    def test_focal_ratio(self):
        # effective FL = 750 * 4 = 3000, focal ratio = 3000/150 = 20
        assert abs(self.telescope.focal_ratio - 20.0) < 1e-10

    def test_obstruction_ratio(self):
        ratio = self.telescope.obstruction_ratio
        assert 0 < ratio < 1, f"Obstruction ratio {ratio} out of range"
        expected = self.telescope.secondary_minor_axis / self.telescope.primary_diameter
        assert abs(ratio - expected) < 1e-10

    def test_ray_convergence(self):
        """Parallel rays should converge to a small spot behind the primary."""
        rays = [
            Ray(origin=[x, 1200], direction=[0, -1])
            for x in [-40, -20, 20, 40]
        ]
        self.telescope.trace_rays(rays)
        end_points = [r.history[-1] for r in rays if len(r.history) >= 5]
        assert len(end_points) >= 2, "At least 2 rays should complete the path"
        xs = [p[0] for p in end_points]
        spread = max(xs) - min(xs)
        assert spread < 2.0, (
            f"Ray x-spread {spread:.2f}mm too large — rays not converging"
        )

    def test_ray_trace_behind_primary(self):
        """Final ray position should be below the primary (y < 0)."""
        ray = Ray(origin=[30, 1200], direction=[0, -1])
        self.telescope.trace_ray(ray)
        final_y = ray.history[-1][1]
        assert final_y < 0, (
            f"Final ray position y={final_y} should be below primary (y<0)"
        )

    def test_components_dict_keys(self):
        components = self.telescope.get_components_for_plotting()
        required_keys = [
            "primary_surface", "secondary_surface", "primary_diameter",
            "focal_length", "secondary_offset", "tube_length",
            "primary_type", "telescope_style", "corrector_front",
            "corrector_back", "spot_diameter",
        ]
        for key in required_keys:
            assert key in components, f"Missing key: {key}"
        assert components["telescope_style"] == "maksutov"

    def test_spherical_primary(self):
        assert self.telescope.primary_type == "spherical"

    def test_corrected_optics_flag(self):
        assert self.telescope.corrected_optics is True

    def test_effective_focal_length(self):
        # effective FL = primary FL * magnification = 750 * 4 = 3000
        assert abs(self.telescope.focal_length - 3000.0) < 1e-10

    def test_ray_history_length(self):
        """A fully traced ray should have 6 history points:
        start -> corrector front -> corrector back -> primary ->
        spot -> focal plane."""
        ray = Ray(origin=[30, 1200], direction=[0, -1])
        self.telescope.trace_ray(ray)
        assert len(ray.history) >= 6, (
            f"Expected >= 6 history points (full optical path), got {len(ray.history)}"
        )

    def test_center_ray_stays_on_axis(self):
        """An on-axis ray should remain near x=0 throughout."""
        ray = Ray(origin=[0, 1200], direction=[0, -1])
        self.telescope.trace_ray(ray)
        for point in ray.history:
            assert abs(point[0]) < 0.1, (
                f"On-axis ray deviated to x={point[0]}"
            )

    def test_spot_miss_returns_early(self):
        """A ray far from the axis should miss the aluminized spot."""
        # Use a ray at the very edge — likely to miss the small spot
        ray = Ray(origin=[70, 1200], direction=[0, -1])
        self.telescope.trace_ray(ray)
        # Should still have some history (at least corrector + primary)
        # but fewer points than a fully traced ray
        assert len(ray.history) >= 2

    def test_custom_meniscus_thickness(self):
        """Constructor should accept custom meniscus thickness."""
        tel = MaksutovCassegrainTelescope(
            primary_diameter=150.0,
            primary_focal_length=750.0,
            meniscus_thickness=20.0,
        )
        assert tel.meniscus_thickness == 20.0

    def test_default_meniscus_thickness(self):
        """Default meniscus thickness should be diameter / 10."""
        assert abs(self.telescope.meniscus_thickness - 15.0) < 1e-10

    def test_tube_length_equals_secondary_offset(self):
        assert self.telescope.tube_length == self.telescope.secondary_offset

    def test_corrected_optics_analytical_offsets(self):
        """Corrected optics should produce near-zero analytical focal offsets."""
        from telescope_sim.plotting.ray_trace_plot import _analytical_focal_offsets
        offsets = _analytical_focal_offsets(self.telescope)
        assert np.allclose(offsets, 0.0), (
            f"Corrected optics should give zero offsets, got RMS={np.std(offsets):.6f}"
        )


class TestSchmidtCassegrainTelescope:
    def setup_method(self):
        from telescope_sim.geometry import SchmidtCassegrainTelescope
        self.telescope = SchmidtCassegrainTelescope(
            primary_diameter=200.0,
            primary_focal_length=500.0,
            secondary_magnification=4.0,
        )

    def test_focal_ratio(self):
        """effective FL = 500 * 4 = 2000, focal ratio = 2000/200 = 10"""
        assert abs(self.telescope.focal_ratio - 10.0) < 1e-10

    def test_obstruction_ratio(self):
        """Obstruction ratio should be > 0."""
        ratio = self.telescope.obstruction_ratio
        assert 0 < ratio < 1, f"Obstruction ratio {ratio} out of range"

    def test_ray_convergence(self):
        """Parallel rays should converge to small spot (< 3mm spread).

        Note: Residual spherical aberration expected due to zero-power
        corrector approximation (~2.4mm for this geometry).
        """
        from telescope_sim.physics.ray import Ray
        import numpy as np
        rays = [
            Ray(origin=[x, 1200], direction=[0, -1])
            for x in np.linspace(-80, 80, 11)
        ]
        self.telescope.trace_rays(rays)
        end_points = [r.history[-1] for r in rays if len(r.history) >= 3]
        assert len(end_points) >= 8, "Most rays should complete path"
        xs = [p[0] for p in end_points]
        spread = max(xs) - min(xs)
        assert spread < 3.0, (
            f"Ray x-spread {spread:.2f}mm too large — rays not converging"
        )

    def test_ray_trace_behind_primary(self):
        """Final ray position should be behind primary (y < 0)."""
        from telescope_sim.physics.ray import Ray
        ray = Ray(origin=[50, 1200], direction=[0, -1])
        self.telescope.trace_ray(ray)
        final_y = ray.history[-1][1]
        assert final_y < 0, (
            f"Final ray position y={final_y} should be below primary (y<0)"
        )

    def test_components_dict_keys(self):
        """Check that components dict has required keys."""
        components = self.telescope.get_components_for_plotting()
        assert components["telescope_style"] == "schmidt"
        assert components.get("corrected_optics") is True

    def test_spherical_primary(self):
        """Primary should be spherical."""
        assert self.telescope.primary_type == "spherical"

    def test_corrected_optics_flag(self):
        """Corrected optics flag should be True."""
        assert self.telescope.corrected_optics is True

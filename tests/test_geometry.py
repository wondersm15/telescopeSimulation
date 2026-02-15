"""Tests for the geometry module (mirrors and telescope)."""

import numpy as np
import pytest

from telescope_sim.physics.ray import Ray
from telescope_sim.geometry.mirrors import ParabolicMirror, SphericalMirror, FlatMirror
from telescope_sim.geometry.telescope import NewtonianTelescope


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

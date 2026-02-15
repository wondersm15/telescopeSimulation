"""Tests for the physics module (Ray and reflection)."""

import numpy as np
import pytest

from telescope_sim.physics.ray import Ray
from telescope_sim.physics.reflection import reflect_direction


# --- Ray tests ---

class TestRay:
    def test_direction_is_normalized(self):
        ray = Ray(origin=[0, 10], direction=[0, -5])
        assert np.allclose(np.linalg.norm(ray.direction), 1.0)

    def test_initial_history_contains_origin(self):
        ray = Ray(origin=[3, 7], direction=[0, -1])
        assert len(ray.history) == 1
        assert np.allclose(ray.history[0], [3, 7])

    def test_propagate_to_updates_origin_and_history(self):
        ray = Ray(origin=[0, 10], direction=[0, -1])
        ray.propagate_to([0, 5])
        assert np.allclose(ray.origin, [0, 5])
        assert len(ray.history) == 2
        assert np.allclose(ray.history[1], [0, 5])

    def test_set_direction_normalizes(self):
        ray = Ray(origin=[0, 0], direction=[0, -1])
        ray.set_direction([3, 4])
        assert np.allclose(ray.direction, [0.6, 0.8])

    def test_history_tracks_full_path(self):
        ray = Ray(origin=[0, 10], direction=[0, -1])
        ray.propagate_to([0, 5])
        ray.propagate_to([5, 5])
        ray.propagate_to([10, 5])
        assert len(ray.history) == 4


# --- Reflection tests ---

class TestReflection:
    def test_vertical_ray_off_horizontal_surface(self):
        """A ray going straight down hitting a horizontal mirror
        should reflect straight back up."""
        reflected = reflect_direction([0, -1], [0, 1])
        assert np.allclose(reflected, [0, 1])

    def test_45_degree_reflection(self):
        """A ray going down hitting a 45-degree surface should
        redirect 90 degrees (horizontally)."""
        # Surface normal at 45 degrees: (1, 1) normalized
        normal = np.array([1, 1]) / np.sqrt(2)
        reflected = reflect_direction([0, -1], normal)
        assert np.allclose(reflected, [1, 0], atol=1e-10)

    def test_reflected_direction_is_normalized(self):
        reflected = reflect_direction([0.6, -0.8], [0, 1])
        assert np.allclose(np.linalg.norm(reflected), 1.0)

    def test_normal_direction_auto_corrected(self):
        """reflect_direction should work regardless of which way
        the normal points — it auto-flips to face the incoming ray."""
        r1 = reflect_direction([0, -1], [0, 1])
        r2 = reflect_direction([0, -1], [0, -1])
        assert np.allclose(r1, r2)

    def test_grazing_angle(self):
        """A ray at a shallow angle should reflect at the same
        shallow angle on the other side."""
        incoming = np.array([1, -0.1])
        incoming = incoming / np.linalg.norm(incoming)
        reflected = reflect_direction(incoming, [0, 1])
        # x component should stay the same, y should flip
        assert np.allclose(reflected[0], incoming[0], atol=1e-10)
        assert np.allclose(reflected[1], -incoming[1], atol=1e-10)

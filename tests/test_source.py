"""Tests for the source module (light source generation)."""

import numpy as np

from telescope_sim.source.light_source import create_parallel_rays


class TestCreateParallelRays:
    def test_correct_number_of_rays(self):
        rays = create_parallel_rays(num_rays=11, aperture_diameter=200,
                                    entry_height=1000)
        assert len(rays) == 11

    def test_single_ray_at_center(self):
        rays = create_parallel_rays(num_rays=1, aperture_diameter=200,
                                    entry_height=1000)
        assert len(rays) == 1
        assert np.allclose(rays[0].origin[0], 0.0)

    def test_all_rays_have_same_direction(self):
        rays = create_parallel_rays(num_rays=7, aperture_diameter=200,
                                    entry_height=1000)
        for ray in rays:
            assert np.allclose(ray.direction, [0, -1])

    def test_rays_at_correct_height(self):
        rays = create_parallel_rays(num_rays=5, aperture_diameter=200,
                                    entry_height=1500)
        for ray in rays:
            assert ray.origin[1] == 1500.0

    def test_rays_span_aperture_with_margin(self):
        rays = create_parallel_rays(num_rays=11, aperture_diameter=200,
                                    entry_height=1000, margin_fraction=0.05)
        x_positions = [ray.origin[0] for ray in rays]
        # With 5% margin on a 200mm aperture (radius 100),
        # usable radius = 95mm
        assert min(x_positions) >= -95.0
        assert max(x_positions) <= 95.0

    def test_rays_symmetrically_distributed(self):
        rays = create_parallel_rays(num_rays=11, aperture_diameter=200,
                                    entry_height=1000)
        x_positions = [ray.origin[0] for ray in rays]
        # Should be symmetric around 0
        assert np.allclose(np.mean(x_positions), 0.0, atol=1e-10)

    def test_custom_direction(self):
        rays = create_parallel_rays(num_rays=3, aperture_diameter=200,
                                    entry_height=1000, direction=(1, -1))
        expected = np.array([1, -1]) / np.sqrt(2)
        for ray in rays:
            assert np.allclose(ray.direction, expected)

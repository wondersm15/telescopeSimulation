"""Tests for the shared telescope_builder module."""

import pytest

from telescope_gui.telescope_builder import build_telescope, OBJECTIVE_TYPE_MAP
from telescope_sim.geometry import (
    NewtonianTelescope, CassegrainTelescope, RefractingTelescope,
    MaksutovCassegrainTelescope, SchmidtCassegrainTelescope,
)
from telescope_sim.source.light_source import create_parallel_rays


class TestBuildTelescopeTypes:
    """Verify build_telescope() returns the correct class for each type."""

    def test_newtonian(self):
        t = build_telescope("Newtonian", 200, 1000)
        assert isinstance(t, NewtonianTelescope)

    def test_cassegrain(self):
        t = build_telescope("Cassegrain", 200, 800, secondary_magnification=3.0)
        assert isinstance(t, CassegrainTelescope)

    def test_refractor(self):
        t = build_telescope("Refractor", 100, 900, objective_type="Achromat")
        assert isinstance(t, RefractingTelescope)

    def test_maksutov_cassegrain(self):
        t = build_telescope("Maksutov-Cassegrain", 150, 750,
                            secondary_magnification=3.0, meniscus_thickness=15.0)
        assert isinstance(t, MaksutovCassegrainTelescope)

    def test_schmidt_cassegrain(self):
        t = build_telescope("Schmidt-Cassegrain", 200, 400,
                            secondary_magnification=5.0)
        assert isinstance(t, SchmidtCassegrainTelescope)

    def test_unknown_type_falls_back_to_newtonian(self):
        t = build_telescope("FuturisticScope", 200, 1000)
        assert isinstance(t, NewtonianTelescope)

    def test_case_insensitive(self):
        t = build_telescope("newtonian", 200, 1000)
        assert isinstance(t, NewtonianTelescope)

    def test_hyphenation_ignored(self):
        t = build_telescope("Schmidt Cassegrain", 200, 400)
        assert isinstance(t, SchmidtCassegrainTelescope)


class TestBuildTelescopeParameters:
    """Verify that builder parameters propagate to the telescope object."""

    def test_newtonian_diameter(self):
        t = build_telescope("Newtonian", 250, 1250)
        assert t.primary_diameter == 250

    def test_newtonian_focal_length(self):
        t = build_telescope("Newtonian", 200, 1000)
        assert t.focal_length == 1000

    def test_newtonian_parabolic_primary(self):
        t = build_telescope("Newtonian", 200, 1000, primary_type="parabolic")
        assert t.primary_type == "parabolic"

    def test_newtonian_spherical_primary(self):
        t = build_telescope("Newtonian", 200, 1000, primary_type="spherical")
        assert t.primary_type == "spherical"

    def test_newtonian_spider_vanes(self):
        t = build_telescope("Newtonian", 200, 1000, spider_vanes=4, spider_vane_width=3.0)
        assert t.spider_vanes == 4
        assert t.spider_vane_width == 3.0

    def test_obstruction_ratio(self):
        t = build_telescope("Newtonian", 200, 1000, obstruction_ratio=0.25)
        # secondary_minor_axis = diameter * obstruction_ratio = 50
        assert abs(t.secondary_minor_axis - 50.0) < 0.01

    def test_zero_obstruction(self):
        t = build_telescope("Newtonian", 200, 1000, obstruction_ratio=0.0,
                            enable_obstruction=False)
        assert t.secondary_minor_axis == 0.0

    def test_refractor_objective_types(self):
        for gui_label, internal_value in OBJECTIVE_TYPE_MAP.items():
            t = build_telescope("Refractor", 100, 900, objective_type=gui_label)
            assert isinstance(t, RefractingTelescope)

    def test_maksutov_meniscus_default(self):
        """When meniscus_thickness is None, should default to diameter/10."""
        t = build_telescope("Maksutov-Cassegrain", 200, 800,
                            meniscus_thickness=None)
        assert isinstance(t, MaksutovCassegrainTelescope)

    def test_maksutov_meniscus_explicit(self):
        t = build_telescope("Maksutov-Cassegrain", 200, 800,
                            meniscus_thickness=25.0)
        assert isinstance(t, MaksutovCassegrainTelescope)

    def test_schmidt_cassegrain_secondary_minor_axis(self):
        """Regression test: SCT should receive secondary_minor_axis, not
        hardcode secondary_magnification=3.0."""
        t = build_telescope("Schmidt-Cassegrain", 200, 400,
                            secondary_magnification=5.0,
                            obstruction_ratio=0.35)
        # secondary_minor_axis = 200 * 0.35 = 70
        assert abs(t.secondary_minor_axis - 70.0) < 0.01

    def test_cassegrain_secondary_magnification(self):
        t = build_telescope("Cassegrain", 200, 800, secondary_magnification=4.0)
        # focal_length = primary_focal_length * magnification = 800 * 4 = 3200
        assert abs(t.focal_length - 3200.0) < 0.1


class TestBuildTelescopeRayTracing:
    """Integration tests: built telescopes can trace rays without errors."""

    @pytest.mark.parametrize("ttype,fratio", [
        ("Newtonian", 5.0),
        ("Cassegrain", 10.0),
        ("Refractor", 8.0),
        ("Maksutov-Cassegrain", 12.0),
        ("Schmidt-Cassegrain", 10.0),
    ])
    def test_trace_rays(self, ttype, fratio):
        diameter = 200
        focal_length = diameter * fratio
        t = build_telescope(ttype, diameter, focal_length)
        rays = create_parallel_rays(
            num_rays=5,
            aperture_diameter=t.primary_diameter,
            entry_height=t.tube_length * 1.15,
        )
        t.trace_rays(rays)

    @pytest.mark.parametrize("ttype", [
        "Newtonian", "Cassegrain", "Refractor",
        "Maksutov-Cassegrain", "Schmidt-Cassegrain",
    ])
    def test_get_components_for_plotting(self, ttype):
        t = build_telescope(ttype, 200, 1000)
        components = t.get_components_for_plotting()
        assert isinstance(components, (list, dict))
        assert len(components) > 0


class TestBuildTelescopeEdgeCases:
    """Edge cases and boundary values."""

    def test_extreme_low_fratio(self):
        t = build_telescope("Newtonian", 200, 600)  # f/3
        assert isinstance(t, NewtonianTelescope)

    def test_extreme_high_fratio(self):
        t = build_telescope("Newtonian", 200, 3000)  # f/15
        assert isinstance(t, NewtonianTelescope)

    def test_small_aperture(self):
        t = build_telescope("Refractor", 50, 400)
        assert isinstance(t, RefractingTelescope)

    def test_large_aperture(self):
        t = build_telescope("Newtonian", 500, 2500)
        assert isinstance(t, NewtonianTelescope)

    def test_max_obstruction(self):
        t = build_telescope("Newtonian", 200, 1000, obstruction_ratio=0.5)
        assert abs(t.secondary_minor_axis - 100.0) < 0.01

    def test_six_spider_vanes(self):
        t = build_telescope("Newtonian", 200, 1000, spider_vanes=6)
        assert t.spider_vanes == 6

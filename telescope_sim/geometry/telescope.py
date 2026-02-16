"""Telescope assembly that combines optical components."""

import numpy as np

from telescope_sim.geometry.mirrors import (
    FlatMirror,
    Mirror,
    ParabolicMirror,
    SphericalMirror,
)
from telescope_sim.physics.ray import Ray


class NewtonianTelescope:
    """A Newtonian reflector telescope.

    Coordinate system:
        - The primary mirror vertex sits at (0, 0).
        - The optical axis runs along the y-axis (positive y
          is upward, toward incoming light).
        - The secondary mirror redirects light to the +x direction
          (to the right) toward the eyepiece.

    The primary mirror type is configurable — use 'parabolic' for
    a standard Newtonian or 'spherical' to study spherical aberration.

    Attributes:
        primary_diameter: Diameter of the primary mirror in mm.
        focal_length: Focal length of the primary mirror in mm.
        secondary_offset: Distance of secondary mirror center from
                          primary vertex along the y-axis in mm.
        secondary_minor_axis: Minor axis size of the secondary in mm.
        primary_type: Type of primary mirror ('parabolic' or 'spherical').
    """

    def __init__(self, primary_diameter: float, focal_length: float,
                 secondary_offset: float | None = None,
                 secondary_minor_axis: float | None = None,
                 primary_type: str = "parabolic"):
        self.primary_diameter = primary_diameter
        self.focal_length = focal_length
        self.primary_type = primary_type

        if secondary_offset is None:
            secondary_offset = focal_length - primary_diameter * 0.1
        self.secondary_offset = secondary_offset

        if secondary_minor_axis is None:
            secondary_minor_axis = primary_diameter * 0.2
        self.secondary_minor_axis = secondary_minor_axis

        # Build primary mirror
        self.primary: Mirror = self._create_primary(primary_type)

        # Build secondary mirror (flat diagonal at 45 degrees)
        self.secondary = FlatMirror.create_diagonal(
            center=(0.0, secondary_offset),
            minor_axis=secondary_minor_axis,
            angle_deg=45.0,
        )

    def _create_primary(self, mirror_type: str) -> Mirror:
        """Create the primary mirror based on the specified type."""
        if mirror_type == "parabolic":
            return ParabolicMirror(
                focal_length=self.focal_length,
                diameter=self.primary_diameter,
                center=(0.0, 0.0),
            )
        elif mirror_type == "spherical":
            # For a spherical mirror, R = 2f gives the same paraxial
            # focal length as a parabolic mirror with focal length f.
            return SphericalMirror(
                radius_of_curvature=2.0 * self.focal_length,
                diameter=self.primary_diameter,
                center=(0.0, 0.0),
            )
        else:
            raise ValueError(
                f"Unknown primary mirror type: '{mirror_type}'. "
                f"Use 'parabolic' or 'spherical'."
            )

    @property
    def focal_ratio(self) -> float:
        """The f-number (focal ratio) of the telescope."""
        return self.focal_length / self.primary_diameter

    @property
    def tube_length(self) -> float:
        """Approximate tube length (primary to secondary)."""
        return self.secondary_offset

    @property
    def obstruction_ratio(self) -> float:
        """Central obstruction ratio (secondary diameter / primary diameter)."""
        return self.secondary_minor_axis / self.primary_diameter

    def trace_ray(self, ray: Ray) -> Ray:
        """Trace a single ray through the full optical system.

        The ray is modified in place and also returned.
        Sequence: primary mirror -> secondary mirror -> propagate
        to focal area.

        Args:
            ray: The incoming Ray to trace.

        Returns:
            The same Ray, now with updated history.
        """
        # Step 1: Reflect off primary mirror
        hit_primary = self.primary.reflect_ray(ray)
        if not hit_primary:
            return ray

        # Step 2: Reflect off secondary mirror
        hit_secondary = self.secondary.reflect_ray(ray)
        if not hit_secondary:
            end_point = ray.origin + ray.direction * self.focal_length * 0.3
            ray.propagate_to(end_point)
            return ray

        # Step 3: Propagate to focal plane
        extension = self.primary_diameter * 0.6
        focal_point = ray.origin + ray.direction * extension
        ray.propagate_to(focal_point)

        return ray

    def trace_rays(self, rays: list[Ray]) -> list[Ray]:
        """Trace multiple rays through the telescope.

        Args:
            rays: List of incoming Ray objects.

        Returns:
            The same list of rays, now traced.
        """
        for ray in rays:
            self.trace_ray(ray)
        return rays

    def get_components_for_plotting(self) -> dict:
        """Return geometric data needed by the plotting module."""
        return {
            "primary_surface": self.primary.get_surface_points(),
            "secondary_surface": self.secondary.get_surface_points(),
            "primary_diameter": self.primary_diameter,
            "focal_length": self.focal_length,
            "secondary_offset": self.secondary_offset,
            "tube_length": self.tube_length,
            "primary_type": self.primary_type,
        }

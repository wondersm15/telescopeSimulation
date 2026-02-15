"""Light source definitions for telescope simulation."""

import numpy as np

from telescope_sim.physics.ray import Ray


def create_parallel_rays(num_rays: int, aperture_diameter: float,
                         entry_height: float,
                         direction: tuple[float, float] = (0.0, -1.0),
                         margin_fraction: float = 0.05) -> list[Ray]:
    """Create parallel rays simulating a point source at infinity.

    Rays are evenly spaced across the aperture diameter and enter
    from a specified height, traveling in the given direction.
    This models starlight (effectively parallel due to immense distance).

    Args:
        num_rays: Number of rays to generate.
        aperture_diameter: Diameter across which to spread the rays,
                           matching the telescope primary mirror.
        entry_height: The y-coordinate where rays start (should be
                      above the telescope).
        direction: Direction vector for all rays. Default is
                   (0, -1) for straight down (on-axis).
        margin_fraction: Fraction of the aperture to leave as
                         margin at edges to avoid edge effects.

    Returns:
        List of Ray objects.
    """
    direction = np.asarray(direction, dtype=float)
    direction = direction / np.linalg.norm(direction)

    usable_radius = (aperture_diameter / 2.0) * (1.0 - margin_fraction)

    if num_rays == 1:
        x_positions = np.array([0.0])
    else:
        x_positions = np.linspace(-usable_radius, usable_radius, num_rays)

    rays = []
    for x in x_positions:
        origin = np.array([x, entry_height])
        rays.append(Ray(origin=origin, direction=direction.copy()))

    return rays

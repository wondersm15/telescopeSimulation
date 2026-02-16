"""Physics module: ray representation and optical physics."""

from telescope_sim.physics.ray import Ray
from telescope_sim.physics.reflection import reflect_direction
from telescope_sim.physics.diffraction import compute_psf

__all__ = ["Ray", "reflect_direction", "compute_psf"]

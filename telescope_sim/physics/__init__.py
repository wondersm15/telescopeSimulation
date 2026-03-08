"""Physics module: ray representation and optical physics."""

from telescope_sim.physics.ray import Ray
from telescope_sim.physics.reflection import reflect_direction
from telescope_sim.physics.refraction import (
    refract_direction,
    refractive_index_cauchy,
    GLASS_CATALOG,
)
from telescope_sim.physics.diffraction import compute_psf
from telescope_sim.physics.vignetting import (
    circle_overlap_fraction,
    compute_vignetting,
    fully_illuminated_field,
)
from telescope_sim.physics.fft_psf import build_pupil_mask, compute_fft_psf
from telescope_sim.physics.aberrations import (
    compute_coma_spot,
    compute_coma_rms,
    coma_free_field,
)

__all__ = [
    "Ray",
    "reflect_direction",
    "refract_direction",
    "refractive_index_cauchy",
    "GLASS_CATALOG",
    "compute_psf",
    "circle_overlap_fraction",
    "compute_vignetting",
    "fully_illuminated_field",
    "build_pupil_mask",
    "compute_fft_psf",
    "compute_coma_spot",
    "compute_coma_rms",
    "coma_free_field",
]

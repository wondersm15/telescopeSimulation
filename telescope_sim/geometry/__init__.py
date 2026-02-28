"""Geometry module: telescope structures and optical components."""

from telescope_sim.geometry.eyepiece import Eyepiece
from telescope_sim.geometry.mirrors import (
    FlatMirror,
    HyperbolicMirror,
    Mirror,
    ParabolicMirror,
    SphericalMirror,
)
from telescope_sim.geometry.lenses import Lens, SphericalLens
from telescope_sim.geometry.telescope import (
    CassegrainTelescope,
    MaksutovCassegrainTelescope,
    NewtonianTelescope,
    RefractingTelescope,
)

__all__ = [
    "Eyepiece",
    "Mirror",
    "ParabolicMirror",
    "SphericalMirror",
    "HyperbolicMirror",
    "FlatMirror",
    "Lens",
    "SphericalLens",
    "NewtonianTelescope",
    "CassegrainTelescope",
    "MaksutovCassegrainTelescope",
    "RefractingTelescope",
]

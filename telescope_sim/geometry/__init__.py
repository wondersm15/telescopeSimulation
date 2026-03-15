"""Geometry module: telescope structures and optical components."""

from telescope_sim.geometry.eyepiece import Eyepiece
from telescope_sim.geometry.mirrors import (
    FlatMirror,
    HyperbolicMirror,
    Mirror,
    ParabolicMirror,
    SphericalMirror,
)
from telescope_sim.geometry.lenses import AchromaticDoublet, Lens, SphericalLens
from telescope_sim.geometry.telescope import (
    CassegrainTelescope,
    MaksutovCassegrainTelescope,
    NewtonianTelescope,
    RefractingTelescope,
    SchmidtCassegrainTelescope,
)

__all__ = [
    "AchromaticDoublet",
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
    "SchmidtCassegrainTelescope",
]

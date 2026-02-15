"""Geometry module: telescope structures and optical components."""

from telescope_sim.geometry.mirrors import (
    FlatMirror,
    Mirror,
    ParabolicMirror,
    SphericalMirror,
)
from telescope_sim.geometry.telescope import NewtonianTelescope

__all__ = [
    "Mirror",
    "ParabolicMirror",
    "SphericalMirror",
    "FlatMirror",
    "NewtonianTelescope",
]

"""Source module: light source definitions."""

from telescope_sim.source.light_source import create_parallel_rays
from telescope_sim.source.sources import (
    AstronomicalSource,
    DoubleStar,
    Jupiter,
    Moon,
    MultiColorStarField,
    PointSource,
    Saturn,
    StarField,
    TutorialStarField,
)

__all__ = [
    "create_parallel_rays",
    "AstronomicalSource",
    "DoubleStar",
    "Jupiter",
    "Moon",
    "MultiColorStarField",
    "PointSource",
    "Saturn",
    "StarField",
    "TutorialStarField",
]

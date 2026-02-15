"""Ray data class for representing light rays in 2D."""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class Ray:
    """A single light ray in 2D space.

    Attributes:
        origin: Starting point as numpy array [x, y].
        direction: Unit direction vector as numpy array [dx, dy].
        history: List of (x, y) points the ray has visited,
                 used for plotting the ray path.
    """

    origin: np.ndarray
    direction: np.ndarray
    history: list = field(default_factory=list)

    def __post_init__(self):
        self.origin = np.asarray(self.origin, dtype=float)
        self.direction = np.asarray(self.direction, dtype=float)
        norm = np.linalg.norm(self.direction)
        if norm > 0:
            self.direction = self.direction / norm
        if not self.history:
            self.history.append(self.origin.copy())

    def propagate_to(self, point: np.ndarray):
        """Update the ray's origin to a new point and record it in history."""
        self.origin = np.asarray(point, dtype=float)
        self.history.append(self.origin.copy())

    def set_direction(self, new_direction: np.ndarray):
        """Set a new direction (will be normalized)."""
        new_direction = np.asarray(new_direction, dtype=float)
        norm = np.linalg.norm(new_direction)
        if norm > 0:
            self.direction = new_direction / norm

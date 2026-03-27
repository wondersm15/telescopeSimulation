"""Ray data class for representing light rays in 2D."""

import numpy as np
from dataclasses import dataclass, field

# Standard wavelengths for chromatic analysis (nm).
CHROMATIC_WAVELENGTHS = {
    "R": 656.3,   # Hydrogen-alpha (red)
    "G": 550.0,   # Green (design wavelength)
    "B": 486.1,   # Hydrogen-beta (blue)
}

# Matplotlib colors for each chromatic wavelength.
WAVELENGTH_COLORS = {
    656.3: "#cc3333",  # red
    550.0: "#33cc33",  # green
    486.1: "#3333cc",  # blue
}


def wavelength_to_color(wavelength_nm: float) -> str:
    """Return a hex color for a given wavelength, with fallback interpolation."""
    if wavelength_nm in WAVELENGTH_COLORS:
        return WAVELENGTH_COLORS[wavelength_nm]
    # Simple fallback: map wavelength to RGB
    if wavelength_nm <= 486.1:
        return "#3333cc"
    elif wavelength_nm >= 656.3:
        return "#cc3333"
    else:
        return "#33cc33"


@dataclass
class Ray:
    """A single light ray in 2D space.

    Attributes:
        origin: Starting point as numpy array [x, y].
        direction: Unit direction vector as numpy array [dx, dy].
        wavelength_nm: Wavelength of light in nanometers (default 550.0 green).
        aperture_position: Radial distance from aperture center in mm (optional).
                          Used for color-coding spot diagrams by incident position.
        history: List of (x, y) points the ray has visited,
                 used for plotting the ray path.
    """

    origin: np.ndarray
    direction: np.ndarray
    wavelength_nm: float = 550.0
    aperture_position: float | None = None
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

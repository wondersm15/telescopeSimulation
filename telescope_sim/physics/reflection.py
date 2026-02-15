"""Reflection physics for optical surfaces."""

import numpy as np


def reflect_direction(incoming_direction: np.ndarray,
                      surface_normal: np.ndarray) -> np.ndarray:
    """Compute the reflected direction using the law of reflection.

    Uses the formula: d_reflected = d - 2 * dot(d, n) * n

    Args:
        incoming_direction: Unit vector of the incoming ray direction.
        surface_normal: Unit vector normal to the surface at the
                        point of incidence.

    Returns:
        Unit vector of the reflected direction.
    """
    d = np.asarray(incoming_direction, dtype=float)
    n = np.asarray(surface_normal, dtype=float)
    n = n / np.linalg.norm(n)

    # Ensure normal points toward the incoming ray
    if np.dot(d, n) > 0:
        n = -n

    reflected = d - 2.0 * np.dot(d, n) * n
    return reflected / np.linalg.norm(reflected)

"""Optical lens components for telescope geometry.

All lens types implement the Lens abstract base class, ensuring
a consistent interface for intersection, refraction, and plotting.
"""

from abc import ABC, abstractmethod

import numpy as np

from telescope_sim.physics.ray import Ray
from telescope_sim.physics.refraction import (
    GLASS_CATALOG,
    refract_direction,
    refractive_index_cauchy,
)


class Lens(ABC):
    """Abstract base class for all lens types.

    Any new lens type should subclass this and implement:
        - front_intersect(ray) -> find where a ray hits the front surface
        - back_intersect(ray) -> find where a ray hits the back surface
        - front_normal_at(point) -> surface normal at front
        - back_normal_at(point) -> surface normal at back
        - get_front_surface_points() -> points for plotting
        - get_back_surface_points() -> points for plotting
    """

    @abstractmethod
    def front_intersect(self, ray: Ray) -> float | None:
        """Find the parameter t where the ray hits the front surface."""

    @abstractmethod
    def back_intersect(self, ray: Ray) -> float | None:
        """Find the parameter t where the ray hits the back surface."""

    @abstractmethod
    def front_normal_at(self, point: np.ndarray) -> np.ndarray:
        """Compute the surface normal at a point on the front surface."""

    @abstractmethod
    def back_normal_at(self, point: np.ndarray) -> np.ndarray:
        """Compute the surface normal at a point on the back surface."""

    @abstractmethod
    def get_front_surface_points(self, num_points: int = 100) -> np.ndarray:
        """Generate points along the front surface for plotting.

        Returns an array of shape (N, 2).
        """

    @abstractmethod
    def get_back_surface_points(self, num_points: int = 100) -> np.ndarray:
        """Generate points along the back surface for plotting.

        Returns an array of shape (N, 2).
        """

    def refract_ray(self, ray: Ray, wavelength_nm: float = 550.0) -> bool:
        """Refract a ray through this lens. Modifies the ray in place.

        Sequence: refract at front surface -> propagate through glass ->
        refract at back surface.

        Returns True if the ray passed through the lens, False otherwise.
        """
        # Front surface: air -> glass
        t_front = self.front_intersect(ray)
        if t_front is None:
            return False

        hit_front = ray.origin + t_front * ray.direction
        front_n = self.front_normal_at(hit_front)

        n_glass = self._refractive_index(wavelength_nm)
        new_dir = refract_direction(ray.direction, front_n, 1.0, n_glass)
        if new_dir is None:
            return False

        ray.propagate_to(hit_front)
        ray.set_direction(new_dir)

        # Back surface: glass -> air
        t_back = self.back_intersect(ray)
        if t_back is None:
            return False

        hit_back = ray.origin + t_back * ray.direction
        back_n = self.back_normal_at(hit_back)

        new_dir = refract_direction(ray.direction, back_n, n_glass, 1.0)
        if new_dir is None:
            return False

        ray.propagate_to(hit_back)
        ray.set_direction(new_dir)
        return True

    @abstractmethod
    def _refractive_index(self, wavelength_nm: float) -> float:
        """Return the refractive index of the lens material."""


class SphericalLens(Lens):
    """A lens with spherical front and back surfaces.

    Sign convention for radii of curvature (standard optics):
        - Positive R: center of curvature is on the transmission side
          (below the surface for light traveling in -y direction).
          For the front surface, R > 0 means convex toward incoming light.
        - Negative R: center of curvature is on the incidence side.
        - float('inf'): flat surface (plano).

    Common configurations:
        - Biconvex: R_front > 0, R_back < 0
        - Planoconvex: R_front > 0, R_back = inf
        - Meniscus: both R same sign

    Attributes:
        R_front: Radius of curvature of the front surface (mm).
        R_back: Radius of curvature of the back surface (mm).
        thickness: Center thickness of the lens (mm).
        diameter: Physical diameter of the lens (mm).
        center: (x, y) position of the front surface vertex.
        glass: Glass type name (looked up in GLASS_CATALOG).
    """

    def __init__(self, R_front: float, R_back: float,
                 thickness: float, diameter: float,
                 center: tuple[float, float] = (0.0, 0.0),
                 glass: str = "BK7"):
        self.R_front = R_front
        self.R_back = R_back
        self.thickness = thickness
        self.diameter = diameter
        self.center = np.asarray(center, dtype=float)
        self.radius = diameter / 2.0
        self.glass = glass

        if glass not in GLASS_CATALOG:
            raise ValueError(
                f"Unknown glass '{glass}'. "
                f"Available: {sorted(GLASS_CATALOG)}"
            )
        self._glass_coeffs = GLASS_CATALOG[glass]

        # Compute sphere centers for front and back surfaces.
        # Front surface vertex is at self.center.
        # Back surface vertex is at self.center - (0, thickness)
        # (light travels in -y direction, so back surface is below front).
        self._front_vertex = self.center.copy()
        self._back_vertex = self.center - np.array([0.0, self.thickness])

        # Standard optics: sphere center is at vertex - (0, R).
        # R > 0 → center on transmission side (below surface for front).
        # R < 0 → center on incidence side (above surface for front).
        if np.isfinite(R_front):
            self._front_sphere_center = (
                self._front_vertex - np.array([0.0, R_front])
            )
        else:
            self._front_sphere_center = None

        if np.isfinite(R_back):
            self._back_sphere_center = (
                self._back_vertex - np.array([0.0, R_back])
            )
        else:
            self._back_sphere_center = None

    def _refractive_index(self, wavelength_nm: float) -> float:
        return refractive_index_cauchy(
            wavelength_nm, self._glass_coeffs["B"], self._glass_coeffs["C"]
        )

    def _sphere_intersect(self, ray: Ray, sphere_center: np.ndarray | None,
                          R: float, vertex: np.ndarray) -> float | None:
        """Ray-sphere intersection for a single lens surface.

        For a flat surface (R = inf), does a ray-line intersection at
        the vertex y-coordinate.
        """
        if sphere_center is None:
            # Flat surface: intersect at y = vertex_y
            if abs(ray.direction[1]) < 1e-12:
                return None
            t = (vertex[1] - ray.origin[1]) / ray.direction[1]
            if t < 1e-6:
                return None
            hit_x = ray.origin[0] + t * ray.direction[0]
            if abs(hit_x - vertex[0]) > self.radius:
                return None
            return t

        # Ray-circle intersection
        oc = ray.origin - sphere_center
        a = np.dot(ray.direction, ray.direction)
        b = 2.0 * np.dot(oc, ray.direction)
        c = np.dot(oc, oc) - R * R

        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            return None

        sqrt_disc = np.sqrt(discriminant)
        t1 = (-b - sqrt_disc) / (2 * a)
        t2 = (-b + sqrt_disc) / (2 * a)

        candidates = [t for t in [t1, t2] if t > 1e-6]
        if not candidates:
            return None

        # Pick the smallest positive t within the lens diameter.
        # This selects the intersection nearest to the lens surface
        # (the correct arc of the sphere for both convex and concave).
        for t in sorted(candidates):
            hit = ray.origin + t * ray.direction
            local_x = hit[0] - vertex[0]
            if abs(local_x) <= self.radius:
                return t

        return None

    def front_intersect(self, ray: Ray) -> float | None:
        return self._sphere_intersect(
            ray, self._front_sphere_center, self.R_front,
            self._front_vertex,
        )

    def back_intersect(self, ray: Ray) -> float | None:
        return self._sphere_intersect(
            ray, self._back_sphere_center, self.R_back,
            self._back_vertex,
        )

    def _sphere_normal(self, point: np.ndarray,
                       sphere_center: np.ndarray | None) -> np.ndarray:
        """Surface normal at a point on a spherical surface."""
        if sphere_center is None:
            # Flat surface: normal is straight up
            return np.array([0.0, 1.0])
        normal = point - sphere_center
        return normal / np.linalg.norm(normal)

    def front_normal_at(self, point: np.ndarray) -> np.ndarray:
        return self._sphere_normal(point, self._front_sphere_center)

    def back_normal_at(self, point: np.ndarray) -> np.ndarray:
        return self._sphere_normal(point, self._back_sphere_center)

    def _surface_points(self, vertex: np.ndarray, R: float,
                        sphere_center: np.ndarray | None,
                        num_points: int) -> np.ndarray:
        """Generate surface points for plotting."""
        x_local = np.linspace(-self.radius, self.radius, num_points)
        if sphere_center is None:
            # Flat surface
            y_local = np.zeros(num_points)
        else:
            # Surface sag (height offset from vertex).
            # With sphere center at vertex - (0, R):
            #   R > 0: center below, surface is top arc → y = -(R - sqrt(R²-x²))
            #   R < 0: center above, surface is bottom arc → y = |R| - sqrt(R²-x²)
            r_abs = abs(R)
            safe_x = np.clip(x_local, -r_abs + 1e-6, r_abs - 1e-6)
            sag = r_abs - np.sqrt(r_abs ** 2 - safe_x ** 2)
            if R > 0:
                y_local = -sag  # surface curves downward at edges
            else:
                y_local = sag   # surface curves upward at edges
        return np.column_stack([
            x_local + vertex[0],
            y_local + vertex[1],
        ])

    def get_front_surface_points(self, num_points: int = 100) -> np.ndarray:
        return self._surface_points(
            self._front_vertex, self.R_front,
            self._front_sphere_center, num_points,
        )

    def get_back_surface_points(self, num_points: int = 100) -> np.ndarray:
        return self._surface_points(
            self._back_vertex, self.R_back,
            self._back_sphere_center, num_points,
        )

"""Optical mirror components for telescope geometry.

All mirror types implement the Mirror abstract base class, ensuring
a consistent interface for intersection, reflection, and plotting.
"""

from abc import ABC, abstractmethod

import numpy as np

from telescope_sim.physics.ray import Ray
from telescope_sim.physics.reflection import reflect_direction


class Mirror(ABC):
    """Abstract base class for all mirror types.

    Any new mirror type should subclass this and implement:
        - intersect(ray) -> find where a ray hits the surface
        - normal_at(point) -> surface normal at a given point
        - get_surface_points() -> points for plotting the mirror shape
    """

    @abstractmethod
    def intersect(self, ray: Ray) -> float | None:
        """Find the parameter t where the ray hits this mirror.

        Returns None if the ray does not hit the mirror.
        """

    @abstractmethod
    def normal_at(self, point: np.ndarray) -> np.ndarray:
        """Compute the surface normal at a given point on the mirror."""

    @abstractmethod
    def get_surface_points(self, num_points: int = 100) -> np.ndarray:
        """Generate points along the mirror surface for plotting.

        Returns an array of shape (N, 2).
        """

    def reflect_ray(self, ray: Ray) -> bool:
        """Reflect a ray off this mirror. Modifies the ray in place.

        Returns True if the ray hit the mirror, False otherwise.
        This default implementation works for all mirror types using
        the common intersect/normal_at interface.
        """
        t = self.intersect(ray)
        if t is None:
            return False

        hit_point = ray.origin + t * ray.direction
        normal = self.normal_at(hit_point)
        new_direction = reflect_direction(ray.direction, normal)

        ray.propagate_to(hit_point)
        ray.set_direction(new_direction)
        return True


class ParabolicMirror(Mirror):
    """A parabolic mirror defined by y = x^2 / (4 * focal_length).

    The mirror vertex is at the given center position and its optical
    axis is aligned along the y-axis. The reflective surface faces
    upward (toward positive y).

    Attributes:
        focal_length: Focal length of the parabola in mm.
        diameter: Physical diameter of the mirror in mm.
        center: (x, y) position of the mirror vertex.
    """

    def __init__(self, focal_length: float, diameter: float,
                 center: tuple[float, float] = (0.0, 0.0)):
        self.focal_length = focal_length
        self.diameter = diameter
        self.center = np.asarray(center, dtype=float)
        self.radius = diameter / 2.0

    def intersect(self, ray: Ray) -> float | None:
        # Shift ray to mirror-local coordinates (vertex at origin)
        ox = ray.origin[0] - self.center[0]
        oy = ray.origin[1] - self.center[1]
        dx, dy = ray.direction[0], ray.direction[1]
        f = self.focal_length

        # Solve: (ox + t*dx)^2 = 4*f*(oy + t*dy)
        a = dx * dx
        b = 2 * ox * dx - 4 * f * dy
        c = ox * ox - 4 * f * oy

        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            return None

        sqrt_disc = np.sqrt(discriminant)

        if abs(a) < 1e-12:
            # Linear case (ray parallel to parabola axis)
            if abs(b) < 1e-12:
                return None
            t = -c / b
        else:
            t1 = (-b - sqrt_disc) / (2 * a)
            t2 = (-b + sqrt_disc) / (2 * a)
            candidates = [t for t in [t1, t2] if t > 1e-6]
            if not candidates:
                return None
            t = min(candidates)

        # Check if intersection is within the mirror diameter
        hit_x = ox + t * dx
        if abs(hit_x) > self.radius:
            return None

        return t

    def normal_at(self, point: np.ndarray) -> np.ndarray:
        local_x = point[0] - self.center[0]
        f = self.focal_length
        # For y = x^2/(4f), the outward normal direction is (x/(2f), -1)
        normal = np.array([local_x / (2 * f), -1.0])
        return normal / np.linalg.norm(normal)

    def get_surface_points(self, num_points: int = 100) -> np.ndarray:
        x = np.linspace(-self.radius, self.radius, num_points)
        y = x**2 / (4 * self.focal_length)
        return np.column_stack([x + self.center[0], y + self.center[1]])


class SphericalMirror(Mirror):
    """A spherical (concave) mirror defined by a radius of curvature.

    The mirror surface is a circular arc. The center of curvature is
    at (center_x, center_y + radius_of_curvature), so the mirror
    vertex is at center and it curves upward (concave facing up).

    For comparison: a spherical mirror has focal length ~ R/2 for
    paraxial rays, but suffers from spherical aberration for
    off-axis rays (unlike a parabolic mirror).

    Attributes:
        radius_of_curvature: Radius of the spherical surface in mm.
        diameter: Physical diameter of the mirror in mm.
        center: (x, y) position of the mirror vertex.
    """

    def __init__(self, radius_of_curvature: float, diameter: float,
                 center: tuple[float, float] = (0.0, 0.0)):
        self.radius_of_curvature = radius_of_curvature
        self.diameter = diameter
        self.center = np.asarray(center, dtype=float)
        self.radius = diameter / 2.0
        # Center of the sphere is above the mirror vertex
        self.sphere_center = self.center + np.array([0.0, radius_of_curvature])

    @property
    def approximate_focal_length(self) -> float:
        """Paraxial focal length approximation: f ~ R/2."""
        return self.radius_of_curvature / 2.0

    def intersect(self, ray: Ray) -> float | None:
        # Ray-circle intersection in 2D
        # Circle: (x - cx)^2 + (y - cy)^2 = R^2
        oc = ray.origin - self.sphere_center
        dx, dy = ray.direction[0], ray.direction[1]
        r = self.radius_of_curvature

        a = dx * dx + dy * dy  # Should be 1 for unit direction
        b = 2.0 * (oc[0] * dx + oc[1] * dy)
        c = oc[0] * oc[0] + oc[1] * oc[1] - r * r

        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            return None

        sqrt_disc = np.sqrt(discriminant)
        t1 = (-b - sqrt_disc) / (2 * a)
        t2 = (-b + sqrt_disc) / (2 * a)

        # We want the intersection on the concave side (closer to vertex)
        # which is the larger t (the far side of the sphere from above)
        candidates = [t for t in [t1, t2] if t > 1e-6]
        if not candidates:
            return None

        # The concave surface is the one closer to the vertex.
        # For rays coming from above (dy < 0), this is the larger t.
        t = max(candidates)

        # Check if hit point is within the mirror diameter
        hit_point = ray.origin + t * ray.direction
        local_x = hit_point[0] - self.center[0]
        if abs(local_x) > self.radius:
            return None

        return t

    def normal_at(self, point: np.ndarray) -> np.ndarray:
        # Normal points from sphere center toward the surface point
        normal = point - self.sphere_center
        return normal / np.linalg.norm(normal)

    def get_surface_points(self, num_points: int = 100) -> np.ndarray:
        x_local = np.linspace(-self.radius, self.radius, num_points)
        r = self.radius_of_curvature
        # From circle equation: y_local = R - sqrt(R^2 - x^2)
        # (measured from vertex at origin)
        y_local = r - np.sqrt(r * r - x_local * x_local)
        return np.column_stack([
            x_local + self.center[0],
            y_local + self.center[1]
        ])


class FlatMirror(Mirror):
    """A flat mirror defined by two endpoints (a line segment in 2D).

    Used for the Newtonian secondary (diagonal) mirror.

    Attributes:
        point1: First endpoint (x, y).
        point2: Second endpoint (x, y).
    """

    def __init__(self, point1: tuple[float, float],
                 point2: tuple[float, float]):
        self.point1 = np.asarray(point1, dtype=float)
        self.point2 = np.asarray(point2, dtype=float)

    @classmethod
    def create_diagonal(cls, center: tuple[float, float],
                        minor_axis: float,
                        angle_deg: float = 45.0) -> "FlatMirror":
        """Create a diagonal flat mirror at a given angle.

        Args:
            center: Center position of the mirror (x, y).
            minor_axis: Length of the mirror along its minor axis.
            angle_deg: Angle relative to the optical axis in degrees.
                       45 degrees for a standard Newtonian.

        Returns:
            A FlatMirror instance.
        """
        center = np.asarray(center, dtype=float)
        angle_rad = np.radians(angle_deg)
        half_length = minor_axis / 2.0
        mirror_dir = np.array([np.cos(angle_rad), np.sin(angle_rad)])
        p1 = center - half_length * mirror_dir
        p2 = center + half_length * mirror_dir
        return cls(p1, p2)

    def intersect(self, ray: Ray) -> float | None:
        # Ray-line-segment intersection
        # Ray: P = O + t * D
        # Segment: Q = P1 + s * (P2 - P1), s in [0, 1]
        d = ray.direction
        seg = self.point2 - self.point1

        denom = d[0] * seg[1] - d[1] * seg[0]
        if abs(denom) < 1e-12:
            return None  # Parallel

        diff = self.point1 - ray.origin
        t = (diff[0] * seg[1] - diff[1] * seg[0]) / denom
        s = (diff[0] * d[1] - diff[1] * d[0]) / denom

        if t > 1e-6 and 0.0 <= s <= 1.0:
            return t
        return None

    def normal_at(self, point: np.ndarray) -> np.ndarray:
        # Normal is perpendicular to the segment (same everywhere)
        seg = self.point2 - self.point1
        normal = np.array([-seg[1], seg[0]])
        return normal / np.linalg.norm(normal)

    def get_surface_points(self, num_points: int = 2) -> np.ndarray:
        return np.array([self.point1, self.point2])

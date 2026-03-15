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

    def refract_ray(self, ray: Ray, wavelength_nm: float | None = None) -> bool:
        """Refract a ray through this lens. Modifies the ray in place.

        Sequence: refract at front surface -> propagate through glass ->
        refract at back surface.

        If *wavelength_nm* is not given, uses the ray's own
        ``wavelength_nm`` attribute (defaults to 550 nm for backward
        compatibility).

        Returns True if the ray passed through the lens, False otherwise.
        """
        if wavelength_nm is None:
            wavelength_nm = getattr(ray, 'wavelength_nm', 550.0)

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


class AchromaticDoublet:
    """Two-element cemented doublet objective (crown + flint glass).

    Achromatism condition: the combined lens brings two wavelengths
    (typically F and C Fraunhofer lines, 486.1 nm and 656.3 nm) to the
    same focus.  This is achieved when:

        phi_crown / V_crown + phi_flint / V_flint = 0

    where phi = 1/f is the optical power and V is the Abbe number.

    The doublet is cemented: the crown back surface and flint front
    surface share the same radius, so the interface refracts directly
    from crown glass to flint glass (no air gap).

    Attributes:
        focal_length: Combined focal length of the doublet (mm).
        diameter: Lens diameter (mm).
        center: (x, y) of the front vertex of the crown element.
        crown_glass: Glass type for the crown element (low dispersion).
        flint_glass: Glass type for the flint element (high dispersion).
        objective_type: Always ``"achromat"``.
    """

    def __init__(self, focal_length: float, diameter: float,
                 center: tuple[float, float] = (0.0, 0.0),
                 crown_glass: str = "BK7", flint_glass: str = "F2"):
        self.focal_length = focal_length
        self.diameter = diameter
        self.center = np.asarray(center, dtype=float)
        self.crown_glass = crown_glass
        self.flint_glass = flint_glass
        self.objective_type = "achromat"
        self.glass = f"{crown_glass}+{flint_glass}"

        # Compute Abbe numbers from glass catalog
        self._crown_coeffs = GLASS_CATALOG[crown_glass]
        self._flint_coeffs = GLASS_CATALOG[flint_glass]

        n_d_crown = refractive_index_cauchy(587.6, self._crown_coeffs["B"],
                                            self._crown_coeffs["C"])
        n_f_crown = refractive_index_cauchy(486.1, self._crown_coeffs["B"],
                                            self._crown_coeffs["C"])
        n_c_crown = refractive_index_cauchy(656.3, self._crown_coeffs["B"],
                                            self._crown_coeffs["C"])
        v_crown = (n_d_crown - 1.0) / (n_f_crown - n_c_crown)

        n_d_flint = refractive_index_cauchy(587.6, self._flint_coeffs["B"],
                                            self._flint_coeffs["C"])
        n_f_flint = refractive_index_cauchy(486.1, self._flint_coeffs["B"],
                                            self._flint_coeffs["C"])
        n_c_flint = refractive_index_cauchy(656.3, self._flint_coeffs["B"],
                                            self._flint_coeffs["C"])
        v_flint = (n_d_flint - 1.0) / (n_f_flint - n_c_flint)

        # Achromatism: phi_crown/V_crown + phi_flint/V_flint = 0
        # Combined power: phi_crown + phi_flint = 1/f
        phi_total = 1.0 / focal_length
        phi_crown = phi_total * v_crown / (v_crown - v_flint)
        phi_flint = phi_total - phi_crown

        # Individual focal lengths
        f_crown = 1.0 / phi_crown
        f_flint = 1.0 / phi_flint

        # Lens thicknesses
        thickness_crown = max(diameter / 15.0, 3.0)
        thickness_flint = max(diameter / 25.0, 2.0)
        self.thickness = thickness_crown + thickness_flint
        self.radius = diameter / 2.0

        # Compute radii via thin-lens lensmaker's equation.
        n_crown = refractive_index_cauchy(550.0, self._crown_coeffs["B"],
                                          self._crown_coeffs["C"])
        n_flint = refractive_index_cauchy(550.0, self._flint_coeffs["B"],
                                          self._flint_coeffs["C"])

        # Crown: symmetric biconvex → R1 = -R2 = R
        r1_crown = 2.0 * f_crown * (n_crown - 1.0)
        # Interface: from crown lensmaker's
        r_interface_inv = 1.0 / r1_crown - phi_crown / (n_crown - 1.0)
        r_interface = (1.0 / r_interface_inv
                       if abs(r_interface_inv) > 1e-12 else float('inf'))
        # Flint back:
        r3_inv = r_interface_inv - phi_flint / (n_flint - 1.0)
        r3_flint = (1.0 / r3_inv
                    if abs(r3_inv) > 1e-12 else float('inf'))

        # Iterative paraxial-ray solver to refine radii for thick lenses.
        # Trace a ray through the cemented doublet (air→crown→flint→air)
        # and adjust radii to match the target focal length.
        crown_y = center[1]
        for _iteration in range(15):
            # Build temporary lens objects for the cemented doublet
            temp_crown = SphericalLens(
                R_front=r1_crown, R_back=r_interface,
                thickness=thickness_crown, diameter=diameter,
                center=(center[0], crown_y), glass=crown_glass,
            )
            temp_flint = SphericalLens(
                R_front=r_interface, R_back=r3_flint,
                thickness=thickness_flint, diameter=diameter,
                center=(center[0], crown_y - thickness_crown),
                glass=flint_glass,
            )

            h = diameter * 0.02
            test_ray = Ray(
                origin=np.array([h, crown_y + 100.0]),
                direction=np.array([0.0, -1.0]),
            )

            # Manually trace: air→crown, crown→flint, flint→air
            wl = 550.0
            nc = refractive_index_cauchy(wl, self._crown_coeffs["B"],
                                         self._crown_coeffs["C"])
            nf = refractive_index_cauchy(wl, self._flint_coeffs["B"],
                                         self._flint_coeffs["C"])

            # Surface 1: air→crown
            t1 = temp_crown.front_intersect(test_ray)
            if t1 is None:
                break
            p1 = test_ray.origin + t1 * test_ray.direction
            n1 = temp_crown.front_normal_at(p1)
            d1 = refract_direction(test_ray.direction, n1, 1.0, nc)
            if d1 is None:
                break
            test_ray.propagate_to(p1)
            test_ray.set_direction(d1)

            # Surface 2: crown→flint (cemented)
            t2 = temp_crown.back_intersect(test_ray)
            if t2 is None:
                break
            p2 = test_ray.origin + t2 * test_ray.direction
            n2 = temp_crown.back_normal_at(p2)
            d2 = refract_direction(test_ray.direction, n2, nc, nf)
            if d2 is None:
                break
            test_ray.propagate_to(p2)
            test_ray.set_direction(d2)

            # Surface 3: flint→air
            t3 = temp_flint.back_intersect(test_ray)
            if t3 is None:
                break
            p3 = test_ray.origin + t3 * test_ray.direction
            n3 = temp_flint.back_normal_at(p3)
            d3 = refract_direction(test_ray.direction, n3, nf, 1.0)
            if d3 is None:
                break
            test_ray.propagate_to(p3)
            test_ray.set_direction(d3)

            if abs(test_ray.direction[0]) < 1e-15:
                break
            t_axis = -test_ray.origin[0] / test_ray.direction[0]
            focus_y = (test_ray.origin[1]
                       + t_axis * test_ray.direction[1])
            lens_center_y = crown_y - thickness_crown / 2.0
            measured_f = lens_center_y - focus_y
            if abs(measured_f) < 1e-6:
                break
            scale = focal_length / measured_f
            if abs(scale - 1.0) < 1e-4:
                break
            r1_crown *= scale
            r_interface *= scale
            r3_flint *= scale

        # Store final radii
        self._r1 = r1_crown
        self._r_interface = r_interface
        self._r3 = r3_flint
        self._thickness_crown = thickness_crown
        self._thickness_flint = thickness_flint

        # Build SphericalLens objects for surface geometry (plotting).
        # These are NOT used for refraction — refract_ray handles
        # the cemented interface directly.
        self.crown = SphericalLens(
            R_front=r1_crown, R_back=r_interface,
            thickness=thickness_crown, diameter=diameter,
            center=(center[0], crown_y), glass=crown_glass,
        )
        flint_y = crown_y - thickness_crown
        self.flint = SphericalLens(
            R_front=r_interface, R_back=r3_flint,
            thickness=thickness_flint, diameter=diameter,
            center=(center[0], flint_y), glass=flint_glass,
        )

    def _n_crown(self, wavelength_nm: float) -> float:
        return refractive_index_cauchy(
            wavelength_nm, self._crown_coeffs["B"],
            self._crown_coeffs["C"],
        )

    def _n_flint(self, wavelength_nm: float) -> float:
        return refractive_index_cauchy(
            wavelength_nm, self._flint_coeffs["B"],
            self._flint_coeffs["C"],
        )

    def refract_ray(self, ray: Ray, wavelength_nm: float | None = None) -> bool:
        """Refract a ray through the cemented doublet.

        Sequence:
        1. Air → crown front surface (air→glass refraction)
        2. Propagate through crown glass
        3. Crown back / flint front surface (crown→flint refraction)
        4. Propagate through flint glass
        5. Flint back surface (glass→air refraction)

        Returns True if the ray passed through all three surfaces.
        """
        if wavelength_nm is None:
            wavelength_nm = getattr(ray, 'wavelength_nm', 550.0)

        n_crown = self._n_crown(wavelength_nm)
        n_flint = self._n_flint(wavelength_nm)

        # Surface 1: air → crown (front surface of crown lens)
        t_front = self.crown.front_intersect(ray)
        if t_front is None:
            return False
        hit_front = ray.origin + t_front * ray.direction
        front_n = self.crown.front_normal_at(hit_front)
        new_dir = refract_direction(ray.direction, front_n, 1.0, n_crown)
        if new_dir is None:
            return False
        ray.propagate_to(hit_front)
        ray.set_direction(new_dir)

        # Surface 2: crown → flint (cemented interface)
        t_interface = self.crown.back_intersect(ray)
        if t_interface is None:
            return False
        hit_interface = ray.origin + t_interface * ray.direction
        interface_n = self.crown.back_normal_at(hit_interface)
        new_dir = refract_direction(ray.direction, interface_n,
                                    n_crown, n_flint)
        if new_dir is None:
            return False
        ray.propagate_to(hit_interface)
        ray.set_direction(new_dir)

        # Surface 3: flint → air (back surface of flint lens)
        t_back = self.flint.back_intersect(ray)
        if t_back is None:
            return False
        hit_back = ray.origin + t_back * ray.direction
        back_n = self.flint.back_normal_at(hit_back)
        new_dir = refract_direction(ray.direction, back_n, n_flint, 1.0)
        if new_dir is None:
            return False
        ray.propagate_to(hit_back)
        ray.set_direction(new_dir)
        return True

    def get_front_surface_points(self, num_points: int = 100) -> np.ndarray:
        """Front surface of the crown element."""
        return self.crown.get_front_surface_points(num_points)

    def get_back_surface_points(self, num_points: int = 100) -> np.ndarray:
        """Back surface of the flint element."""
        return self.flint.get_back_surface_points(num_points)

    def get_interface_surface_points(self, num_points: int = 100) -> np.ndarray:
        """Cemented interface between crown and flint."""
        return self.crown.get_back_surface_points(num_points)

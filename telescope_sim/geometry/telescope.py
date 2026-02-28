"""Telescope assembly that combines optical components."""

import numpy as np

from telescope_sim.geometry.mirrors import (
    FlatMirror,
    HyperbolicMirror,
    Mirror,
    ParabolicMirror,
    SphericalMirror,
)
from telescope_sim.geometry.lenses import SphericalLens
from telescope_sim.physics.ray import Ray
from telescope_sim.physics.reflection import reflect_direction


class NewtonianTelescope:
    """A Newtonian reflector telescope.

    Coordinate system:
        - The primary mirror vertex sits at (0, 0).
        - The optical axis runs along the y-axis (positive y
          is upward, toward incoming light).
        - The secondary mirror redirects light to the +x direction
          (to the right) toward the eyepiece.

    The primary mirror type is configurable — use 'parabolic' for
    a standard Newtonian or 'spherical' to study spherical aberration.

    Attributes:
        primary_diameter: Diameter of the primary mirror in mm.
        focal_length: Focal length of the primary mirror in mm.
        secondary_offset: Distance of secondary mirror center from
                          primary vertex along the y-axis in mm.
        secondary_minor_axis: Minor axis size of the secondary in mm.
        primary_type: Type of primary mirror ('parabolic' or 'spherical').
        spider_vanes: Number of spider vanes holding the secondary
                      (0=none, 3/4/6 typical).
        spider_vane_width: Width of each spider vane in mm.
    """

    def __init__(self, primary_diameter: float, focal_length: float,
                 secondary_offset: float | None = None,
                 secondary_minor_axis: float | None = None,
                 primary_type: str = "parabolic",
                 spider_vanes: int = 0,
                 spider_vane_width: float = 1.0):
        self.primary_diameter = primary_diameter
        self.focal_length = focal_length
        self.primary_type = primary_type
        self.spider_vanes = spider_vanes
        self.spider_vane_width = spider_vane_width

        if secondary_offset is None:
            secondary_offset = focal_length - primary_diameter * 0.1
        self.secondary_offset = secondary_offset

        if secondary_minor_axis is None:
            secondary_minor_axis = primary_diameter * 0.2
        self.secondary_minor_axis = secondary_minor_axis

        # Build primary mirror
        self.primary: Mirror = self._create_primary(primary_type)

        # Build secondary mirror (flat diagonal at 45 degrees)
        self.secondary = FlatMirror.create_diagonal(
            center=(0.0, secondary_offset),
            minor_axis=secondary_minor_axis,
            angle_deg=45.0,
        )

    def _create_primary(self, mirror_type: str) -> Mirror:
        """Create the primary mirror based on the specified type."""
        if mirror_type == "parabolic":
            return ParabolicMirror(
                focal_length=self.focal_length,
                diameter=self.primary_diameter,
                center=(0.0, 0.0),
            )
        elif mirror_type == "spherical":
            # For a spherical mirror, R = 2f gives the same paraxial
            # focal length as a parabolic mirror with focal length f.
            return SphericalMirror(
                radius_of_curvature=2.0 * self.focal_length,
                diameter=self.primary_diameter,
                center=(0.0, 0.0),
            )
        else:
            raise ValueError(
                f"Unknown primary mirror type: '{mirror_type}'. "
                f"Use 'parabolic' or 'spherical'."
            )

    @property
    def focal_ratio(self) -> float:
        """The f-number (focal ratio) of the telescope."""
        return self.focal_length / self.primary_diameter

    @property
    def tube_length(self) -> float:
        """Approximate tube length (primary to secondary)."""
        return self.secondary_offset

    @property
    def obstruction_ratio(self) -> float:
        """Central obstruction ratio (secondary diameter / primary diameter)."""
        return self.secondary_minor_axis / self.primary_diameter

    def trace_ray(self, ray: Ray) -> Ray:
        """Trace a single ray through the full optical system.

        The ray is modified in place and also returned.
        Sequence: primary mirror -> secondary mirror -> propagate
        to focal area.

        Args:
            ray: The incoming Ray to trace.

        Returns:
            The same Ray, now with updated history.
        """
        # Step 1: Reflect off primary mirror
        hit_primary = self.primary.reflect_ray(ray)
        if not hit_primary:
            return ray

        # Step 2: Reflect off secondary mirror
        hit_secondary = self.secondary.reflect_ray(ray)
        if not hit_secondary:
            end_point = ray.origin + ray.direction * self.focal_length * 0.3
            ray.propagate_to(end_point)
            return ray

        # Step 3: Propagate to focal plane
        extension = self.primary_diameter * 0.6
        focal_point = ray.origin + ray.direction * extension
        ray.propagate_to(focal_point)

        return ray

    def trace_rays(self, rays: list[Ray]) -> list[Ray]:
        """Trace multiple rays through the telescope.

        Args:
            rays: List of incoming Ray objects.

        Returns:
            The same list of rays, now traced.
        """
        for ray in rays:
            self.trace_ray(ray)
        return rays

    def compute_vignetting(self, field_angle_arcsec):
        """Illumination fraction at a given off-axis field angle.

        Delegates to the vignetting physics module.  See
        ``telescope_sim.physics.vignetting.compute_vignetting`` for details.

        NOTE: Tube wall vignetting is not modeled.

        Args:
            field_angle_arcsec: Off-axis angle in arcseconds (scalar or array).

        Returns:
            Illumination fraction (0.0 to 1.0), same shape as input.
        """
        from telescope_sim.physics.vignetting import compute_vignetting
        return compute_vignetting(
            field_angle_arcsec, self.primary_diameter, self.focal_length,
            self.secondary_offset, self.secondary_minor_axis,
        )

    def fully_illuminated_field(self) -> float:
        """Field angle (arcsec) where vignetting begins.

        Returns:
            Field angle in arcseconds where illumination first drops
            below 1.0.
        """
        from telescope_sim.physics.vignetting import fully_illuminated_field
        return fully_illuminated_field(
            self.primary_diameter, self.focal_length,
            self.secondary_offset, self.secondary_minor_axis,
        )

    def get_components_for_plotting(self) -> dict:
        """Return geometric data needed by the plotting module."""
        components = {
            "primary_surface": self.primary.get_surface_points(),
            "secondary_surface": self.secondary.get_surface_points(),
            "primary_diameter": self.primary_diameter,
            "focal_length": self.focal_length,
            "secondary_offset": self.secondary_offset,
            "tube_length": self.tube_length,
            "primary_type": self.primary_type,
            "secondary_type": "flat",
        }
        if self.spider_vanes > 0:
            components["spider_vanes"] = self.spider_vanes
            components["spider_vane_width"] = self.spider_vane_width
            components["secondary_minor_axis"] = self.secondary_minor_axis
        return components


class CassegrainTelescope:
    """A Classical Cassegrain reflector telescope.

    Uses a parabolic primary and a convex hyperbolic secondary. Light
    reflects off the primary, hits the convex secondary which magnifies
    and reflects it back down through a central hole in the primary to
    a focal point behind the primary mirror.

    Coordinate system:
        - The primary mirror vertex sits at (0, 0).
        - The optical axis runs along the y-axis (positive y is upward,
          toward incoming light).
        - The focal point is below the primary at (0, -back_focal_distance).

    Attributes:
        primary_diameter: Diameter of the primary mirror in mm.
        primary_focal_length: Focal length of the primary alone in mm.
        focal_length: Effective system focal length in mm
                      (= primary_focal_length × secondary_magnification).
        secondary_magnification: Amplification factor of the secondary.
        back_focal_distance: Distance from primary vertex to focal point
                             behind the primary (mm).
        secondary_offset: Distance of secondary from primary along y-axis.
        secondary_minor_axis: Diameter of the secondary mirror in mm.
        primary_type: Always 'parabolic' for a Classical Cassegrain.
        spider_vanes: Number of spider vanes (0=none, 3/4/6 typical).
        spider_vane_width: Width of each spider vane in mm.
    """

    def __init__(self, primary_diameter: float,
                 primary_focal_length: float,
                 secondary_magnification: float = 4.0,
                 back_focal_distance: float | None = None,
                 spider_vanes: int = 0,
                 spider_vane_width: float = 1.0):
        self.primary_diameter = primary_diameter
        self.primary_focal_length = primary_focal_length
        self.secondary_magnification = secondary_magnification
        self.primary_type = "parabolic"
        self.spider_vanes = spider_vanes
        self.spider_vane_width = spider_vane_width

        # Effective focal length of the whole system
        self.focal_length = primary_focal_length * secondary_magnification

        # Back focal distance: how far behind the primary the focus lands.
        # Default to a reasonable value if not specified.
        if back_focal_distance is None:
            back_focal_distance = primary_diameter * 0.15
        self.back_focal_distance = back_focal_distance

        # --- Cassegrain geometry derivation ---
        # F1 = primary focal point = (0, primary_focal_length)
        # The secondary sits between the primary and F1.
        # Let M = secondary_magnification, f = primary_focal_length,
        #     B = back_focal_distance.
        #
        # The secondary distance from F1:
        #   s = f * (M - 1) / (M + 1) ... but we also need B.
        # More precisely, from the Cassegrain mirror equation:
        #   secondary_offset = f - f*(M-1)/(M+1) ... simplified:
        #
        # Standard formulas:
        #   d = distance from secondary to primary focus = (B + f) / (M + 1)
        #   secondary_offset from primary = f - d

        m = secondary_magnification
        f = primary_focal_length
        b = back_focal_distance

        # Distance from secondary to primary focal point
        d = (b + f) / (m + 1.0)
        self.secondary_offset = f - d

        # Secondary mirror diameter: determined by the light cone from
        # the primary. At the secondary's position, the beam from the
        # primary edge subtends:
        self.secondary_minor_axis = (
            primary_diameter * d / f
        )

        # --- Hyperbolic secondary parameters ---
        # The two foci of the hyperbola are at:
        #   F1 = primary focal point = (0, f)   (far focus)
        #   F2 = system focal point = (0, -B)   (back focus)
        # The secondary vertex is at (0, secondary_offset).
        #
        # For a hyperbola with foci at distance 2c apart:
        #   2c = F1-to-F2 distance = f + B
        #   c = (f + B) / 2
        # The vertex of the branch nearest F1 is at distance
        # (c - a) from F1:
        #   c - a = d  =>  a = c - d
        #
        # Using d = (f+B)/(M+1):
        #   a = (f+B)/2 - (f+B)/(M+1) = (f+B)(M-1) / (2(M+1))
        #   e = c/a = (M+1)/(M-1)

        half_c = (f + b) / 2.0
        semi_major = half_c - d  # a = c - d
        eccentricity = half_c / semi_major  # e = c/a = (M+1)/(M-1)

        # Build the primary mirror (parabolic)
        self.primary: Mirror = ParabolicMirror(
            focal_length=primary_focal_length,
            diameter=primary_diameter,
            center=(0.0, 0.0),
        )

        # Build the secondary mirror (convex hyperbolic)
        self.secondary = HyperbolicMirror(
            semi_major_axis=semi_major,
            eccentricity=eccentricity,
            diameter=self.secondary_minor_axis,
            center=(0.0, self.secondary_offset),
        )

    @property
    def focal_ratio(self) -> float:
        """The f-number (effective focal ratio) of the telescope."""
        return self.focal_length / self.primary_diameter

    @property
    def tube_length(self) -> float:
        """Approximate tube length (primary to secondary)."""
        return self.secondary_offset

    @property
    def obstruction_ratio(self) -> float:
        """Central obstruction ratio (secondary diameter / primary diameter)."""
        return self.secondary_minor_axis / self.primary_diameter

    def trace_ray(self, ray: Ray) -> Ray:
        """Trace a single ray through the Cassegrain optical system.

        Sequence: primary (concave parabolic) -> secondary (convex
        hyperbolic) -> back through central hole -> focal plane
        behind primary.

        Args:
            ray: The incoming Ray to trace.

        Returns:
            The same Ray, now with updated history.
        """
        # Step 1: Reflect off primary mirror
        hit_primary = self.primary.reflect_ray(ray)
        if not hit_primary:
            return ray

        # Step 2: Reflect off secondary mirror (convex hyperbolic)
        hit_secondary = self.secondary.reflect_ray(ray)
        if not hit_secondary:
            # Missed secondary — propagate toward primary focus
            end_point = ray.origin + ray.direction * self.primary_focal_length * 0.3
            ray.propagate_to(end_point)
            return ray

        # Step 3: Propagate down through the hole in the primary to
        # the focal plane behind it. The focal point is at
        # y = -back_focal_distance. Extend a bit past for visualization.
        target_y = -self.back_focal_distance - self.primary_diameter * 0.05
        if abs(ray.direction[1]) > 1e-12:
            t = (target_y - ray.origin[1]) / ray.direction[1]
            if t > 0:
                focal_point = ray.origin + ray.direction * t
                ray.propagate_to(focal_point)
            else:
                # Fallback: propagate a fixed distance
                ray.propagate_to(
                    ray.origin + ray.direction * self.primary_focal_length * 0.5
                )
        else:
            ray.propagate_to(
                ray.origin + ray.direction * self.primary_focal_length * 0.5
            )

        return ray

    def trace_rays(self, rays: list[Ray]) -> list[Ray]:
        """Trace multiple rays through the telescope."""
        for ray in rays:
            self.trace_ray(ray)
        return rays

    def compute_vignetting(self, field_angle_arcsec):
        """Illumination fraction at a given off-axis field angle.

        Uses the same vignetting model as Newtonian, treating the
        secondary as the limiting obstruction.

        NOTE: Tube wall vignetting and central hole vignetting not modeled.
        """
        from telescope_sim.physics.vignetting import compute_vignetting
        return compute_vignetting(
            field_angle_arcsec, self.primary_diameter,
            self.primary_focal_length,
            self.secondary_offset, self.secondary_minor_axis,
        )

    def fully_illuminated_field(self) -> float:
        """Field angle (arcsec) where vignetting begins."""
        from telescope_sim.physics.vignetting import fully_illuminated_field
        return fully_illuminated_field(
            self.primary_diameter, self.primary_focal_length,
            self.secondary_offset, self.secondary_minor_axis,
        )

    def get_components_for_plotting(self) -> dict:
        """Return geometric data needed by the plotting module.

        Returns the same dict keys as NewtonianTelescope so all
        existing plotting code works unchanged.
        """
        components = {
            "primary_surface": self.primary.get_surface_points(),
            "secondary_surface": self.secondary.get_surface_points(),
            "primary_diameter": self.primary_diameter,
            "focal_length": self.focal_length,
            "secondary_offset": self.secondary_offset,
            "tube_length": self.tube_length,
            "primary_type": self.primary_type,
            "secondary_type": "hyperbolic",
        }
        if self.spider_vanes > 0:
            components["spider_vanes"] = self.spider_vanes
            components["spider_vane_width"] = self.spider_vane_width
            components["secondary_minor_axis"] = self.secondary_minor_axis
        return components


class RefractingTelescope:
    """A refracting telescope with an objective lens.

    Uses a converging lens (objective) to focus incoming light directly
    to a focal point.  No secondary mirror — zero central obstruction,
    producing a clean Airy diffraction pattern.

    Coordinate system:
        - The objective lens front vertex sits at (0, tube_length).
        - The optical axis runs along the y-axis (positive y is upward,
          toward incoming light).
        - The focal point is at (0, 0) approximately.

    Attributes:
        primary_diameter: Diameter of the objective lens in mm.
        focal_length: Focal length of the objective in mm.
        objective_type: Currently ``"singlet"``; future: ``"achromat"``.
        primary_type: Always ``"lens"`` — used by plotting and analysis
                      code to distinguish from reflectors.
        secondary_minor_axis: Always 0 (no secondary).
        spider_vanes: Always 0 (no spider support needed).
        spider_vane_width: Always 0.
    """

    def __init__(self, primary_diameter: float, focal_length: float,
                 objective_type: str = "singlet",
                 spider_vanes: int = 0,
                 spider_vane_width: float = 0.0):
        self.primary_diameter = primary_diameter
        self.focal_length = focal_length
        self.objective_type = objective_type
        self.primary_type = "lens"
        self.secondary_minor_axis = 0.0
        self.spider_vanes = spider_vanes
        self.spider_vane_width = spider_vane_width

        # Build objective lens using thin-lens / lensmaker's equation.
        # For a symmetric biconvex singlet in BK7 (n ≈ 1.519 at 550nm):
        #   1/f = (n-1) * [1/R_front - 1/R_back]
        # For symmetric biconvex: R_front = R, R_back = -R
        #   1/f = (n-1) * 2/R  =>  R = 2*f*(n-1)
        from telescope_sim.physics.refraction import (
            GLASS_CATALOG,
            refractive_index_cauchy,
        )
        glass = "BK7"
        coeffs = GLASS_CATALOG[glass]
        n = refractive_index_cauchy(550.0, coeffs["B"], coeffs["C"])
        R = 2.0 * focal_length * (n - 1.0)

        # Lens thickness: reasonable default
        thickness = max(primary_diameter / 15.0, 3.0)

        # Place the lens so that its front vertex is at (0, focal_length).
        # Light enters from above (y > focal_length), refracts through
        # the lens, and converges near y = 0.
        lens_y = focal_length
        self.objective = SphericalLens(
            R_front=R,
            R_back=-R,
            thickness=thickness,
            diameter=primary_diameter,
            center=(0.0, lens_y),
            glass=glass,
        )

        # Store derived quantities
        self._lens_y = lens_y
        self._thickness = thickness

    @property
    def focal_ratio(self) -> float:
        """The f-number (focal ratio) of the telescope."""
        return self.focal_length / self.primary_diameter

    @property
    def tube_length(self) -> float:
        """Approximate tube length (lens to focal plane)."""
        return self.focal_length

    @property
    def obstruction_ratio(self) -> float:
        """Central obstruction ratio — always 0 for a refractor."""
        return 0.0

    def trace_ray(self, ray: Ray) -> Ray:
        """Trace a single ray through the refracting telescope.

        Sequence: refract through objective lens -> propagate to
        focal area.

        Args:
            ray: The incoming Ray to trace.

        Returns:
            The same Ray, now with updated history.
        """
        hit = self.objective.refract_ray(ray)
        if not hit:
            return ray

        # Propagate toward the focal plane (y ≈ 0).
        # Extend a bit past for visualization.
        target_y = -self.primary_diameter * 0.05
        if abs(ray.direction[1]) > 1e-12:
            t = (target_y - ray.origin[1]) / ray.direction[1]
            if t > 0:
                focal_point = ray.origin + ray.direction * t
                ray.propagate_to(focal_point)
            else:
                ray.propagate_to(
                    ray.origin + ray.direction * self.focal_length * 0.3
                )
        else:
            ray.propagate_to(
                ray.origin + ray.direction * self.focal_length * 0.3
            )

        return ray

    def trace_rays(self, rays: list[Ray]) -> list[Ray]:
        """Trace multiple rays through the telescope."""
        for ray in rays:
            self.trace_ray(ray)
        return rays

    def compute_vignetting(self, field_angle_arcsec):
        """Illumination fraction at a given off-axis field angle.

        For a refractor with no secondary obstruction, vignetting is
        minimal (only tube wall, which is not modeled).  Returns 1.0
        for all field angles.

        NOTE: Tube wall vignetting is not modeled.
        """
        field_angle_arcsec = np.asarray(field_angle_arcsec)
        return np.ones_like(field_angle_arcsec, dtype=float)

    def fully_illuminated_field(self) -> float:
        """Field angle (arcsec) where vignetting begins.

        Without tube wall modeling, returns a large value.
        """
        return 1e6  # effectively infinite

    def get_components_for_plotting(self) -> dict:
        """Return geometric data needed by the plotting module.

        Returns dict with standard keys plus ``"telescope_style": "refractor"``
        to signal lens-specific drawing.
        """
        components = {
            "primary_surface": self.objective.get_front_surface_points(),
            "secondary_surface": self.objective.get_back_surface_points(),
            "primary_diameter": self.primary_diameter,
            "focal_length": self.focal_length,
            "secondary_offset": self._lens_y,
            "tube_length": self.tube_length,
            "primary_type": self.primary_type,
            "secondary_type": "lens",
            "telescope_style": "refractor",
            "objective_glass": self.objective.glass,
        }
        return components


class MaksutovCassegrainTelescope:
    """A Maksutov-Cassegrain catadioptric telescope.

    Combines a meniscus corrector lens with a spherical primary mirror.
    An aluminized spot on the back surface of the meniscus acts as the
    convex secondary mirror, reflecting converging light back through
    a hole in the primary to a back focus.

    This design exercises both refraction (meniscus) and reflection
    (primary + aluminized spot) in a single ray path.

    Coordinate system:
        - The primary mirror vertex sits at (0, 0).
        - The optical axis runs along the y-axis (positive y is upward,
          toward incoming light).
        - The focal point is below the primary at (0, -back_focal_distance).

    Attributes:
        primary_diameter: Diameter of the primary mirror in mm.
        primary_focal_length: Focal length of the spherical primary in mm.
        focal_length: Effective system focal length in mm
                      (= primary_focal_length x secondary_magnification).
        secondary_magnification: Amplification factor of the secondary.
        back_focal_distance: Distance from primary vertex to focal point
                             behind the primary (mm).
        secondary_offset: Distance of corrector/spot from primary along y.
        secondary_minor_axis: Diameter of the aluminized spot in mm.
        primary_type: Always 'spherical' for a Maksutov-Cassegrain.
        corrected_optics: Always True — meniscus corrects spherical
                          aberration of the primary.
        spider_vanes: Number of spider vanes (0 = none, typical for Mak).
        spider_vane_width: Width of each spider vane in mm.
    """

    def __init__(self, primary_diameter: float,
                 primary_focal_length: float,
                 secondary_magnification: float = 4.0,
                 back_focal_distance: float | None = None,
                 meniscus_thickness: float | None = None,
                 spider_vanes: int = 0,
                 spider_vane_width: float = 1.0):
        self.primary_diameter = primary_diameter
        self.primary_focal_length = primary_focal_length
        self.secondary_magnification = secondary_magnification
        self.primary_type = "spherical"
        self.corrected_optics = True
        self.spider_vanes = spider_vanes
        self.spider_vane_width = spider_vane_width

        # Effective focal length of the whole system
        self.focal_length = primary_focal_length * secondary_magnification

        # Back focal distance default
        if back_focal_distance is None:
            back_focal_distance = primary_diameter * 0.15
        self.back_focal_distance = back_focal_distance

        # Meniscus thickness default
        if meniscus_thickness is None:
            meniscus_thickness = primary_diameter / 10.0
        self.meniscus_thickness = meniscus_thickness

        # --- Cassegrain geometry (identical formulas) ---
        m = secondary_magnification
        f = primary_focal_length
        b = back_focal_distance

        # Distance from secondary to primary focal point
        d = (b + f) / (m + 1.0)
        self.secondary_offset = f - d

        # Aluminized spot diameter (same as Cassegrain secondary sizing)
        self.secondary_minor_axis = primary_diameter * d / f

        # Spot radius of curvature (convex secondary)
        # R_secondary = 2(f+B)M / (M^2 - 1)
        r_secondary = 2.0 * (f + b) * m / (m * m - 1.0)

        # The meniscus back surface has the same radius as the spot
        # (aluminized spot is on the back surface).
        # Convention: negative R means concave toward incoming light
        # in our lens sign convention.
        r_back = -r_secondary

        # Near-concentric meniscus: front radius from
        # 1/R_front ≈ 1/R_back + t / (n * R_back^2)
        # Approximation: assumes near-concentric design for
        # auto-computed radii.
        from telescope_sim.physics.refraction import (
            GLASS_CATALOG,
            refractive_index_cauchy,
        )
        glass = "BK7"
        coeffs = GLASS_CATALOG[glass]
        n_glass = refractive_index_cauchy(550.0, coeffs["B"], coeffs["C"])
        r_front = 1.0 / (1.0 / r_back
                         + meniscus_thickness / (n_glass * r_back ** 2))

        # Build the spherical primary mirror
        self.primary: Mirror = SphericalMirror(
            radius_of_curvature=2.0 * f,
            diameter=primary_diameter,
            center=(0.0, 0.0),
        )

        # Build the meniscus corrector lens at the secondary offset
        self.corrector = SphericalLens(
            R_front=r_front,
            R_back=r_back,
            thickness=meniscus_thickness,
            diameter=primary_diameter,
            center=(0.0, self.secondary_offset),
            glass=glass,
        )

        # Store spot geometry for the aluminized spot reflection
        self._spot_diameter = self.secondary_minor_axis
        self._spot_radius = r_secondary  # positive = convex toward primary
        # The spot is on the back surface of the meniscus.
        # Back surface sphere center (same as the lens computes internally):
        self._spot_sphere_center = self.corrector._back_sphere_center.copy()

    def _reflect_off_spot(self, ray: Ray) -> bool:
        """Reflect a ray off the aluminized spot on the meniscus back surface.

        Uses the meniscus back surface sphere geometry for ray-circle
        intersection, limited to within spot_diameter/2 of the optical axis.

        Returns True if the ray hit the spot, False otherwise.
        """
        # Ray-circle intersection with the back surface sphere
        sphere_center = self._spot_sphere_center
        r = abs(self.corrector.R_back)

        oc = ray.origin - sphere_center
        a_coeff = np.dot(ray.direction, ray.direction)
        b_coeff = 2.0 * np.dot(oc, ray.direction)
        c_coeff = np.dot(oc, oc) - r * r

        discriminant = b_coeff ** 2 - 4 * a_coeff * c_coeff
        if discriminant < 0:
            return False

        sqrt_disc = np.sqrt(discriminant)
        t1 = (-b_coeff - sqrt_disc) / (2 * a_coeff)
        t2 = (-b_coeff + sqrt_disc) / (2 * a_coeff)

        # Pick smallest positive t
        candidates = sorted(t for t in [t1, t2] if t > 1e-6)
        if not candidates:
            return False

        for t in candidates:
            hit_point = ray.origin + t * ray.direction
            # Check within spot diameter
            local_x = hit_point[0] - self.corrector._back_vertex[0]
            if abs(local_x) <= self._spot_diameter / 2.0:
                # Compute surface normal at hit point
                normal = hit_point - sphere_center
                normal = normal / np.linalg.norm(normal)

                new_direction = reflect_direction(ray.direction, normal)
                ray.propagate_to(hit_point)
                ray.set_direction(new_direction)
                return True

        return False

    @property
    def focal_ratio(self) -> float:
        """The f-number (effective focal ratio) of the telescope."""
        return self.focal_length / self.primary_diameter

    @property
    def tube_length(self) -> float:
        """Approximate tube length (primary to corrector)."""
        return self.secondary_offset

    @property
    def obstruction_ratio(self) -> float:
        """Central obstruction ratio (spot diameter / primary diameter)."""
        return self.secondary_minor_axis / self.primary_diameter

    def trace_ray(self, ray: Ray) -> Ray:
        """Trace a single ray through the Maksutov-Cassegrain system.

        Sequence:
        1. Refract through meniscus corrector
        2. Reflect off spherical primary
        3. Reflect off aluminized spot (back of meniscus)
        4. Propagate through hole in primary to back focal plane

        Args:
            ray: The incoming Ray to trace.

        Returns:
            The same Ray, now with updated history.
        """
        # Step 1: Refract through meniscus corrector
        hit_corrector = self.corrector.refract_ray(ray)
        if not hit_corrector:
            return ray

        # Step 2: Reflect off spherical primary
        hit_primary = self.primary.reflect_ray(ray)
        if not hit_primary:
            return ray

        # Step 3: Reflect off aluminized spot
        hit_spot = self._reflect_off_spot(ray)
        if not hit_spot:
            # Missed spot — propagate toward primary focus
            end_point = ray.origin + ray.direction * self.primary_focal_length * 0.3
            ray.propagate_to(end_point)
            return ray

        # Step 4: Propagate through hole in primary to back focal plane
        target_y = -self.back_focal_distance - self.primary_diameter * 0.05
        if abs(ray.direction[1]) > 1e-12:
            t = (target_y - ray.origin[1]) / ray.direction[1]
            if t > 0:
                focal_point = ray.origin + ray.direction * t
                ray.propagate_to(focal_point)
            else:
                ray.propagate_to(
                    ray.origin + ray.direction * self.primary_focal_length * 0.5
                )
        else:
            ray.propagate_to(
                ray.origin + ray.direction * self.primary_focal_length * 0.5
            )

        return ray

    def trace_rays(self, rays: list[Ray]) -> list[Ray]:
        """Trace multiple rays through the telescope."""
        for ray in rays:
            self.trace_ray(ray)
        return rays

    def compute_vignetting(self, field_angle_arcsec):
        """Illumination fraction at a given off-axis field angle.

        Uses the same vignetting model as Cassegrain, treating the
        aluminized spot as the limiting obstruction.

        NOTE: Tube wall vignetting and meniscus edge vignetting not modeled.
        """
        from telescope_sim.physics.vignetting import compute_vignetting
        return compute_vignetting(
            field_angle_arcsec, self.primary_diameter,
            self.primary_focal_length,
            self.secondary_offset, self.secondary_minor_axis,
        )

    def fully_illuminated_field(self) -> float:
        """Field angle (arcsec) where vignetting begins."""
        from telescope_sim.physics.vignetting import fully_illuminated_field
        return fully_illuminated_field(
            self.primary_diameter, self.primary_focal_length,
            self.secondary_offset, self.secondary_minor_axis,
        )

    def get_components_for_plotting(self) -> dict:
        """Return geometric data needed by the plotting module.

        Returns dict with standard keys plus Maksutov-specific entries
        for drawing the meniscus corrector and aluminized spot.
        """
        components = {
            "primary_surface": self.primary.get_surface_points(),
            "secondary_surface": self.corrector.get_back_surface_points(),
            "corrector_front": self.corrector.get_front_surface_points(),
            "corrector_back": self.corrector.get_back_surface_points(),
            "spot_diameter": self._spot_diameter,
            "primary_diameter": self.primary_diameter,
            "focal_length": self.focal_length,
            "secondary_offset": self.secondary_offset,
            "tube_length": self.tube_length,
            "primary_type": self.primary_type,
            "secondary_type": "aluminized spot",
            "telescope_style": "maksutov",
        }
        if self.spider_vanes > 0:
            components["spider_vanes"] = self.spider_vanes
            components["spider_vane_width"] = self.spider_vane_width
            components["secondary_minor_axis"] = self.secondary_minor_axis
        return components

"""
Apochromatic lens designs for high-end refracting telescopes.

APO refractors use ED (Extra-low Dispersion) glass to minimize chromatic
aberration across a wider wavelength range than standard achromats.
"""

import numpy as np
from telescope_sim.physics.refraction import GLASS_CATALOG, refractive_index_cauchy
from telescope_sim.geometry.lenses import SphericalLens
from telescope_sim.physics.ray import Ray


class ApochromaticDoublet:
    """Two-element apochromatic doublet using ED glass.

    APO doublets use extra-low dispersion (ED) glass (e.g., FPL51, FPL53)
    combined with crown glass to achieve better chromatic correction than
    standard achromats. Brings three wavelengths to nearly the same focus.

    Design: ED element (positive) + crown element (negative/weak positive)
    cemented together.

    Attributes:
        focal_length: Combined focal length of the doublet (mm).
        diameter: Lens diameter (mm).
        center: (x, y) of the front vertex.
        ed_glass: ED glass type (low dispersion).
        crown_glass: Crown glass type.
        objective_type: Always "apo-doublet".
    """

    def __init__(self, focal_length: float, diameter: float,
                 center: tuple[float, float] = (0.0, 0.0),
                 ed_glass: str = "FPL51", crown_glass: str = "BK7"):
        self.focal_length = focal_length
        self.diameter = diameter
        self.center = np.asarray(center, dtype=float)
        self.ed_glass = ed_glass
        self.crown_glass = crown_glass
        self.objective_type = "apo-doublet"
        self.glass = f"{ed_glass}+{crown_glass}"

        # Compute Abbe numbers
        ed_coeffs = GLASS_CATALOG[ed_glass]
        crown_coeffs = GLASS_CATALOG[crown_glass]

        n_d_ed = refractive_index_cauchy(587.6, ed_coeffs["B"], ed_coeffs["C"])
        n_f_ed = refractive_index_cauchy(486.1, ed_coeffs["B"], ed_coeffs["C"])
        n_c_ed = refractive_index_cauchy(656.3, ed_coeffs["B"], ed_coeffs["C"])
        v_ed = (n_d_ed - 1.0) / (n_f_ed - n_c_ed)

        n_d_crown = refractive_index_cauchy(587.6, crown_coeffs["B"], crown_coeffs["C"])
        n_f_crown = refractive_index_cauchy(486.1, crown_coeffs["B"], crown_coeffs["C"])
        n_c_crown = refractive_index_cauchy(656.3, crown_coeffs["B"], crown_coeffs["C"])
        v_crown = (n_d_crown - 1.0) / (n_f_crown - n_c_crown)

        # Apochromatic condition (similar to achromat but with ED glass)
        phi_total = 1.0 / focal_length
        phi_ed = phi_total * v_ed / (v_ed - v_crown)
        phi_crown = phi_total - phi_ed

        # Individual focal lengths
        f_ed = 1.0 / phi_ed
        f_crown = 1.0 / phi_crown

        # Lens thicknesses
        thickness_ed = max(diameter / 12.0, 3.5)
        thickness_crown = max(diameter / 25.0, 2.0)
        self.thickness = thickness_ed + thickness_crown
        self.radius = diameter / 2.0

        # Compute radii
        n_ed = refractive_index_cauchy(550.0, ed_coeffs["B"], ed_coeffs["C"])
        n_crown = refractive_index_cauchy(550.0, crown_coeffs["B"], crown_coeffs["C"])

        # ED: symmetric biconvex
        r1_ed = 2.0 * f_ed * (n_ed - 1.0)
        r2_ed = -r1_ed  # Symmetric

        # Interface radius (from ED element)
        r_interface = r2_ed

        # Crown element radii
        # Using lensmaker's equation: 1/f = (n-1)[1/R1 - 1/R2]
        # R1 = r_interface (cemented), solve for R2
        r1_crown = r_interface
        # For thin lens: 1/f_crown = (n-1) * [1/r1_crown - 1/r2_crown]
        # r2_crown = 1 / [1/r1_crown - 1/((n-1)*f_crown)]
        term = 1.0 / r1_crown - 1.0 / ((n_crown - 1.0) * f_crown)
        r2_crown = 1.0 / term if abs(term) > 1e-9 else 1e6

        # Build elements
        ed_center_y = self.center[1]
        crown_center_y = ed_center_y - thickness_ed

        self.ed_element = SphericalLens(
            R_front=r1_ed,
            R_back=r2_ed,
            thickness=thickness_ed,
            diameter=diameter,
            center=(self.center[0], ed_center_y),
            glass=ed_glass
        )

        self.crown_element = SphericalLens(
            R_front=r1_crown,
            R_back=r2_crown,
            thickness=thickness_crown,
            diameter=diameter,
            center=(self.center[0], crown_center_y),
            glass=crown_glass
        )

    def refract_ray(self, ray: Ray, wavelength_nm: float | None = None) -> Ray:
        """Refract ray through both elements."""
        ray = self.ed_element.refract_ray(ray, wavelength_nm)
        ray = self.crown_element.refract_ray(ray, wavelength_nm)
        return ray

    def get_front_surface_points(self, num_points: int = 100) -> np.ndarray:
        """Front surface of the ED element."""
        return self.ed_element.get_front_surface_points(num_points)

    def get_back_surface_points(self, num_points: int = 100) -> np.ndarray:
        """Back surface of the crown element."""
        return self.crown_element.get_back_surface_points(num_points)

    def get_interface_surface_points(self, num_points: int = 100) -> np.ndarray:
        """Cemented interface between ED and crown."""
        return self.ed_element.get_back_surface_points(num_points)


class ApochromaticTriplet:
    """Three-element apochromatic triplet.

    Classic triplet design: crown + flint + crown (or ED + crown + ED variants).
    Provides excellent chromatic correction across the visible spectrum.

    Common design: two outer crown/ED elements (positive power) with a
    central flint element (negative power) to correct chromatic aberration.

    Attributes:
        focal_length: Combined focal length (mm).
        diameter: Lens diameter (mm).
        center: (x, y) of the front vertex.
        outer_glass: Glass for outer elements (crown or ED).
        middle_glass: Glass for middle element (flint).
        objective_type: Always "apo-triplet".
    """

    def __init__(self, focal_length: float, diameter: float,
                 center: tuple[float, float] = (0.0, 0.0),
                 outer_glass: str = "FPL51", middle_glass: str = "F2"):
        self.focal_length = focal_length
        self.diameter = diameter
        self.center = np.asarray(center, dtype=float)
        self.outer_glass = outer_glass
        self.middle_glass = middle_glass
        self.objective_type = "apo-triplet"
        self.glass = f"{outer_glass}+{middle_glass}+{outer_glass}"

        # Compute Abbe numbers
        outer_coeffs = GLASS_CATALOG[outer_glass]
        middle_coeffs = GLASS_CATALOG[middle_glass]

        n_d_outer = refractive_index_cauchy(587.6, outer_coeffs["B"], outer_coeffs["C"])
        n_f_outer = refractive_index_cauchy(486.1, outer_coeffs["B"], outer_coeffs["C"])
        n_c_outer = refractive_index_cauchy(656.3, outer_coeffs["B"], outer_coeffs["C"])
        v_outer = (n_d_outer - 1.0) / (n_f_outer - n_c_outer)

        n_d_middle = refractive_index_cauchy(587.6, middle_coeffs["B"], middle_coeffs["C"])
        n_f_middle = refractive_index_cauchy(486.1, middle_coeffs["B"], middle_coeffs["C"])
        n_c_middle = refractive_index_cauchy(656.3, middle_coeffs["B"], middle_coeffs["C"])
        v_middle = (n_d_middle - 1.0) / (n_f_middle - n_c_middle)

        # Triplet design: distribute power across three elements
        # Simplified approach: outer elements positive, middle negative
        phi_total = 1.0 / focal_length

        # Distribute power (approximate triplet design)
        # Two outer elements contribute positive power, middle negative
        phi_outer_each = phi_total * 0.7  # Each outer element
        phi_middle = -phi_total * 0.4  # Middle (diverging)

        f_outer = 1.0 / phi_outer_each
        f_middle = 1.0 / phi_middle

        # Lens thicknesses
        thickness_outer = max(diameter / 15.0, 3.0)
        thickness_middle = max(diameter / 30.0, 1.5)
        self.thickness = 2 * thickness_outer + thickness_middle
        self.radius = diameter / 2.0

        # Compute radii
        n_outer = refractive_index_cauchy(550.0, outer_coeffs["B"], outer_coeffs["C"])
        n_middle = refractive_index_cauchy(550.0, middle_coeffs["B"], middle_coeffs["C"])

        # Element 1 (front outer): symmetric biconvex
        r1_elem1 = 2.0 * f_outer * (n_outer - 1.0)
        r2_elem1 = -r1_elem1

        # Element 2 (middle): biconcave (negative power)
        r1_elem2 = -2.0 * abs(f_middle) * (n_middle - 1.0)
        r2_elem2 = -r1_elem2

        # Element 3 (back outer): symmetric biconvex
        r1_elem3 = 2.0 * f_outer * (n_outer - 1.0)
        r2_elem3 = -r1_elem3

        # Build elements
        elem1_y = self.center[1]
        elem2_y = elem1_y - thickness_outer
        elem3_y = elem2_y - thickness_middle

        self.element1 = SphericalLens(
            R_front=r1_elem1,
            R_back=r2_elem1,
            thickness=thickness_outer,
            diameter=diameter,
            center=(self.center[0], elem1_y),
            glass=outer_glass
        )

        self.element2 = SphericalLens(
            R_front=r1_elem2,
            R_back=r2_elem2,
            thickness=thickness_middle,
            diameter=diameter,
            center=(self.center[0], elem2_y),
            glass=middle_glass
        )

        self.element3 = SphericalLens(
            R_front=r1_elem3,
            R_back=r2_elem3,
            thickness=thickness_outer,
            diameter=diameter,
            center=(self.center[0], elem3_y),
            glass=outer_glass
        )

    def refract_ray(self, ray: Ray, wavelength_nm: float | None = None) -> Ray:
        """Refract ray through all three elements."""
        ray = self.element1.refract_ray(ray, wavelength_nm)
        ray = self.element2.refract_ray(ray, wavelength_nm)
        ray = self.element3.refract_ray(ray, wavelength_nm)
        return ray

    def get_front_surface_points(self, num_points: int = 100) -> np.ndarray:
        """Front surface of element 1."""
        return self.element1.get_front_surface_points(num_points)

    def get_back_surface_points(self, num_points: int = 100) -> np.ndarray:
        """Back surface of element 3."""
        return self.element3.get_back_surface_points(num_points)

    def get_interface1_surface_points(self, num_points: int = 100) -> np.ndarray:
        """Interface between element 1 and 2."""
        return self.element1.get_back_surface_points(num_points)

    def get_interface2_surface_points(self, num_points: int = 100) -> np.ndarray:
        """Interface between element 2 and 3."""
        return self.element2.get_back_surface_points(num_points)

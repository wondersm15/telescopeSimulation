"""
Apochromatic lens designs for high-end refracting telescopes.

APO refractors use ED (Extra-low Dispersion) glass to minimize chromatic
aberration across a wider wavelength range than standard achromats.
"""

import numpy as np
from telescope_sim.physics.refraction import (
    GLASS_CATALOG, refract_direction, refractive_index_cauchy,
)
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
                 ed_glass: str = "FPL51", crown_glass: str = "F2"):
        self.focal_length = focal_length
        self.diameter = diameter
        self.center = np.asarray(center, dtype=float)
        self.ed_glass = ed_glass
        self.crown_glass = crown_glass
        self.objective_type = "apo-doublet"
        self.glass = f"{ed_glass}+{crown_glass}"

        # Glass coefficients (3-term Cauchy: B, C, D)
        ed_coeffs = GLASS_CATALOG[ed_glass]
        crown_coeffs = GLASS_CATALOG[crown_glass]
        D_ed = ed_coeffs.get("D", 0.0)
        D_cr = crown_coeffs.get("D", 0.0)

        n_d_ed = refractive_index_cauchy(587.6, ed_coeffs["B"],
                                          ed_coeffs["C"], D_ed)
        n_f_ed = refractive_index_cauchy(486.1, ed_coeffs["B"],
                                          ed_coeffs["C"], D_ed)
        n_c_ed = refractive_index_cauchy(656.3, ed_coeffs["B"],
                                          ed_coeffs["C"], D_ed)
        v_ed = (n_d_ed - 1.0) / (n_f_ed - n_c_ed)

        n_d_crown = refractive_index_cauchy(587.6, crown_coeffs["B"],
                                             crown_coeffs["C"], D_cr)
        n_f_crown = refractive_index_cauchy(486.1, crown_coeffs["B"],
                                             crown_coeffs["C"], D_cr)
        n_c_crown = refractive_index_cauchy(656.3, crown_coeffs["B"],
                                             crown_coeffs["C"], D_cr)
        v_crown = (n_d_crown - 1.0) / (n_f_crown - n_c_crown)

        # Apochromatic doublet: ED crown paired with flint. The Abbe-number
        # spread is larger than a standard achromat (V_ed > V_BK7), and the
        # ED glass's anomalous partial dispersion (non-zero D in catalog)
        # reduces the secondary spectrum — bringing three wavelengths very
        # close together rather than the achromat's two.
        phi_total = 1.0 / focal_length
        phi_ed = phi_total * v_ed / (v_ed - v_crown)
        phi_crown = phi_total - phi_ed

        # Individual focal lengths
        f_ed = 1.0 / phi_ed
        f_crown = 1.0 / phi_crown

        self.radius = diameter / 2.0

        # Compute radii at design wavelength (550 nm)
        n_ed = refractive_index_cauchy(550.0, ed_coeffs["B"],
                                        ed_coeffs["C"], D_ed)
        n_crown = refractive_index_cauchy(550.0, crown_coeffs["B"],
                                           crown_coeffs["C"], D_cr)

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

        # Lens thicknesses — must exceed front+back surface sag so the edge
        # thickness stays positive (otherwise edge rays miss surfaces and
        # the trace fails). Use the larger of the heuristic and sag-derived
        # minimum.
        from telescope_sim.geometry.lenses import _min_safe_thickness
        half_d = self.radius
        thickness_ed = max(diameter / 12.0, 3.5,
                            _min_safe_thickness(r1_ed, r2_ed, half_d))
        thickness_crown = max(diameter / 25.0, 2.0,
                               _min_safe_thickness(r1_crown, r2_crown, half_d))
        self.thickness = thickness_ed + thickness_crown

        # Iterative paraxial-ray refinement (matches AchromaticDoublet):
        # the thin-lens analytic radii above ignore thick-lens corrections.
        # Trace a near-axis ray through the cemented doublet and rescale
        # all radii until the achieved focal length matches the target.
        # Without this, the thin-lens APO doublet focuses at a slightly
        # different y than expected and the per-ray scatter at the focal
        # plane is amplified — observed as a ~1 mm spread in our tests.
        from telescope_sim.physics.refraction import refract_direction
        from telescope_sim.physics.ray import Ray
        from telescope_sim.geometry.lenses import SphericalLens
        ed_center_y = self.center[1]
        for _iteration in range(15):
            crown_center_y_iter = ed_center_y - thickness_ed
            temp_ed = SphericalLens(
                R_front=r1_ed, R_back=r2_ed,
                thickness=thickness_ed, diameter=diameter,
                center=(self.center[0], ed_center_y), glass=self.ed_glass,
            )
            temp_crown = SphericalLens(
                R_front=r1_crown, R_back=r2_crown,
                thickness=thickness_crown, diameter=diameter,
                center=(self.center[0], crown_center_y_iter),
                glass=self.crown_glass,
            )
            h = diameter * 0.02
            test_ray = Ray(
                origin=np.array([h, ed_center_y + 100.0]),
                direction=np.array([0.0, -1.0]),
            )
            # Surface 1: air → ED
            t1 = temp_ed.front_intersect(test_ray)
            if t1 is None: break
            p1 = test_ray.origin + t1 * test_ray.direction
            n1 = temp_ed.front_normal_at(p1)
            d1 = refract_direction(test_ray.direction, n1, 1.0, n_ed)
            if d1 is None: break
            test_ray.propagate_to(p1); test_ray.set_direction(d1)
            # Surface 2: ED → crown (cemented)
            t2 = temp_ed.back_intersect(test_ray)
            if t2 is None: break
            p2 = test_ray.origin + t2 * test_ray.direction
            n2 = temp_ed.back_normal_at(p2)
            d2 = refract_direction(test_ray.direction, n2, n_ed, n_crown)
            if d2 is None: break
            test_ray.propagate_to(p2); test_ray.set_direction(d2)
            # Surface 3: crown → air
            t3 = temp_crown.back_intersect(test_ray)
            if t3 is None: break
            p3 = test_ray.origin + t3 * test_ray.direction
            n3 = temp_crown.back_normal_at(p3)
            d3 = refract_direction(test_ray.direction, n3, n_crown, 1.0)
            if d3 is None: break
            test_ray.propagate_to(p3); test_ray.set_direction(d3)
            if abs(test_ray.direction[0]) < 1e-15: break
            t_axis = -test_ray.origin[0] / test_ray.direction[0]
            focus_y = test_ray.origin[1] + t_axis * test_ray.direction[1]
            lens_mid_y = ed_center_y - (thickness_ed + thickness_crown) / 2.0
            measured_f = lens_mid_y - focus_y
            if abs(measured_f) < 1e-6: break
            scale = focal_length / measured_f
            if abs(scale - 1.0) < 1e-4: break
            r1_ed *= scale; r2_ed *= scale
            r1_crown *= scale; r2_crown *= scale

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

    def refract_ray(self, ray: Ray, wavelength_nm: float | None = None) -> bool:
        """Idealized thin-lens refraction through the apochromatic doublet.

        Real APO doublets use aspheric or carefully-bent spherical
        surfaces to remove residual spherical aberration. The simulation
        models this idealization: every ray of a given wavelength is
        bent to pass through the per-wavelength focal point. Result:
        zero spherical aberration, with a small wavelength-dependent
        focal shift that is the chromatic residual (∼ f/8000 by design).

        Physically, this is the APO design *target*; a real well-built
        APO doublet's residual SA is well under λ/4 wavefront error at
        marginal rays, so the idealization is faithful for tutorial
        purposes. Compare with the singlet (full Cauchy SA + chromatic)
        and the achromat (residual SA + secondary spectrum).
        """
        if wavelength_nm is None:
            wavelength_nm = getattr(ray, "wavelength_nm", 550.0)

        # Per-wavelength focal length: textbook parabolic apo-doublet
        # residual (~f/8000), zero at design wavelength and equal
        # magnitude at the F and C lines (the achromatic-design points).
        # Uses the SAME parabolic formula as `chromatic_defocus()` so
        # the ray-trace, the 1D radial profile, and the per-channel
        # PSF all agree on where each wavelength's focal plane lies.
        F_line, C_line = 486.1, 656.3
        mid = (F_line + C_line) / 2.0
        half = (C_line - F_line) / 2.0
        delta = wavelength_nm - mid
        delta_design = 550.0 - mid
        quad = (delta / half) ** 2 - (delta_design / half) ** 2
        f_wl = self.focal_length + (self.focal_length / 8000.0) * quad

        # Intersect the ray with the lens plane (front vertex of the
        # ED element — the entrance pupil for idealized refraction).
        front_y = self.center[1]
        if abs(ray.direction[1]) < 1e-12:
            return False
        t_lens = (front_y - ray.origin[1]) / ray.direction[1]
        if t_lens < 0:
            return False
        hit = ray.origin + t_lens * ray.direction
        # Clip rays that miss the clear aperture
        if abs(hit[0] - self.center[0]) > self.radius:
            return False

        # Bend so the ray passes through the focal point at f_wl below
        # the lens vertex on the optical axis.
        focal_y = front_y - f_wl
        focal_pt = np.array([self.center[0], focal_y])
        new_dir = focal_pt - hit
        norm = float(np.linalg.norm(new_dir))
        if norm < 1e-12:
            return False
        new_dir = new_dir / norm

        # Place the ray at the back of the doublet (so the trace shows
        # a "lens region" of finite thickness) before setting direction.
        back_y = front_y - self.thickness
        if abs(new_dir[1]) < 1e-12:
            return False
        t_back = (back_y - hit[1]) / new_dir[1]
        # Propagate through the lens region first
        ray.propagate_to(hit)
        ray.set_direction(new_dir)
        if t_back > 0:
            back_pt = hit + t_back * new_dir
            ray.propagate_to(back_pt)
        return True

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
    """Three-element apochromatic triplet with air-spaced design.

    Classic triplet design: crown + flint + crown (or ED + crown + ED variants).
    Provides excellent chromatic correction across the visible spectrum.

    Air-spaced design (small gaps between elements) is typical for high-end
    APO refractors from manufacturers like TEC, Astro-Physics, and Takahashi.
    Air gaps provide more design freedom and superior chromatic correction
    compared to cemented triplets.

    Common design: two outer crown/ED elements (positive power) with a
    central flint element (negative power) to correct chromatic aberration.

    Attributes:
        focal_length: Combined focal length (mm).
        diameter: Lens diameter (mm).
        center: (x, y) of the front vertex.
        outer_glass: Glass for outer elements (crown or ED).
        middle_glass: Glass for middle element (flint).
        air_gap: Spacing between elements (mm). Default 2.5mm is typical.
        objective_type: Always "apo-triplet".
    """

    def __init__(self, focal_length: float, diameter: float,
                 center: tuple[float, float] = (0.0, 0.0),
                 outer_glass: str = "APO-S", middle_glass: str = "F2",
                 air_gap: float = 2.5):
        self.focal_length = focal_length
        self.diameter = diameter
        self.center = np.asarray(center, dtype=float)
        self.outer_glass = outer_glass
        self.middle_glass = middle_glass
        self.air_gap = air_gap
        self.objective_type = "apo-triplet"
        self.glass = f"{outer_glass}+{middle_glass}+{outer_glass}"

        # Glass coefficients (3-term Cauchy: B, C, D)
        outer_coeffs = GLASS_CATALOG[outer_glass]
        middle_coeffs = GLASS_CATALOG[middle_glass]
        D_outer = outer_coeffs.get("D", 0.0)
        D_middle = middle_coeffs.get("D", 0.0)

        # Reference wavelengths (d, F, C lines)
        n_d_outer = refractive_index_cauchy(
            587.6, outer_coeffs["B"], outer_coeffs["C"], D_outer)
        n_f_outer = refractive_index_cauchy(
            486.1, outer_coeffs["B"], outer_coeffs["C"], D_outer)
        n_c_outer = refractive_index_cauchy(
            656.3, outer_coeffs["B"], outer_coeffs["C"], D_outer)
        v_outer = (n_d_outer - 1.0) / (n_f_outer - n_c_outer)

        n_d_middle = refractive_index_cauchy(
            587.6, middle_coeffs["B"], middle_coeffs["C"], D_middle)
        n_f_middle = refractive_index_cauchy(
            486.1, middle_coeffs["B"], middle_coeffs["C"], D_middle)
        n_c_middle = refractive_index_cauchy(
            656.3, middle_coeffs["B"], middle_coeffs["C"], D_middle)
        v_middle = (n_d_middle - 1.0) / (n_f_middle - n_c_middle)

        # Triplet design: solve the achromatic condition for the chosen
        # glass pair. With two outer elements of equal power Φ_o and one
        # middle of power Φ_m:
        #   2·Φ_o + Φ_m   = Φ_total      (combined power)
        #   2·Φ_o / V_o + Φ_m / V_m = 0  (achromatic condition)
        # Solving:
        #   Φ_o = Φ_total · V_o / (2·(V_o − V_m))
        #   Φ_m = Φ_total · (−V_m / (V_o − V_m))
        # If the outer glass has anomalous partial dispersion (non-zero D)
        # the residual third-wavelength error is also small — i.e. true
        # apochromatic correction with three elements.
        phi_total = 1.0 / focal_length
        v_diff = v_outer - v_middle
        if abs(v_diff) < 1e-9:
            # Degenerate case (shouldn't happen with our glasses)
            phi_outer_each = phi_total / 2.0
            phi_middle = 0.0
        else:
            phi_outer_each = phi_total * v_outer / (2.0 * v_diff)
            phi_middle = phi_total * (-v_middle) / v_diff

        f_outer = 1.0 / phi_outer_each
        f_middle = 1.0 / phi_middle

        self.radius = diameter / 2.0

        # Compute radii from each element's f at design wavelength (550 nm)
        n_outer = refractive_index_cauchy(
            550.0, outer_coeffs["B"], outer_coeffs["C"], D_outer)
        n_middle = refractive_index_cauchy(
            550.0, middle_coeffs["B"], middle_coeffs["C"], D_middle)

        # Element 1 (front outer): symmetric biconvex
        r1_elem1 = 2.0 * f_outer * (n_outer - 1.0)
        r2_elem1 = -r1_elem1

        # Element 2 (middle): biconcave (negative power)
        r1_elem2 = -2.0 * abs(f_middle) * (n_middle - 1.0)
        r2_elem2 = -r1_elem2

        # Element 3 (back outer): symmetric biconvex
        r1_elem3 = 2.0 * f_outer * (n_outer - 1.0)
        r2_elem3 = -r1_elem3

        # Lens thicknesses — must exceed surface sag so edge thickness > 0
        from telescope_sim.geometry.lenses import _min_safe_thickness
        half_d = self.radius
        thickness_outer = max(diameter / 15.0, 3.0,
                               _min_safe_thickness(r1_elem1, r2_elem1, half_d))
        thickness_middle = max(diameter / 30.0, 1.5,
                                _min_safe_thickness(r1_elem2, r2_elem2, half_d))
        # Total thickness includes air gaps between elements
        self.thickness = 2 * thickness_outer + thickness_middle + 2 * air_gap

        # Iterative paraxial-ray refinement (matches AchromaticDoublet
        # and ApochromaticDoublet): the thin-lens analytic radii ignore
        # thick-lens corrections AND air-gap propagation effects in the
        # triplet. Trace a near-axis ray through the air-spaced triplet
        # and rescale all radii until the achieved focal length matches
        # the target. Without this the air-spaced triplet focused at
        # the wrong y and produced ~2 mm of spurious "spherical-like"
        # spread that was actually a focal-length error.
        from telescope_sim.physics.refraction import refract_direction
        from telescope_sim.physics.ray import Ray
        from telescope_sim.geometry.lenses import SphericalLens
        elem1_y_iter = self.center[1]
        for _iteration in range(15):
            elem2_y_iter = elem1_y_iter - thickness_outer - air_gap
            elem3_y_iter = elem2_y_iter - thickness_middle - air_gap
            t_e1 = SphericalLens(R_front=r1_elem1, R_back=r2_elem1,
                                  thickness=thickness_outer, diameter=diameter,
                                  center=(self.center[0], elem1_y_iter),
                                  glass=outer_glass)
            t_e2 = SphericalLens(R_front=r1_elem2, R_back=r2_elem2,
                                  thickness=thickness_middle, diameter=diameter,
                                  center=(self.center[0], elem2_y_iter),
                                  glass=middle_glass)
            t_e3 = SphericalLens(R_front=r1_elem3, R_back=r2_elem3,
                                  thickness=thickness_outer, diameter=diameter,
                                  center=(self.center[0], elem3_y_iter),
                                  glass=outer_glass)
            h = diameter * 0.02
            test_ray = Ray(
                origin=np.array([h, elem1_y_iter + 100.0]),
                direction=np.array([0.0, -1.0]),
            )
            ok = True
            for surf, (n_in, n_out) in (
                    (("front", t_e1), (1.0, n_outer)),
                    (("back", t_e1), (n_outer, 1.0)),
                    (("front", t_e2), (1.0, n_middle)),
                    (("back", t_e2), (n_middle, 1.0)),
                    (("front", t_e3), (1.0, n_outer)),
                    (("back", t_e3), (n_outer, 1.0))):
                side, lens = surf
                if side == "front":
                    t_int = lens.front_intersect(test_ray)
                    if t_int is None: ok = False; break
                    pt = test_ray.origin + t_int * test_ray.direction
                    norm = lens.front_normal_at(pt)
                else:
                    t_int = lens.back_intersect(test_ray)
                    if t_int is None: ok = False; break
                    pt = test_ray.origin + t_int * test_ray.direction
                    norm = lens.back_normal_at(pt)
                nd = refract_direction(test_ray.direction, norm, n_in, n_out)
                if nd is None: ok = False; break
                test_ray.propagate_to(pt); test_ray.set_direction(nd)
            if not ok: break
            if abs(test_ray.direction[0]) < 1e-15: break
            t_axis = -test_ray.origin[0] / test_ray.direction[0]
            focus_y = test_ray.origin[1] + t_axis * test_ray.direction[1]
            lens_mid_y = (elem1_y_iter
                           - (2 * thickness_outer + thickness_middle
                              + 2 * air_gap) / 2.0)
            measured_f = lens_mid_y - focus_y
            if abs(measured_f) < 1e-6: break
            scale = focal_length / measured_f
            if abs(scale - 1.0) < 1e-4: break
            r1_elem1 *= scale; r2_elem1 *= scale
            r1_elem2 *= scale; r2_elem2 *= scale
            r1_elem3 *= scale; r2_elem3 *= scale

        # Build elements with air gaps
        # Air-spaced triplet: element1 -> air gap -> element2 -> air gap -> element3
        elem1_y = self.center[1]
        elem2_y = elem1_y - thickness_outer - air_gap
        elem3_y = elem2_y - thickness_middle - air_gap

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

    def refract_ray(self, ray: Ray, wavelength_nm: float | None = None) -> bool:
        """Idealized thin-lens refraction through the apochromatic triplet.

        Real APO triplets use aspheric or precisely-bent spherical
        surfaces that drive marginal-ray spherical aberration well
        below diffraction limits. The simulation models this
        idealization: rays of a given wavelength converge to one focal
        point with the appropriate per-wavelength shift (~f/20000
        residual for a triplet) so the tutorial can focus on
        chromatic correction without spherical contamination.
        """
        if wavelength_nm is None:
            wavelength_nm = getattr(ray, "wavelength_nm", 550.0)
        # Per-wavelength focal length: textbook parabolic apo-triplet
        # residual (~f/20000). Matches `chromatic_defocus()` so the
        # ray-trace stays consistent with every other view.
        F_line, C_line = 486.1, 656.3
        mid = (F_line + C_line) / 2.0
        half = (C_line - F_line) / 2.0
        delta = wavelength_nm - mid
        delta_design = 550.0 - mid
        quad = (delta / half) ** 2 - (delta_design / half) ** 2
        f_wl = self.focal_length + (self.focal_length / 20000.0) * quad

        front_y = self.center[1]
        if abs(ray.direction[1]) < 1e-12:
            return False
        t_lens = (front_y - ray.origin[1]) / ray.direction[1]
        if t_lens < 0:
            return False
        hit = ray.origin + t_lens * ray.direction
        if abs(hit[0] - self.center[0]) > self.radius:
            return False

        focal_y = front_y - f_wl
        focal_pt = np.array([self.center[0], focal_y])
        new_dir = focal_pt - hit
        norm = float(np.linalg.norm(new_dir))
        if norm < 1e-12:
            return False
        new_dir = new_dir / norm

        back_y = front_y - self.thickness
        ray.propagate_to(hit)
        ray.set_direction(new_dir)
        if abs(new_dir[1]) > 1e-12:
            t_back = (back_y - hit[1]) / new_dir[1]
            if t_back > 0:
                back_pt = hit + t_back * new_dir
                ray.propagate_to(back_pt)
        return True

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

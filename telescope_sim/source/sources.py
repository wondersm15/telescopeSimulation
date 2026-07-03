"""Astronomical source definitions for simulated telescope imaging.

Each source defines an ideal focal-plane image (what a perfect optical system
would produce), which is then convolved with the telescope's PSF to produce
the final simulated image.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class AstronomicalSource(ABC):
    """Base class for astronomical sources."""

    @abstractmethod
    def render_ideal(self, half_fov_arcsec: float,
                     num_pixels: int) -> np.ndarray:
        """Return a 2D ideal image of the source.

        The image covers [-half_fov_arcsec, +half_fov_arcsec] on each axis
        and is normalized so the peak value is 1.0.

        Args:
            half_fov_arcsec: Half the field of view in arcseconds.
            num_pixels: Number of pixels along each axis.

        Returns:
            2D numpy array of shape (num_pixels, num_pixels).
        """

    @property
    @abstractmethod
    def field_extent_arcsec(self) -> float:
        """Full angular extent (diameter) needed to frame this source."""


class PointSource(AstronomicalSource):
    """A single point star at a given field position.

    Args:
        field_angle_arcsec: Angular distance from optical axis.
        position_angle_deg: Position angle measured counter-clockwise
            from the +x axis (degrees).
        magnitude: Apparent magnitude (used for relative brightness
            in star fields).
        spectral_rgb: Optional (R, G, B) intrinsic colour tint in [0, 1]
            representing the star's spectral energy distribution. None
            (default) = white. When set, the renderer tints the star with
            this colour — independent of chromatic aberration, so even a
            reflector shows the star's true colour. Used to demonstrate
            saturation whiteout / cone desaturation on a coloured star.
    """

    def __init__(self, field_angle_arcsec: float = 0.0,
                 position_angle_deg: float = 0.0,
                 magnitude: float = 0.0,
                 spectral_rgb: tuple[float, float, float] | None = None):
        self.field_angle_arcsec = field_angle_arcsec
        self.position_angle_deg = position_angle_deg
        self.magnitude = magnitude
        # Exposed as a 1-row array so the per-star renderer's
        # `star_spectral_rgb[idx]` lookup works uniformly with star fields.
        if spectral_rgb is not None:
            self.star_spectral_rgb = np.array([spectral_rgb], dtype=float)

    def render_ideal(self, half_fov_arcsec: float,
                     num_pixels: int) -> np.ndarray:
        image = np.zeros((num_pixels, num_pixels))
        pa_rad = np.radians(self.position_angle_deg)
        x_arcsec = self.field_angle_arcsec * np.cos(pa_rad)
        y_arcsec = self.field_angle_arcsec * np.sin(pa_rad)

        # Convert arcsec position to pixel index
        pixel_scale = 2.0 * half_fov_arcsec / num_pixels
        ix = int(round(num_pixels / 2 + x_arcsec / pixel_scale))
        iy = int(round(num_pixels / 2 + y_arcsec / pixel_scale))

        if 0 <= ix < num_pixels and 0 <= iy < num_pixels:
            intensity = 10.0 ** (-0.4 * self.magnitude)
            image[iy, ix] = intensity

        if image.max() > 0:
            image /= image.max()
        return image

    @property
    def field_extent_arcsec(self) -> float:
        # 20″ default for on-axis source — wider than 10″ to give the
        # Eye-view asinh stretch room to reveal Airy-ring structure and
        # diffraction-spike falloff without saturating.
        if self.field_angle_arcsec < 1.0:
            return 20.0
        return self.field_angle_arcsec * 2.5


class DoubleStar(AstronomicalSource):
    """Two point sources at a configurable angular separation.

    Primarily used for Rayleigh criterion demonstrations. The two stars
    are placed symmetrically about the optical axis along the x-axis.

    Args:
        separation_arcsec: Angular separation between the two stars.
        magnitude_primary: Apparent magnitude of the primary (brighter) star.
        magnitude_secondary: Apparent magnitude of the secondary star.
    """

    def __init__(self, separation_arcsec: float = 1.0,
                 magnitude_primary: float = 0.0,
                 magnitude_secondary: float = 0.0):
        self.separation_arcsec = separation_arcsec
        self.magnitude_primary = magnitude_primary
        self.magnitude_secondary = magnitude_secondary

    def render_ideal(self, half_fov_arcsec: float,
                     num_pixels: int) -> np.ndarray:
        image = np.zeros((num_pixels, num_pixels))
        pixel_scale = 2.0 * half_fov_arcsec / num_pixels
        center = num_pixels // 2

        half_sep_px = (self.separation_arcsec / 2.0) / pixel_scale
        ix_a = int(round(center - half_sep_px))
        ix_b = int(round(center + half_sep_px))

        # Absolute fluxes from magnitudes (no peak normalisation —
        # downstream renderer needs the absolute scale to interact
        # correctly with aperture × exposure × saturation).
        intensity_a = 10.0 ** (-0.4 * self.magnitude_primary)
        intensity_b = 10.0 ** (-0.4 * self.magnitude_secondary)

        if 0 <= ix_a < num_pixels:
            image[center, ix_a] = intensity_a
        if 0 <= ix_b < num_pixels:
            image[center, ix_b] = intensity_b

        return image

    @property
    def field_extent_arcsec(self) -> float:
        return max(self.separation_arcsec * 10.0, 10.0)


class StarField(AstronomicalSource):
    """A random field of stars at various field angles and magnitudes.

    Args:
        num_stars: Number of stars in the field.
        field_radius_arcsec: Radius of the field in arcseconds.
        seed: Random seed for reproducibility.
        magnitude_range: Tuple of (min_mag, max_mag) for star magnitudes.
    """

    def __init__(self, num_stars: int = 20,
                 field_radius_arcsec: float = 300.0,
                 seed: int = 42,
                 magnitude_range: tuple[float, float] = (0.0, 4.0)):
        self.num_stars = num_stars
        self.field_radius_arcsec = field_radius_arcsec
        self.seed = seed
        self.magnitude_range = magnitude_range

        # Generate star positions and magnitudes
        rng = np.random.default_rng(seed)
        # Uniform in area: r proportional to sqrt(uniform)
        r = field_radius_arcsec * np.sqrt(rng.uniform(0, 1, num_stars))
        theta = rng.uniform(0, 2 * np.pi, num_stars)
        self.star_x_arcsec = r * np.cos(theta)
        self.star_y_arcsec = r * np.sin(theta)
        self.star_magnitudes = rng.uniform(
            magnitude_range[0], magnitude_range[1], num_stars
        )

    def render_ideal(self, half_fov_arcsec: float,
                     num_pixels: int) -> np.ndarray:
        image = np.zeros((num_pixels, num_pixels))
        pixel_scale = 2.0 * half_fov_arcsec / num_pixels

        for x_as, y_as, mag in zip(self.star_x_arcsec,
                                   self.star_y_arcsec,
                                   self.star_magnitudes):
            ix = int(round(num_pixels / 2 + x_as / pixel_scale))
            iy = int(round(num_pixels / 2 + y_as / pixel_scale))
            if 0 <= ix < num_pixels and 0 <= iy < num_pixels:
                intensity = 10.0 ** (-0.4 * mag)
                image[iy, ix] += intensity

        if image.max() > 0:
            image /= image.max()
        return image

    @property
    def field_extent_arcsec(self) -> float:
        return self.field_radius_arcsec * 2.0


class TutorialStarField(StarField):
    """Deterministic star field for tutorial demonstrations.

    Stars are placed at known field angles to highlight specific effects:
      - 1 bright on-axis star (resolution / PSF reference)
      - 2 close pairs (1.0″ and 0.5″) — resolution test
      - 8 mid-field stars at r=50″ (mild coma, full illumination)
      - 8 edge stars at r=150″ (strong coma + onset of vignetting)
      - 4 prominent bright stars near each cardinal direction at the edge,
        magnitude 0.0 — so coma blur on bright stars is unmistakable

    Magnitudes are chosen so the dimmest star is ~50% of the brightest's
    intensity (peak normalisation makes anything dimmer than ~0.05 nearly
    invisible against a black background).

    Same render path as StarField — just deterministic positions.
    """

    def __init__(self, field_radius_arcsec: float = 100.0):
        # Bypass StarField's random init by setting attributes directly
        self.field_radius_arcsec = field_radius_arcsec
        self.seed = 0
        self.magnitude_range = (-0.5, 1.5)

        # Position scales: stars at 33% and 75% of the field radius
        r_mid = field_radius_arcsec * 0.33
        r_edge = field_radius_arcsec * 0.75
        r_edge_bright = field_radius_arcsec * 0.80
        # Close-pair offset and separations are small but not vanishing
        pair_y = max(field_radius_arcsec * 0.05, 4.0)
        sep_1 = max(field_radius_arcsec * 0.008, 0.5)
        sep_2 = max(field_radius_arcsec * 0.004, 0.25)

        xs: list[float] = []
        ys: list[float] = []
        mags: list[float] = []

        # On-axis bright reference star (the brightest in the field)
        xs.append(0.0); ys.append(0.0); mags.append(-0.5)

        # Close pairs to probe resolution — placed off-axis vertically so
        # they don't overlap the on-axis star.
        xs.append(-sep_1); ys.append(+pair_y); mags.append(0.5)
        xs.append(+sep_1); ys.append(+pair_y); mags.append(0.5)
        xs.append(-sep_2); ys.append(-pair_y); mags.append(0.5)
        xs.append(+sep_2); ys.append(-pair_y); mags.append(0.5)

        # Mid-field ring (8 stars at 45° spacing)
        for k in range(8):
            angle = k * np.pi / 4
            xs.append(r_mid * np.cos(angle))
            ys.append(r_mid * np.sin(angle))
            mags.append(0.8)

        # Edge ring (8 stars at 45° spacing)
        for k in range(8):
            angle = k * np.pi / 4
            xs.append(r_edge * np.cos(angle))
            ys.append(r_edge * np.sin(angle))
            mags.append(1.0)

        # 4 prominent bright stars near edges along cardinal directions —
        # offset slightly from the regular ring so they don't overlap.
        for k in range(4):
            angle = k * np.pi / 2 + np.pi / 8
            xs.append(r_edge_bright * np.cos(angle))
            ys.append(r_edge_bright * np.sin(angle))
            mags.append(0.0)  # As bright as on-axis

        self.star_x_arcsec = np.array(xs)
        self.star_y_arcsec = np.array(ys)
        self.star_magnitudes = np.array(mags)
        self.num_stars = len(xs)


class StarFieldResolutionField(StarField):
    """Wide-field star field designed for the Star Field Resolution scenario.

    Combines a seeded-random background population with planted features
    that test the population-effects the scenario teaches:

      - 1 bright on-axis reference star (mag 0).
      - 4 close pairs at separations 0.6/0.9/1.3/1.8″ — straddling the
        Rayleigh limit for a typical 200 mm aperture so the user can see
        which pairs the scope resolves.
      - 5 bright edge stars (mag 0.5–1.5) at 80% of the field radius,
        placed at non-cardinal angles so the user sees coma and vignetting
        dim them differently.
      - ~70 background stars uniformly distributed in area with magnitudes
        1.5–5.0, seeded for reproducibility.

    Total ≈ 84 stars across the configured field (default 600″ extent).
    """

    def __init__(self, field_radius_arcsec: float = 300.0,
                 num_background: int = 70,
                 seed: int = 17):
        # Bypass StarField's random-init constructor and place stars directly
        self.field_radius_arcsec = field_radius_arcsec
        self.seed = seed
        # Magnitudes span ~3.5 stops (-1 to 2.5). After peak-normalising
        # to the brightest star, the dimmest is ~4% — still visible
        # against black, while preserving a clear bright/dim variation.
        # Wider ranges drive the faint end below the rasterisation
        # noise floor.
        self.magnitude_range = (-1.0, 2.5)

        xs: list[float] = []
        ys: list[float] = []
        mags: list[float] = []

        # On-axis reference — brightest in the field so it dominates the
        # peak normalisation and the rest of the field is properly scaled
        # against it.
        xs.append(0.0); ys.append(0.0); mags.append(-1.0)

        # Close pairs at increasing separation — straddles the Rayleigh
        # limit for D=100–300 mm at 550 nm (~0.5–1.5″). Bright enough
        # (mag ~0.5) to be clearly visible against the saturated
        # on-axis reference.
        pair_positions = [
            (60.0,  70.0,  0.6),   # tight
            (-80.0, 50.0,  0.9),   # near 200 mm Rayleigh limit
            (90.0, -55.0,  1.3),
            (-65.0, -85.0, 1.8),   # easily split
        ]
        for cx, cy, sep in pair_positions:
            xs.append(cx - sep / 2.0); ys.append(cy); mags.append(0.5)
            xs.append(cx + sep / 2.0); ys.append(cy); mags.append(0.8)

        # Bright edge stars — non-cardinal so coma's astigmatic
        # orientation is visible at multiple angles.
        r_edge = field_radius_arcsec * 0.80
        edge_angles_deg = [25, 95, 155, 220, 305]
        edge_mags = [0.0, 0.8, 0.3, 1.0, 0.5]
        for ang_deg, mg in zip(edge_angles_deg, edge_mags):
            ang = np.radians(ang_deg)
            xs.append(r_edge * np.cos(ang))
            ys.append(r_edge * np.sin(ang))
            mags.append(mg)

        # Background population — uniform in area, seeded random.
        # Variable brightness spans the dim end of the range so the
        # population has a clear bright/dim distribution (avoids the
        # "every star same brightness" look).
        rng = np.random.default_rng(seed)
        r_bg = field_radius_arcsec * np.sqrt(rng.uniform(0, 1, num_background))
        theta_bg = rng.uniform(0, 2 * np.pi, num_background)
        mag_bg = rng.uniform(1.2, 2.5, num_background)
        for r, t, m in zip(r_bg, theta_bg, mag_bg):
            xs.append(r * np.cos(t))
            ys.append(r * np.sin(t))
            mags.append(float(m))

        self.star_x_arcsec = np.array(xs)
        self.star_y_arcsec = np.array(ys)
        self.star_magnitudes = np.array(mags)
        self.num_stars = len(xs)


class ComaDemoField(StarField):
    """Four stars at the exact field angles used by the coma spot grid.

    The companion `plot_coma_field_analysis` plot samples spot diagrams
    at 0″, 60″, 120″, 240″. This source places one star at each of those
    angles along the east axis, so the user can read the comet-shaped
    blur on each star and match it to the corresponding spot panel.

    `field_radius_arcsec` defaults to 280″ to keep the 240″ outermost
    star a comfortable distance from the rendered field edge.
    """

    DEMO_ANGLES_ARCSEC = (0.0, 30.0, 60.0, 120.0)

    def __init__(self, field_radius_arcsec: float = 150.0):
        self.field_radius_arcsec = field_radius_arcsec
        self.seed = 0
        # Bright (mag -1.0) so the small Airy disks are clearly visible
        # at the 560″ FOV without any auxiliary markers/labels.
        self.magnitude_range = (-1.0, -1.0)
        xs = list(self.DEMO_ANGLES_ARCSEC)
        ys = [0.0] * len(xs)
        mags = [-1.0] * len(xs)
        self.star_x_arcsec = np.array(xs)
        self.star_y_arcsec = np.array(ys)
        self.star_magnitudes = np.array(mags)
        self.num_stars = len(xs)


class MultiColorStarField(StarField):
    """A small deterministic field of stars with realistic spectral colours.

    Each star has an intrinsic RGB tint mimicking real stellar spectral
    classes (M, K, G, F/A, B). When rendered through a polychromatic
    refractor the chromatic aberration adds *additional* halos on top of
    the natural colours — exactly what a real observer sees through a
    coloured-fringe telescope.

    Used by the chromatic + seeing tutorial scenario.
    """

    # (label, x_arcsec, y_arcsec, magnitude, (R, G, B) tint, T_eff_K)
    # Stars are spread across a wide field (~80″ extent) so achromat
    # chromatic halos (~5″ radius) fit comfortably around each isolated
    # star without overlapping its neighbours.
    # T_eff_K is the characteristic effective surface temperature in
    # Kelvin (textbook values for each spectral class); kT in eV =
    # T_eff_K / 11604.5.
    STARS = [
        ("Antares-like (M1)",   -25.0, +18.0,  0.5, (1.00, 0.45, 0.10),  3500),
        ("Arcturus-like (K1)",  +25.0, +18.0,  0.0, (1.00, 0.70, 0.30),  4300),
        ("Sun-like (G2)",       -25.0, -18.0,  0.5, (1.00, 0.92, 0.65),  5800),
        ("Sirius-like (A1)",      0.0,   0.0, -0.5, (0.85, 0.92, 1.00),  9900),
        ("Spica-like (B1)",     +25.0, -18.0,  0.0, (0.55, 0.75, 1.00), 22400),
    ]

    def __init__(self, field_radius_arcsec: float = 40.0):
        # Bypass StarField's random init by setting attributes directly
        self.field_radius_arcsec = field_radius_arcsec
        self.seed = 0
        self.magnitude_range = (-0.5, 0.5)
        xs = [s[1] for s in self.STARS]
        ys = [s[2] for s in self.STARS]
        mags = [s[3] for s in self.STARS]
        # Per-star spectral RGB tint (used by the polychromatic per-star
        # renderer to weight each channel)
        self.star_spectral_rgb = np.array([s[4] for s in self.STARS])
        self.star_labels = [s[0] for s in self.STARS]
        # Effective surface temperatures in Kelvin
        self.star_temperatures_K = np.array([s[5] for s in self.STARS])
        self.star_x_arcsec = np.array(xs)
        self.star_y_arcsec = np.array(ys)
        self.star_magnitudes = np.array(mags)
        self.num_stars = len(xs)


# Spectral-class RGB palette (approximate visual tints, normalised so the
# brightest channel ≈ 1.0). Ordered hot → cool. Used by ShowcaseStarField to
# give the population realistic colour so the star-field showcase reads as a
# rich, varied field rather than uniform white dots.
_SPECTRAL_PALETTE = [
    ("O/B", (0.62, 0.72, 1.00), 25000),   # blue
    ("A",   (0.80, 0.86, 1.00), 9500),    # blue-white
    ("F",   (1.00, 0.97, 0.92), 7000),    # white
    ("G",   (1.00, 0.93, 0.72), 5600),    # yellow (Sun-like)
    ("K",   (1.00, 0.78, 0.48), 4300),    # orange
    ("M",   (1.00, 0.52, 0.32), 3400),    # red
]


class ShowcaseStarField(StarField):
    """Flagship star field for the Act 4 showcase — engineered to exhibit
    EVERY modelled optical effect at once, with the effect toggles.

    Layout (deterministic planted features + seeded background):
      - 1 bright blue-white reference star on-axis (diffraction spikes, the
        cleanest PSF in the field).
      - 4 bright coloured stars near the edge (~90% of field radius) at
        non-cardinal position angles — the primary coma + spider-spike +
        vignetting demonstrators (coma tails point radially, so off-cardinal
        placement makes the comet orientation obvious).
      - 3 double stars at 8″ / 4″ / 2″ separation across mid-field — a
        resolution ladder: the 8″ pair splits trivially, the 2″ pair blends
        under ~1.5″ seeing (the Rayleigh scenario covers the sub-arcsec limit
        proper).
      - ~55 seeded background stars, uniform in area, spanning mag 1.5–4.5
        and the full spectral palette — the population that shows brightness
        variation and how halos/spikes overlap in a crowded field.

    All stars carry a spectral RGB tint (`star_spectral_rgb`), so the field
    renders in colour through any telescope (the renderer tints each star by
    its SED — colour is intrinsic, not a chromatic-aberration artefact).

    Default field radius 150″ (300″ FOV): wide enough that edge stars sit far
    off-axis (strong coma / vignetting) yet tight enough that per-star detail
    (comet shape, spikes) survives rasterisation to the GUI canvas.
    """

    def __init__(self, field_radius_arcsec: float = 150.0, seed: int = 7):
        self.field_radius_arcsec = field_radius_arcsec
        self.seed = seed
        self.magnitude_range = (-1.0, 4.5)
        R = field_radius_arcsec

        xs: list[float] = []
        ys: list[float] = []
        mags: list[float] = []
        rgb: list[tuple] = []

        def _add(x, y, mag, tint):
            xs.append(x); ys.append(y); mags.append(mag); rgb.append(tint)

        pal = {name: tint for name, tint, _T in _SPECTRAL_PALETTE}

        # On-axis bright reference (blue-white A star) — brightest, cleanest.
        _add(0.0, 0.0, -1.0, pal["A"])

        # Bright edge stars — coma + spikes + vignetting demonstrators.
        # Non-cardinal PAs so the radial comet orientation is unmistakable.
        edge_r = R * 0.90
        edge = [(35, -0.5, "O/B"), (120, 0.0, "K"),
                (215, 0.2, "G"), (305, -0.2, "M")]
        for pa_deg, mag, cls in edge:
            a = np.radians(pa_deg)
            _add(edge_r * np.cos(a), edge_r * np.sin(a), mag, pal[cls])

        # Double-star resolution ladder at mid-field.
        doubles = [
            (-0.45 * R, 0.35 * R, 8.0, 0.6, 1.1, "F", "K"),   # wide, easy
            (0.50 * R, -0.30 * R, 4.0, 0.9, 1.4, "A", "G"),   # moderate
            (0.20 * R, 0.55 * R, 2.0, 1.2, 1.6, "G", "M"),    # tight (~seeing)
        ]
        for cx, cy, sep, m1, m2, c1, c2 in doubles:
            _add(cx - sep / 2.0, cy, m1, pal[c1])
            _add(cx + sep / 2.0, cy, m2, pal[c2])

        # Seeded background population — uniform in area, varied mag + colour.
        rng = np.random.default_rng(seed)
        n_bg = 55
        r_bg = R * np.sqrt(rng.uniform(0, 1, n_bg))
        th_bg = rng.uniform(0, 2 * np.pi, n_bg)
        m_bg = rng.uniform(1.5, 4.5, n_bg)
        palette_tints = [t for _n, t, _T in _SPECTRAL_PALETTE]
        idx_bg = rng.integers(0, len(palette_tints), n_bg)
        for r, t, m, ci in zip(r_bg, th_bg, m_bg, idx_bg):
            _add(r * np.cos(t), r * np.sin(t), float(m), palette_tints[ci])

        self.star_x_arcsec = np.array(xs)
        self.star_y_arcsec = np.array(ys)
        self.star_magnitudes = np.array(mags)
        self.star_spectral_rgb = np.array(rgb, dtype=float)
        self.num_stars = len(xs)


class Jupiter(AstronomicalSource):
    """Parametric model of Jupiter with limb darkening and equatorial bands.

    Produces a simplified but recognizable Jupiter disk with:
    - Limb darkening using a standard cosine law
    - Alternating light/dark equatorial bands
    - A Great Red Spot approximation

    Approximation: This is a parametric/artistic model, not a physically
    accurate radiative transfer simulation. Band positions and contrasts
    are approximate. Sufficient for demonstrating telescope resolution
    and PSF effects on extended objects.

    Args:
        angular_diameter_arcsec: Angular diameter of Jupiter in arcseconds.
            Typical range: ~30" (far) to ~50" (near opposition).
    """

    def __init__(self, angular_diameter_arcsec: float = 40.0,
                 use_realtime: bool = False):
        """
        Args:
            angular_diameter_arcsec: Fixed angular diameter when not
                using the live ephemeris. Default 40″ is typical near
                opposition; Jupiter varies from ~30″ (apoaposition) to
                ~50″ (closest approach near opposition).
            use_realtime: When True, query skyfield + DE421 at
                construction time and override
                `angular_diameter_arcsec` with the *current* Earth–
                Jupiter geometry. Requires skyfield (already in
                requirements); the ephemeris file downloads on first
                use and caches at ~/.skyfield.
        """
        if use_realtime:
            from telescope_sim.source.realtime import (
                jupiter_angular_diameter,
            )
            angular_diameter_arcsec = jupiter_angular_diameter()
        self.angular_diameter_arcsec = angular_diameter_arcsec
        self.use_realtime = use_realtime

    def render_ideal(self, half_fov_arcsec: float,
                     num_pixels: int) -> np.ndarray:
        coords = np.linspace(-half_fov_arcsec, half_fov_arcsec, num_pixels)
        xx, yy = np.meshgrid(coords, coords)

        radius_arcsec = self.angular_diameter_arcsec / 2.0
        # Normalized radial distance from center (0 at center, 1 at limb)
        rr = np.sqrt(xx ** 2 + yy ** 2) / radius_arcsec

        # Disk mask
        disk = rr <= 1.0

        # Limb darkening: I(r) = I_0 * (1 - u*(1 - sqrt(1 - r^2)))
        # u ~ 0.5 is typical for Jupiter in visible light
        u = 0.5
        mu = np.zeros_like(rr)
        mu[disk] = np.sqrt(1.0 - rr[disk] ** 2)
        limb_darkening = np.zeros_like(rr)
        limb_darkening[disk] = 1.0 - u * (1.0 - mu[disk])

        # Equatorial band structure
        # Jupiter's latitude in the image (yy/radius gives sin(lat) approx)
        lat = np.zeros_like(yy)
        lat[disk] = np.arcsin(np.clip(yy[disk] / radius_arcsec, -1, 1))

        # Band pattern: superposition of sinusoids at different frequencies
        # to create alternating light/dark bands
        bands = np.zeros_like(lat)
        # Main bands (North/South Equatorial Belts, Tropical Zones, etc.)
        bands += 0.08 * np.sin(6.0 * lat)    # broad bands
        bands += 0.05 * np.sin(12.0 * lat)   # finer structure
        bands += 0.03 * np.sin(20.0 * lat)   # fine detail

        # Great Red Spot: elliptical brightening at ~22°S latitude
        grs_lat = np.radians(-22.0)
        grs_lon = np.radians(30.0)  # arbitrary longitude position
        grs_x_center = radius_arcsec * np.cos(grs_lat) * np.sin(grs_lon)
        grs_y_center = radius_arcsec * np.sin(grs_lat)
        # Elliptical Gaussian (wider in longitude than latitude)
        grs_sigma_x = radius_arcsec * 0.12
        grs_sigma_y = radius_arcsec * 0.07
        grs = 0.10 * np.exp(
            -((xx - grs_x_center) ** 2 / (2 * grs_sigma_x ** 2)
              + (yy - grs_y_center) ** 2 / (2 * grs_sigma_y ** 2))
        )

        # Combine: base brightness with bands and GRS
        image = np.zeros_like(rr)
        image[disk] = limb_darkening[disk] * (1.0 + bands[disk]) + grs[disk]

        # Ensure non-negative and normalize
        image = np.clip(image, 0.0, None)
        if image.max() > 0:
            image /= image.max()
        return image

    def render_ideal_rgb(self, half_fov_arcsec: float,
                         num_pixels: int) -> np.ndarray:
        """Return a 3-channel RGB ideal image with realistic Jupiter colors.

        Zones (bright bands) are cream/tan, belts (dark bands) are brown,
        and the Great Red Spot is reddish-orange. Background is black.

        Returns:
            Array of shape (num_pixels, num_pixels, 3) with values in [0, 1].
        """
        coords = np.linspace(-half_fov_arcsec, half_fov_arcsec, num_pixels)
        xx, yy = np.meshgrid(coords, coords)

        radius_arcsec = self.angular_diameter_arcsec / 2.0
        rr = np.sqrt(xx ** 2 + yy ** 2) / radius_arcsec
        disk = rr <= 1.0

        # Limb darkening
        u = 0.5
        mu = np.zeros_like(rr)
        mu[disk] = np.sqrt(1.0 - rr[disk] ** 2)
        limb = np.zeros_like(rr)
        limb[disk] = 1.0 - u * (1.0 - mu[disk])

        # Latitude (radians, ±π/2) and approximate longitude for
        # in-plane texture. Longitude is the x-coordinate on the
        # apparent disk projected through the equator — a flat
        # projection that ignores foreshortening but is fine for
        # the level of detail we render.
        lat = np.zeros_like(yy)
        lat[disk] = np.arcsin(np.clip(yy[disk] / radius_arcsec, -1, 1))
        lon = np.zeros_like(xx)  # rough longitude on the visible face
        lon[disk] = np.arcsin(np.clip(
            xx[disk] / (radius_arcsec * np.cos(lat[disk]) + 1e-9),
            -1, 1
        ))

        # Multi-scale band pattern: more frequency components than the
        # original (which had only 6/12/20 sin terms producing ~3-6
        # broad bands). Real Jupiter shows ~15 named belts/zones plus
        # finer turbulent boundaries, so we layer additional 30 and
        # 60-cycle components. Equator-weighted amplitude concentrates
        # detail at low latitudes where Jovian banding is genuinely
        # most active.
        equator_weight = np.exp(-((lat / np.radians(45.0)) ** 2))
        band_signal = (
            0.10 * np.sin(6.0 * lat)
            + 0.07 * np.sin(12.0 * lat)
            + 0.05 * np.sin(24.0 * lat)
            + 0.03 * np.sin(36.0 * lat) * equator_weight
            + 0.02 * np.sin(60.0 * lat) * equator_weight
        )

        # Longitude-dependent festoon turbulence — small zonal waves
        # along the belts where they meet zones. Deterministic
        # (seeded by lat·lon) so a given scope always sees the same
        # disk; not animated.
        festoon = (
            0.025 * np.sin(8.0 * lon) * np.sin(20.0 * lat)
            + 0.015 * np.sin(13.0 * lon) * np.sin(28.0 * lat)
        )
        band_signal = band_signal + festoon * equator_weight

        # Map signed band signal to a [0, 1] blend factor.
        blend = np.clip(0.5 + band_signal / 0.36, 0.0, 1.0)

        # Realistic Jupiter colors (RGB, 0-1 scale)
        zone_color = np.array([235, 220, 185]) / 255.0  # cream zones
        belt_color = np.array([155, 110, 75]) / 255.0   # warm brown belts (deeper than before)

        rgb = np.zeros((num_pixels, num_pixels, 3))
        for c in range(3):
            rgb[..., c] = (belt_color[c] * (1.0 - blend)
                           + zone_color[c] * blend)

        # Great Red Spot — slightly tighter and more saturated than
        # the original (real GRS is about 0.3 × Jupiter's diameter
        # across, tapering in latitude).
        grs_lat = np.radians(-22.0)
        grs_lon = np.radians(30.0)
        grs_x = radius_arcsec * np.cos(grs_lat) * np.sin(grs_lon)
        grs_y = radius_arcsec * np.sin(grs_lat)
        grs_sigma_x = radius_arcsec * 0.13
        grs_sigma_y = radius_arcsec * 0.06
        grs_mask = np.exp(
            -((xx - grs_x) ** 2 / (2 * grs_sigma_x ** 2)
              + (yy - grs_y) ** 2 / (2 * grs_sigma_y ** 2))
        )
        grs_color = np.array([210, 105, 75]) / 255.0
        for c in range(3):
            rgb[..., c] = (rgb[..., c] * (1.0 - grs_mask)
                           + grs_color[c] * grs_mask)

        # Small white ovals at typical temperate latitudes — the
        # long-lived anticyclonic features seen in Hubble Jupiter
        # images. Each is a faint Gaussian brightening relative to
        # the band.
        ovals = [
            (np.radians(38.0),  np.radians(-60.0)),  # northern temperate
            (np.radians(-38.0), np.radians(80.0)),   # southern temperate
            (np.radians(-22.0), np.radians(-110.0)), # near GRS band
        ]
        oval_color = np.array([245, 235, 215]) / 255.0
        for o_lat, o_lon in ovals:
            ox = radius_arcsec * np.cos(o_lat) * np.sin(o_lon)
            oy = radius_arcsec * np.sin(o_lat)
            sigma = radius_arcsec * 0.035
            mask = np.exp(
                -((xx - ox) ** 2 + (yy - oy) ** 2) / (2 * sigma ** 2)
            ) * 0.65
            for c in range(3):
                rgb[..., c] = rgb[..., c] * (1.0 - mask) + oval_color[c] * mask

        # Apply limb darkening and disk mask
        for c in range(3):
            rgb[..., c] *= limb
            rgb[..., c] *= disk

        return np.clip(rgb, 0.0, 1.0)

    @property
    def field_extent_arcsec(self) -> float:
        return self.angular_diameter_arcsec * 1.5


class Saturn(AstronomicalSource):
    """Parametric model of Saturn with rings, Cassini division, and bands.

    Features:
    - Oblate planetary disk (equatorial bulge ~10%)
    - Subtle equatorial bands (less prominent than Jupiter)
    - Limb darkening on the disk
    - Ring system with A, B, C rings and Cassini division
    - Ring tilt (inclination) parameter

    Approximation: This is a parametric/artistic model. Ring opacity,
    planet oblateness, and band structure are approximate. The ring
    shadow on the planet is not modeled.

    Args:
        angular_diameter_arcsec: Equatorial diameter of the planet disk.
            Typical range: ~15" (far) to ~20" (near opposition).
        ring_tilt_deg: Tilt of rings toward observer (0 = edge-on,
            26.7 = maximum opening). Typical range: 0-27 degrees.
    """

    def __init__(self, angular_diameter_arcsec: float = 18.0,
                 ring_tilt_deg: float = 20.0,
                 use_realtime: bool = False):
        """
        Args:
            angular_diameter_arcsec: Equatorial diameter of the planet
                disk. Saturn's body varies ~15″-20″ over its orbit;
                Cassini-mission peaks at opposition.
            ring_tilt_deg: Tilt of rings toward observer (0 = edge-on,
                ±26.7 = maximum opening). The sign matters: positive =
                rings tilted with north hemisphere toward us.
            use_realtime: When True, query skyfield/DE421 for the
                current Saturn geometry and override both the
                angular diameter and ring tilt. Honest representation
                of "what Saturn looks like tonight" — particularly
                useful around ring-plane crossings (next one in 2025)
                when the rings disappear from view.
        """
        if use_realtime:
            from telescope_sim.source.realtime import (
                saturn_angular_diameter, saturn_ring_tilt,
            )
            angular_diameter_arcsec = saturn_angular_diameter()
            ring_tilt_deg = saturn_ring_tilt()
        self.angular_diameter_arcsec = angular_diameter_arcsec
        self.ring_tilt_deg = ring_tilt_deg
        self.use_realtime = use_realtime

    def _build_geometry(self, half_fov_arcsec, num_pixels):
        """Compute shared coordinate grids and geometry parameters."""
        coords = np.linspace(-half_fov_arcsec, half_fov_arcsec, num_pixels)
        xx, yy = np.meshgrid(coords, coords)

        r_eq = self.angular_diameter_arcsec / 2.0  # equatorial radius
        r_pol = r_eq * 0.9  # polar radius (Saturn is ~10% oblate)
        tilt_rad = np.radians(self.ring_tilt_deg)

        # Planet disk (elliptical due to oblateness)
        disk_r = np.sqrt((xx / r_eq) ** 2 + (yy / r_pol) ** 2)
        disk = disk_r <= 1.0

        # Limb darkening on the disk
        u = 0.4
        mu = np.zeros_like(disk_r)
        mu[disk] = np.sqrt(1.0 - np.clip(disk_r[disk], 0, 1) ** 2)
        limb = np.zeros_like(disk_r)
        limb[disk] = 1.0 - u * (1.0 - mu[disk])

        # Band structure: Saturn's bands are subtler than Jupiter's
        # but still resolve into a half-dozen alternating belts at
        # large apertures. Multi-frequency model gives finer detail
        # than the old 5/10 cycle pair.
        lat = np.zeros_like(yy)
        lat[disk] = np.arcsin(np.clip(yy[disk] / r_pol, -1, 1))
        bands = (
            0.05 * np.sin(5.0 * lat)
            + 0.03 * np.sin(10.0 * lat)
            + 0.02 * np.sin(18.0 * lat)
            + 0.01 * np.sin(30.0 * lat)
        )

        # Ring geometry: rings are circular but appear as an ellipse
        # due to tilt. Ring plane is tilted relative to line of sight.
        # In projection, rings are an ellipse with semi-major = r_ring
        # and semi-minor = r_ring * sin(tilt).
        ring_inner_b = r_eq * 1.24   # inner edge of C ring
        ring_cassini_inner = r_eq * 1.95  # Cassini division inner edge
        ring_cassini_outer = r_eq * 2.02  # Cassini division outer edge
        # Encke gap (in the A ring, ~133,500 km / R_eq ≈ 2.22 R_eq).
        # Real width ≈ 325 km — extremely narrow, only visible in
        # large amateur scopes under exceptional seeing. Including it
        # makes the resolution-limit lesson more useful.
        ring_encke_inner = r_eq * 2.214
        ring_encke_outer = r_eq * 2.224
        ring_outer_a = r_eq * 2.27   # outer edge of A ring

        # Projected ring coordinates (ellipse due to tilt)
        sin_tilt = np.sin(tilt_rad)
        # Ring distance from center in ring-plane coordinates
        ring_r = np.sqrt((xx / 1.0) ** 2 + (yy / sin_tilt) ** 2)

        # Ring mask (annulus, excluding Cassini and Encke gaps)
        in_rings = (ring_r >= ring_inner_b) & (ring_r <= ring_outer_a)
        in_cassini = ((ring_r >= ring_cassini_inner)
                      & (ring_r <= ring_cassini_outer))
        in_encke = ((ring_r >= ring_encke_inner)
                    & (ring_r <= ring_encke_outer))
        ring_mask = in_rings & ~in_cassini & ~in_encke

        # Ring brightness varies with radius (B ring brightest).
        # B-ring inner edge has the strongest "ramp" — a brightness
        # gradient real observers can see.
        ring_brightness = np.zeros_like(ring_r)
        # C ring (inner, dim): ring_inner_b to ~1.53*r_eq, dims toward inner
        c_ring = (ring_r >= ring_inner_b) & (ring_r < r_eq * 1.53)
        c_grad = (ring_r[c_ring] - ring_inner_b) / (r_eq * 1.53 - ring_inner_b)
        ring_brightness[c_ring] = 0.30 + 0.20 * c_grad
        # B ring (middle, brightest): ~1.53*r_eq to cassini_inner; brightness
        # gradient peaks near the middle.
        b_ring = ((ring_r >= r_eq * 1.53)
                  & (ring_r < ring_cassini_inner))
        b_center = (r_eq * 1.53 + ring_cassini_inner) / 2.0
        b_half_width = (ring_cassini_inner - r_eq * 1.53) / 2.0
        b_grad = 1.0 - 0.25 * np.abs(
            (ring_r[b_ring] - b_center) / b_half_width
        )
        ring_brightness[b_ring] = b_grad
        # A ring (outer, moderate): cassini_outer to ring_outer_a
        a_ring = ((ring_r >= ring_cassini_outer)
                  & (ring_r <= ring_outer_a))
        ring_brightness[a_ring] = 0.65

        ring_brightness *= ring_mask

        # Ring shadow on the planet: where the rings cross the
        # equatorial line in front of the disk, they cast a thin
        # shadow on the planet behind. Approximated as a darkening
        # band where the rings' near-edge projection meets the disk.
        # Strength scales with sin(tilt) — invisible edge-on.
        shadow = np.zeros_like(disk_r)
        if abs(sin_tilt) > 0.03:
            # Shadow is a thin strip just below the ring projection,
            # only on the part of the disk *not* covered by the
            # rings in projection.
            shadow_band = (
                (np.abs(yy) < 0.05 * r_eq)
                & disk
                & ~ring_mask
            )
            shadow[shadow_band] = 0.35 * abs(sin_tilt)

        # Separate front and back rings relative to planet disk.
        # For positive tilt (viewing from above the ring plane), the
        # near side of the rings is at y < 0 (front, visible over disk)
        # and the far side at y > 0 (back, hidden behind disk).
        ring_front = ring_mask & (yy <= 0)  # in front of planet
        ring_back = ring_mask & (yy > 0)    # behind planet

        return {
            "xx": xx, "yy": yy, "disk": disk, "limb": limb,
            "bands": bands, "ring_mask": ring_mask,
            "ring_front": ring_front, "ring_back": ring_back,
            "ring_brightness": ring_brightness, "r_eq": r_eq,
            "sin_tilt": sin_tilt, "shadow": shadow,
        }

    def render_ideal(self, half_fov_arcsec: float,
                     num_pixels: int) -> np.ndarray:
        g = self._build_geometry(half_fov_arcsec, num_pixels)

        image = np.zeros((num_pixels, num_pixels))

        # Layer 1: back rings (behind the planet, only outside disk)
        back_visible = g["ring_back"] & ~g["disk"]
        image[back_visible] = g["ring_brightness"][back_visible]

        # Layer 2: planet disk (on top of back rings)
        image[g["disk"]] = g["limb"][g["disk"]] * (
            1.0 + g["bands"][g["disk"]])

        # Layer 3: front rings (in front of the planet, drawn on top)
        # These are visible even where they cross the disk face
        front_visible = g["ring_front"]
        # Where front rings overlap the disk, blend: show ring over disk
        # with slight transparency to hint at the planet beneath
        ring_over_disk = front_visible & g["disk"]
        ring_outside = front_visible & ~g["disk"]
        image[ring_outside] = g["ring_brightness"][ring_outside]
        # Front rings crossing the planet face: blend ring + disk
        ring_opacity = 0.85  # rings are mostly opaque
        image[ring_over_disk] = (
            ring_opacity * g["ring_brightness"][ring_over_disk]
            + (1.0 - ring_opacity) * image[ring_over_disk])

        image = np.clip(image, 0.0, None)
        if image.max() > 0:
            image /= image.max()
        return image

    def render_ideal_rgb(self, half_fov_arcsec: float,
                         num_pixels: int) -> np.ndarray:
        """Return a 3-channel RGB image with realistic Saturn colors.

        Planet disk is pale gold, rings are cream/tan with color variation
        by ring section. Background is black.

        Returns:
            Array of shape (num_pixels, num_pixels, 3) with values in [0, 1].
        """
        g = self._build_geometry(half_fov_arcsec, num_pixels)

        rgb = np.zeros((num_pixels, num_pixels, 3))

        # Planet disk color: pale gold/tan with subtle band variation
        disk_color_bright = np.array([225, 210, 170]) / 255.0
        disk_color_dark = np.array([190, 175, 140]) / 255.0
        band_blend = np.clip(0.5 + g["bands"] / 0.12, 0.0, 1.0)

        for c in range(3):
            rgb[..., c] = np.where(
                g["disk"],
                g["limb"] * (disk_color_dark[c] * (1.0 - band_blend)
                             + disk_color_bright[c] * band_blend),
                0.0,
            )

        # Ring colors vary by section
        c_ring_color = np.array([160, 150, 140]) / 255.0   # grayish
        b_ring_color = np.array([220, 210, 185]) / 255.0   # bright cream
        a_ring_color = np.array([195, 185, 165]) / 255.0   # muted cream
        r_eq = g["r_eq"]
        xx, yy = g["xx"], g["yy"]
        ring_r = np.sqrt(xx ** 2 + (yy / g["sin_tilt"]) ** 2)

        # Build ring color layer
        ring_rgb = np.zeros_like(rgb)
        c_mask = g["ring_mask"] & (ring_r < r_eq * 1.53)
        b_mask = g["ring_mask"] & (ring_r >= r_eq * 1.53) & (
            ring_r < r_eq * 1.95)
        a_mask = g["ring_mask"] & (ring_r >= r_eq * 2.02)
        for ch in range(3):
            ring_rgb[..., ch] = np.where(c_mask, c_ring_color[ch], 0.0)
            ring_rgb[..., ch] = np.where(b_mask, b_ring_color[ch],
                                         ring_rgb[..., ch])
            ring_rgb[..., ch] = np.where(a_mask, a_ring_color[ch],
                                         ring_rgb[..., ch])

        # Ring shadow on the disk: darken the equatorial strip where
        # the rings cast a shadow across the planet (only when not
        # already covered by front-facing rings).
        if g["shadow"].max() > 0:
            for ch in range(3):
                rgb[..., ch] = rgb[..., ch] * (1.0 - g["shadow"])

        # Layer back rings (behind planet, only outside disk)
        back_vis = g["ring_back"] & ~g["disk"]
        for ch in range(3):
            rgb[..., ch] = np.where(back_vis, ring_rgb[..., ch],
                                    rgb[..., ch])

        # Layer front rings (in front of planet, including over disk)
        front_outside = g["ring_front"] & ~g["disk"]
        front_over = g["ring_front"] & g["disk"]
        ring_opacity = 0.85
        for ch in range(3):
            rgb[..., ch] = np.where(front_outside, ring_rgb[..., ch],
                                    rgb[..., ch])
            rgb[..., ch] = np.where(
                front_over,
                ring_opacity * ring_rgb[..., ch]
                + (1.0 - ring_opacity) * rgb[..., ch],
                rgb[..., ch],
            )

        return np.clip(rgb, 0.0, 1.0)

    @property
    def field_extent_arcsec(self) -> float:
        # Rings extend to ~2.27x planet radius; add padding
        return self.angular_diameter_arcsec * 2.27 * 1.3


class Moon(AstronomicalSource):
    """Texture-mapped model of the Moon using NASA LRO data.

    Uses a real lunar albedo map (NASA/GSFC/ASU LRO LROC WAC mosaic)
    projected onto a sphere with orthographic projection, plus:
    - Limb darkening (mild, u=0.15)
    - Phase illumination with curved terminator
    - Sub-observer longitude for libration/rotation

    The texture file (lroc_color_2k.jpg) is an equirectangular map
    where longitude 0° is the center and latitude runs pole-to-pole.

    Data source: NASA Scientific Visualization Studio, CGI Moon Kit
    (https://svs.gsfc.nasa.gov/4720). Credit: NASA/GSFC/ASU.

    Args:
        angular_diameter_arcsec: Angular diameter in arcseconds.
            Typical: ~1870" (about 31 arcminutes).
        phase: Illumination fraction (0 = new, 0.5 = quarter,
            1.0 = full). Default is full moon.
        sub_observer_lon_deg: Sub-observer longitude in degrees.
            0° shows the standard near side. Adjust for libration.
    """

    # Class-level texture cache (loaded once, shared by all instances)
    _texture_cache = None

    def __init__(self, angular_diameter_arcsec: float = 1870.0,
                 phase: float = 1.0,
                 sub_observer_lon_deg: float = 0.0,
                 use_realtime: bool = False):
        """
        Args:
            angular_diameter_arcsec: Apparent diameter (1850″-2000″
                range; mean ~1870″).
            phase: Illuminated fraction 0..1 (0 = new, 0.5 = half, 1 = full).
            sub_observer_lon_deg: Sub-observer longitude — controls
                which face of the Moon is presented.
            use_realtime: When True, query skyfield for the *current*
                Moon geometry: angular diameter (varies with the
                ~14% Earth–Moon distance change over a month),
                illumination phase, and approximate sub-observer
                longitude.
        """
        if use_realtime:
            from telescope_sim.source.realtime import (
                moon_angular_diameter, moon_phase, moon_phase_angle,
            )
            angular_diameter_arcsec = moon_angular_diameter()
            phase = moon_phase()
            sub_observer_lon_deg = moon_phase_angle()
        self.angular_diameter_arcsec = angular_diameter_arcsec
        self.phase = np.clip(phase, 0.0, 1.0)
        self.sub_observer_lon_deg = sub_observer_lon_deg
        self.use_realtime = use_realtime

    @classmethod
    def _load_texture(cls):
        """Load the NASA lunar albedo texture (cached at class level)."""
        if cls._texture_cache is not None:
            return cls._texture_cache

        import os
        from PIL import Image

        texture_path = os.path.join(
            os.path.dirname(__file__), "data", "moon_albedo.jpg"
        )
        if not os.path.exists(texture_path):
            raise FileNotFoundError(
                f"Lunar texture not found at {texture_path}. "
                "Download from: https://svs.gsfc.nasa.gov/4720"
            )

        img = Image.open(texture_path)
        # Convert to float RGB array, shape (H, W, 3), values [0, 1]
        cls._texture_cache = np.asarray(img, dtype=np.float64) / 255.0
        return cls._texture_cache

    def _sample_texture(self, lat, lon, disk):
        """Sample the equirectangular texture at given lat/lon coords.

        Args:
            lat: Latitude array in radians (-pi/2 to +pi/2).
            lon: Longitude array in radians (-pi to +pi).
            disk: Boolean mask of valid (on-disk) pixels.

        Returns:
            RGB array of shape (*lat.shape, 3) with values in [0, 1].
        """
        texture = self._load_texture()
        tex_h, tex_w = texture.shape[:2]

        rgb = np.zeros((*lat.shape, 3))

        # Map lat/lon to texture pixel coordinates
        # Texture: x = 0..W maps to lon = -180..+180
        #          y = 0..H maps to lat = +90..-90
        u = (lon[disk] / np.pi + 1.0) * 0.5  # [0, 1]
        v = (0.5 - lat[disk] / np.pi)         # [0, 1]

        # Convert to pixel indices with bilinear interpolation
        px = np.clip(u * (tex_w - 1), 0, tex_w - 1)
        py = np.clip(v * (tex_h - 1), 0, tex_h - 1)

        # Bilinear interpolation for smooth sampling
        x0 = np.floor(px).astype(int)
        y0 = np.floor(py).astype(int)
        x1 = np.minimum(x0 + 1, tex_w - 1)
        y1 = np.minimum(y0 + 1, tex_h - 1)
        fx = px - x0
        fy = py - y0

        for c in range(3):
            val = (texture[y0, x0, c] * (1 - fx) * (1 - fy)
                   + texture[y0, x1, c] * fx * (1 - fy)
                   + texture[y1, x0, c] * (1 - fx) * fy
                   + texture[y1, x1, c] * fx * fy)
            rgb[..., c][disk] = val

        return rgb

    def _build_geometry(self, half_fov_arcsec, num_pixels):
        """Compute grids, disk mask, spherical coords, and phase."""
        coords = np.linspace(-half_fov_arcsec, half_fov_arcsec, num_pixels)
        xx, yy = np.meshgrid(coords, coords)

        radius = self.angular_diameter_arcsec / 2.0
        rr = np.sqrt(xx ** 2 + yy ** 2) / radius
        disk = rr <= 1.0

        # Limb darkening (mild for the Moon)
        u = 0.15
        mu = np.zeros_like(rr)
        mu[disk] = np.sqrt(1.0 - np.clip(rr[disk], 0, 1) ** 2)
        limb = np.zeros_like(rr)
        limb[disk] = 1.0 - u * (1.0 - mu[disk])

        # Orthographic projection: convert image (x, y) to
        # selenographic (lat, lon) for texture lookup.
        # x/radius = cos(lat) * sin(lon - lon0)
        # y/radius = sin(lat)
        # z/radius = cos(lat) * cos(lon - lon0)  [z > 0 = visible]
        lat = np.zeros_like(rr)
        lon = np.zeros_like(rr)

        # Normalized coords on the unit sphere
        xn = xx[disk] / radius
        yn = yy[disk] / radius
        zn = np.sqrt(np.clip(1.0 - xn ** 2 - yn ** 2, 0, 1))

        lat[disk] = np.arcsin(np.clip(yn, -1, 1))
        lon[disk] = np.arctan2(xn, zn) + np.radians(
            self.sub_observer_lon_deg)

        # Wrap longitude to [-pi, pi]
        lon[disk] = (lon[disk] + np.pi) % (2 * np.pi) - np.pi

        # Phase terminator
        illuminated = np.ones_like(rr, dtype=bool)
        if self.phase < 1.0:
            term_x = (2.0 * self.phase - 1.0) * radius
            term_curve = term_x * mu
            illuminated = xx >= term_curve

        return {
            "xx": xx, "yy": yy, "disk": disk, "limb": limb,
            "lat": lat, "lon": lon, "illuminated": illuminated,
            "radius": radius, "mu": mu,
        }

    def render_ideal(self, half_fov_arcsec: float,
                     num_pixels: int) -> np.ndarray:
        g = self._build_geometry(half_fov_arcsec, num_pixels)

        # Sample texture and convert to grayscale
        rgb = self._sample_texture(g["lat"], g["lon"], g["disk"])
        surface = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + \
            0.114 * rgb[..., 2]

        image = surface * g["limb"] * g["illuminated"] * g["disk"]

        image = np.clip(image, 0.0, None)
        if image.max() > 0:
            image /= image.max()
        return image

    def render_ideal_rgb(self, half_fov_arcsec: float,
                         num_pixels: int) -> np.ndarray:
        """Return a 3-channel RGB image using NASA lunar texture.

        The texture provides real surface color from LRO LROC WAC
        data. Limb darkening and phase illumination are applied on top.

        Returns:
            Array of shape (num_pixels, num_pixels, 3) with values in [0, 1].
        """
        g = self._build_geometry(half_fov_arcsec, num_pixels)

        rgb = self._sample_texture(g["lat"], g["lon"], g["disk"])

        # Apply limb darkening, disk mask, and phase
        for c in range(3):
            rgb[..., c] *= g["limb"]
            rgb[..., c] *= g["disk"]
            rgb[..., c] *= g["illuminated"]

        return np.clip(rgb, 0.0, 1.0)

    @property
    def field_extent_arcsec(self) -> float:
        return self.angular_diameter_arcsec * 1.3

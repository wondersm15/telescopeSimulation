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
    """

    def __init__(self, field_angle_arcsec: float = 0.0,
                 position_angle_deg: float = 0.0,
                 magnitude: float = 0.0):
        self.field_angle_arcsec = field_angle_arcsec
        self.position_angle_deg = position_angle_deg
        self.magnitude = magnitude

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
        if self.field_angle_arcsec < 1.0:
            return 10.0
        return self.field_angle_arcsec * 2.5


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

    def __init__(self, angular_diameter_arcsec: float = 40.0):
        self.angular_diameter_arcsec = angular_diameter_arcsec

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

        # Latitude
        lat = np.zeros_like(yy)
        lat[disk] = np.arcsin(np.clip(yy[disk] / radius_arcsec, -1, 1))

        # Band pattern as signed value: positive = zone (bright/cream),
        # negative = belt (dark/brown)
        band_signal = (0.08 * np.sin(6.0 * lat)
                       + 0.05 * np.sin(12.0 * lat)
                       + 0.03 * np.sin(20.0 * lat))

        # Map band_signal to a blend factor: 0 = belt color, 1 = zone color
        # band_signal range is roughly [-0.16, +0.16]
        blend = np.clip(0.5 + band_signal / 0.32, 0.0, 1.0)

        # Realistic Jupiter colors (RGB, 0-1 scale)
        # Zones (bright): cream/pale yellow
        zone_color = np.array([235, 220, 185]) / 255.0
        # Belts (dark): warm brown
        belt_color = np.array([170, 130, 90]) / 255.0

        # Interpolate between belt and zone colors
        rgb = np.zeros((num_pixels, num_pixels, 3))
        for c in range(3):
            rgb[..., c] = (belt_color[c] * (1.0 - blend)
                           + zone_color[c] * blend)

        # Great Red Spot: reddish-orange tint
        grs_lat = np.radians(-22.0)
        grs_lon = np.radians(30.0)
        grs_x = radius_arcsec * np.cos(grs_lat) * np.sin(grs_lon)
        grs_y = radius_arcsec * np.sin(grs_lat)
        grs_sigma_x = radius_arcsec * 0.12
        grs_sigma_y = radius_arcsec * 0.07
        grs_mask = np.exp(
            -((xx - grs_x) ** 2 / (2 * grs_sigma_x ** 2)
              + (yy - grs_y) ** 2 / (2 * grs_sigma_y ** 2))
        )
        grs_color = np.array([200, 120, 80]) / 255.0
        for c in range(3):
            rgb[..., c] = (rgb[..., c] * (1.0 - grs_mask)
                           + grs_color[c] * grs_mask)

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
                 ring_tilt_deg: float = 20.0):
        self.angular_diameter_arcsec = angular_diameter_arcsec
        self.ring_tilt_deg = ring_tilt_deg

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

        # Subtle band structure (less pronounced than Jupiter)
        lat = np.zeros_like(yy)
        lat[disk] = np.arcsin(np.clip(yy[disk] / r_pol, -1, 1))
        bands = 0.04 * np.sin(5.0 * lat) + 0.02 * np.sin(10.0 * lat)

        # Ring geometry: rings are circular but appear as an ellipse
        # due to tilt. Ring plane is tilted relative to line of sight.
        # In projection, rings are an ellipse with semi-major = r_ring
        # and semi-minor = r_ring * sin(tilt).
        ring_inner_b = r_eq * 1.24   # inner edge of C ring
        ring_cassini_inner = r_eq * 1.95  # Cassini division inner edge
        ring_cassini_outer = r_eq * 2.02  # Cassini division outer edge
        ring_outer_a = r_eq * 2.27   # outer edge of A ring

        # Projected ring coordinates (ellipse due to tilt)
        sin_tilt = np.sin(tilt_rad)
        # Ring distance from center in ring-plane coordinates
        ring_r = np.sqrt((xx / 1.0) ** 2 + (yy / sin_tilt) ** 2)

        # Ring mask (annulus, excluding Cassini division)
        in_rings = (ring_r >= ring_inner_b) & (ring_r <= ring_outer_a)
        in_cassini = ((ring_r >= ring_cassini_inner)
                      & (ring_r <= ring_cassini_outer))
        ring_mask = in_rings & ~in_cassini

        # Ring brightness varies with radius (B ring brightest)
        ring_brightness = np.zeros_like(ring_r)
        # C ring (inner, dim): ring_inner_b to ~1.53*r_eq
        c_ring = (ring_r >= ring_inner_b) & (ring_r < r_eq * 1.53)
        ring_brightness[c_ring] = 0.35
        # B ring (middle, brightest): ~1.53*r_eq to cassini_inner
        b_ring = ((ring_r >= r_eq * 1.53)
                  & (ring_r < ring_cassini_inner))
        ring_brightness[b_ring] = 1.0
        # A ring (outer, moderate): cassini_outer to ring_outer_a
        a_ring = ((ring_r >= ring_cassini_outer)
                  & (ring_r <= ring_outer_a))
        ring_brightness[a_ring] = 0.65

        ring_brightness *= ring_mask

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
            "sin_tilt": sin_tilt,
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
                 sub_observer_lon_deg: float = 0.0):
        self.angular_diameter_arcsec = angular_diameter_arcsec
        self.phase = np.clip(phase, 0.0, 1.0)
        self.sub_observer_lon_deg = sub_observer_lon_deg

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

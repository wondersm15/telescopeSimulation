"""2D FFT-based PSF computation with pupil mask support.

Computes the Fraunhofer diffraction PSF as |FFT(pupil)|^2.  The pupil
mask can include a central obstruction and spider vanes, producing
realistic diffraction spikes in the PSF image.

When no spider vanes are present, the result matches the analytical
Airy/annular PSF (validated in tests via azimuthal average comparison).
"""

import numpy as np


def build_pupil_mask(grid_size: int, aperture_diameter: float,
                     obstruction_ratio: float = 0.0,
                     spider_vanes: int = 0,
                     spider_vane_width: float = 1.0) -> np.ndarray:
    """Build a 2D binary pupil mask.

    Args:
        grid_size: Number of pixels across the mask (square).
        aperture_diameter: Primary mirror diameter in mm.
        obstruction_ratio: Central obstruction ratio (0.0 to <1.0).
        spider_vanes: Number of spider vanes (0, 3, 4, 6 typical).
        spider_vane_width: Width of each vane in mm.

    Returns:
        2D float array (grid_size x grid_size), 1.0 = open, 0.0 = blocked.
    """
    # Coordinates in mm, centered on aperture
    radius = aperture_diameter / 2.0
    coords = np.linspace(-radius, radius, grid_size)
    xx, yy = np.meshgrid(coords, coords)
    rr = np.sqrt(xx ** 2 + yy ** 2)

    # Circular aperture
    mask = (rr <= radius).astype(float)

    # Central obstruction
    if obstruction_ratio > 0:
        obstruction_radius = radius * obstruction_ratio
        mask[rr <= obstruction_radius] = 0.0

    # Spider vanes: thin rectangles from center to edge, equally spaced
    if spider_vanes > 0:
        vane_half_width = spider_vane_width / 2.0
        for k in range(spider_vanes):
            angle = k * np.pi / spider_vanes
            # Rotate coordinates to align vane with the x-axis
            cos_a = np.cos(angle)
            sin_a = np.sin(angle)
            # Distance from each point to the vane line
            perp_dist = np.abs(-sin_a * xx + cos_a * yy)
            # Points along the vane direction (both positive and negative
            # from center, so the vane spans the full diameter)
            along_dist = cos_a * xx + sin_a * yy
            in_vane = (perp_dist <= vane_half_width) & (rr <= radius)
            mask[in_vane] = 0.0

    return mask


def compute_fft_psf(aperture_diameter: float, focal_length: float,
                    wavelength_mm: float, obstruction_ratio: float = 0.0,
                    spider_vanes: int = 0, spider_vane_width: float = 1.0,
                    grid_size: int = 1024,
                    oversample: int = 1):
    """Compute the 2D PSF via Fraunhofer diffraction (FFT of the pupil).

    PSF = |FFT(pupil)|^2, normalized so peak = 1.0.

    The pupil mask is built at *grid_size* resolution, then zero-padded
    to *grid_size * oversample* before FFT.  This increases image-plane
    sampling without changing the pupil sampling.

    The image-plane pixel pitch is:
        di = wavelength * focal_length / (fft_size * dp)
    where dp = aperture_diameter / grid_size, fft_size = grid_size * oversample.

    Args:
        aperture_diameter: Primary mirror diameter in mm.
        focal_length: Focal length in mm.
        wavelength_mm: Wavelength of light in mm.
        obstruction_ratio: Central obstruction ratio (0.0 to <1.0).
        spider_vanes: Number of spider vanes (0 = none).
        spider_vane_width: Width of each vane in mm.
        grid_size: Pupil mask resolution (power of 2 recommended).
        oversample: Zero-padding factor for finer image-plane sampling.
            Higher values give more pixels across the Airy disk.
            Default 1 (no padding).

    Returns:
        Tuple of (psf_2d, half_size_mm) where:
        - psf_2d: 2D array normalized to peak = 1.0
        - half_size_mm: half-width of the image in mm
    """
    mask = build_pupil_mask(grid_size, aperture_diameter, obstruction_ratio,
                            spider_vanes, spider_vane_width)

    # Zero-pad for finer image-plane sampling
    fft_size = grid_size * oversample
    if oversample > 1:
        padded = np.zeros((fft_size, fft_size))
        offset = (fft_size - grid_size) // 2
        padded[offset:offset + grid_size, offset:offset + grid_size] = mask
        mask = padded

    # Compute the Fraunhofer diffraction pattern
    # PSF = |FFT(pupil)|^2
    field = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(mask)))
    psf = np.abs(field) ** 2

    # Normalize to peak = 1.0
    peak = psf.max()
    if peak > 0:
        psf = psf / peak

    # Image plane pixel pitch (dp stays based on original grid_size)
    dp = aperture_diameter / grid_size  # pupil plane pixel size (mm)
    di = wavelength_mm * focal_length / (fft_size * dp)  # image plane pixel size (mm)
    half_size_mm = (fft_size / 2.0) * di

    return psf, half_size_mm

"""Eyepiece model for visual observing calculations.

This is NOT a ray-tracing optical element — the eyepiece doesn't change the
PSF (the image is formed at the focal plane before the eyepiece). It determines
magnification, true field of view, and exit pupil for visual observing.
"""

from __future__ import annotations

import dataclasses


EYEPIECE_PRESETS = {
    "plossl_25mm": {"focal_length_mm": 25.0, "apparent_fov_deg": 50.0},
    "plossl_10mm": {"focal_length_mm": 10.0, "apparent_fov_deg": 50.0},
    "wide_20mm": {"focal_length_mm": 20.0, "apparent_fov_deg": 68.0},
    "wide_13mm": {"focal_length_mm": 13.0, "apparent_fov_deg": 68.0},
    "ultra_wide_9mm": {"focal_length_mm": 9.0, "apparent_fov_deg": 82.0},
    "ultra_wide_5mm": {"focal_length_mm": 5.0, "apparent_fov_deg": 82.0},
}


@dataclasses.dataclass
class Eyepiece:
    """Simple eyepiece model for visual observing.

    Computes magnification, true field of view, and exit pupil from the
    eyepiece focal length and apparent field of view combined with the
    telescope's focal length and aperture.

    Attributes:
        focal_length_mm: Eyepiece focal length in mm.
        apparent_fov_deg: Apparent field of view in degrees.
    """

    focal_length_mm: float
    apparent_fov_deg: float = 50.0

    def magnification(self, telescope_focal_length_mm: float) -> float:
        """Compute magnification = f_telescope / f_eyepiece."""
        return telescope_focal_length_mm / self.focal_length_mm

    def true_fov_arcsec(self, telescope_focal_length_mm: float) -> float:
        """Compute true field of view in arcseconds.

        TFOV = apparent_FOV / magnification, converted to arcseconds.
        """
        mag = self.magnification(telescope_focal_length_mm)
        return self.apparent_fov_deg / mag * 3600.0

    def true_fov_arcmin(self, telescope_focal_length_mm: float) -> float:
        """Compute true field of view in arcminutes."""
        return self.true_fov_arcsec(telescope_focal_length_mm) / 60.0

    def exit_pupil_mm(self, primary_diameter_mm: float,
                      telescope_focal_length_mm: float) -> float:
        """Compute exit pupil diameter in mm.

        Exit pupil = aperture / magnification.
        """
        mag = self.magnification(telescope_focal_length_mm)
        return primary_diameter_mm / mag

    def max_useful_magnification(self, primary_diameter_mm: float) -> float:
        """Rule-of-thumb maximum useful magnification (2x aperture in mm)."""
        return 2.0 * primary_diameter_mm

    def min_useful_magnification(self, primary_diameter_mm: float) -> float:
        """Minimum magnification to fill exit pupil (aperture / 7mm)."""
        return primary_diameter_mm / 7.0

    def magnification_assessment(self, telescope_focal_length_mm: float,
                                  primary_diameter_mm: float) -> str:
        """Return a human-readable assessment of this eyepiece's magnification.

        Returns one of: "too low", "low", "good", "high", "too high"
        """
        mag = self.magnification(telescope_focal_length_mm)
        ep = self.exit_pupil_mm(primary_diameter_mm, telescope_focal_length_mm)
        max_mag = self.max_useful_magnification(primary_diameter_mm)
        min_mag = self.min_useful_magnification(primary_diameter_mm)

        if mag > max_mag * 1.5:
            return "too high"
        elif mag > max_mag:
            return "high"
        elif mag < min_mag:
            return "too low"
        elif ep > 5.0:
            return "low"
        else:
            return "good"

    def summary(self, telescope_focal_length_mm: float,
                primary_diameter_mm: float) -> str:
        """Return a multi-line summary string for this eyepiece + telescope."""
        mag = self.magnification(telescope_focal_length_mm)
        tfov = self.true_fov_arcmin(telescope_focal_length_mm)
        ep = self.exit_pupil_mm(primary_diameter_mm, telescope_focal_length_mm)
        assessment = self.magnification_assessment(
            telescope_focal_length_mm, primary_diameter_mm)
        max_mag = self.max_useful_magnification(primary_diameter_mm)
        min_mag = self.min_useful_magnification(primary_diameter_mm)
        return (
            f"Eyepiece: {self.focal_length_mm}mm, {self.apparent_fov_deg}° AFOV\n"
            f"  Magnification: {mag:.0f}x ({assessment})\n"
            f"  True FOV: {tfov:.1f} arcmin\n"
            f"  Exit pupil: {ep:.1f} mm\n"
            f"  Useful range: {min_mag:.0f}x – {max_mag:.0f}x"
        )

    @classmethod
    def from_preset(cls, name: str) -> Eyepiece:
        """Create an Eyepiece from a named preset.

        Available presets: plossl_25mm, plossl_10mm, wide_20mm, wide_13mm,
        ultra_wide_9mm, ultra_wide_5mm.

        Raises:
            ValueError: If the preset name is not recognized.
        """
        if name not in EYEPIECE_PRESETS:
            available = ", ".join(sorted(EYEPIECE_PRESETS.keys()))
            raise ValueError(
                f"Unknown eyepiece preset '{name}'. "
                f"Available: {available}"
            )
        return cls(**EYEPIECE_PRESETS[name])

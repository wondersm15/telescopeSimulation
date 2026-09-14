"""Eyepiece model for visual observing calculations.

This is NOT a ray-tracing optical element — the eyepiece doesn't change the
PSF (the image is formed at the focal plane before the eyepiece). It determines
magnification, true field of view, and exit pupil for visual observing.
"""

from __future__ import annotations

import dataclasses
import math


EYEPIECE_PRESETS = {
    "plossl_25mm": {"focal_length_mm": 25.0, "apparent_fov_deg": 50.0},
    "plossl_10mm": {"focal_length_mm": 10.0, "apparent_fov_deg": 50.0},
    "wide_20mm": {"focal_length_mm": 20.0, "apparent_fov_deg": 68.0},
    "wide_13mm": {"focal_length_mm": 13.0, "apparent_fov_deg": 68.0},
    "ultra_wide_9mm": {"focal_length_mm": 9.0, "apparent_fov_deg": 82.0},
    "ultra_wide_5mm": {"focal_length_mm": 5.0, "apparent_fov_deg": 82.0},
}

#: Exit pupil below which extra magnification stops delivering detail, in mm.
#: The eye's own aperture becomes the limit: its diffraction grows, and floaters
#: and lens imperfections are projected onto a smaller and smaller retinal
#: patch. 0.5 mm is the conventional figure and it is where the familiar
#: "maximum useful magnification = 2x aperture in mm" comes from — that rule is
#: not independent, it is exactly D / 0.5 mm restated. ⚠️ EMPIRICAL: a
#: physiological threshold that varies between observers and with seeing, not a
#: derived constant.
MIN_USEFUL_EXIT_PUPIL_MM = 0.5

#: Dark-adapted pupil diameter assumed when no observer is specified, in mm.
#: ⚠️ EMPIRICAL and AGE-DEPENDENT: ~7 mm is a young dark-adapted eye; it falls
#: to roughly 5 mm by middle age. Any exit pupil larger than this spills light
#: outside the observer's own pupil, so aperture is wasted — which is why the
#: number matters and why it is a parameter here rather than a constant.
DEFAULT_EYE_PUPIL_MM = 7.0


@dataclasses.dataclass
class Eyepiece:
    """Simple eyepiece model for visual observing.

    Computes magnification, true field of view, and exit pupil from the
    eyepiece focal length and apparent field of view combined with the
    telescope's focal length and aperture.

    Attributes:
        focal_length_mm: Eyepiece focal length in mm.
        apparent_fov_deg: Apparent field of view in degrees.
        field_stop_mm: Field stop diameter in mm, if known. Manufacturers
            publish this, and it gives the EXACT true field of view. When
            None, `true_fov_arcsec` falls back to the AFOV/magnification
            approximation and says so via `tfov_is_exact`.
        eye_pupil_mm: The observer's dark-adapted pupil diameter in mm, used
            for the minimum useful magnification. See DEFAULT_EYE_PUPIL_MM —
            this is an observer property, not a telescope property.
    """

    focal_length_mm: float
    apparent_fov_deg: float = 50.0
    field_stop_mm: float | None = None
    eye_pupil_mm: float = DEFAULT_EYE_PUPIL_MM

    def magnification(self, telescope_focal_length_mm: float) -> float:
        """Compute magnification = f_telescope / f_eyepiece."""
        return telescope_focal_length_mm / self.focal_length_mm

    @property
    def tfov_is_exact(self) -> bool:
        """True when the true field of view comes from the field stop."""
        return self.field_stop_mm is not None

    def true_fov_arcsec(self, telescope_focal_length_mm: float) -> float:
        """Compute true field of view in arcseconds.

        Two formulas, and which one runs depends on what is known:

        * **Field stop (exact).** The field stop is a real aperture at the
          focal plane, so the sky it admits follows directly from the plate
          scale: ``TFOV = 206265 * d_stop / f_telescope``. Nothing about the
          eyepiece's internal design enters.
        * **AFOV / magnification (approximate).** ⚠️ Used only when
          `field_stop_mm` is None. It assumes the eyepiece maps field angle
          to apparent angle linearly, which no real wide-field eyepiece does
          — they deliberately carry angular magnification distortion to keep
          the exit pupil manageable. The error is typically a few percent and
          usually OPTIMISTIC (a real 25 mm Plossl admits slightly less sky
          than 50 deg / M suggests). Flagged by `tfov_is_exact` so callers
          can label it; see `nominal_field_stop_mm` for why the two disagree.
        """
        if self.field_stop_mm is not None:
            return 206265.0 * self.field_stop_mm / telescope_focal_length_mm
        mag = self.magnification(telescope_focal_length_mm)
        return self.apparent_fov_deg / mag * 3600.0

    def nominal_field_stop_mm(self) -> float:
        """Field stop a DISTORTION-FREE eyepiece of this AFOV would need.

        ``d = 2 * f_eyepiece * tan(AFOV / 2)`` — the field stop that maps the
        stated apparent field with no distortion at all.

        ⚠️ ESTIMATE, deliberately NOT used as a default for `field_stop_mm`.
        Real eyepieces come in a few percent under this figure, and the
        shortfall grows with apparent field, because ultra-wides trade
        rectilinearity for a usable exit pupil. Substituting this value would
        replace an honest approximation with a confident wrong number, so it
        is offered for comparison only — pass the manufacturer's published
        field stop to `field_stop_mm` for an exact answer.
        """
        half = math.radians(self.apparent_fov_deg) / 2.0
        return 2.0 * self.focal_length_mm * math.tan(half)

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
        """Magnification at which the exit pupil gets too small to help.

        Derived from the exit pupil rather than asserted: magnification is
        useful until ``D / M`` falls below MIN_USEFUL_EXIT_PUPIL_MM, so
        ``M_max = D / 0.5 mm``.

        This reproduces the familiar "2x the aperture in mm" rule EXACTLY —
        ``D / 0.5 == 2 * D`` — which is the point. That rule is not an
        independent fact to be memorised; it is the exit-pupil criterion
        restated, and writing it this way means changing the threshold
        changes the limit consistently everywhere. ⚠️ The threshold itself is
        empirical (see MIN_USEFUL_EXIT_PUPIL_MM).
        """
        return primary_diameter_mm / MIN_USEFUL_EXIT_PUPIL_MM

    def min_useful_magnification(self, primary_diameter_mm: float) -> float:
        """Magnification below which light spills outside the observer's pupil.

        ``M_min = D / eye_pupil``. Below this the exit pupil is wider than the
        eye's own pupil, so the outer part of the beam never enters the eye:
        the extra aperture is simply thrown away, and the telescope behaves
        like a smaller one.

        Depends on the OBSERVER, not the telescope — `eye_pupil_mm` defaults
        to 7 mm (young, dark-adapted) and is roughly 5 mm by middle age, which
        raises this limit by 40%.
        """
        return primary_diameter_mm / self.eye_pupil_mm

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
            # Not wasted aperture yet (that is `min_mag` above), but a large
            # exit pupil floods the eye and washes out contrast on planets,
            # and on a reflector the observer's own pupil starts to see the
            # secondary shadow. See `_apply_exit_pupil_washout`.
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
        # The TFOV basis has to travel with the number. Reporting a field of
        # view to 0.1' when it came from AFOV/M implies a precision the
        # approximation does not have (see `true_fov_arcsec`).
        basis = ("from field stop"
                 if self.tfov_is_exact else "approx: AFOV/mag")
        return (
            f"Eyepiece: {self.focal_length_mm}mm, {self.apparent_fov_deg}° AFOV\n"
            f"  Magnification: {mag:.0f}x ({assessment})\n"
            f"  True FOV: {tfov:.1f} arcmin ({basis})\n"
            f"  Exit pupil: {ep:.1f} mm\n"
            f"  Useful range: {min_mag:.0f}x – {max_mag:.0f}x "
            f"(exit pupil {self.eye_pupil_mm:.0f}mm – "
            f"{MIN_USEFUL_EXIT_PUPIL_MM:.1f}mm)"
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

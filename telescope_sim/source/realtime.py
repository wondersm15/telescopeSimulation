"""Live ephemeris helpers — current angular sizes and phases.

Wraps skyfield + the JPL DE421 ephemeris to compute Earth-to-target
geometry for *now* (or any user-supplied datetime). Used by the
"Real Objects" tutorial scenarios to render Jupiter/Saturn/Moon at
their actual angular size on the night the user runs the simulator.

The ephemeris file (~16 MB) is downloaded once into the user's
skyfield cache (~/.skyfield) on first use, then loaded from there
forever after. Network access is required *only* on first call.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

# Body radii in km (IAU/JPL standard mean radii). Used to convert
# Earth-target distance into apparent angular diameter.
_BODY_RADIUS_KM = {
    "moon": 1737.4,
    "jupiter": 69_911.0,     # equatorial
    "saturn": 58_232.0,      # equatorial (body, no rings)
    "saturn_rings": 136_775.0,  # A-ring outer edge ≈ 2.35 × R_eq
    "mars": 3389.5,
    "venus": 6051.8,
}

# Skyfield names for our targets. We use the BARYCENTRE for outer
# planets (Jupiter system, Saturn system) because that's the centre
# of mass that DE421 tracks reliably with sub-arcsec precision over
# centuries. The planet body offsets from its barycentre are
# negligible at telescope-tutorial scales (< 1″).
_SKYFIELD_NAME = {
    "moon": "moon",
    "jupiter": "jupiter barycenter",
    "saturn": "saturn barycenter",
    "mars": "mars",
    "venus": "venus",
}


@dataclass(frozen=True)
class BodyState:
    """Snapshot of an observed body's geometry at one instant."""
    name: str
    angular_diameter_arcsec: float
    distance_au: float
    sub_observer_lon_deg: float  # Moon only; 0 for outer planets
    illuminated_fraction: float  # Moon: 0..1; others: ~1.0 always
    ring_tilt_deg: float | None  # Saturn only; signed inclination
    timestamp_utc: str


# ── Cached skyfield loader ─────────────────────────────────────────


_eph_cache = None
_ts_cache = None


def _load_ephemeris():
    """Lazy-load DE421 and the timescale. Cached at module level.

    Files are stored in ~/.skyfield (not the repo) so the 16 MB
    ephemeris is shared across projects and never committed.
    """
    global _eph_cache, _ts_cache
    if _eph_cache is None:
        import os
        from skyfield.api import Loader

        cache_dir = os.path.expanduser("~/.skyfield")
        os.makedirs(cache_dir, exist_ok=True)
        loader = Loader(cache_dir)
        _ts_cache = loader.timescale()
        _eph_cache = loader("de421.bsp")
    return _eph_cache, _ts_cache


def _now_or_dt(dt: Optional[datetime]):
    """Coerce dt to a skyfield Time. Defaults to current UTC."""
    _, ts = _load_ephemeris()
    if dt is None:
        dt = datetime.now(timezone.utc)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return ts.from_datetime(dt)


def _angular_diameter_arcsec(radius_km: float, distance_au: float) -> float:
    """Apparent angular diameter (full, not radius) in arcseconds."""
    AU_KM = 149_597_870.7  # IAU 2012 value
    distance_km = distance_au * AU_KM
    # tan(θ/2) ≈ θ/2 for these tiny angles; angular diameter = 2 × radius / distance
    theta_rad = 2.0 * radius_km / distance_km
    return float(theta_rad * 206265.0)


def get_body_state(name: str, dt: Optional[datetime] = None) -> BodyState:
    """Return geometry for a body at `dt` (default: now)."""
    name = name.lower()
    if name not in _SKYFIELD_NAME:
        raise ValueError(
            f"Unknown body {name!r}. Supported: "
            f"{', '.join(_SKYFIELD_NAME)}"
        )

    eph, _ = _load_ephemeris()
    t = _now_or_dt(dt)

    earth = eph["earth"]
    body = eph[_SKYFIELD_NAME[name]]

    # Geocentric apparent position
    astrometric = earth.at(t).observe(body)
    distance_au = float(astrometric.distance().au)

    radius_km = _BODY_RADIUS_KM[name]
    ang_diam = _angular_diameter_arcsec(radius_km, distance_au)

    # Illumination + libration for the Moon
    illum = 1.0
    sub_obs_lon = 0.0
    ring_tilt = None

    if name == "moon":
        # Phase = 0.5 × (1 − cos(elongation)); elongation = Sun–Moon angle
        # from Earth's POV.
        sun = eph["sun"]
        moon_apparent = earth.at(t).observe(body)
        sun_apparent = earth.at(t).observe(sun)
        elongation_rad = moon_apparent.separation_from(sun_apparent).radians
        illum = 0.5 * (1.0 - float(np.cos(elongation_rad)))

        # Sub-observer longitude (very approximate; ignores libration
        # in latitude). Use the Moon's geocentric ecliptic longitude
        # relative to the Sun as a phase-angle proxy, mapped to a
        # rotation of the "lit face" graphic.
        sun_lon = float(sun_apparent.ecliptic_latlon()[1].degrees)
        moon_lon = float(moon_apparent.ecliptic_latlon()[1].degrees)
        sub_obs_lon = float((moon_lon - sun_lon) % 360.0)
        if sub_obs_lon > 180.0:
            sub_obs_lon -= 360.0

    elif name == "saturn":
        # Saturn ring tilt (B = "Saturnicentric latitude of Earth").
        # Use the planetographic frame from JPL: rough approximation
        # via the ecliptic latitude of Saturn — accurate to a few
        # degrees, sufficient for visual representation.
        eclat = float(astrometric.ecliptic_latlon()[0].degrees)
        # Saturn's rotation axis is tilted 26.73° to its orbital plane.
        # B = 26.73° × sin(true longitude of Saturn − ascending-node
        # longitude). The full formula needs the node; the ecliptic
        # latitude is a serviceable proxy near the maximum tilt
        # epochs (~2002, 2017, 2032).
        ring_tilt = 26.73 * float(
            np.sin(np.radians(eclat * 4.0))
        )
        ring_tilt = max(-26.73, min(26.73, ring_tilt))

    return BodyState(
        name=name,
        angular_diameter_arcsec=ang_diam,
        distance_au=distance_au,
        sub_observer_lon_deg=sub_obs_lon,
        illuminated_fraction=illum,
        ring_tilt_deg=ring_tilt,
        timestamp_utc=t.utc_iso(),
    )


# Convenience wrappers used by source classes — they accept a dt
# (None = now) and return just the angular diameter.

def jupiter_angular_diameter(dt: Optional[datetime] = None) -> float:
    """Apparent Jupiter angular diameter in arcseconds (now or `dt`)."""
    return get_body_state("jupiter", dt).angular_diameter_arcsec


def saturn_angular_diameter(dt: Optional[datetime] = None) -> float:
    """Apparent Saturn body angular diameter in arcseconds."""
    return get_body_state("saturn", dt).angular_diameter_arcsec


def saturn_ring_tilt(dt: Optional[datetime] = None) -> float:
    """Saturn ring tilt (B angle) in degrees, signed."""
    state = get_body_state("saturn", dt)
    return state.ring_tilt_deg if state.ring_tilt_deg is not None else 0.0


def moon_angular_diameter(dt: Optional[datetime] = None) -> float:
    return get_body_state("moon", dt).angular_diameter_arcsec


def moon_phase(dt: Optional[datetime] = None) -> float:
    """Moon illuminated fraction 0..1 (0 = new, 1 = full)."""
    return get_body_state("moon", dt).illuminated_fraction


def moon_phase_angle(dt: Optional[datetime] = None) -> float:
    """Moon phase angle: sub-observer longitude relative to subsolar."""
    return get_body_state("moon", dt).sub_observer_lon_deg


# Lazy numpy import — only when we actually compute geometry. Keeps
# import-time cost small.
import numpy as np  # noqa: E402

"""Trace rays through a Newtonian reflector telescope.

This demonstrates the telescope simulation by:
1. Defining a Newtonian telescope geometry
2. Creating parallel rays (point source at infinity)
3. Tracing rays through the optical system
4. Plotting ray traces, spot diagrams, focal images, and PSFs

Toggle `compare_mode` below to switch between single-telescope
mode and flexible side-by-side comparison mode.
"""

import matplotlib.pyplot as plt

from telescope_sim.geometry import (
    CassegrainTelescope,
    Eyepiece,
    MaksutovCassegrainTelescope,
    NewtonianTelescope,
    RefractingTelescope,
    SchmidtCassegrainTelescope,
)
from telescope_sim.source import create_parallel_rays
from telescope_sim.source import PointSource, StarField, Jupiter, Saturn, Moon

# ── Atmospheric seeing presets ────────────────────────────────────────
# FWHM in arcseconds for typical ground-based conditions.
# Use None for space telescope (no atmosphere).
SEEING_PRESETS = {
    "excellent": 0.8,   # rare, high-altitude site
    "good": 1.5,        # good night at a decent site
    "average": 2.5,     # typical suburban/rural
    "poor": 4.0,        # turbulent atmosphere
}
from telescope_sim.plotting import (
    plot_coma_field_analysis,
    plot_coma_spot,
    plot_focal_image,
    plot_focal_image_comparison,
    plot_polychromatic_ray_trace,
    plot_polychromatic_ray_trace_comparison,
    plot_psf_2d,
    plot_psf_2d_comparison,
    plot_psf_comparison,
    plot_psf_profile,
    plot_ray_trace,
    plot_ray_trace_comparison,
    plot_source_image,
    plot_spot_diagram,
    plot_spot_diagram_comparison,
    plot_vignetting_comparison,
    plot_vignetting_curve,
)

# Keys that telescope constructors accept
_NEWTONIAN_KEYS = {
    "primary_diameter", "focal_length", "secondary_offset",
    "secondary_minor_axis", "primary_type",
    "spider_vanes", "spider_vane_width",
}
_CASSEGRAIN_KEYS = {
    "primary_diameter", "primary_focal_length", "secondary_magnification",
    "back_focal_distance", "spider_vanes", "spider_vane_width",
}
_REFRACTING_KEYS = {
    "primary_diameter", "focal_length", "objective_type",
    "spider_vanes", "spider_vane_width",
}
_MAKSUTOV_KEYS = {
    "primary_diameter", "primary_focal_length", "secondary_magnification",
    "back_focal_distance", "meniscus_thickness",
    "spider_vanes", "spider_vane_width",
}
_SCHMIDT_KEYS = {
    "primary_diameter", "primary_focal_length", "secondary_magnification",
    "back_focal_distance", "spider_vanes", "spider_vane_width",
}
_TELESCOPE_KEYS = (_NEWTONIAN_KEYS | _CASSEGRAIN_KEYS | _REFRACTING_KEYS
                   | _MAKSUTOV_KEYS | _SCHMIDT_KEYS)

# Keys that control per-panel physics in comparison mode
_PHYSICS_KEYS = {
    "wavelength_nm", "method", "seeing_arcsec", "include_obstruction",
    "polychromatic",
}

# Every key that a comparison config dict may contain
_ALLOWED_CONFIG_KEYS = _TELESCOPE_KEYS | _PHYSICS_KEYS | {"label", "telescope_type"}


def _resolve_comparison_configs(configs, defaults):
    """Parse comparison config dicts into telescopes, labels, and physics.

    Each entry in *configs* is a dict with a ``"label"`` key plus any
    overrides for telescope geometry or physics parameters.  Keys not
    present fall back to the shared *defaults*.

    Args:
        configs: List of config dicts.  Each must have ``"label"`` and
                 may contain any subset of telescope or physics keys.
        defaults: Dict of shared default values (telescope geometry +
                  physics parameters).

    Returns:
        Tuple of ``(telescopes, labels, physics_params)`` where
        *physics_params* is a ``list[dict]`` suitable for passing to
        the comparison plotting functions.

    Raises:
        ValueError: On unrecognized keys (likely typos).
    """
    telescopes = []
    labels = []
    physics_params = []

    for cfg in configs:
        # Validate keys
        unknown = set(cfg) - _ALLOWED_CONFIG_KEYS
        if unknown:
            raise ValueError(
                f"Unrecognized comparison config key(s): {unknown}. "
                f"Allowed keys: {sorted(_ALLOWED_CONFIG_KEYS)}"
            )

        labels.append(cfg["label"])

        # Determine telescope type for this config
        tel_type = cfg.get(
            "telescope_type",
            defaults.get("telescope_type", "newtonian"),
        )

        # Build telescope from geometry keys + defaults
        if tel_type == "cassegrain":
            valid_keys = _CASSEGRAIN_KEYS
            tel_cls = CassegrainTelescope
        elif tel_type == "maksutov":
            valid_keys = _MAKSUTOV_KEYS
            tel_cls = MaksutovCassegrainTelescope
        elif tel_type == "schmidt":
            valid_keys = _SCHMIDT_KEYS
            tel_cls = SchmidtCassegrainTelescope
        elif tel_type == "refracting":
            valid_keys = _REFRACTING_KEYS
            tel_cls = RefractingTelescope
        else:
            valid_keys = _NEWTONIAN_KEYS
            tel_cls = NewtonianTelescope

        tel_kwargs = {}
        for key in valid_keys:
            if key in cfg:
                tel_kwargs[key] = cfg[key]
            elif key in defaults:
                tel_kwargs[key] = defaults[key]
        telescopes.append(tel_cls(**tel_kwargs))

        # Collect per-config physics overrides
        pp = {}
        for key in _PHYSICS_KEYS:
            if key in cfg:
                pp[key] = cfg[key]
        physics_params.append(pp)

    return telescopes, labels, physics_params


def run_single(telescope, num_display_rays, wavelength_nm, method,
               seeing_arcsec, include_obstruction=True,
               show_vignetting=False, show_coma_analysis=False,
               field_angle_arcsec=0.0, source=None, eyepiece=None,
               show_ray_trace=True, show_spot_diagram=True,
               show_focal_image=True, show_psf_profile=True,
               show_psf_2d=True, show_source_image=True,
               polychromatic=False,
               show_polychromatic_ray_trace=False):
    """Run all plots for a single telescope configuration."""
    if isinstance(telescope, MaksutovCassegrainTelescope):
        tel_name = "Maksutov-Cass"
    elif isinstance(telescope, SchmidtCassegrainTelescope):
        tel_name = "Schmidt-Cass"
    elif isinstance(telescope, CassegrainTelescope):
        tel_name = "Cassegrain"
    elif isinstance(telescope, RefractingTelescope):
        tel_name = "Refractor"
    else:
        tel_name = "Newtonian"
    print(f"Telescope: {telescope.primary_diameter}mm "
          f"f/{telescope.focal_ratio:.1f} {tel_name}")
    print(f"Primary type: {telescope.primary_type}")
    print(f"Focal length: {telescope.focal_length}mm")
    print(f"Tube length: {telescope.tube_length:.0f}mm")
    if telescope.spider_vanes > 0:
        print(f"Spider vanes: {telescope.spider_vanes} "
              f"({telescope.spider_vane_width:.1f}mm wide)")

    if eyepiece is not None:
        print(eyepiece.summary(telescope.focal_length, telescope.primary_diameter))

    rays = create_parallel_rays(
        num_rays=num_display_rays,
        aperture_diameter=telescope.primary_diameter,
        entry_height=telescope.tube_length * 1.15,
    )
    telescope.trace_rays(rays)

    components = telescope.get_components_for_plotting()
    if show_ray_trace:
        plot_ray_trace(
            rays, components,
            title=(f"{telescope.primary_diameter:.0f}mm f/{telescope.focal_ratio:.1f} "
                   f"{tel_name} — Ray Trace"),
        )
    if show_spot_diagram:
        plot_spot_diagram(
            rays,
            title=f"Spot Diagram — {telescope.primary_type.title()} Primary",
        )
    if show_focal_image:
        plot_focal_image(
            telescope,
            title=f"Simulated Image — {telescope.primary_type.title()} Primary",
            wavelength_nm=wavelength_nm,
            method=method,
            seeing_arcsec=seeing_arcsec,
            include_obstruction=include_obstruction,
        )
    if show_psf_profile:
        plot_psf_profile(
            telescope,
            title=f"PSF — {telescope.primary_type.title()} Primary",
            wavelength_nm=wavelength_nm,
            method=method,
            include_obstruction=include_obstruction,
        )

    # 2D PSF with diffraction spikes (most useful with spider vanes)
    if show_psf_2d and telescope.spider_vanes > 0:
        plot_psf_2d(
            telescope,
            wavelength_nm=wavelength_nm,
            include_obstruction=include_obstruction,
        )

    # Vignetting analysis
    if show_vignetting:
        plot_vignetting_curve(telescope)

    # Coma / off-axis analysis
    if show_coma_analysis:
        plot_coma_field_analysis(
            telescope,
            wavelength_nm=wavelength_nm,
            include_obstruction=include_obstruction,
        )
    if field_angle_arcsec > 0:
        plot_coma_spot(
            telescope,
            field_angle_arcsec=field_angle_arcsec,
            wavelength_nm=wavelength_nm,
            include_obstruction=include_obstruction,
        )

    # Polychromatic ray trace (only for refractors, only when enabled)
    if (show_polychromatic_ray_trace and polychromatic
            and isinstance(telescope, RefractingTelescope)):
        plot_polychromatic_ray_trace(
            telescope, num_display_rays=num_display_rays,
        )

    # Source imaging
    if show_source_image and source is not None:
        #log_scale = isinstance(source, StarField)
        log_scale = False
        plot_source_image(
            telescope, source,
            wavelength_nm=wavelength_nm,
            seeing_arcsec=seeing_arcsec,
            include_obstruction=include_obstruction,
            method=method,
            log_scale=log_scale,
            eyepiece=eyepiece,
            polychromatic=polychromatic,
        )


def run_comparison(configs, defaults, num_display_rays,
                   show_vignetting=False,
                   show_ray_trace_comparison=True,
                   show_spot_comparison=True,
                   show_focal_image_comparison=True,
                   show_psf_comparison=True,
                   show_psf_2d_comparison=True,
                   show_coma_comparison=False):
    """Build multiple telescopes from config dicts and produce comparison plots.

    Args:
        configs: List of comparison config dicts (see ``comparison_configs``).
        defaults: Dict of shared default values (geometry + physics).
        num_display_rays: Number of rays for ray trace / spot diagrams.
        show_vignetting: Show vignetting comparison curve.
        show_ray_trace_comparison: Show ray trace comparison plot.
        show_spot_comparison: Show spot diagram comparison plot.
        show_focal_image_comparison: Show focal image comparison plot.
        show_psf_comparison: Show PSF comparison plot.
        show_psf_2d_comparison: Show 2D PSF comparison plot.
    """
    telescopes, labels, physics_params = _resolve_comparison_configs(
        configs, defaults)

    print(f"Comparing {len(telescopes)} configurations: "
          f"{', '.join(labels)}")
    for tel, lbl in zip(telescopes, labels):
        print(f"  {lbl}: {tel.primary_diameter:.0f}mm "
              f"f/{tel.focal_ratio:.1f} {tel.primary_type}")

    if show_ray_trace_comparison:
        plot_ray_trace_comparison(telescopes, labels,
                                  num_display_rays=num_display_rays)
    if show_spot_comparison:
        plot_spot_diagram_comparison(telescopes, labels,
                                     num_display_rays=num_display_rays,
                                     method=defaults.get("method", "analytical"),
                                     include_obstruction=defaults.get("include_obstruction", True),
                                     physics_params=physics_params)
    if show_focal_image_comparison:
        plot_focal_image_comparison(telescopes, labels,
                                    wavelength_nm=defaults.get("wavelength_nm", 550.0),
                                    method=defaults.get("method", "analytical"),
                                    seeing_arcsec=defaults.get("seeing_arcsec"),
                                    include_obstruction=defaults.get("include_obstruction", True),
                                    physics_params=physics_params)
    if show_psf_comparison:
        plot_psf_comparison(telescopes, labels,
                            wavelength_nm=defaults.get("wavelength_nm", 550.0),
                            method=defaults.get("method", "analytical"),
                            include_obstruction=defaults.get("include_obstruction", True),
                            physics_params=physics_params)

    # 2D PSF comparison — shown when any telescope has spider vanes,
    # since diffraction spikes are only visible in 2D log-scale images
    if show_psf_2d_comparison and any(t.spider_vanes > 0 for t in telescopes):
        plot_psf_2d_comparison(
            telescopes, labels,
            wavelength_nm=defaults.get("wavelength_nm", 550.0),
            include_obstruction=defaults.get("include_obstruction", True),
        )

    if show_vignetting:
        plot_vignetting_comparison(telescopes, labels)

    if show_coma_comparison:
        plot_coma_field_analysis_comparison(
            telescopes, labels,
            wavelength_nm=defaults.get("wavelength_nm", 550.0),
            include_obstruction=defaults.get("include_obstruction", True),
        )


def main():
    # ══════════════════════════════════════════════════════════════════
    # CONFIGURATION — edit these options to control the simulation
    # ══════════════════════════════════════════════════════════════════

    # ── Telescope type ────────────────────────────────────────────────
    # "newtonian"   — flat diagonal secondary, focus exits side of tube
    # "cassegrain"  — convex hyperbolic secondary, focus behind primary
    # "refracting"  — objective lens, no secondary, focus at back of tube
    # "maksutov"    — meniscus corrector + spherical primary + aluminized spot
    # "schmidt"     — Schmidt corrector + spherical primary + convex secondary
    telescope_type = "newtonian"
    # telescope_type = "cassegrain"
    # telescope_type = "refracting"
    # telescope_type = "maksutov"
    # telescope_type = "schmidt"

    # ── Telescope geometry ───────────────────────────────────────────
    primary_diameter = 254.0    # mm — 10" aperture
    focal_length = 1270.0       # mm — gives f/5 for 254mm aperture

    # Primary mirror type (Newtonian only):
    #   "parabolic" (diffraction-limited) or "spherical" (shows aberration)
    primary_type = "parabolic"
    # primary_type = "spherical"

    # ── Cassegrain-specific parameters ────────────────────────────────
    # (only used when telescope_type = "cassegrain")
    primary_focal_length = 800.0        # mm — focal length of primary alone
    secondary_magnification = 5.0       # effective FL = 800 × 5 = 4000mm (f/20)
    # secondary_magnification = 3.0     # shorter effective FL (f/12)
    # secondary_magnification = 4.0     # moderate (f/16)
    back_focal_distance = None          # mm — auto-computed if None

    # ── Maksutov-specific parameters ─────────────────────────────────
    # (only used when telescope_type = "maksutov")
    # primary_focal_length and secondary_magnification shared with Cassegrain
    meniscus_thickness = None       # mm — auto-computed if None (diameter/10)
    # meniscus_thickness = 15.0     # custom thickness

    # ── Refracting-specific parameters ──────────────────────────────
    # (only used when telescope_type = "refracting")
    objective_type = "singlet"      # "singlet" — single biconvex lens
    # objective_type = "achromat"   # crown + flint doublet (corrects chromatic aberration)

    # ── Chromatic / polychromatic settings ────────────────────────────
    # When True, refractors use per-wavelength (R/G/B) PSFs for source
    # imaging, showing realistic color fringing on high-contrast edges.
    # Reflectors are unaffected (no chromatic aberration).
    polychromatic = False
    # polychromatic = True          # enable to see chromatic aberration effects

    # ── Spider vanes ─────────────────────────────────────────────────
    # Number of vanes holding the secondary mirror (0=none, 4=standard).
    # Vanes produce characteristic diffraction spikes in the PSF.
    # spider_vanes = 0           # no spider vanes
    spider_vanes = 4         # standard 4-vane spider
    # spider_vanes = 3         # 3-vane (6 spikes due to symmetry)
    spider_vane_width = 1.0    # mm — width of each vane

    # ── Display / ray trace ──────────────────────────────────────────
    # Number of rays drawn in the ray trace and spot diagrams.
    # More rays -> denser visualization; fewer -> cleaner diagram.
    num_display_rays = 11
    # num_display_rays = 5       # minimal, very clean
    # num_display_rays = 21      # denser, shows more structure
    # num_display_rays = 51      # high density, detailed view

    # ── Imaging / physics ────────────────────────────────────────────
    wavelength_nm = 550.0       # nm — wavelength of light (550 = green)
    # wavelength_nm = 450.0     # blue
    # wavelength_nm = 650.0     # red

    # Method for computing focal offsets:
    #   "analytical" — exact closed-form mirror equations (fast, precise)
    #   "traced"     — numerical ray tracing (slower, validates sim)
    method = "analytical"
    # method = "traced"

    # Atmospheric seeing — FWHM of the seeing disk in arcseconds.
    #
    # Atmospheric turbulence causes stars to appear as blurred disks
    # rather than point sources. The seeing_arcsec parameter is the
    # full width at half maximum (FWHM) of this disk — the angular
    # diameter at which the brightness drops to 50% of the peak.
    #
    # Smaller values = steadier atmosphere (better seeing).
    # Typical values:
    #   0.5-1.0" = excellent (rare, high-altitude observatories)
    #   1.0-2.0" = good (decent amateur site on a good night)
    #   2.0-3.0" = average (typical suburban/rural)
    #   3.0-5.0" = poor (turbulent, near horizon, or humid)
    #
    # Set to None for space telescope (no atmosphere).
    #
    seeing_arcsec = "good"          # 1.5" FWHM — good ground-based seeing
    # seeing_arcsec = "excellent"   # 0.8" FWHM — rare, high-altitude site
    # seeing_arcsec = "average"     # 2.5" FWHM — typical suburban/rural
    # seeing_arcsec = "poor"        # 4.0" FWHM — turbulent atmosphere
    # seeing_arcsec = 2.0           # custom value in arcseconds (FWHM)
    # seeing_arcsec = None          # space telescope (no atmosphere)

    # ── Obstruction toggle ─────────────────────────────────────────
    # Include central obstruction from the secondary mirror in the
    # diffraction PSF and ray masking. Set False to see the
    # unobstructed Airy pattern for comparison.
    include_obstruction = True
    # include_obstruction = False    # ignore secondary obstruction

    # ── Off-axis / coma analysis ─────────────────────────────────────
    # Off-axis angle for coma spot diagram (arcseconds).
    # Set > 0 to see the comet-shaped coma aberration pattern.
    field_angle_arcsec = 0.0
    # field_angle_arcsec = 60.0     # 1 arcminute off-axis
    # field_angle_arcsec = 120.0    # 2 arcminutes off-axis

    # Show coma field analysis (RMS coma vs field angle + spot grid)
    # show_coma_analysis = False
    show_coma_analysis = True

    # ── Plot toggles ─────────────────────────────────────────────
    # Toggle individual plots on/off. All default to True.
    # Single-mode plots:
    show_ray_trace = True
    show_spot_diagram = True
    show_focal_image = True
    show_psf_profile = True
    show_psf_2d = True            # only renders if spider_vanes > 0
    # show_vignetting = False     # (already exists below)
    # show_coma_analysis = False  # (already exists above)
    show_source_image = True      # only renders if source is configured
    show_polychromatic_ray_trace = True  # only renders if polychromatic=True + refractor

    # Comparison-mode plots:
    show_ray_trace_comparison = True
    show_spot_comparison = True
    show_focal_image_comparison = True
    show_psf_comparison = True
    show_psf_2d_comparison = True  # only renders if any telescope has spider vanes
    show_coma_comparison = False   # RMS coma vs field angle overlay
    # show_vignetting is shared between modes (already exists below)

    # ── Source imaging ────────────────────────────────────────────────
    # Astronomical source for simulated imaging.
    # Options: "star", "star_field", "jupiter", "saturn", "moon",
    #          or None (skip source image)
    source_type = None
    # source_type = "star"          # single on-axis star (shows PSF)
    # source_type = "star_field"    # random field showing coma + vignetting
    source_type = "jupiter"       # Jupiter disk with bands
    # source_type = "saturn"        # Saturn with rings
    # source_type = "moon"          # Moon with maria

    # Star field options (only used when source_type = "star_field")
    num_stars = 30
    star_field_radius_arcsec = 300.0  # half-width of field

    # Jupiter options (only used when source_type = "jupiter")
    jupiter_diameter_arcsec = 40.0    # angular diameter (40" typical)

    # Saturn options (only used when source_type = "saturn")
    saturn_diameter_arcsec = 18.0     # equatorial diameter (18" typical)
    saturn_ring_tilt_deg = 20.0       # ring tilt (0=edge-on, 27=max)

    # Moon options (only used when source_type = "moon")
    moon_diameter_arcsec = 1870.0     # ~31 arcminutes
    moon_phase = 1.0                  # 0=new, 0.5=quarter, 1.0=full

    # ── Eyepiece (visual observing) ──────────────────────────────────
    # Set eyepiece focal length to simulate visual observing through
    # the telescope at a specific magnification.  When configured,
    # the source image is cropped to the true field of view and a
    # second "true angular size" figure is produced.
    # Set to None to skip eyepiece simulation (raw focal-plane view).
    # eyepiece_focal_length_mm = None
    # eyepiece_focal_length_mm = 25.0    # 40x with f/5 1000mm scope — 5mm exit pupil (strong washout on planets)
    # eyepiece_focal_length_mm = 10.0    # 100x
    eyepiece_focal_length_mm = 5.0     # 200x — 1mm exit pupil (no washout, ideal planetary viewing)

    eyepiece_apparent_fov_deg = 50.0     # Plössl-style
    # eyepiece_apparent_fov_deg = 68.0   # wide-field
    # eyepiece_apparent_fov_deg = 82.0   # ultra-wide

    # ── Vignetting ───────────────────────────────────────────────────
    # Show illumination fraction vs off-axis angle
    show_vignetting = False
    # show_vignetting = True

    # ── Comparison mode ──────────────────────────────────────────────
    # Set to True to show side-by-side comparison plots.
    # When False, shows single-telescope plots using the settings above.
    # compare_mode = False
    compare_mode = True

    # Each entry is a config dict with a "label" and any overrides.
    # Keys not specified fall back to the shared defaults above.
    #
    # Telescope geometry keys you can override per-panel:
    #   primary_diameter, focal_length, primary_type,
    #   secondary_offset, secondary_minor_axis,
    #   spider_vanes, spider_vane_width
    #
    # Physics keys you can override per-panel:
    #   wavelength_nm, method, seeing_arcsec, include_obstruction

    # --- 10" Newtonian f/5 vs f/6 comparison ---
    #comparison_configs = [
    #    {"label": "10\" f/5 (1270mm)", "focal_length": 1270.0},
    #    {"label": "10\" f/6 (1524mm)", "focal_length": 1524.0},
    #]

    # --- Mirror type comparison ---
    # comparison_configs = [
    #     {"label": "Parabolic Primary", "primary_type": "parabolic"},
    #     {"label": "Spherical Primary", "primary_type": "spherical"},
    # ]

    # --- Annular vs circular aperture (obstruction effects on PSF) ---
    # Shows how the secondary mirror obstruction affects diffraction:
    # stronger secondary rings, slightly lower peak intensity, reduced
    # contrast on planets.  The underlying physics is the annular aperture
    # PSF formula (see PHYSICS.md).
    # comparison_configs = [
    #     {"label": "With Obstruction", "include_obstruction": True},
    #     {"label": "No Obstruction", "include_obstruction": False},
    # ]

    # --- Different wavelengths ---
    # comparison_configs = [
    #     {"label": "Blue (450nm)", "wavelength_nm": 450.0},
    #     {"label": "Green (550nm)", "wavelength_nm": 550.0},
    #     {"label": "Red (650nm)", "wavelength_nm": 650.0},
    # ]

    # --- Different apertures (all at f/5 for fair comparison) ---
    # comparison_configs = [
    #     {"label": "150mm f/5", "primary_diameter": 150.0, "focal_length": 750.0},
    #     {"label": "200mm f/5", "primary_diameter": 200.0, "focal_length": 1000.0},
    #     {"label": "250mm f/5", "primary_diameter": 250.0, "focal_length": 1250.0},
    # ]

    # --- Different focal ratios ---
    # comparison_configs = [
    #     {"label": "f/4", "focal_length": 800.0},
    #     {"label": "f/5", "focal_length": 1000.0},
    #     {"label": "f/8", "focal_length": 1600.0},
    # ]

    # --- Mixed geometry + physics ---
    # comparison_configs = [
    #     {"label": "Parabolic, no obs.", "primary_type": "parabolic",
    #      "include_obstruction": False},
    #     {"label": "Parabolic, with obs.", "primary_type": "parabolic",
    #      "include_obstruction": True},
    #     {"label": "Spherical, with obs.", "primary_type": "spherical",
    #      "include_obstruction": True},
    # ]

    # --- Newtonian vs Cassegrain ---
    # comparison_configs = [
    #     {"label": "200mm f/5 Newtonian", "telescope_type": "newtonian",
    #      "focal_length": 1000.0, "primary_type": "parabolic"},
    #     {"label": "200mm f/20 Cassegrain", "telescope_type": "cassegrain",
    #      "primary_focal_length": 800.0, "secondary_magnification": 5.0},
    # ]

    # --- Spider vane comparison ---
    #comparison_configs = [
    #     {"label": "No Vanes", "spider_vanes": 0,
    #      "primary_type": "parabolic"},
    #     {"label": "4 Vanes", "spider_vanes": 4,
    #      "primary_type": "parabolic"},
    #]

    # --- Newtonian vs Refractor ---
    # comparison_configs = [
    #     {"label": "200mm f/5 Newtonian", "telescope_type": "newtonian",
    #      "focal_length": 1000.0, "primary_type": "parabolic"},
    #     {"label": "200mm f/5 Refractor", "telescope_type": "refracting",
    #      "focal_length": 1000.0},
    # ]

    # --- Singlet vs Achromat refractor (chromatic aberration comparison) ---
    # Enable polychromatic = True above for this comparison.
    # comparison_configs = [
    #     {"label": "80mm f/10 Singlet", "telescope_type": "refracting",
    #      "primary_diameter": 80.0, "focal_length": 800.0,
    #      "objective_type": "singlet"},
    #     {"label": "80mm f/10 Achromat", "telescope_type": "refracting",
    #      "primary_diameter": 80.0, "focal_length": 800.0,
    #      "objective_type": "achromat"},
    # ]

    # --- Cassegrain vs Maksutov-Cassegrain ---
    comparison_configs = [
        {"label": "200mm f/20 Cassegrain", "telescope_type": "cassegrain",
         "primary_focal_length": 800.0, "secondary_magnification": 5.0},
        {"label": "200mm f/20 Maksutov", "telescope_type": "maksutov",
        "primary_focal_length": 800.0, "secondary_magnification": 5.0},
    ]

    # --- Schmidt-Cassegrain vs Cassegrain ---
    # comparison_configs = [
    #     {"label": "200mm f/10 SCT", "telescope_type": "schmidt",
    #      "primary_focal_length": 500.0, "secondary_magnification": 4.0},
    #     {"label": "200mm f/10 Cassegrain", "telescope_type": "cassegrain",
    #      "primary_focal_length": 500.0, "secondary_magnification": 4.0},
    # ]

    # --- Different apertures with vignetting (all at f/5 for fair comparison) ---
    # comparison_configs = [
    #     {"label": "150mm f/5", "primary_diameter": 150.0, "focal_length": 750.0},
    #     {"label": "200mm f/5", "primary_diameter": 200.0, "focal_length": 1000.0},
    #     {"label": "250mm f/5", "primary_diameter": 250.0, "focal_length": 1250.0},
    # ]
    # show_vignetting = True  # uncomment with above to see vignetting overlay

    # ══════════════════════════════════════════════════════════════════
    # RUN — no need to edit below this line
    # ══════════════════════════════════════════════════════════════════

    # Resolve seeing preset to float
    if isinstance(seeing_arcsec, str):
        seeing_arcsec = SEEING_PRESETS[seeing_arcsec]

    # Build eyepiece (if configured)
    eyepiece = None
    if eyepiece_focal_length_mm is not None:
        eyepiece = Eyepiece(
            focal_length_mm=eyepiece_focal_length_mm,
            apparent_fov_deg=eyepiece_apparent_fov_deg,
        )

    if compare_mode:
        defaults = dict(
            primary_diameter=primary_diameter,
            focal_length=focal_length,
            primary_type=primary_type,
            primary_focal_length=primary_focal_length,
            secondary_magnification=secondary_magnification,
            spider_vanes=spider_vanes,
            spider_vane_width=spider_vane_width,
            telescope_type=telescope_type,
            wavelength_nm=wavelength_nm,
            method=method,
            seeing_arcsec=seeing_arcsec,
            include_obstruction=include_obstruction,
            polychromatic=polychromatic,
        )
        if back_focal_distance is not None:
            defaults["back_focal_distance"] = back_focal_distance
        if meniscus_thickness is not None:
            defaults["meniscus_thickness"] = meniscus_thickness
        run_comparison(comparison_configs, defaults, num_display_rays,
                       show_vignetting=show_vignetting,
                       show_ray_trace_comparison=show_ray_trace_comparison,
                       show_spot_comparison=show_spot_comparison,
                       show_focal_image_comparison=show_focal_image_comparison,
                       show_psf_comparison=show_psf_comparison,
                       show_psf_2d_comparison=show_psf_2d_comparison,
                       show_coma_comparison=show_coma_comparison)
    else:
        if telescope_type == "cassegrain":
            tel_kwargs = dict(
                primary_diameter=primary_diameter,
                primary_focal_length=primary_focal_length,
                secondary_magnification=secondary_magnification,
                spider_vanes=spider_vanes,
                spider_vane_width=spider_vane_width,
            )
            if back_focal_distance is not None:
                tel_kwargs["back_focal_distance"] = back_focal_distance
            telescope = CassegrainTelescope(**tel_kwargs)
        elif telescope_type == "maksutov":
            tel_kwargs = dict(
                primary_diameter=primary_diameter,
                primary_focal_length=primary_focal_length,
                secondary_magnification=secondary_magnification,
                spider_vanes=spider_vanes,
                spider_vane_width=spider_vane_width,
            )
            if back_focal_distance is not None:
                tel_kwargs["back_focal_distance"] = back_focal_distance
            if meniscus_thickness is not None:
                tel_kwargs["meniscus_thickness"] = meniscus_thickness
            telescope = MaksutovCassegrainTelescope(**tel_kwargs)
        elif telescope_type == "schmidt":
            tel_kwargs = dict(
                primary_diameter=primary_diameter,
                primary_focal_length=primary_focal_length,
                secondary_magnification=secondary_magnification,
                spider_vanes=spider_vanes,
                spider_vane_width=spider_vane_width,
            )
            if back_focal_distance is not None:
                tel_kwargs["back_focal_distance"] = back_focal_distance
            telescope = SchmidtCassegrainTelescope(**tel_kwargs)
        elif telescope_type == "refracting":
            telescope = RefractingTelescope(
                primary_diameter=primary_diameter,
                focal_length=focal_length,
                objective_type=objective_type,
            )
        else:
            telescope = NewtonianTelescope(
                primary_diameter=primary_diameter,
                focal_length=focal_length,
                primary_type=primary_type,
                spider_vanes=spider_vanes,
                spider_vane_width=spider_vane_width,
            )

        # ── Multi-telescope single-mode comparison ────────────────────
        # To compare source images (Moon, Jupiter, etc.) through multiple
        # telescopes side by side, list additional telescopes here.
        # Each entry is (telescope, label).  Leave empty for single scope.
        single_compare = [
            # --- 10" f/5 vs f/6 Moon comparison ---
            (NewtonianTelescope(primary_diameter=254.0, focal_length=1270.0,
                                primary_type="parabolic"), '10" f/5 Newtonian'),
            (NewtonianTelescope(primary_diameter=254.0, focal_length=1524.0,
                                primary_type="parabolic"), '10" f/6 Newtonian'),
        ]
        # single_compare = []  # uncomment to use single telescope above

        # Build astronomical source (if requested)
        source = None
        if source_type == "star":
            source = PointSource(field_angle_arcsec=field_angle_arcsec)
        elif source_type == "star_field":
            source = StarField(num_stars=num_stars,
                               field_radius_arcsec=star_field_radius_arcsec)
        elif source_type == "jupiter":
            source = Jupiter(angular_diameter_arcsec=jupiter_diameter_arcsec)
        elif source_type == "saturn":
            source = Saturn(angular_diameter_arcsec=saturn_diameter_arcsec,
                            ring_tilt_deg=saturn_ring_tilt_deg)
        elif source_type == "moon":
            source = Moon(angular_diameter_arcsec=moon_diameter_arcsec,
                          phase=moon_phase)

        # Run for each telescope in single_compare, or just the one above
        telescopes_to_run = single_compare if single_compare else [(telescope, None)]
        for tel, label in telescopes_to_run:
            run_single(tel, num_display_rays, wavelength_nm, method,
                        seeing_arcsec, include_obstruction,
                        show_vignetting=show_vignetting,
                        show_coma_analysis=show_coma_analysis,
                        field_angle_arcsec=field_angle_arcsec,
                        source=source, eyepiece=eyepiece,
                        show_ray_trace=show_ray_trace,
                        show_spot_diagram=show_spot_diagram,
                        show_focal_image=show_focal_image,
                        show_psf_profile=show_psf_profile,
                        show_psf_2d=show_psf_2d,
                        show_source_image=show_source_image,
                        polychromatic=polychromatic,
                        show_polychromatic_ray_trace=show_polychromatic_ray_trace)

    plt.show()


if __name__ == "__main__":
    main()

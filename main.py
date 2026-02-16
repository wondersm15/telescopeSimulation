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

from telescope_sim.geometry import NewtonianTelescope
from telescope_sim.source import create_parallel_rays
from telescope_sim.plotting import (
    plot_focal_image,
    plot_focal_image_comparison,
    plot_psf_comparison,
    plot_psf_profile,
    plot_ray_trace,
    plot_ray_trace_comparison,
    plot_spot_diagram,
    plot_spot_diagram_comparison,
)

# Keys that NewtonianTelescope.__init__() accepts
_TELESCOPE_KEYS = {
    "primary_diameter", "focal_length", "secondary_offset",
    "secondary_minor_axis", "primary_type",
}

# Keys that control per-panel physics in comparison mode
_PHYSICS_KEYS = {
    "wavelength_nm", "method", "seeing_arcsec", "include_obstruction",
}

# Every key that a comparison config dict may contain
_ALLOWED_CONFIG_KEYS = _TELESCOPE_KEYS | _PHYSICS_KEYS | {"label"}


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

        # Build telescope from geometry keys + defaults
        tel_kwargs = {}
        for key in _TELESCOPE_KEYS:
            if key in cfg:
                tel_kwargs[key] = cfg[key]
            elif key in defaults:
                tel_kwargs[key] = defaults[key]
        telescopes.append(NewtonianTelescope(**tel_kwargs))

        # Collect per-config physics overrides
        pp = {}
        for key in _PHYSICS_KEYS:
            if key in cfg:
                pp[key] = cfg[key]
        physics_params.append(pp)

    return telescopes, labels, physics_params


def run_single(telescope, num_display_rays, wavelength_nm, method,
               seeing_arcsec, include_obstruction=True):
    """Run all plots for a single telescope configuration."""
    print(f"Telescope: {telescope.primary_diameter}mm "
          f"f/{telescope.focal_ratio:.1f} Newtonian")
    print(f"Primary type: {telescope.primary_type}")
    print(f"Focal length: {telescope.focal_length}mm")
    print(f"Tube length: {telescope.tube_length:.0f}mm")

    rays = create_parallel_rays(
        num_rays=num_display_rays,
        aperture_diameter=telescope.primary_diameter,
        entry_height=telescope.tube_length * 1.15,
    )
    telescope.trace_rays(rays)

    components = telescope.get_components_for_plotting()
    plot_ray_trace(
        rays, components,
        title=(f"{telescope.primary_diameter:.0f}mm f/{telescope.focal_ratio:.1f} "
               f"Newtonian — Ray Trace"),
    )
    plot_spot_diagram(
        rays,
        title=f"Spot Diagram — {telescope.primary_type.title()} Primary",
    )
    plot_focal_image(
        telescope,
        title=f"Simulated Image — {telescope.primary_type.title()} Primary",
        wavelength_nm=wavelength_nm,
        method=method,
        seeing_arcsec=seeing_arcsec,
        include_obstruction=include_obstruction,
    )
    plot_psf_profile(
        telescope,
        title=f"PSF — {telescope.primary_type.title()} Primary",
        wavelength_nm=wavelength_nm,
        method=method,
        include_obstruction=include_obstruction,
    )


def run_comparison(configs, defaults, num_display_rays):
    """Build multiple telescopes from config dicts and produce comparison plots.

    Args:
        configs: List of comparison config dicts (see ``comparison_configs``).
        defaults: Dict of shared default values (geometry + physics).
        num_display_rays: Number of rays for ray trace / spot diagrams.
    """
    telescopes, labels, physics_params = _resolve_comparison_configs(
        configs, defaults)

    print(f"Comparing {len(telescopes)} configurations: "
          f"{', '.join(labels)}")
    for tel, lbl in zip(telescopes, labels):
        print(f"  {lbl}: {tel.primary_diameter:.0f}mm "
              f"f/{tel.focal_ratio:.1f} {tel.primary_type}")

    plot_ray_trace_comparison(telescopes, labels,
                              num_display_rays=num_display_rays)
    plot_spot_diagram_comparison(telescopes, labels,
                                 num_display_rays=num_display_rays)
    plot_focal_image_comparison(telescopes, labels,
                                wavelength_nm=defaults.get("wavelength_nm", 550.0),
                                method=defaults.get("method", "analytical"),
                                seeing_arcsec=defaults.get("seeing_arcsec"),
                                include_obstruction=defaults.get("include_obstruction", True),
                                physics_params=physics_params)
    plot_psf_comparison(telescopes, labels,
                        wavelength_nm=defaults.get("wavelength_nm", 550.0),
                        method=defaults.get("method", "analytical"),
                        include_obstruction=defaults.get("include_obstruction", True),
                        physics_params=physics_params)


def main():
    # ══════════════════════════════════════════════════════════════════
    # CONFIGURATION — edit these options to control the simulation
    # ══════════════════════════════════════════════════════════════════

    # ── Telescope geometry ───────────────────────────────────────────
    primary_diameter = 200.0    # mm — aperture of the primary mirror
    focal_length = 1000.0       # mm — gives f/5 for 200mm aperture

    # Primary mirror type: "parabolic" (diffraction-limited) or
    #                      "spherical" (shows aberration)
    primary_type = "spherical"
    # primary_type = "parabolic"

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

    # Atmospheric seeing — set to None for no atmosphere (space view),
    # or a value in arcseconds for ground-based seeing simulation.
    seeing_arcsec = None
    # seeing_arcsec = 1.0       # typical good seeing
    # seeing_arcsec = 2.0       # average seeing
    # seeing_arcsec = 4.0       # poor seeing

    # ── Obstruction toggle ─────────────────────────────────────────
    # Include central obstruction from the secondary mirror in the
    # diffraction PSF and ray masking. Set False to see the
    # unobstructed Airy pattern for comparison.
    include_obstruction = True
    # include_obstruction = False    # ignore secondary obstruction

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
    #   secondary_offset, secondary_minor_axis
    #
    # Physics keys you can override per-panel:
    #   wavelength_nm, method, seeing_arcsec, include_obstruction

    # --- Mirror type comparison (default) ---
    comparison_configs = [
        {"label": "Parabolic Primary", "primary_type": "parabolic"},
        {"label": "Spherical Primary", "primary_type": "spherical"},
    ]

    # --- Obstruction toggle ---
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

    # --- Different apertures ---
    # comparison_configs = [
    #     {"label": "150mm f/6.7", "primary_diameter": 150.0},
    #     {"label": "200mm f/5.0", "primary_diameter": 200.0},
    #     {"label": "250mm f/4.0", "primary_diameter": 250.0},
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

    # ══════════════════════════════════════════════════════════════════
    # RUN — no need to edit below this line
    # ══════════════════════════════════════════════════════════════════

    if compare_mode:
        defaults = dict(
            primary_diameter=primary_diameter,
            focal_length=focal_length,
            primary_type=primary_type,
            wavelength_nm=wavelength_nm,
            method=method,
            seeing_arcsec=seeing_arcsec,
            include_obstruction=include_obstruction,
        )
        run_comparison(comparison_configs, defaults, num_display_rays)
    else:
        telescope = NewtonianTelescope(
            primary_diameter=primary_diameter,
            focal_length=focal_length,
            primary_type=primary_type,
        )
        run_single(telescope, num_display_rays, wavelength_nm, method,
                    seeing_arcsec, include_obstruction)

    plt.show()


if __name__ == "__main__":
    main()

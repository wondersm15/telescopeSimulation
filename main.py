"""Trace rays through a Newtonian reflector telescope.

This demonstrates the telescope simulation by:
1. Defining a Newtonian telescope geometry
2. Creating parallel rays (point source at infinity)
3. Tracing rays through the optical system
4. Plotting ray traces, spot diagrams, focal images, and PSFs

Toggle `compare_mirrors` below to switch between single-telescope
mode and side-by-side mirror type comparison mode.
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


def run_single(telescope, num_display_rays, wavelength_nm, method,
               seeing_arcsec):
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
    )
    plot_psf_profile(
        telescope,
        title=f"PSF — {telescope.primary_type.title()} Primary",
        wavelength_nm=wavelength_nm,
        method=method,
    )


def run_comparison(primary_diameter, focal_length, compare_types,
                   num_display_rays, wavelength_nm, method,
                   seeing_arcsec):
    """Build multiple telescopes and produce side-by-side comparison plots."""
    telescopes = []
    labels = []
    for ptype in compare_types:
        t = NewtonianTelescope(
            primary_diameter=primary_diameter,
            focal_length=focal_length,
            primary_type=ptype,
        )
        telescopes.append(t)
        labels.append(f"{ptype.title()} Primary")

    print(f"Comparing {len(telescopes)} configurations: "
          f"{', '.join(labels)}")
    print(f"Aperture: {primary_diameter:.0f}mm  "
          f"f/{focal_length / primary_diameter:.1f}  "
          f"FL: {focal_length:.0f}mm")

    plot_ray_trace_comparison(telescopes, labels,
                              num_display_rays=num_display_rays)
    plot_spot_diagram_comparison(telescopes, labels,
                                 num_display_rays=num_display_rays)
    plot_focal_image_comparison(telescopes, labels,
                                wavelength_nm=wavelength_nm,
                                method=method,
                                seeing_arcsec=seeing_arcsec)
    plot_psf_comparison(telescopes, labels,
                        wavelength_nm=wavelength_nm,
                        method=method)


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
    # More rays → denser visualization; fewer → cleaner diagram.
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

    # ── Comparison mode ──────────────────────────────────────────────
    # Set to True to show side-by-side comparison of mirror types
    # instead of the single-telescope plots.
    #compare_mirrors = False
    compare_mirrors = True

    # Mirror types to compare (used only when compare_mirrors = True)
    compare_types = ["parabolic", "spherical"]

    # ══════════════════════════════════════════════════════════════════
    # RUN — no need to edit below this line
    # ══════════════════════════════════════════════════════════════════

    if compare_mirrors:
        run_comparison(
            primary_diameter, focal_length, compare_types,
            num_display_rays, wavelength_nm, method, seeing_arcsec,
        )
    else:
        telescope = NewtonianTelescope(
            primary_diameter=primary_diameter,
            focal_length=focal_length,
            primary_type=primary_type,
        )
        run_single(telescope, num_display_rays, wavelength_nm, method,
                    seeing_arcsec)

    plt.show()


if __name__ == "__main__":
    main()

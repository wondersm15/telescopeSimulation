"""Trace rays through a Newtonian reflector telescope.

This demonstrates the v0.1 telescope simulation by:
1. Defining a Newtonian telescope geometry
2. Creating parallel rays (point source at infinity)
3. Tracing rays through the optical system
4. Plotting a 2D side-view ray trace diagram
"""

import matplotlib.pyplot as plt

from telescope_sim.geometry import NewtonianTelescope
from telescope_sim.source import create_parallel_rays
from telescope_sim.plotting import (
    plot_focal_image,
    plot_psf_profile,
    plot_ray_trace,
    plot_spot_diagram,
)


def main():
    # --- Define the telescope ---
    # A 200mm f/5 Newtonian reflector
    telescope = NewtonianTelescope(
        primary_diameter=200.0,   # mm
        focal_length=1000.0,      # mm (f/5)
        primary_type = "spherical"
    )


    print(f"Telescope: {telescope.primary_diameter}mm "
          f"f/{telescope.focal_ratio:.1f} Newtonian")
    print(f"Primary type: {telescope.primary_type}")
    print(f"Focal length: {telescope.focal_length}mm")
    print(f"Tube length: {telescope.tube_length:.0f}mm")

    # --- Create incoming light ---
    # Few rays for clean ray trace visualization
    rays = create_parallel_rays(
        num_rays=11,
        aperture_diameter=telescope.primary_diameter,
        entry_height=telescope.tube_length * 1.15,
    )

    # --- Trace rays through the telescope ---
    telescope.trace_rays(rays)

    # --- Visualize ---
    # Ray trace and spot diagram use the visual rays
    components = telescope.get_components_for_plotting()
    plot_ray_trace(
        rays, components,
        title="200mm f/5 Newtonian Reflector — Ray Trace",
    )
    plot_spot_diagram(
        rays,
        title=f"Spot Diagram — {telescope.primary_type.title()} Primary",
    )
    # Focal image and PSF trace their own dense rays internally
    plot_focal_image(
        telescope,
        title=f"Simulated Image — {telescope.primary_type.title()} Primary",
    )
    plot_psf_profile(
        telescope,
        title=f"PSF — {telescope.primary_type.title()} Primary",
    )
    plt.show()


if __name__ == "__main__":
    main()

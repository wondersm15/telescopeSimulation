"""Plotting module: visualization of ray traces and optical systems."""

from telescope_sim.plotting.ray_trace_plot import (
    plot_focal_image,
    plot_focal_image_comparison,
    plot_psf_comparison,
    plot_psf_profile,
    plot_ray_trace,
    plot_ray_trace_comparison,
    plot_spot_diagram,
    plot_spot_diagram_comparison,
)

__all__ = [
    "plot_focal_image",
    "plot_focal_image_comparison",
    "plot_psf_comparison",
    "plot_psf_profile",
    "plot_ray_trace",
    "plot_ray_trace_comparison",
    "plot_spot_diagram",
    "plot_spot_diagram_comparison",
]

"""2D side-view ray trace visualization."""

import numpy as np
import matplotlib.pyplot as plt

from telescope_sim.physics.ray import Ray


def plot_ray_trace(rays: list[Ray], components: dict,
                   title: str = "Newtonian Telescope Ray Trace",
                   figsize: tuple[float, float] = (14, 8),
                   ray_color: str = "gold",
                   ray_alpha: float = 0.7,
                   mirror_color: str = "steelblue",
                   mirror_linewidth: float = 3.0,
                   show_tube: bool = True,
                   save_path: str | None = None) -> plt.Figure:
    """Plot a 2D side-view ray trace diagram.

    Args:
        rays: List of traced Ray objects (with populated history).
        components: Dictionary from
                    NewtonianTelescope.get_components_for_plotting().
        title: Plot title.
        figsize: Figure size in inches.
        ray_color: Color for ray lines.
        ray_alpha: Transparency for ray lines.
        mirror_color: Color for mirror surfaces.
        mirror_linewidth: Line width for mirrors.
        show_tube: Whether to draw the telescope tube outline.
        save_path: If provided, save the figure to this path.

    Returns:
        The matplotlib Figure object.
    """
    fig, ax = plt.subplots(1, 1, figsize=figsize)

    # Draw telescope tube
    if show_tube:
        _draw_tube(ax, components)

    # Draw primary mirror
    primary_pts = components["primary_surface"]
    ax.plot(primary_pts[:, 0], primary_pts[:, 1],
            color=mirror_color, linewidth=mirror_linewidth,
            solid_capstyle="round", label="Primary mirror")

    # Draw secondary mirror
    secondary_pts = components["secondary_surface"]
    ax.plot(secondary_pts[:, 0], secondary_pts[:, 1],
            color="firebrick", linewidth=mirror_linewidth,
            solid_capstyle="round", label="Secondary mirror")

    # Draw rays
    for ray in rays:
        if len(ray.history) < 2:
            continue
        path = np.array(ray.history)
        ax.plot(path[:, 0], path[:, 1],
                color=ray_color, alpha=ray_alpha, linewidth=1.0)

    # Mark focal area (average end-point of fully traced rays)
    end_points = [ray.history[-1] for ray in rays if len(ray.history) >= 3]
    if end_points:
        focal_area = np.mean(end_points, axis=0)
        ax.plot(focal_area[0], focal_area[1], "r*", markersize=12,
                label="Focal point", zorder=5)

    # Formatting
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title(title)
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_spot_diagram(rays: list[Ray],
                      title: str = "Spot Diagram at Focal Plane",
                      figsize: tuple[float, float] = (7, 7),
                      save_path: str | None = None) -> plt.Figure:
    """Plot a spot diagram showing where rays converge at the focal plane.

    After tracing, each ray's final segment (post-secondary) travels
    toward the focal area. This function finds the focal plane position
    where the rays are most concentrated and plots their crossing points.

    Args:
        rays: List of fully traced Ray objects (with populated history).
        title: Plot title.
        figsize: Figure size in inches.
        save_path: If provided, save the figure to this path.

    Returns:
        The matplotlib Figure object.
    """
    # Only use rays that completed the full trace (4 history points)
    traced_rays = [r for r in rays if len(r.history) >= 4]
    if not traced_rays:
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_title(title)
        ax.text(0.5, 0.5, "No fully traced rays", ha="center",
                va="center", transform=ax.transAxes)
        return fig

    # Extract the final segment of each ray (secondary → focal area)
    # and find the best focal plane (x-position where y-spread is minimized)
    segments = []
    for ray in traced_rays:
        p_start = np.array(ray.history[-2])
        p_end = np.array(ray.history[-1])
        segments.append((p_start, p_end))

    # Sample x-positions along the final segments to find best focus
    x_min = min(s[0][0] for s in segments)
    x_max = max(s[1][0] for s in segments)
    test_x_positions = np.linspace(x_min, x_max, 200)

    best_x = x_min
    best_spread = float("inf")

    for test_x in test_x_positions:
        y_crossings = []
        for p_start, p_end in segments:
            dx = p_end[0] - p_start[0]
            if abs(dx) < 1e-12:
                continue
            t = (test_x - p_start[0]) / dx
            if 0 <= t <= 1.5:
                y_at_x = p_start[1] + t * (p_end[1] - p_start[1])
                y_crossings.append(y_at_x)
        if len(y_crossings) >= 2:
            spread = np.std(y_crossings)
            if spread < best_spread:
                best_spread = spread
                best_x = test_x

    # Compute ray positions at the best focal plane
    y_positions = []
    for p_start, p_end in segments:
        dx = p_end[0] - p_start[0]
        if abs(dx) < 1e-12:
            continue
        t = (best_x - p_start[0]) / dx
        y_at_x = p_start[1] + t * (p_end[1] - p_start[1])
        y_positions.append(y_at_x)

    y_positions = np.array(y_positions)
    y_center = np.mean(y_positions)
    y_offsets = y_positions - y_center  # Center on zero

    # Spot size metrics
    rms_spot = np.std(y_offsets)
    max_spot = np.max(np.abs(y_offsets))

    # Plot
    fig, ax = plt.subplots(figsize=figsize)

    # Plot ray crossing points
    ax.scatter(y_offsets, np.zeros_like(y_offsets), c="gold",
               edgecolors="darkorange", s=80, zorder=3, label="Ray positions")

    # Draw the focal plane line
    margin = max(max_spot * 3, 0.5)
    ax.axhline(0, color="gray", linewidth=0.5, alpha=0.5)
    ax.axvline(0, color="gray", linewidth=0.5, alpha=0.5)

    # Draw a circle showing the RMS spot size
    if rms_spot > 1e-6:
        circle = plt.Circle((0, 0), rms_spot, fill=False,
                             color="red", linestyle="--", linewidth=1.5,
                             label=f"RMS spot: {rms_spot:.3f} mm")
        ax.add_patch(circle)

    ax.set_xlim(-margin, margin)
    ax.set_ylim(-margin, margin)
    ax.set_aspect("equal")
    ax.set_xlabel("Position on focal plane (mm)")
    ax.set_ylabel("Position on focal plane (mm)")
    ax.set_title(title)
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

    # Add spot size text
    ax.text(0.02, 0.02,
            f"RMS spot size: {rms_spot:.4f} mm\n"
            f"Max spread: {max_spot * 2:.4f} mm",
            transform=ax.transAxes, fontsize=10,
            verticalalignment="bottom",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def _draw_tube(ax: plt.Axes, components: dict):
    """Draw a simple rectangular tube outline."""
    half_d = components["primary_diameter"] / 2.0
    tube_len = components["tube_length"]

    # Left wall
    ax.plot([-half_d, -half_d], [0, tube_len * 1.1],
            color="gray", linewidth=1.5, linestyle="--", alpha=0.5)
    # Right wall
    ax.plot([half_d, half_d], [0, tube_len * 1.1],
            color="gray", linewidth=1.5, linestyle="--", alpha=0.5)

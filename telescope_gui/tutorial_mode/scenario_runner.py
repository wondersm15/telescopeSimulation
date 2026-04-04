"""Executes tutorial scenarios: builds telescopes, runs plot functions, computes theory.

This module is the bridge between the scenario registry (data) and the
telescope_sim API (computation). It keeps all simulation logic out of the
UI layer.
"""

from __future__ import annotations

import traceback

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from telescope_gui.telescope_builder import build_telescope
from telescope_gui.tutorial_mode.scenario_registry import (
    ScenarioDefinition, TelescopeConfig, SourceConfig,
)
from telescope_gui.tutorial_mode.theory_computations import (
    THEORY_FUNCTIONS, OVERLAY_FUNCTIONS,
)
from telescope_sim.source.sources import PointSource, DoubleStar, Jupiter, Saturn, StarField


def build_source(config: SourceConfig):
    """Instantiate a source from a SourceConfig."""
    st = config.source_type
    kw = dict(config.kwargs)  # unfreeze the frozen dict
    if st == "PointSource":
        return PointSource(**kw)
    elif st == "DoubleStar":
        return DoubleStar(**kw)
    elif st == "Jupiter":
        return Jupiter(**kw)
    elif st == "Saturn":
        return Saturn(**kw)
    elif st == "StarField":
        return StarField(**kw)
    return PointSource()


def _telescope_kwargs(config: TelescopeConfig) -> dict:
    """Convert a TelescopeConfig to kwargs suitable for build_telescope()."""
    d = {
        "telescope_type": config.telescope_type,
        "diameter": config.diameter,
        "focal_length": config.focal_length,
        "primary_type": config.primary_type,
        "objective_type": config.objective_type,
        "secondary_magnification": config.secondary_magnification,
        "spider_vanes": config.spider_vanes,
        "spider_vane_width": config.spider_vane_width,
        "obstruction_ratio": config.obstruction_ratio,
        "enable_obstruction": config.enable_obstruction,
    }
    if config.meniscus_thickness is not None:
        d["meniscus_thickness"] = config.meniscus_thickness
    return d


def run_scenario_side(
    telescope_config: TelescopeConfig,
    source_config: SourceConfig,
    plot_function_name: str,
    wavelength_nm: float = 550.0,
    seeing_arcsec: float | None = None,
    polychromatic: bool = False,
    apply_coma: bool = True,
    apply_vignetting: bool = True,
    figsize: tuple[float, float] = (5, 5),
) -> tuple[Figure | None, dict, str | None]:
    """Run one side (before or after) of a scenario.

    Returns:
        (figure, info_dict, error_message)
        figure is None and error_message is set if rendering fails.
    """
    try:
        telescope = build_telescope(**_telescope_kwargs(telescope_config))
        source = build_source(source_config)

        fig, info = _call_plot_function(
            plot_function_name, telescope, source,
            wavelength_nm=wavelength_nm,
            seeing_arcsec=seeing_arcsec,
            polychromatic=polychromatic,
            apply_coma=apply_coma,
            apply_vignetting=apply_vignetting,
            figsize=figsize,
        )
        info["telescope"] = telescope
        info["source"] = source
        return fig, info, None

    except Exception:
        return None, {}, traceback.format_exc()


def _call_plot_function(
    name: str,
    telescope,
    source,
    wavelength_nm: float = 550.0,
    seeing_arcsec: float | None = None,
    polychromatic: bool = False,
    apply_coma: bool = True,
    apply_vignetting: bool = True,
    figsize: tuple[float, float] = (5, 5),
) -> tuple[Figure, dict]:
    """Dispatch to the appropriate telescope_sim plot function."""
    from telescope_sim.plotting import (
        plot_source_image, plot_psf_2d, plot_psf_profile,
        plot_coma_field_analysis,
    )
    from telescope_sim.plotting.ray_trace_plot import plot_polychromatic_ray_trace

    if name == "plot_source_image":
        fig = plot_source_image(
            telescope, source,
            wavelength_nm=wavelength_nm,
            seeing_arcsec=seeing_arcsec,
            polychromatic=polychromatic,
            apply_coma=apply_coma,
            apply_vignetting=apply_vignetting,
            figsize=figsize,
        )
        if isinstance(fig, list):
            fig = fig[0]
        return fig, {"plot_function": name}

    elif name == "plot_psf_2d":
        fig = plot_psf_2d(
            telescope,
            wavelength_nm=wavelength_nm,
            include_obstruction=(telescope.obstruction_ratio > 0.0),
            figsize=figsize,
        )
        return fig, {"plot_function": name}

    elif name == "plot_psf_profile":
        fig = plot_psf_profile(
            telescope,
            wavelength_nm=wavelength_nm,
            include_obstruction=(telescope.obstruction_ratio > 0.0),
            figsize=figsize,
        )
        return fig, {"plot_function": name}

    elif name == "plot_coma_field_analysis":
        fig = plot_coma_field_analysis(
            telescope,
            wavelength_nm=wavelength_nm,
            figsize=figsize,
        )
        return fig, {"plot_function": name}

    elif name == "plot_polychromatic_ray_trace":
        fig = plot_polychromatic_ray_trace(telescope, figsize=figsize)
        return fig, {"plot_function": name}

    else:
        raise ValueError(f"Unknown plot function: {name!r}")


def compute_theory_for_scenario(
    scenario: ScenarioDefinition,
    telescope,
    seeing_arcsec: float | None = None,
    wavelength_nm: float = 550.0,
    **extra_kwargs,
) -> dict | None:
    """Run the theory computation for a scenario, if defined.

    Returns a theory dict (see theory_computations.py) or None.
    """
    if scenario.theory_function is None:
        return None
    fn = THEORY_FUNCTIONS.get(scenario.theory_function)
    if fn is None:
        return None
    # Pass extra kwargs that some theory functions need (e.g. seeing_arcsec)
    try:
        import inspect
        sig = inspect.signature(fn)
        kw = {}
        if "wavelength_nm" in sig.parameters:
            kw["wavelength_nm"] = wavelength_nm
        if "seeing_arcsec" in sig.parameters and seeing_arcsec is not None:
            kw["seeing_arcsec"] = seeing_arcsec
        kw.update(extra_kwargs)
        return fn(telescope, **kw)
    except Exception:
        return None


def apply_theory_overlay(
    scenario: ScenarioDefinition,
    fig: Figure,
    theory_result: dict,
) -> None:
    """Draw a theory overlay onto the figure's axes, if applicable.

    Must be called BEFORE MatplotlibCanvas.set_figure() since that rasterizes.
    """
    overlay_fn = OVERLAY_FUNCTIONS.get(scenario.id)
    if overlay_fn is None:
        return
    try:
        # Pass the primary theory value to the overlay function
        overlay_fn(fig, theory_result.get("theory_value", 0.0))
    except Exception:
        pass  # Overlay failure should never crash the main UI


def build_terminal_command(scenario: ScenarioDefinition, params: dict) -> str:
    """Format the scenario's terminal template with the given parameters."""
    if not scenario.terminal_template:
        return f"# No terminal template defined for '{scenario.id}'"
    try:
        return scenario.terminal_template.format(**params)
    except KeyError as e:
        return f"# Template error: missing key {e}\n# Params: {params}"

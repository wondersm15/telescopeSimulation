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
from telescope_sim.geometry.eyepiece import Eyepiece
from telescope_gui.tutorial_mode.scenario_registry import (
    ScenarioDefinition, TelescopeConfig, SourceConfig,
)
from telescope_gui.tutorial_mode.theory_computations import (
    THEORY_FUNCTIONS, OVERLAY_FUNCTIONS,
)
from telescope_sim.source.sources import (
    PointSource, DoubleStar, Jupiter, Saturn, Moon,
    StarField, TutorialStarField, MultiColorStarField,
    StarFieldResolutionField, ComaDemoField, ShowcaseStarField,
    DynamicRangeField,
)


#: Which figure `plot_source_image` returns for each eyepiece view mode.
#: The names match `design_tab`'s `display_mode` so single-telescope mode and
#: the tutorial refer to the same three views by the same words.
_EYEPIECE_VIEW_INDEX = {
    "enhanced": 0,      # analysis view, cropped to TFOV when TFOV < source FOV
    "true_size": 1,     # apparent angular size at a standard viewing distance
    "eyepiece_view": 2,  # circular field stop, source at true relative scale
}


def _select_eyepiece_figure(result, eyepiece_view_mode: str) -> Figure:
    """Pick one figure out of `plot_source_image`'s result and close the rest.

    With an eyepiece, `plot_source_image` returns a LIST of up to three
    figures; without one it returns a bare Figure. The tutorial's
    before/after panel shows a single figure per side, so the others must be
    closed rather than dropped — an unclosed Agg figure stays in matplotlib's
    registry for the life of the process, and the tutorial re-renders on
    every control change (R5.9/S2).

    Falls back to the enhanced view if the requested mode was not built, so a
    scenario asking for a view it did not enable still renders something real
    instead of raising.
    """
    if not isinstance(result, list):
        return result

    idx = _EYEPIECE_VIEW_INDEX.get(eyepiece_view_mode, 0)
    if idx >= len(result):
        idx = 0
    chosen = result[idx]
    for other in result:
        if other is not chosen:
            plt.close(other)
    return chosen


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
    elif st == "TutorialStarField":
        return TutorialStarField(**kw)
    elif st == "MultiColorStarField":
        return MultiColorStarField(**kw)
    elif st == "StarFieldResolutionField":
        return StarFieldResolutionField(**kw)
    elif st == "ShowcaseStarField":
        return ShowcaseStarField(**kw)
    elif st == "DynamicRangeField":
        return DynamicRangeField(**kw)
    elif st == "ComaDemoField":
        return ComaDemoField(**kw)
    elif st == "Moon":
        return Moon(**kw)
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


def build_scenario_telescope(config: TelescopeConfig):
    """Build the telescope a scenario side will actually render through.

    Public because the UI needs the SAME object the render uses: the eyepiece
    combo labels magnification and exit pupil, and both depend on the
    effective focal length, which for a compound scope is not the config's
    `focal_length` field. Reading the config directly would let the label and
    the render disagree (R5.9/S2).
    """
    return build_telescope(**_telescope_kwargs(config))


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
    log_scale: bool | None = None,
    focus_wavelength_nm: float = 550.0,
    display_stretch: str = "linear",
    exposure_level: float = 1.0,
    filter_name: str = "None",
    exit_pupil_mm: float = 7.0,
    peak_reference: float | None = None,
    idealize_sa: bool = False,
    focal_zoom_arcsec: float | None = None,
    coma_view_mode: str = "ray_fan",
    apply_aperture_diffraction: bool = True,
    eyepiece_focal_length_mm: float | None = None,
    eyepiece_afov_deg: float = 50.0,
    eyepiece_field_stop_mm: float | None = None,
    eyepiece_view_mode: str = "eyepiece_view",
) -> tuple[Figure | None, dict, str | None]:
    """Run one side (before or after) of a scenario.

    Returns:
        (figure, info_dict, error_message)
        figure is None and error_message is set if rendering fails.
    """
    try:
        telescope = build_scenario_telescope(telescope_config)
        source = build_source(source_config)

        # R5.9/S2: with a real eyepiece the exit pupil is DERIVED, not chosen.
        # Exit pupil = D / magnification, so letting the eyepiece combo and the
        # exit-pupil combo be set independently would let the tutorial display
        # a pair that no telescope can produce — a 25 mm eyepiece on this scope
        # simply cannot give a 0.5 mm exit pupil. One control, one consistent
        # set of numbers: magnification, true field, apparent size and eye-view
        # surface brightness all follow from the eyepiece.
        eyepiece = None
        if eyepiece_focal_length_mm is not None:
            eyepiece = Eyepiece(
                focal_length_mm=eyepiece_focal_length_mm,
                apparent_fov_deg=eyepiece_afov_deg,
                field_stop_mm=eyepiece_field_stop_mm,
            )
            exit_pupil_mm = eyepiece.exit_pupil_mm(
                telescope.primary_diameter, telescope.focal_length)

        fig, info = _call_plot_function(
            plot_function_name, telescope, source,
            eyepiece=eyepiece,
            eyepiece_view_mode=eyepiece_view_mode,
            wavelength_nm=wavelength_nm,
            seeing_arcsec=seeing_arcsec,
            polychromatic=polychromatic,
            apply_coma=apply_coma,
            apply_vignetting=apply_vignetting,
            figsize=figsize,
            log_scale=log_scale,
            focus_wavelength_nm=focus_wavelength_nm,
            display_stretch=display_stretch,
            exposure_level=exposure_level,
            filter_name=filter_name,
            exit_pupil_mm=exit_pupil_mm,
            peak_reference=peak_reference,
            idealize_sa=idealize_sa,
            focal_zoom_arcsec=focal_zoom_arcsec,
            coma_view_mode=coma_view_mode,
            apply_aperture_diffraction=apply_aperture_diffraction,
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
    log_scale: bool | None = None,
    focus_wavelength_nm: float = 550.0,
    display_stretch: str = "linear",
    exposure_level: float = 1.0,
    filter_name: str = "None",
    exit_pupil_mm: float = 7.0,
    peak_reference: float | None = None,
    idealize_sa: bool = False,
    focal_zoom_arcsec: float | None = None,
    coma_view_mode: str = "ray_fan",
    apply_aperture_diffraction: bool = True,
    eyepiece=None,
    eyepiece_view_mode: str = "eyepiece_view",
) -> tuple[Figure, dict]:
    """Dispatch to the appropriate telescope_sim plot function."""
    from telescope_sim.plotting import (
        plot_source_image, plot_psf_2d, plot_psf_profile,
        plot_coma_field_analysis,
    )
    from telescope_sim.plotting.ray_trace_plot import (
        plot_polychromatic_ray_trace,
        plot_vignetting_curve,
        plot_spot_diagram_telescope,
        plot_chromatic_focal_planes,
        plot_ray_fan_telescope,
        plot_spherical_focal_analysis,
        plot_ray_trace_pupil_colored,
    )

    if name == "plot_source_image":
        # Only ask for the circular eyepiece view when it will be shown —
        # building it costs a third figure.
        want_ev = eyepiece is not None and eyepiece_view_mode == "eyepiece_view"
        fig = plot_source_image(
            telescope, source,
            wavelength_nm=wavelength_nm,
            seeing_arcsec=seeing_arcsec,
            polychromatic=polychromatic,
            apply_coma=apply_coma,
            apply_vignetting=apply_vignetting,
            figsize=figsize,
            display_stretch=display_stretch,
            focus_wavelength_nm=focus_wavelength_nm,
            exposure_level=exposure_level,
            filter_name=filter_name,
            exit_pupil_mm=exit_pupil_mm,
            apply_aperture_diffraction=apply_aperture_diffraction,
            eyepiece=eyepiece,
            eyepiece_view_figsize=figsize if want_ev else None,
        )
        fig = _select_eyepiece_figure(fig, eyepiece_view_mode)
        info = {
            "plot_function": name,
            "display_stretch": display_stretch,
            "exposure_level": exposure_level,
            "filter_name": filter_name,
            "exit_pupil_mm": exit_pupil_mm,
        }
        if eyepiece is not None:
            # Surfaced so the terminal panel and the theory readout quote the
            # same numbers the render used, rather than recomputing them.
            info.update(
                eyepiece_focal_length_mm=eyepiece.focal_length_mm,
                eyepiece_afov_deg=eyepiece.apparent_fov_deg,
                magnification=eyepiece.magnification(telescope.focal_length),
                true_fov_arcsec=eyepiece.true_fov_arcsec(
                    telescope.focal_length),
                tfov_is_exact=eyepiece.tfov_is_exact,
                eyepiece_view_mode=eyepiece_view_mode,
            )
        return fig, info

    elif name == "plot_psf_2d":
        # log_scale defaults to True (legacy behavior) for plot_psf_2d
        _log = True if log_scale is None else log_scale
        fig = plot_psf_2d(
            telescope,
            wavelength_nm=wavelength_nm,
            include_obstruction=(telescope.obstruction_ratio > 0.0),
            figsize=figsize,
            log_scale=_log,
            peak_reference=peak_reference,
        )
        # Surface the FFT raw peak so the tutorial can use this frame as the
        # shared-normalisation reference for a paired frame (1.5).
        return fig, {
            "plot_function": name,
            "psf_raw_peak": getattr(fig, "_psf_raw_peak", None),
            "psf_relative_peak": getattr(fig, "_psf_relative_peak", 1.0),
        }

    elif name == "plot_psf_profile":
        # When log_scale is None: dual-panel (linear+log) layout.
        # When True/False: single-panel mode driven by the view combo.
        fig = plot_psf_profile(
            telescope,
            wavelength_nm=wavelength_nm,
            include_obstruction=(telescope.obstruction_ratio > 0.0),
            figsize=figsize,
            log_scale=log_scale,
        )
        return fig, {"plot_function": name}

    elif name == "plot_coma_field_analysis":
        fig = plot_coma_field_analysis(
            telescope,
            wavelength_nm=wavelength_nm,
            figsize=figsize,
            view_mode=coma_view_mode,
        )
        return fig, {"plot_function": name}

    elif name == "plot_polychromatic_ray_trace":
        # Use a tall aspect so the full optical-axis ray trace can use
        # the full BeforeAfterPanel height. The focal-region zoom is
        # paired with the after-side (plot_chromatic_focal_planes).
        tall_figsize = (figsize[0], figsize[1] * 1.6)
        fig = plot_polychromatic_ray_trace(
            telescope, figsize=tall_figsize,
            focus_wavelength_nm=focus_wavelength_nm,
            show_inset=False,
            idealize_sa=idealize_sa,
        )
        return fig, {"plot_function": name}

    elif name == "plot_vignetting_curve":
        fig = plot_vignetting_curve(telescope, figsize=figsize)
        return fig, {"plot_function": name}

    elif name == "plot_spot_diagram_telescope":
        fig = plot_spot_diagram_telescope(
            telescope, wavelength_nm=wavelength_nm, figsize=figsize)
        return fig, {"plot_function": name}

    elif name == "plot_ray_fan_telescope":
        fig = plot_ray_fan_telescope(
            telescope, wavelength_nm=wavelength_nm, figsize=figsize)
        return fig, {"plot_function": name}

    elif name == "plot_spherical_focal_analysis":
        # Tall two-panel secondary (focal caustic + ray fan) mirroring the
        # chromatic focal-plane layout.
        tall = (figsize[0], figsize[1] * 1.5)
        fig = plot_spherical_focal_analysis(
            telescope, wavelength_nm=wavelength_nm, figsize=tall)
        return fig, {"plot_function": name}

    elif name == "plot_ray_trace_pupil_colored":
        # Newtonian ray traces are tall (rays travel ~focal_length
        # along the y-axis vs ~aperture wide); use the scenario's
        # native square canvas. matplotlib auto-fits within set_aspect.
        fig = plot_ray_trace_pupil_colored(
            telescope, wavelength_nm=wavelength_nm,
            figsize=figsize,
        )
        return fig, {"plot_function": name}

    elif name == "plot_chromatic_focal_planes":
        # focal_zoom_arcsec controls the radial-profile x-axis range: a
        # "wide" view (≈120″) shows the singlet halo running off-panel; a
        # "close" view (≈12″) resolves the achromat/APO-doublet/APO-triplet
        # differences. None → the function's default.
        kw = {}
        if focal_zoom_arcsec is not None:
            kw["fixed_xlim_arcsec"] = focal_zoom_arcsec
        fig = plot_chromatic_focal_planes(
            telescope,
            figsize=(figsize[0] * 2.4, figsize[1] * 0.9),
            focus_wavelength_nm=focus_wavelength_nm,
            **kw,
        )
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
        # Only forward extra kwargs the theory function actually accepts.
        # (Callers pass a superset — e.g. obstruction_ratio — but most
        # theory functions don't take them; passing an unexpected kwarg
        # raised TypeError, which the except below swallowed as None, so
        # e.g. the aperture-vs-seeing after side silently lost its whole
        # theory dict — and with it the Airy overlay circle.)
        for k, v in extra_kwargs.items():
            if k in sig.parameters:
                kw[k] = v
        return fn(telescope, **kw)
    except Exception:
        return None


def apply_theory_overlay(
    scenario: ScenarioDefinition,
    fig: Figure,
    theory_result: dict,
    telescope=None,
    seeing_arcsec: float | None = None,
    side: str = "after",
) -> None:
    """Draw a theory overlay onto the figure's axes, if applicable.

    Dispatches by scenario id with two recognised signatures:
      - simple(fig, theory_value) — for circle overlays sized by a scalar
      - full(fig, theory_result, telescope, seeing_arcsec) — for richer overlays

    Must be called BEFORE MatplotlibCanvas.set_figure() since that rasterizes.
    """
    overlay_fn = OVERLAY_FUNCTIONS.get(scenario.id)
    if overlay_fn is None:
        return
    try:
        import inspect
        sig = inspect.signature(overlay_fn)
        params = sig.parameters
        # Detect optional keyword arguments the overlay supports
        kw_extra = {}
        if "scenario" in params:
            kw_extra["scenario"] = scenario
        if "side" in params:
            kw_extra["side"] = side
        n_pos = sum(1 for p in params.values()
                    if p.name not in ("scenario", "side")
                    and p.kind in (p.POSITIONAL_OR_KEYWORD, p.POSITIONAL_ONLY))
        if n_pos >= 4:
            overlay_fn(fig, theory_result, telescope, seeing_arcsec, **kw_extra)
        elif n_pos >= 3:
            overlay_fn(fig, theory_result, telescope, **kw_extra)
        else:
            overlay_fn(fig, theory_result.get("theory_value", 0.0), **kw_extra)
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

"""Scenario definitions for the Tutorial & Testing tab.

Each ScenarioDefinition fully specifies one tutorial scenario:
- before/after telescope and source configurations
- which plot function to call
- which theory function to compare against
- which parameters are tweakable on the live "after" side
- a terminal command template showing the Python API
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TelescopeConfig:
    """Parameters passed to build_telescope(). Mirrors its kwargs."""
    telescope_type: str = "Newtonian"
    diameter: float = 200.0
    focal_length: float = 1000.0
    primary_type: str = "parabolic"
    objective_type: str = "singlet"
    secondary_magnification: float = 3.0
    meniscus_thickness: float | None = None
    spider_vanes: int = 0
    spider_vane_width: float = 2.0
    obstruction_ratio: float = 0.20
    enable_obstruction: bool = True


@dataclass(frozen=True)
class SourceConfig:
    """Source specification for a scenario side."""
    source_type: str  # "PointSource", "DoubleStar", "Jupiter", "Saturn", "StarField"
    kwargs: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ScenarioDefinition:
    """Complete definition of a tutorial scenario."""
    id: str
    title: str
    act: int                       # 1, 2, or 3
    act_label: str                 # "Isolated Effects", "Compounding Effects", "Real Objects"
    description: str               # 2-3 sentence inline description for display
    learn_more_section: str        # Key hint for linking to Parameters & Physics tab

    # "Before" state (static baseline, rendered once on scenario load)
    before_telescope: TelescopeConfig
    before_source: SourceConfig

    # "After" state (starting config for the live/tweakable side)
    after_telescope: TelescopeConfig
    after_source: SourceConfig

    # Optional fields with defaults
    before_seeing_arcsec: float | None = None
    before_wavelength_nm: float = 550.0
    before_polychromatic: bool = False
    before_label: str = "Baseline"
    after_seeing_arcsec: float | None = None
    after_wavelength_nm: float = 550.0
    after_polychromatic: bool = False
    after_label: str = "With Effect"

    # Which plot function to use (name looked up in scenario_runner)
    plot_function: str = "plot_psf_2d"

    # Theory function name (looked up in theory_computations.THEORY_FUNCTIONS)
    theory_function: str | None = None

    # Parameters the user can tweak on the "after" side
    # Each entry is a param name from TelescopeConfig or "seeing" / "wavelength_nm"
    tweakable_params: tuple[str, ...] = field(default_factory=tuple)

    # Override effect application on the "before" side (e.g. vignetting off)
    before_apply_vignetting: bool = True
    before_apply_coma: bool = True

    # When True, "Update" re-renders both sides (separation slider affects both)
    both_sides_dynamic: bool = False

    # When True, the before-side telescope is rebuilt from live widget params
    # (using scenario.before_telescope as the base). Use for scenarios where
    # both sides should track aperture/obstruction/etc. simultaneously.
    before_telescope_dynamic: bool = False

    # Independent before-side widgets (G2.2). When set, the controls panel
    # renders TWO labeled groups ("Before:" and "After:") with separate
    # widget bindings. The before side reads from its own widgets only.
    tweakable_params_before: tuple[str, ...] | None = None

    # Use a different plot function for the after side (paired visualisations).
    # When None, both sides use plot_function. When set, before uses
    # plot_function and after uses secondary_plot_function.
    secondary_plot_function: str | None = None

    # Whether to show the 1D/2D PSF view toggle for this scenario
    # (False for scenarios where the azimuthal pattern is the point, e.g. spiders)
    show_psf_toggle: bool = True

    # For Act 3: which effects can be individually toggled on/off
    effect_toggles: tuple[str, ...] = field(default_factory=tuple)

    # Whether this scenario is fully implemented (False = placeholder "coming soon")
    implemented: bool = False

    # Which telescope class the demonstrated physics applies to.
    # "refractor" — applies only to refractors (e.g., chromatic aberration)
    # "reflector" — applies only to reflectors / catadioptric (e.g., spider vanes)
    # "both"      — geometry-driven, applies to any aperture (e.g., diffraction)
    applies_to: str = "both"

    # Python API terminal command template (use {param} placeholders)
    terminal_template: str = ""

    # Default exposure level for this scenario. 1.0 = anchor (mag 0
    # through 100 mm peaks just below saturation). Scenarios that
    # contain only dim stars or that need extra headroom for asinh
    # stretch can override; Act 1+2 scenarios pick whatever exposure
    # makes the lesson read cleanly (this is a display knob, not a
    # physics override). Act 3 ("Brightness, Saturation & Filters")
    # exposes this directly to the user.
    default_exposure: float = 1.0

    # Default filter for this scenario ("None" = unfiltered). Act 3
    # filter scenarios use this to demonstrate ND and colour filters.
    default_filter: str = "None"

    # When True, expose a Filter dropdown in the UI controls. Filters
    # multiply per-channel flux before saturation clipping, so they
    # interact with exposure + saturation correctly.
    show_filter_combo: bool = False

    # When True, expose a "Use live ephemeris" checkbox. The after-side
    # source is then constructed with use_realtime=True so its angular
    # size (Jupiter/Saturn/Moon) and Saturn ring tilt come from skyfield
    # at scenario-load time. Useful for "what does this look like
    # tonight" — and for ring-plane crossing demos where the fixed
    # tilt value would mislead.
    supports_realtime: bool = False

    # ── Per-side display controls (Phase 1.2) ────────────────────────────
    # The View / Filter / Exposure controls live on the After side and are
    # live. By default the Before side mirrors them (both sides track the
    # same control). Pin any of these on the Before side so the two panels
    # form an honest comparison — e.g. before = Detector(linear)+no filter
    # while after = Eye(log)+ND. None = mirror the live after-side control.
    before_display_stretch: str | None = None   # "linear" | "log" | "log_integrated"
    before_filter: str | None = None            # filter name, e.g. "None"
    before_exposure: float | None = None        # fixed exposure multiplier

    # Default for the After-side View combo. "log" (Eye) matches what you
    # see at the eyepiece and is the right default for most scenarios.
    # Detector-centric lessons (exposure / saturation / ND filter) set
    # "linear" so the exposure slider and saturation clipping are live.
    default_display_stretch: str = "log"

    # When set, the After side is PINNED to this view and the free View combo
    # is hidden — used when the two panes are a fixed Eye-vs-Detector
    # comparison (e.g. Exposure & Saturation: Eye left / Detector right) rather
    # than a single toggleable view. None = show the View combo as usual.
    after_display_stretch: str | None = None

    # When True, show an "Eye blur" checkbox that toggles the EYE pane between
    # log (no spatial integration) and log_integrated (1″ eye-resolution
    # blur). Used for fixed Eye-vs-Detector scenarios so the eye pane can show
    # the eye's spatial integration without a full View combo.
    show_eye_blur_toggle: bool = False

    # ── Shared PSF normalisation (Phase 1.5) ─────────────────────────────
    # When True, the after-side 2D PSF is displayed relative to the
    # before-side (unobstructed) on-axis peak instead of being independently
    # peak-normalised to 1.0. This makes the central-obstruction Strehl drop
    # (1−ε²)² visible in the 2D view rather than erased by per-frame
    # normalisation. Only meaningful for plot_psf_2d scenarios whose before
    # side is the unobstructed reference.
    shared_psf_normalization: bool = False

    # ── Exit-pupil eye model (Phase 1.4) ─────────────────────────────────
    # Default exit pupil (mm) for the Eye-view brightness model on extended
    # sources: surface brightness ∝ (exit_pupil / 7 mm)², capped at the
    # naked-eye level. ~2 mm is a typical planetary exit pupil. Only used
    # when the exit-pupil control is shown (extended-source scenarios).
    default_exit_pupil_mm: float = 2.0

    # ── Chromatic ray-trace idealisation (Phase B4) ──────────────────────
    # When True, the polychromatic ray trace draws each colour converging to
    # a point (spherical aberration removed) so the singlet/achromat/APO
    # comparison isolates *chromatic* focal shift. Flagged on the plot as a
    # teaching idealisation. Only meaningful for plot_polychromatic_ray_trace.
    idealize_singlet_sa: bool = False

    # When True, expose a "Focal zoom" combo (Wide / Close) on the after-side
    # chromatic focal-plane image: Wide shows the singlet halo running
    # off-panel; Close resolves the achromat/APO-doublet/APO-triplet
    # differences. Only meaningful for plot_chromatic_focal_planes.
    show_focal_zoom_combo: bool = False

    # When True, expose a "Coma view" combo (Ray fan / Spot grid) on the
    # coma analysis (plot_coma_field_analysis): the ray fan is the default
    # optical-design signature view; the spot grid is the 2D-comet view.
    show_coma_view_combo: bool = False

    # When True, expose "Aperture diffraction" and "Atmospheric seeing"
    # checkboxes on the AFTER side (R3.10, aperture_vs_seeing): each toggles
    # its effect in the render AND its reference circle in the overlay, so
    # the viewer can isolate which limit dominates. The BEFORE side stays a
    # fixed both-limits reference.
    show_resolution_toggles: bool = False


# ---------------------------------------------------------------------------
# Shared telescope configs used across multiple scenarios
# ---------------------------------------------------------------------------

_CLEAN_200MM = TelescopeConfig(
    telescope_type="Newtonian", diameter=200.0, focal_length=1000.0,
    enable_obstruction=False, spider_vanes=0,
)
_OBSTRUCTED_200MM = TelescopeConfig(
    telescope_type="Newtonian", diameter=200.0, focal_length=1000.0,
    enable_obstruction=True, obstruction_ratio=0.30, spider_vanes=0,
)
_SPIDER_200MM = TelescopeConfig(
    telescope_type="Newtonian", diameter=200.0, focal_length=800.0,  # f/4 — coma visible on edge stars
    enable_obstruction=True, obstruction_ratio=0.20, spider_vanes=4, spider_vane_width=2.0,
)
_FAST_200MM = TelescopeConfig(
    telescope_type="Newtonian", diameter=200.0, focal_length=600.0,  # f/3
    enable_obstruction=True, obstruction_ratio=0.20, spider_vanes=0,
)
_SLOW_200MM = TelescopeConfig(
    telescope_type="Newtonian", diameter=200.0, focal_length=1600.0,  # f/8
    enable_obstruction=True, obstruction_ratio=0.20, spider_vanes=0,
)
_SINGLET_80MM = TelescopeConfig(
    telescope_type="Refractor", diameter=80.0, focal_length=640.0,
    objective_type="singlet",
)
_ACHROMAT_80MM = TelescopeConfig(
    telescope_type="Refractor", diameter=80.0, focal_length=640.0,
    objective_type="achromat",
)
# f/5 singlet — larger aperture & faster ratio amplifies chromatic aberration
# so the singlet vs achromat difference is more dramatic in the ray-trace plot
_SINGLET_100MM_F5 = TelescopeConfig(
    telescope_type="Refractor", diameter=100.0, focal_length=500.0,
    objective_type="singlet",
)
_JUPITER_200MM = TelescopeConfig(
    telescope_type="Newtonian", diameter=200.0, focal_length=1000.0,
    enable_obstruction=True, obstruction_ratio=0.20, spider_vanes=4, spider_vane_width=2.0,
)

_POINT = SourceConfig(source_type="PointSource")
_DOUBLE = SourceConfig(source_type="DoubleStar", kwargs={"separation_arcsec": 1.4})
_JUPITER = SourceConfig(source_type="Jupiter")
_SATURN = SourceConfig(source_type="Saturn")
_STARFIELD = SourceConfig(source_type="StarField")


# ---------------------------------------------------------------------------
# Scenario registry — all 13 scenarios
# ---------------------------------------------------------------------------

SCENARIOS: list[ScenarioDefinition] = [

    # ------------------------------------------------------------------
    # Act 1: Isolated Effects
    # ------------------------------------------------------------------

    ScenarioDefinition(
        id="airy_disk", applies_to="both",
        title="Airy Disk",
        act=1, act_label="Isolated Effects",
        description=(
            "A circular aperture diffracts light into a central bright disk surrounded by "
            "concentric rings — the Airy pattern. The angular radius of the first dark "
            "ring is 1.22\u03bb/D — it depends only on aperture and wavelength, not "
            "on focal length (focal length only sets the mm scale at the focal plane). "
            "Scale context: 1″ ≈ a US quarter at 5 km; typical seeing 1–4″."
        ),
        learn_more_section="Diffraction",
        before_telescope=_CLEAN_200MM,
        before_source=_POINT,
        before_label="Reference \u2014 200 mm aperture",
        after_telescope=_CLEAN_200MM,
        after_source=_POINT,
        after_label="Adjust aperture \u2192",
        plot_function="plot_psf_2d",
        theory_function="compute_airy_disk_theory",
        tweakable_params=("diameter",),
        implemented=True,
        terminal_template=(
            "from telescope_sim.geometry import NewtonianTelescope\n"
            "from telescope_sim.plotting import plot_psf_2d\n\n"
            "telescope = NewtonianTelescope(\n"
            "    primary_diameter={diameter},\n"
            "    focal_length={focal_length},\n"
            "    enable_obstruction=False,\n"
            ")\n"
            "fig = plot_psf_2d(telescope, wavelength_nm={wavelength_nm})"
        ),
    ),

    ScenarioDefinition(
        id="rayleigh_criterion", applies_to="both",
        title="Rayleigh Criterion",
        act=1, act_label="Isolated Effects",
        description=(
            "Two stars separated by the same angle look different through different apertures. "
            "The Rayleigh limit 1.22\u03bb/D sets the minimum resolvable separation. A 100\u202fmm scope "
            "needs 1.38\u2033 to resolve; a 200\u202fmm scope needs only 0.69\u2033. Drag the slider to see "
            "both sides update simultaneously. "
            "Scale context: easy doubles ≈ 5\u2033; tough planetary doubles \u2248 1\u2033; typical seeing 1\u20134\u2033 \u2014 atmosphere often dominates.\n"
            "Note: rendered in vacuum (no atmospheric seeing) so the diffraction "
            "limit reads cleanly. Real eyepiece views are seeing-dominated and "
            "rarely show the Airy rings shown here \u2014 see *aperture_vs_seeing* "
            "for the realistic combined view."
        ),
        learn_more_section="Diffraction",
        before_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=100.0, focal_length=500.0,
            enable_obstruction=False, spider_vanes=0,
        ),
        before_source=SourceConfig(source_type="DoubleStar",
            kwargs={"separation_arcsec": 1.0, "field_extent_arcsec": 15.0}),
        before_label="100 mm \u2014 Rayleigh 1.38\u2033",
        after_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=200.0, focal_length=1000.0,
            enable_obstruction=False, spider_vanes=0,
        ),
        after_source=SourceConfig(source_type="DoubleStar",
            kwargs={"separation_arcsec": 1.0, "field_extent_arcsec": 15.0}),
        after_label="Adjustable aperture \u2192",
        plot_function="plot_source_image",
        theory_function="compute_rayleigh_theory",
        tweakable_params=("separation_arcsec", "diameter"),
        both_sides_dynamic=True,
        implemented=True,
        terminal_template=(
            "from telescope_sim.geometry import NewtonianTelescope\n"
            "from telescope_sim.source.sources import DoubleStar\n"
            "from telescope_sim.plotting import plot_source_image\n\n"
            "# 100 mm: Rayleigh limit = 1.38\"\n"
            "t100 = NewtonianTelescope(primary_diameter=100, focal_length=500,\n"
            "                          enable_obstruction=False)\n"
            "# 200 mm: Rayleigh limit = 0.69\"\n"
            "t200 = NewtonianTelescope(primary_diameter=200, focal_length=1000,\n"
            "                          enable_obstruction=False)\n"
            "source = DoubleStar(separation_arcsec={separation_arcsec})\n"
            "fig100 = plot_source_image(t100, source, wavelength_nm={wavelength_nm})\n"
            "fig200 = plot_source_image(t200, source, wavelength_nm={wavelength_nm})"
        ),
    ),

    ScenarioDefinition(
        id="central_obstruction", applies_to="reflector",
        title="Central Obstruction",
        act=1, act_label="Isolated Effects",
        description=(
            "A central secondary mirror blocks part of the aperture, transferring energy from the "
            "Airy disk into the surrounding rings. This reduces peak intensity (Strehl ratio) and "
            "increases contrast in the secondary rings. Compare the theoretical Strehl (1\u2212\u03b5\u00b2)\u00b2 "
            "to the simulation."
        ),
        learn_more_section="Central Obstruction",
        before_telescope=_CLEAN_200MM,
        before_source=_POINT,
        before_label="No obstruction \u2014 reference (PSF peak \u2261 1.0)",
        after_telescope=_OBSTRUCTED_200MM,
        after_source=_POINT,
        after_label="With obstruction \u2192 (same scale; peak = Strehl)",
        plot_function="plot_psf_2d",
        theory_function="compute_central_obstruction_theory",
        tweakable_params=("obstruction_ratio",),
        # Display the obstructed PSF relative to the unobstructed before-side
        # peak so the Strehl drop (1−ε²)² is visible in the 2D view (Phase
        # 1.5) instead of erased by per-frame peak normalisation.
        shared_psf_normalization=True,
        implemented=True,
        terminal_template=(
            "from telescope_sim.geometry import NewtonianTelescope\n"
            "from telescope_sim.plotting import plot_psf_2d\n\n"
            "# Before: no obstruction\n"
            "t_clean = NewtonianTelescope(\n"
            "    primary_diameter=200, focal_length=1000,\n"
            "    enable_obstruction=False,\n"
            ")\n\n"
            "# After: {obstruction_ratio:.0%} obstruction\n"
            "t_obstructed = NewtonianTelescope(\n"
            "    primary_diameter=200, focal_length=1000,\n"
            "    enable_obstruction=True, obstruction_ratio={obstruction_ratio:.2f},\n"
            ")\n"
            "fig = plot_psf_2d(t_obstructed, wavelength_nm={wavelength_nm})"
        ),
    ),

    ScenarioDefinition(
        id="spider_vanes", applies_to="reflector",
        title="Spider Vane Diffraction",
        act=1, act_label="Isolated Effects",
        description=(
            "Spider vanes holding the secondary mirror diffract light into spikes perpendicular "
            "to each vane. Four vanes produce four spikes; three vanes produce six. "
            "Wider vanes produce brighter spikes."
        ),
        learn_more_section="Spider Vanes",
        before_telescope=_OBSTRUCTED_200MM,
        before_source=_POINT,
        before_label="No spider vanes",
        after_telescope=_SPIDER_200MM,
        after_source=_POINT,
        after_label="4 spider vanes \u2192",
        plot_function="plot_psf_2d",
        theory_function=None,
        tweakable_params=("spider_vanes", "spider_vane_width"),
        show_psf_toggle=False,
        implemented=True,
        terminal_template=(
            "from telescope_sim.geometry import NewtonianTelescope\n"
            "from telescope_sim.plotting import plot_psf_2d\n\n"
            "telescope = NewtonianTelescope(\n"
            "    primary_diameter=200, focal_length=1000,\n"
            "    enable_obstruction=True, obstruction_ratio=0.20,\n"
            "    spider_vanes={spider_vanes},\n"
            "    spider_vane_width={spider_vane_width},\n"
            ")\n"
            "fig = plot_psf_2d(telescope, wavelength_nm={wavelength_nm})"
        ),
    ),

    ScenarioDefinition(
        id="chromatic_aberration", applies_to="refractor",
        title="Chromatic Aberration",
        act=1, act_label="Isolated Effects",
        description=(
            "A simple glass lens refracts blue light more strongly than red, so the "
            "three colours focus at slightly different distances. The inset shows the "
            "focal spread (R/G/B stars) along the optical axis. Four objective designs "
            "to compare:\n"
            " \u2022 Singlet (one BK7 lens): worst case \u2014 focal spread scales with aperture "
            "and inversely with f-ratio; bright stars show vivid colour halos.\n"
            " \u2022 Achromat (BK7 + F2 cemented doublet): two wavelengths brought to the "
            "same focus; ~25\u00d7 smaller residual chromatic than a singlet.\n"
            " \u2022 APO doublet (FPL51 ED + BK7 cemented): three wavelengths very nearly "
            "coincident; ~80\u00d7 smaller than a singlet.\n"
            " \u2022 APO triplet (ED + flint + ED, air-spaced): full apochromatic "
            "correction across the visible band; ~200\u00d7 smaller residual.\n"
            "Try changing the f-ratio (focal length) \u2014 chromatic blur scales as 1/F, "
            "so a slow scope tames the same glass.\n"
            "Note: to isolate the chromatic lesson, the ray trace is idealised "
            "so each colour converges to a point (spherical aberration removed) "
            "for every objective \u2014 the only difference you see is the chromatic "
            "focal shift between colours. A real spherical singlet would also "
            "show spherical aberration (marginal rays focusing short); see the "
            "Spherical Aberration scenario for that effect on its own. Use the "
            "Focal zoom control on the right panel: Wide shows the singlet halo "
            "running off-frame; Close resolves the achromat vs APO differences."
        ),
        learn_more_section="Chromatic Aberration",
        before_telescope=_SINGLET_100MM_F5,
        before_source=_POINT,
        before_polychromatic=True,
        before_label="Singlet 100mm f/5 (reference)",
        after_telescope=_SINGLET_100MM_F5,
        after_source=_POINT,
        after_polychromatic=True,
        after_label="Focal-plane image at each colour \u2192",
        plot_function="plot_polychromatic_ray_trace",
        secondary_plot_function="plot_chromatic_focal_planes",
        theory_function=None,
        idealize_singlet_sa=True,
        show_focal_zoom_combo=True,
        tweakable_params=("objective_type", "focal_length"),
        both_sides_dynamic=True,
        before_telescope_dynamic=True,
        implemented=True,
        terminal_template=(
            "from telescope_gui.telescope_builder import build_telescope\n"
            "from telescope_sim.plotting.ray_trace_plot import plot_polychromatic_ray_trace\n\n"
            "telescope = build_telescope(\n"
            "    telescope_type='Refractor',\n"
            "    diameter=100, focal_length=500,\n"
            "    objective_type='{objective_type}',\n"
            ")\n"
            "fig = plot_polychromatic_ray_trace(telescope)"
        ),
    ),

    ScenarioDefinition(
        id="vignetting", applies_to="reflector",
        title="Vignetting",
        act=1, act_label="Isolated Effects",
        description=(
            "Stars away from the optical axis send their light cone into the telescope "
            "at an angle. After bouncing off the primary mirror this converging cone is "
            "laterally offset from the optical axis \u2014 if the offset exceeds the "
            "secondary mirror's clear aperture, part of the cone is clipped and that "
            "star is dimmed. Three things set the falloff: secondary mirror size "
            "(obstruction ratio), distance from primary to secondary (focal length), "
            "and the primary's diameter. Note: a LARGER secondary mirror reduces "
            "vignetting (catches more of the off-axis cone) but INCREASES "
            "the central-obstruction contrast loss — telescope designers balance "
            "these. Below the fully-illuminated field angle "
            "\u03b8_fif the on-axis cone is unobstructed; beyond it, illumination falls "
            "smoothly toward zero at the 50% edge. Adjust the parameters to see how "
            "each shifts the curve.\n"
            "See also the labelled Vignetting diagram in the Parameters & Physics "
            "tab, which shows the clipped-cone geometry and the secondary-face "
            "circle-overlap picture."
        ),
        learn_more_section="Vignetting",
        before_telescope=_SPIDER_200MM,
        before_source=_POINT,  # source unused by plot_vignetting_curve
        before_label="200 mm f/5 baseline",
        after_telescope=_SPIDER_200MM,
        after_source=_POINT,
        after_label="Adjust aperture / f / obstruction \u2192",
        plot_function="plot_vignetting_curve",
        theory_function="compute_vignetting_theory",
        tweakable_params=("diameter", "focal_length", "obstruction_ratio"),
        both_sides_dynamic=True,
        before_telescope_dynamic=False,
        implemented=True,
        terminal_template=(
            "from telescope_sim.geometry import NewtonianTelescope\n"
            "from telescope_sim.source.sources import StarField\n"
            "from telescope_sim.plotting import plot_source_image\n\n"
            "telescope = NewtonianTelescope(\n"
            "    primary_diameter={diameter},\n"
            "    focal_length={focal_length},\n"
            "    enable_obstruction=True,\n"
            ")\n"
            "source = StarField()\n"
            "# With vignetting (default)\n"
            "fig = plot_source_image(telescope, source, wavelength_nm={wavelength_nm})\n\n"
            "# Without vignetting\n"
            "fig = plot_source_image(telescope, source, wavelength_nm={wavelength_nm},\n"
            "                       apply_vignetting=False)"
        ),
    ),

    ScenarioDefinition(
        id="spherical_aberration", applies_to="reflector",
        title="Spherical Aberration",
        act=1, act_label="Isolated Effects",
        description=(
            "A spherical primary mirror does not focus all rays to the same point — "
            "marginal rays focus closer than paraxial rays.\n"
            "Left: the ray trace, with each ray coloured by its pupil entry zone "
            "(dark = central, bright = marginal). The magnified inset zooms into "
            "the focal region so you can SEE the bright marginal rays crossing "
            "the axis short of the dim paraxial rays.\n"
            "Right: the ray fan. The vertical axis, Δx, is the TRANSVERSE RAY "
            "ERROR — for a ray entering the pupil at height h, how far from the "
            "ideal focus it actually lands, measured ACROSS the optical axis "
            "(the same x-direction as the ray trace on the left). Plotting Δx "
            "against h reveals the aberration by its curve shape: a cubic "
            "(S-shape) is the signature of spherical aberration; coma gives a "
            "parabolic (U-shape) fan, defocus a linear one, and a perfect "
            "system gives Δx ≈ 0 at every h.\n"
            "Toggle to a parabolic primary to see both the inset spread vanish "
            "and the ray-fan curve collapse to ≈ 0 (diffraction-limited)."
        ),
        learn_more_section="Implemented Physics",
        before_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=200.0, focal_length=800.0,
            primary_type="spherical",
            enable_obstruction=False, spider_vanes=0,
        ),
        before_source=_POINT,
        before_label="Ray trace (pupil-coloured)",
        after_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=200.0, focal_length=800.0,
            primary_type="spherical",
            enable_obstruction=False, spider_vanes=0,
        ),
        after_source=_POINT,
        after_label="Ray fan (h vs Δx) →",
        plot_function="plot_ray_trace_pupil_colored",
        secondary_plot_function="plot_ray_fan_telescope",
        theory_function="compute_spherical_aberration_theory",
        tweakable_params=("diameter", "focal_length", "primary_type"),
        both_sides_dynamic=True,
        before_telescope_dynamic=True,
        show_psf_toggle=False,
        implemented=True,
        terminal_template=(
            "from telescope_gui.telescope_builder import build_telescope\n"
            "from telescope_sim.plotting import plot_psf_2d\n\n"
            "# Spherical primary — shows spherical aberration blur\n"
            "t_sph = build_telescope(\n"
            "    telescope_type='Newtonian',\n"
            "    diameter=200, focal_length={focal_length},\n"
            "    primary_type='spherical',\n"
            "    enable_obstruction=False,\n"
            ")\n\n"
            "# Parabolic primary — diffraction-limited\n"
            "t_par = build_telescope(\n"
            "    telescope_type='Newtonian',\n"
            "    diameter=200, focal_length={focal_length},\n"
            "    primary_type='parabolic',\n"
            "    enable_obstruction=False,\n"
            ")\n"
            "fig_sph = plot_psf_2d(t_sph, wavelength_nm={wavelength_nm})\n"
            "fig_par = plot_psf_2d(t_par, wavelength_nm={wavelength_nm})"
        ),
    ),

    # ------------------------------------------------------------------
    # Act 2: Compounding Effects
    # ------------------------------------------------------------------

    ScenarioDefinition(
        id="obstruction_plus_spiders", applies_to="reflector",
        title="Obstruction + Spider Vanes",
        act=2, act_label="Compounding Effects",
        description=(
            "Combine central obstruction and spider vanes and see how the modified "
            "Airy ring contrast interacts with diffraction spikes. Both sides have "
            "independent controls so you can isolate either effect \u2014 leave one side "
            "with no spiders, or compare two different obstruction ratios."
        ),
        learn_more_section="Central Obstruction",
        before_telescope=_OBSTRUCTED_200MM,
        before_source=_POINT,
        before_label="Before configuration",
        after_telescope=_SPIDER_200MM,
        after_source=_POINT,
        after_label="After configuration \u2192",
        plot_function="plot_psf_2d",
        theory_function=None,
        tweakable_params=("obstruction_ratio", "spider_vanes", "spider_vane_width"),
        tweakable_params_before=("obstruction_ratio", "spider_vanes", "spider_vane_width"),
        show_psf_toggle=False,
        implemented=True,
        terminal_template=(
            "from telescope_sim.geometry import NewtonianTelescope\n"
            "from telescope_sim.plotting import plot_psf_2d\n\n"
            "telescope = NewtonianTelescope(\n"
            "    primary_diameter=200, focal_length=1000,\n"
            "    enable_obstruction=True, obstruction_ratio={obstruction_ratio:.2f},\n"
            "    spider_vanes={spider_vanes},\n"
            "    spider_vane_width={spider_vane_width},\n"
            ")\n"
            "fig = plot_psf_2d(telescope, wavelength_nm={wavelength_nm})"
        ),
    ),

    ScenarioDefinition(
        id="chromatic_plus_seeing", applies_to="refractor",
        title="Chromatic Aberration + Seeing",
        act=2, act_label="Compounding Effects",
        description=(
            "Five stars with realistic spectral colours (M-type red giant, "
            "K-type orange, G-type yellow Sun, A-type blue-white, B-type "
            "deep blue) seen through an 80 mm f/8 achromat under good "
            "1.5″ atmospheric seeing.\n\n"
            "F and C are the Fraunhofer spectral lines — F = hydrogen Hβ "
            "at 486 nm (blue), C = hydrogen Hα at 656 nm (red). A classical "
            "achromat is *defined* by bringing F and C to a common focal "
            "plane; the small remaining shift at G/d (550-587 nm) is the "
            "secondary spectrum.\n\n"
            "FOCAL-PLANE CHOICE matters: the 'Focus at' combo picks WHICH "
            "wavelength is sharp at the center, which controls the halo color.\n"
            " • G / design (550 nm) — default. Where amateur observers "
            "'snap to focus' an achromat (peak eye sensitivity). Sharp green "
            "core + the classic VIOLET HALO from defocused F and C.\n"
            " • F=C plane — the focal plane where F and C converge in an "
            "achromat. R and B sharp, G defocused → GREEN HALO around "
            "the core. By design, chromatic_defocus(F) ≡ chromatic_defocus(C) "
            "for an achromat — so R, B, and F=C are IDENTICAL choices for "
            "an achromat. (Greyed out for a singlet, where F and C lie on "
            "different focal planes.)\n\n"
            "VIEW: Detector shows raw per-pixel CCD intensity (G core "
            "dominates when focused at G because G is concentrated by the "
            "in-focus Airy peak while F/C are spread thin over the chromatic "
            "disk). Eye applies the eye's logarithmic intensity response so "
            "dim halos are visible. Eye + integration adds 1″ spatial "
            "integration matching eye resolution at a moderate eyepiece — "
            "the chromatic disk mixes into the perceived core, producing "
            "the white-cored, violet-haloed star image observers describe.\n\n"
            "Toggle the objective to see singlet (huge chromatic), achromat "
            "(secondary spectrum residual), APO doublet (3 wavelengths "
            "corrected), and APO triplet (near diffraction-limited)."
        ),
        learn_more_section="Chromatic Aberration",
        before_telescope=_ACHROMAT_80MM,
        before_source=SourceConfig(source_type="MultiColorStarField"),
        before_seeing_arcsec=1.5,
        before_polychromatic=True,
        before_label="Reference — Eye view (achromat, 1.5″)",
        after_telescope=_ACHROMAT_80MM,
        after_source=SourceConfig(source_type="MultiColorStarField"),
        after_seeing_arcsec=1.5,
        after_polychromatic=True,
        after_label="Adjust seeing / objective / view \u2192",
        plot_function="plot_source_image",
        theory_function=None,
        tweakable_params=("seeing", "objective_type"),
        implemented=True,
        # Eye view by default: an 80 mm scope under 1.5" seeing spreads the
        # five faint stars too thin to read in the linear Detector view even
        # at max exposure (try it \u2014 that's a real lesson, not a bug). Pin the
        # left reference to Eye so the spectral colours are always visible;
        # the right can be switched to Detector to see the dim linear truth.
        default_display_stretch="log",
        before_display_stretch="log",
        terminal_template=(
            "from telescope_gui.telescope_builder import build_telescope\n"
            "from telescope_sim.source.sources import PointSource\n"
            "from telescope_sim.plotting import plot_source_image\n\n"
            "telescope = build_telescope(\n"
            "    telescope_type='Refractor',\n"
            "    diameter=80, focal_length=640,\n"
            "    objective_type='{objective_type}',\n"
            ")\n"
            "source = PointSource()\n"
            "fig = plot_source_image(\n"
            "    telescope, source,\n"
            "    seeing_arcsec={seeing_arcsec},\n"
            "    polychromatic=True,\n"
            "    wavelength_nm={wavelength_nm},\n"
            ")"
        ),
    ),

    ScenarioDefinition(
        id="aperture_vs_seeing", applies_to="both",
        title="Aperture vs Seeing",
        act=2, act_label="Compounding Effects",
        description=(
            "This module is about resolution effects: aperture vs seeing vs eye "
            "integration. The LEFT panel is the fixed reference \u2014 the real "
            "telescope with both theoretical-limit overlays (Airy radius and seeing "
            "FWHM) so you can read which one dominates. The RIGHT panel is "
            "interactive: toggle 'Aperture diffraction' and 'Atmospheric seeing' "
            "on/off (each also toggles its reference circle) to isolate each limit "
            "\u2014 aperture only (a crisp Airy disk), seeing only (the atmospheric "
            "blur), both (reality), or neither (an ideal point). Note: 'aperture "
            "off' is an idealisation \u2014 every real aperture diffracts. Once "
            "aperture exceeds D\u2099\u1d63\u1d62\u209c = 1.22\u03bb/\u03b8\u209b\u1d49\u1d49\u1d4f\u1d5f\u1d57 "
            "the atmosphere limits resolution and bigger apertures only gather more "
            "light. The eye adds a third limit \u2014 its ~1\u2032 resolution and "
            "temporal integration smooth fine detail and average out the seeing "
            "(see Parameters & Physics \u2192 Detector vs Eye)."
        ),
        learn_more_section="Atmospheric Seeing",
        before_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=200.0, focal_length=1000.0,
            enable_obstruction=False, spider_vanes=0,
        ),
        before_source=_POINT,
        before_seeing_arcsec=2.5,
        before_label="Reference — both effects + limit overlays",
        after_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=200.0, focal_length=1000.0,
            enable_obstruction=False, spider_vanes=0,
        ),
        after_source=_POINT,
        after_seeing_arcsec=2.5,
        after_label="Interactive \u2014 toggle each limit \u2192",
        plot_function="plot_source_image",
        show_resolution_toggles=True,
        theory_function="compute_aperture_vs_seeing_theory",
        tweakable_params=("diameter", "seeing"),
        both_sides_dynamic=True,
        before_telescope_dynamic=True,
        implemented=True,
        terminal_template=(
            "from telescope_sim.geometry import NewtonianTelescope\n"
            "from telescope_sim.source.sources import PointSource\n"
            "from telescope_sim.plotting import plot_source_image\n\n"
            "telescope = NewtonianTelescope(\n"
            "    primary_diameter={diameter},\n"
            "    focal_length={focal_length},\n"
            "    enable_obstruction=False,\n"
            ")\n"
            "source = PointSource()\n"
            "fig = plot_source_image(\n"
            "    telescope, source,\n"
            "    seeing_arcsec={seeing_arcsec},\n"
            "    wavelength_nm={wavelength_nm},\n"
            ")"
        ),
    ),

    ScenarioDefinition(
        id="fratio_coma", applies_to="reflector",
        title="f-ratio and Coma",
        act=2, act_label="Compounding Effects",
        description=(
            "Coma is comet-shaped off-axis blur; angular coma scales as 1/f\u00b2, so a "
            "fast scope (small f-ratio) suffers \u2014 the coma-free field shrinks as f\u00b2. "
            "Default: 200 mm f/3 (a fast Newtonian where coma is dramatic at the edges), "
            "1.5\u2033 \u2018good\u2019 atmospheric seeing. Left panel (Coma view = Ray fan, default) "
            "shows coma's optical-design signature \u2014 a parabola (\u0394x \u221d h\u00b2) where both "
            "pupil edges bend the same way; switch Coma view to \u2018Spot grid\u2019 for the 2D "
            "comet shapes at 0/30/60/120 arcsec off-axis. The right panel shows "
            "the same field as colored points so you can see comatic stars near the edge. "
            "Field-angle context: 120\u2033 = 2 arcmin \u2248 the corner of a typical eyepiece "
            "view at high magnification (a 50\u00b0 AFOV eyepiece at 150\u00d7 shows 20 arcmin TFOV, "
            "so 120\u2033 is 20% of the field radius). The right-panel reference circles mark "
            "(a) the coma-free zone cff = 1.22 \u03bb F\u00b2/D (where \u03c3_coma equals the Airy radius) "
            "and (b) 10\u00d7 cff where the comatic blur is 10\u00d7 the Airy disk. Try slowing the "
            "scope (raise the focal length) \u2014 coma shrinks rapidly and stars round up."
        ),
        learn_more_section="Coma",
        before_telescope=_FAST_200MM,
        before_source=_POINT,
        before_label="Coma spot grid",
        after_telescope=_FAST_200MM,
        after_source=SourceConfig(
            source_type="ComaDemoField",
            kwargs={"field_radius_arcsec": 150.0},
        ),
        # Seeing 1.5\u2033 \u2014 "good seeing" for an amateur site. Coma at the
        # outermost spot (240\u2033 off-axis, f/3) is ~1.2\u2033 RMS with a ~3-4\u2033
        # visible spot extent \u2014 larger than the seeing FWHM, so comatic
        # elongation reads through the atmosphere. (At f/4 with 5\u2033 seeing
        # in the old default, coma was 7\u00d7 smaller than seeing and stars
        # looked perfectly circular.)
        after_seeing_arcsec=1.5,
        after_label="Star field \u2014 same field angles as spot grid \u2192",
        plot_function="plot_coma_field_analysis",
        secondary_plot_function="plot_source_image",
        show_coma_view_combo=True,
        theory_function="compute_coma_fratio_theory",
        tweakable_params=("focal_length", "diameter"),
        both_sides_dynamic=True,
        before_telescope_dynamic=True,
        implemented=True,
        terminal_template=(
            "from telescope_sim.geometry import NewtonianTelescope\n"
            "from telescope_sim.plotting import plot_coma_field_analysis\n\n"
            "telescope = NewtonianTelescope(\n"
            "    primary_diameter={diameter},\n"
            "    focal_length={focal_length},\n"
            ")\n"
            "fig = plot_coma_field_analysis(telescope, wavelength_nm={wavelength_nm})"
        ),
    ),

    # ------------------------------------------------------------------
    # Act 3: Brightness, Saturation & Filters
    # ------------------------------------------------------------------
    #
    # Photometry-focused tutorials. These scenarios introduce the
    # exposure slider, eye/cone desaturation, ND filters, and Wratten
    # colour filters in isolation, so the user understands each
    # mechanism before applying them all together on real targets in
    # Act 4. The brightness pipeline (mag → flux × aperture² × T(λ)
    # × exposure → saturate) is the same in every Act; the difference
    # is which knob the scenario asks you to study.

    ScenarioDefinition(
        id="exposure_demo", applies_to="both",
        title="Exposure & Saturation",
        act=3, act_label="Brightness, Saturation & Filters",
        description=(
            "Applies to: any telescope. "
            "A single warm-orange star (mag 0) shown two ways at once — the "
            "EYE (left) and a DETECTOR (right) — to compare how each responds "
            "to BRIGHTNESS and to SATURATION.\n"
            "APERTURE affects BOTH panes: a bigger mirror collects more light, "
            "so the star brightens on the eye AND the detector (∝ aperture²). "
            "Change the Aperture control and watch both sides respond.\n"
            "EXPOSURE is the DETECTOR's knob — a detector integrates over time, "
            "so longer exposure builds signal until the core SATURATES and "
            "clips to pure white (the colour burns out channel-by-channel). "
            "The eye does not integrate over time, so exposure leaves the eye "
            "pane unchanged — its brightness comes from aperture (and, for "
            "extended objects, exit pupil). So exposure is one brightness knob "
            "among several, specific to the detector; aperture is shared.\n"
            "Toggle 'Eye blur' to add the eye's ~1″ spatial integration to the "
            "eye pane."
        ),
        learn_more_section="Photometry & Filters",
        before_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=100.0, focal_length=800.0,
            enable_obstruction=False, spider_vanes=0,
        ),
        before_source=SourceConfig(
            source_type="PointSource",
            kwargs={"magnitude": 0.0, "field_angle_arcsec": 0.0,
                    "spectral_rgb": (1.0, 0.7, 0.35)},
        ),
        before_label="Eye view (perceptual)",
        after_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=100.0, focal_length=800.0,
            enable_obstruction=False, spider_vanes=0,
        ),
        after_source=SourceConfig(
            source_type="PointSource",
            kwargs={"magnitude": 0.0, "field_angle_arcsec": 0.0,
                    "spectral_rgb": (1.0, 0.7, 0.35)},
        ),
        after_label="Detector view (linear) →",
        plot_function="plot_source_image",
        theory_function=None,
        # Keep aperture (D² changes how fast the star saturates — relevant
        # to the exposure/saturation lesson). Drop focal length: for a point
        # source it changes only the PSF-kernel mm-scale, not the star's
        # angular look, so it read as "no effect" (user feedback).
        tweakable_params=("diameter",),
        before_apply_vignetting=False,
        before_apply_coma=False,
        implemented=True,
        default_exposure=1.0,
        # R3.12: FIXED Eye-vs-Detector layout — Eye on the LEFT (pinned,
        # eye-blur toggle), Detector on the RIGHT (pinned linear, exposure +
        # saturation live). No free View combo. Aperture drives both panes;
        # exposure drives only the Detector.
        before_display_stretch="log",
        after_display_stretch="linear",
        show_eye_blur_toggle=True,
        both_sides_dynamic=True,
        before_telescope_dynamic=True,
        terminal_template=(
            "from telescope_gui.telescope_builder import build_telescope\n"
            "from telescope_sim.source.sources import PointSource\n"
            "from telescope_sim.plotting import plot_source_image\n\n"
            "t = build_telescope(telescope_type='reflector',\n"
            "                    diameter={diameter}, focal_length={focal_length},\n"
            "                    primary_type='parabolic', enable_obstruction=False,\n"
            "                    spider_vanes=0)\n"
            "src = PointSource(magnitude=0.0)\n"
            "fig = plot_source_image(t, src, wavelength_nm={wavelength_nm},\n"
            "                        exposure_level=1.0,  # try 0.1, 1.0, 10.0\n"
            "                        display_stretch='linear')"
        ),
    ),

    ScenarioDefinition(
        id="nd_filter_moon", applies_to="both",
        title="ND Filter on the Moon",
        act=3, act_label="Brightness, Saturation & Filters",
        description=(
            "Applies to: any telescope. "
            "Full Moon through a 100 mm scope at moderate magnification "
            "saturates a real eye — visual observers reach for neutral-"
            "density filters (typical 1.0 or 2.0 OD) for comfort. The "
            "Before side shows the unfiltered view; switch the Filter "
            "control on the After side to ND-1.0 (10 % transmission) or "
            "ND-2.0 (1 %) and watch detail emerge as saturation lifts. "
            "ND filters do *not* change the angular size or PSF — only "
            "the photon count delivered to the detector.\n\n"
            "This is a BRIGHTNESS/SATURATION lesson, not a sharpness one. "
            "The Moon looks soft because the WHOLE disk (~31′) is shown in "
            "one small fixed-scale panel (~5″ per pixel) — far coarser than "
            "the 100 mm optics, which resolve ~1.4″. So no filter, exposure, "
            "or ND setting makes it 'crisper'; what the ND does is uncover "
            "detail that glare/saturation had blown out to white. Real "
            "crispness comes from MAGNIFICATION (enlarging that 1.4″ detail "
            "up to the eye's ~1′ limit) plus steady seeing — magnification "
            "is NOT modelled in this fixed full-disk view (the 'Eye blur' "
            "toggle approximates the eye's resolution, not magnification).\n\n"
            "Exit pupil = the width of the light beam leaving the eyepiece = "
            "aperture ÷ magnification = eyepiece focal length ÷ f-ratio. It "
            "sets how bright an EXTENDED object looks: a bigger exit pupil "
            "packs the same light into a smaller image, so surface brightness "
            "rises — until the exit pupil exceeds your eye's ~7 mm pupil, "
            "where the extra light spills around the iris and is wasted. The "
            "full Moon can be uncomfortably bright at a large exit pupil; an "
            "ND filter (or a smaller exit pupil, i.e. more magnification) "
            "tames it. Use the Exit pupil control to see the surface-"
            "brightness effect."
        ),
        learn_more_section="Photometry & Filters",
        before_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=100.0, focal_length=1000.0,
            enable_obstruction=False, spider_vanes=0,
        ),
        before_source=SourceConfig(source_type="Moon"),
        before_label="No filter",
        after_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=100.0, focal_length=1000.0,
            enable_obstruction=False, spider_vanes=0,
        ),
        after_source=SourceConfig(source_type="Moon"),
        after_label="With filter →",
        plot_function="plot_source_image",
        theory_function=None,
        # No telescope tweakables: the lesson is the FILTER. Aperture would
        # change brightness too (a confound for "what does the filter do"),
        # so it's dropped — same call as the vignetting scenario.
        tweakable_params=(),
        before_apply_vignetting=False,
        before_apply_coma=False,
        implemented=True,
        default_exposure=1.0,
        default_filter="ND-1.0",
        show_filter_combo=True,
        supports_realtime=True,
        # ND filter is a DETECTOR/saturation lesson → default Detector view.
        # Before side is pinned unfiltered so the comparison isolates the
        # filter; both sides follow the live exposure (before-side dynamic).
        default_display_stretch="linear",
        before_filter="None",
        both_sides_dynamic=True,
        before_telescope_dynamic=True,
        terminal_template=(
            "from telescope_gui.telescope_builder import build_telescope\n"
            "from telescope_sim.source.sources import Moon\n"
            "from telescope_sim.plotting import plot_source_image\n\n"
            "t = build_telescope(telescope_type='reflector',\n"
            "                    diameter={diameter}, focal_length=1000,\n"
            "                    primary_type='parabolic',\n"
            "                    enable_obstruction=False, spider_vanes=0)\n"
            "src = Moon()\n"
            "fig = plot_source_image(t, src, wavelength_nm={wavelength_nm},\n"
            "                        filter_name='ND-1.0',\n"
            "                        exposure_level=1.0)"
        ),
    ),

    ScenarioDefinition(
        id="color_filter_jupiter", applies_to="reflector",
        title="Colour Filters on Jupiter",
        act=3, act_label="Brightness, Saturation & Filters",
        description=(
            "Applies to: any telescope. "
            "Jupiter's belts and Great Red Spot absorb blue light (that's "
            "why they look orange/brown); its zones are white and reflect "
            "everything. Colour filters exploit this. The Before side is "
            "unfiltered; pick a filter on the After side:\n"
            "• W80A (light blue) — THE contrast filter: the blue-absorbing "
            "belts and Red Spot go dark against the bright zones, so features "
            "pop. (Default.)\n"
            "• W58 (green) — intermediate; boosts belt contrast.\n"
            "• W25 (red) — passes red, which zones, belts AND the Red Spot "
            "all reflect, so you get a fairly UNIFORM red disk with LITTLE "
            "feature contrast. Its real job is cutting blue haze / atmospheric "
            "dispersion, not boosting contrast (a common misconception).\n\n"
            "The image is NOT rescaled: both panels use the same exposure, so "
            "you see the TRUE effect — a colour filter blocks most of the "
            "spectrum, so the disk also gets dimmer (raise Exposure if it's "
            "too dark). That honest dimming is part of the trade-off a real "
            "observer weighs."
        ),
        learn_more_section="Photometry & Filters",
        before_telescope=_JUPITER_200MM,
        before_source=SourceConfig(source_type="Jupiter"),
        before_label="No filter",
        after_telescope=_JUPITER_200MM,
        after_source=SourceConfig(source_type="Jupiter"),
        after_seeing_arcsec=1.5,
        after_label="With Wratten filter →",
        plot_function="plot_source_image",
        theory_function=None,
        tweakable_params=("diameter", "seeing"),
        before_apply_vignetting=False,
        before_apply_coma=False,
        before_seeing_arcsec=1.5,
        implemented=True,
        # Jupiter at 200 mm with the REAL photo-texture (R4.12). 0.3× keeps
        # the unfiltered disk naturally exposed (muted belts + a realistic
        # Great Red Spot, not washed to white) while the W80A blue after-view
        # stays readable. Users can raise Exposure.
        default_exposure=0.3,
        default_filter="W80A (light blue)",
        show_filter_combo=True,
        supports_realtime=True,
        # Before side pinned unfiltered so the comparison isolates the
        # Wratten filter's colour-balance shift; both sides track
        # aperture/seeing (live before-side). Eye view is kept as the
        # default (planet detail reads well under asinh); the filter still
        # shifts colour balance + dims in both views.
        before_filter="None",
        both_sides_dynamic=True,
        before_telescope_dynamic=True,
        terminal_template=(
            "from telescope_gui.telescope_builder import build_telescope\n"
            "from telescope_sim.source.sources import Jupiter\n"
            "from telescope_sim.plotting import plot_source_image\n\n"
            "t = build_telescope(telescope_type='reflector',\n"
            "                    diameter={diameter}, focal_length=1000,\n"
            "                    primary_type='parabolic',\n"
            "                    enable_obstruction=True, obstruction_ratio=0.20,\n"
            "                    spider_vanes=4, spider_vane_width=2.0)\n"
            "src = Jupiter()\n"
            "fig = plot_source_image(t, src,\n"
            "                        seeing_arcsec={seeing_arcsec},\n"
            "                        wavelength_nm={wavelength_nm},\n"
            "                        filter_name='W25 (red)',\n"
            "                        exposure_level=0.25)"
        ),
    ),

    ScenarioDefinition(
        id="saturation_demo", applies_to="both",
        title="Bright + Dim: Dynamic Range",
        act=3, act_label="Brightness, Saturation & Filters",
        description=(
            "Applies to: any telescope. "
            "Seven stars spanning magnitude −1 to +6.5 — a DYNAMIC RANGE of "
            "~750× in flux (brightest ÷ faintest), laid out brightest (left) "
            "to faintest (right).\n"
            "\"DYNAMIC RANGE\" = the ratio of the brightest to the faintest "
            "signal a scene (or a device) contains. \"HDR\" (High Dynamic "
            "Range) means capturing scenes whose range exceeds what one "
            "linear exposure can record.\n"
            "DETECTOR (left, linear): try the Exposure control — there is NO "
            "single exposure that shows all seven. Expose for the faint stars "
            "and the bright ones saturate and bloom to white; expose for the "
            "bright ones and the faint ones vanish into black. A linear "
            "detector's dynamic range is limited by saturation at the top and "
            "noise at the bottom.\n"
            "EYE (right, logarithmic): the eye's log response compresses the "
            "whole range, so all seven stars read at once — the same trick "
            "photographers call HDR. No magic gain; just log vs linear."
        ),
        learn_more_section="Photometry & Filters",
        before_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=150.0, focal_length=1200.0,
            enable_obstruction=False, spider_vanes=0,
        ),
        before_source=SourceConfig(source_type="DynamicRangeField"),
        before_label="Detector view (linear)",
        after_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=150.0, focal_length=1200.0,
            enable_obstruction=False, spider_vanes=0,
        ),
        after_source=SourceConfig(source_type="DynamicRangeField"),
        after_label="Eye view (logarithmic) →",
        plot_function="plot_source_image",
        theory_function=None,
        tweakable_params=("diameter",),
        before_apply_vignetting=False,
        before_apply_coma=False,
        implemented=True,
        default_exposure=1.0,
        # R3.15: FIXED layout — Detector on the LEFT (linear; exposure shows
        # that no single exposure captures the whole range), Eye on the RIGHT
        # (pinned log; compresses the range so all stars show). No free View
        # combo; eye-blur toggle available. Both panes track aperture.
        before_display_stretch="linear",
        after_display_stretch="log",
        show_eye_blur_toggle=True,
        both_sides_dynamic=True,
        before_telescope_dynamic=True,
        terminal_template=(
            "from telescope_gui.telescope_builder import build_telescope\n"
            "from telescope_sim.source.sources import DoubleStar\n"
            "from telescope_sim.plotting import plot_source_image\n\n"
            "t = build_telescope(telescope_type='reflector',\n"
            "                    diameter={diameter}, focal_length=1200,\n"
            "                    primary_type='parabolic',\n"
            "                    enable_obstruction=False, spider_vanes=0)\n"
            "src = DoubleStar(separation_arcsec=8.0,\n"
            "                 magnitude_primary=0.0, magnitude_secondary=4.0)\n"
            "fig_det = plot_source_image(t, src, wavelength_nm={wavelength_nm},\n"
            "                            display_stretch='linear')\n"
            "fig_eye = plot_source_image(t, src, wavelength_nm={wavelength_nm},\n"
            "                            display_stretch='log')"
        ),
    ),

    # ------------------------------------------------------------------
    # Act 4: Real Objects
    # ------------------------------------------------------------------

    # (Jupiter Full Simulation removed 2026-07-12 — redundant: the same
    # effect toggles on a planet are shown by "Saturn with Rings" below,
    # whose ring structure shows PSF/seeing far better than Jupiter's
    # coarse bands; Jupiter itself is covered by "Colour Filters on
    # Jupiter" in Act 3.)

    ScenarioDefinition(
        id="saturn_rings", applies_to="reflector",
        title="Saturn with Rings",
        act=4, act_label="Real Objects",
        description=(
            "Saturn's ring system provides fine angular structure to probe the PSF. "
            "Spider vane diffraction spikes pass across the rings, and seeing blurs "
            "the Cassini division. Compare how aperture affects ring resolution."
        ),
        learn_more_section="Implemented Physics",
        before_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=200.0, focal_length=2000.0,
            enable_obstruction=False, spider_vanes=0,
        ),
        before_source=_SATURN,
        before_label="Ideal (no aberrations)",
        after_telescope=_JUPITER_200MM,
        after_source=_SATURN,
        after_seeing_arcsec=1.5,
        after_label="Realistic 200 mm Newtonian \u2192",
        plot_function="plot_source_image",
        theory_function=None,
        tweakable_params=("diameter", "focal_length", "obstruction_ratio",
                          "spider_vanes", "spider_vane_width", "seeing"),
        effect_toggles=("obstruction", "spider_vanes", "coma", "vignetting", "seeing"),
        implemented=True,
        # Same reasoning as jupiter_full — bright disk at 200 mm
        # saturates at exp=1.0; lower exposure preserves ring detail.
        default_exposure=0.25,
        supports_realtime=True,
        terminal_template=(
            "from telescope_sim.geometry import NewtonianTelescope\n"
            "from telescope_sim.source.sources import Saturn\n"
            "from telescope_sim.plotting import plot_source_image\n\n"
            "telescope = NewtonianTelescope(\n"
            "    primary_diameter={diameter},\n"
            "    focal_length={focal_length},\n"
            "    obstruction_ratio={obstruction_ratio:.2f},\n"
            "    spider_vanes={spider_vanes},\n"
            "    spider_vane_width={spider_vane_width},\n"
            "    enable_obstruction={enable_obstruction},\n"
            ")\n"
            "source = Saturn()\n"
            "fig = plot_source_image(\n"
            "    telescope, source,\n"
            "    seeing_arcsec={seeing_arcsec},\n"
            "    wavelength_nm={wavelength_nm},\n"
            ")"
        ),
    ),

    ScenarioDefinition(
        id="starfield_resolution", applies_to="reflector",
        title="Star Field Showcase",
        act=4, act_label="Real Objects",
        description=(
            "The capstone field \u2014 the same richly-populated, spectrally-"
            "coloured star field through IDEAL optics (left) and a REALISTIC "
            "200 mm f/4 Newtonian (right), with every effect individually "
            "toggleable so you can peel them back one at a time.\n"
            "The field is engineered to exercise all of them at once:\n"
            " \u2022 The bright on-axis star \u2014 SPIDER-VANE spikes (toggle the "
            "vanes) and the modified ring contrast from the central "
            "OBSTRUCTION.\n"
            " \u2022 COMA (toggle) affects the off-axis edge stars, but note: for a "
            "200 mm f/4 at this field the comatic blur (~0.5\u2033) is SMALLER than "
            "both the Airy disk and the 1.5\u2033 seeing, so the edge stars stay "
            "essentially round \u2014 toggling coma only slightly changes them. "
            "That is realistic. For the dramatic, obviously comet-shaped "
            "version, see the f-ratio & Coma scenario (Act 2), which isolates "
            "coma with spot diagrams at a fast f-ratio and no atmosphere.\n"
            " \u2022 SEEING blurs the whole field (1.5\u2033), softening the fine "
            "structure (including the spikes) that the space-like left panel "
            "keeps sharp.\n"
            "(Vignetting is not toggled here: for a 200 mm f/4 with a normally-"
            "sized secondary the fully-illuminated field is ~75 arcmin \u2014 far "
            "larger than this 5-arcmin field, so no star is dimmed. See the "
            "dedicated Vignetting scenario for the falloff curve, and the "
            "Vignetting diagram in Parameters & Physics for the geometry.)\n"
            " \u2022 A double-star ladder (8\u2033/4\u2033/2\u2033) \u2014 the tight pair blends under "
            "seeing; the wide pair stays split.\n"
            " \u2022 Colour + a wide magnitude range: only the BRIGHT stars carry a "
            "visible spectral tint (blue, orange, red); faint stars read "
            "near-white, as they do to the eye (colour vision needs flux). "
            "Watch bright-star halos and spikes overlap faint neighbours in "
            "the crowd.\n"
            "Left is shown in the same view as the right so the comparison is "
            "honest; switch Detector/Eye to compare linear vs perceptual."
        ),
        learn_more_section="Diffraction",
        before_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=200.0, focal_length=800.0,
            primary_type="parabolic",
            enable_obstruction=False, spider_vanes=0,
        ),
        before_source=SourceConfig(
            source_type="ShowcaseStarField",
            kwargs={"field_radius_arcsec": 150.0},
        ),
        before_label="Ideal optics (no aberrations)",
        # Left = clean reference: no obstruction/spider/coma/vignetting/seeing.
        before_apply_coma=False,
        before_apply_vignetting=False,
        after_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=200.0, focal_length=800.0,
            primary_type="parabolic",
            enable_obstruction=True, obstruction_ratio=0.20,
            spider_vanes=4, spider_vane_width=2.5,
        ),
        after_source=SourceConfig(
            source_type="ShowcaseStarField",
            kwargs={"field_radius_arcsec": 150.0},
        ),
        # 1.5\u2033 "good seeing" \u2014 softens but doesn't erase the spikes/coma;
        # toggle seeing off to see the field at space-like sharpness.
        after_seeing_arcsec=1.5,
        after_label="Realistic 200 mm f/4 \u2014 toggle effects \u2192",
        plot_function="plot_source_image",
        theory_function=None,
        tweakable_params=("diameter", "focal_length", "obstruction_ratio",
                          "spider_vanes", "spider_vane_width", "seeing"),
        # Vignetting omitted: the fully-illuminated field (~75\u2032) dwarfs this
        # 5\u2032 field, so a vignetting toggle would be a dead no-op. Covered by
        # the dedicated Vignetting scenario (curve plot).
        effect_toggles=("obstruction", "spider_vanes", "coma", "seeing"),
        both_sides_dynamic=True,
        before_telescope_dynamic=False,  # left stays the ideal reference
        default_display_stretch="log",
        implemented=True,
        terminal_template=(
            "from telescope_sim.geometry import NewtonianTelescope\n"
            "from telescope_sim.source.sources import ShowcaseStarField\n"
            "from telescope_sim.plotting import plot_source_image\n\n"
            "telescope = NewtonianTelescope(\n"
            "    primary_diameter={diameter},\n"
            "    focal_length={focal_length},\n"
            "    obstruction_ratio={obstruction_ratio:.2f},\n"
            "    spider_vanes={spider_vanes},\n"
            "    spider_vane_width={spider_vane_width},\n"
            "    enable_obstruction={enable_obstruction},\n"
            ")\n"
            "source = ShowcaseStarField()\n"
            "fig = plot_source_image(\n"
            "    telescope, source,\n"
            "    seeing_arcsec={seeing_arcsec},\n"
            "    wavelength_nm={wavelength_nm},\n"
            ")"
        ),
    ),
]


def get_scenarios_by_act() -> dict[int, list[ScenarioDefinition]]:
    """Return scenarios grouped by act number."""
    result: dict[int, list[ScenarioDefinition]] = {1: [], 2: [], 3: [], 4: []}
    for s in SCENARIOS:
        result[s.act].append(s)
    return result


def get_scenario_by_id(scenario_id: str) -> ScenarioDefinition | None:
    """Look up a single scenario by its ID string."""
    for s in SCENARIOS:
        if s.id == scenario_id:
            return s
    return None


def get_first_implemented() -> ScenarioDefinition | None:
    """Return the first implemented scenario in registry order."""
    for s in SCENARIOS:
        if s.implemented:
            return s
    return None

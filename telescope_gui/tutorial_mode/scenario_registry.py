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
        before_label="200 mm aperture",
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
        before_source=SourceConfig(source_type="DoubleStar", kwargs={"separation_arcsec": 1.0}),
        before_label="100 mm \u2014 Rayleigh 1.38\u2033",
        after_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=200.0, focal_length=1000.0,
            enable_obstruction=False, spider_vanes=0,
        ),
        after_source=SourceConfig(source_type="DoubleStar", kwargs={"separation_arcsec": 1.0}),
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
        before_label="No obstruction",
        after_telescope=_OBSTRUCTED_200MM,
        after_source=_POINT,
        after_label="With obstruction \u2192",
        plot_function="plot_psf_2d",
        theory_function="compute_central_obstruction_theory",
        tweakable_params=("obstruction_ratio",),
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
            "Note: the singlet ray trace also shows spherical aberration \u2014 within a "
            "single colour, marginal rays cross the axis closer to the lens than "
            "paraxial rays, so same-colour rays do not all converge to one point. A "
            "spherical singlet has both CA and SA; the achromat reduces both; the APO "
            "models here are idealised to zero SA so only CA remains visible."
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
            "each shifts the curve."
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
            "marginal rays focus closer than paraxial rays. The 1D PSF profile (left) "
            "shows the radial intensity drop; the geometric spot diagram (right) shows "
            "the actual ray landing pattern. Toggle to a parabolic primary to see the "
            "blur disappear; increasing f-ratio shrinks the blur as 1/f³."
        ),
        learn_more_section="Implemented Physics",
        before_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=200.0, focal_length=800.0,
            primary_type="spherical",
            enable_obstruction=False, spider_vanes=0,
        ),
        before_source=_POINT,
        before_label="1D PSF profile",
        after_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=200.0, focal_length=800.0,
            primary_type="spherical",
            enable_obstruction=False, spider_vanes=0,
        ),
        after_source=_POINT,
        after_label="Geometric spot diagram →",
        plot_function="plot_psf_profile",
        secondary_plot_function="plot_spot_diagram_telescope",
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
        before_label="Achromat, 1.5″ seeing",
        after_telescope=_ACHROMAT_80MM,
        after_source=SourceConfig(source_type="MultiColorStarField"),
        after_seeing_arcsec=1.5,
        after_polychromatic=True,
        after_label="With seeing \u2192",
        plot_function="plot_source_image",
        theory_function=None,
        tweakable_params=("seeing", "objective_type"),
        implemented=True,
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
            "Both panels show the same telescope and seeing \u2014 the left panel overlays "
            "the theoretical limits (Airy radius and seeing FWHM) so you can read "
            "which one is dominating. Once aperture exceeds D\u2099\u1d63\u1d62\u209c = "
            "1.22\u03bb/\u03b8\u209b\u1d49\u1d49\u1d4f\u1d5f\u1d57 the atmosphere limits "
            "resolution and bigger apertures only gather more light."
        ),
        learn_more_section="Atmospheric Seeing",
        before_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=200.0, focal_length=1000.0,
            enable_obstruction=False, spider_vanes=0,
        ),
        before_source=_POINT,
        before_seeing_arcsec=2.5,
        before_label="With theoretical-limit overlays",
        after_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=200.0, focal_length=1000.0,
            enable_obstruction=False, spider_vanes=0,
        ),
        after_source=_POINT,
        after_seeing_arcsec=2.5,
        after_label="Rendered image \u2192",
        plot_function="plot_source_image",
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
            "1.5\u2033 \u2018good\u2019 atmospheric seeing. Left panel shows a spot-diagram grid "
            "across the field at 0/30/60/120 arcsec off-axis; the right panel shows "
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
    # Act 3: Real Objects
    # ------------------------------------------------------------------

    ScenarioDefinition(
        id="jupiter_full", applies_to="reflector",
        title="Jupiter Full Simulation",
        act=3, act_label="Real Objects",
        description=(
            "Simulate Jupiter with all optical effects active. Toggle individual effects "
            "on/off to isolate each contribution: obstruction adds secondary ring contrast, "
            "spider vanes create diffraction spikes, seeing blurs fine detail."
        ),
        learn_more_section="Implemented Physics",
        before_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=200.0, focal_length=2000.0,
            enable_obstruction=False, spider_vanes=0,
        ),
        before_source=_JUPITER,
        before_label="Ideal (no aberrations)",
        after_telescope=_JUPITER_200MM,
        after_source=_JUPITER,
        after_seeing_arcsec=1.5,
        after_label="Realistic 200 mm Newtonian \u2192",
        plot_function="plot_source_image",
        theory_function=None,
        tweakable_params=("diameter", "focal_length", "obstruction_ratio",
                          "spider_vanes", "spider_vane_width", "seeing"),
        effect_toggles=("obstruction", "spider_vanes", "coma", "vignetting", "seeing"),
        implemented=True,
        # Jupiter is bright: at 200 mm aperture, the disk surface flux
        # × aperture² saturates well above 1.0. Lower exposure brings
        # the disk into the linear range so bands and limb darkening
        # remain visible without complete clipping.
        default_exposure=0.25,
        terminal_template=(
            "from telescope_sim.geometry import NewtonianTelescope\n"
            "from telescope_sim.source.sources import Jupiter\n"
            "from telescope_sim.plotting import plot_source_image\n\n"
            "telescope = NewtonianTelescope(\n"
            "    primary_diameter={diameter},\n"
            "    focal_length={focal_length},\n"
            "    obstruction_ratio={obstruction_ratio:.2f},\n"
            "    spider_vanes={spider_vanes},\n"
            "    spider_vane_width={spider_vane_width},\n"
            "    enable_obstruction={enable_obstruction},\n"
            ")\n"
            "source = Jupiter()\n"
            "fig = plot_source_image(\n"
            "    telescope, source,\n"
            "    seeing_arcsec={seeing_arcsec},\n"
            "    wavelength_nm={wavelength_nm},\n"
            ")"
        ),
    ),

    ScenarioDefinition(
        id="saturn_rings", applies_to="reflector",
        title="Saturn with Rings",
        act=3, act_label="Real Objects",
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
        title="Star Field Resolution",
        act=3, act_label="Real Objects",
        description=(
            "Single star (left) shows PSF structure in detail \u2014 Airy rings, diffraction "
            "spikes, and seeing blur. Star field (right) shows how these effects scale "
            "across a crowded field: halos overlap, spikes cross neighbours, bright stars "
            "bleed into faint ones. Toggle effects to see each contribution."
        ),
        learn_more_section="Diffraction",
        before_telescope=_SPIDER_200MM,
        before_source=_POINT,
        before_label="Single star \u2014 PSF detail",
        after_telescope=_SPIDER_200MM,
        after_source=SourceConfig(
            source_type="StarFieldResolutionField",
            kwargs={"field_radius_arcsec": 300.0},
        ),
        # 1.5\u2033 "good seeing". Narrow enough that the global normalisation
        # by intrinsic peak keeps stars bright; the f/4 scope makes edge
        # coma visible without atmospheric blur swamping it.
        after_seeing_arcsec=1.5,
        after_label="Star field \u2014 population effects \u2192",
        plot_function="plot_source_image",
        theory_function=None,
        tweakable_params=("diameter", "focal_length", "obstruction_ratio",
                          "spider_vanes", "spider_vane_width", "seeing"),
        effect_toggles=("obstruction", "spider_vanes", "coma", "vignetting", "seeing"),
        both_sides_dynamic=True,
        before_telescope_dynamic=True,
        implemented=True,
        terminal_template=(
            "from telescope_sim.geometry import NewtonianTelescope\n"
            "from telescope_sim.source.sources import StarField\n"
            "from telescope_sim.plotting import plot_source_image\n\n"
            "telescope = NewtonianTelescope(\n"
            "    primary_diameter={diameter},\n"
            "    focal_length={focal_length},\n"
            "    obstruction_ratio={obstruction_ratio:.2f},\n"
            "    spider_vanes={spider_vanes},\n"
            "    spider_vane_width={spider_vane_width},\n"
            "    enable_obstruction={enable_obstruction},\n"
            ")\n"
            "source = StarField()\n"
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
    result: dict[int, list[ScenarioDefinition]] = {1: [], 2: [], 3: []}
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

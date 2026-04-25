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

    # For Act 3: which effects can be individually toggled on/off
    effect_toggles: tuple[str, ...] = field(default_factory=tuple)

    # Whether this scenario is fully implemented (False = placeholder "coming soon")
    implemented: bool = False

    # Python API terminal command template (use {param} placeholders)
    terminal_template: str = ""


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
    telescope_type="Newtonian", diameter=200.0, focal_length=1000.0,
    enable_obstruction=True, obstruction_ratio=0.20, spider_vanes=4, spider_vane_width=2.0,
)
_FAST_200MM = TelescopeConfig(
    telescope_type="Newtonian", diameter=200.0, focal_length=800.0,  # f/4
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
        id="airy_disk",
        title="Airy Disk",
        act=1, act_label="Isolated Effects",
        description=(
            "A circular aperture diffracts light into a central bright disk surrounded by "
            "concentric rings — the Airy pattern. The first dark ring radius is exactly "
            "1.22\u03bb/D. Increase aperture to see the rings shrink; decrease to see them grow."
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
        tweakable_params=("diameter", "focal_length"),
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
        id="rayleigh_criterion",
        title="Rayleigh Criterion",
        act=1, act_label="Isolated Effects",
        description=(
            "Two stars separated by exactly the Rayleigh limit (1.22\u03bb/D) show a just-noticeable "
            "dip between the two Airy disks. Decrease separation below the limit to see them merge; "
            "increase to see them clearly resolved."
        ),
        learn_more_section="Diffraction",
        before_telescope=_CLEAN_200MM,
        before_source=SourceConfig(source_type="DoubleStar", kwargs={"separation_arcsec": 0.69}),
        before_label="At Rayleigh limit",
        after_telescope=_CLEAN_200MM,
        after_source=SourceConfig(source_type="DoubleStar", kwargs={"separation_arcsec": 0.69}),
        after_label="Adjust separation \u2192",
        plot_function="plot_source_image",
        theory_function="compute_rayleigh_theory",
        tweakable_params=("diameter", "separation_arcsec"),
        implemented=True,
        terminal_template=(
            "from telescope_sim.geometry import NewtonianTelescope\n"
            "from telescope_sim.source.sources import DoubleStar\n"
            "from telescope_sim.plotting import plot_source_image\n\n"
            "telescope = NewtonianTelescope(\n"
            "    primary_diameter={diameter},\n"
            "    focal_length=1000,\n"
            "    enable_obstruction=False,\n"
            ")\n"
            "source = DoubleStar(separation_arcsec={separation_arcsec})\n"
            "fig = plot_source_image(telescope, source, wavelength_nm={wavelength_nm})"
        ),
    ),

    ScenarioDefinition(
        id="central_obstruction",
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
        id="spider_vanes",
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
        id="chromatic_aberration",
        title="Chromatic Aberration",
        act=1, act_label="Isolated Effects",
        description=(
            "A singlet lens refracts different wavelengths to different focal points, producing "
            "colour fringing. An achromatic doublet brings two wavelengths to the same focus, "
            "dramatically reducing fringing. Switch objective type to compare."
        ),
        learn_more_section="Chromatic Aberration",
        before_telescope=_SINGLET_80MM,
        before_source=_POINT,
        before_polychromatic=True,
        before_label="Singlet refractor",
        after_telescope=_SINGLET_80MM,
        after_source=_POINT,
        after_polychromatic=True,
        after_label="Adjust objective \u2192",
        plot_function="plot_polychromatic_ray_trace",
        theory_function=None,
        tweakable_params=("objective_type",),
        implemented=True,
        terminal_template=(
            "from telescope_gui.telescope_builder import build_telescope\n"
            "from telescope_sim.plotting.ray_trace_plot import plot_polychromatic_ray_trace\n\n"
            "telescope = build_telescope(\n"
            "    telescope_type='Refractor',\n"
            "    diameter=80, focal_length=640,\n"
            "    objective_type='{objective_type}',\n"
            ")\n"
            "fig = plot_polychromatic_ray_trace(telescope)"
        ),
    ),

    ScenarioDefinition(
        id="vignetting",
        title="Vignetting",
        act=1, act_label="Isolated Effects",
        description=(
            "Off-axis light in a Newtonian is clipped by the secondary mirror, dimming "
            "stars near the field edge. The fully-illuminated field depends on f-ratio "
            "and secondary size. Compare uniform illumination to the vignetted result."
        ),
        learn_more_section="Vignetting",
        before_telescope=_SPIDER_200MM,
        before_source=_STARFIELD,
        before_apply_vignetting=False,
        before_label="No vignetting",
        after_telescope=_SPIDER_200MM,
        after_source=_STARFIELD,
        after_label="With vignetting \u2192",
        plot_function="plot_source_image",
        theory_function="compute_vignetting_theory",
        tweakable_params=("diameter", "focal_length"),
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

    # ------------------------------------------------------------------
    # Act 2: Compounding Effects
    # ------------------------------------------------------------------

    ScenarioDefinition(
        id="obstruction_plus_spiders",
        title="Obstruction + Spider Vanes",
        act=2, act_label="Compounding Effects",
        description=(
            "Combine central obstruction and spider vanes to see how the enhanced secondary "
            "rings interact with diffraction spikes. The PSF is now the product of both effects "
            "simultaneously \u2014 not simply the sum."
        ),
        learn_more_section="Central Obstruction",
        before_telescope=_OBSTRUCTED_200MM,
        before_source=_POINT,
        before_label="Obstruction only",
        after_telescope=_SPIDER_200MM,
        after_source=_POINT,
        after_label="Obstruction + spiders \u2192",
        plot_function="plot_psf_2d",
        theory_function=None,
        tweakable_params=("obstruction_ratio", "spider_vanes", "spider_vane_width"),
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
        id="chromatic_plus_seeing",
        title="Chromatic Aberration + Seeing",
        act=2, act_label="Compounding Effects",
        description=(
            "Atmospheric seeing blurs the image on scales that can mask chromatic fringing. "
            "Under excellent seeing the colour fringes are visible; under poor seeing they "
            "wash out. This shows when chromatic aberration actually matters in practice."
        ),
        learn_more_section="Chromatic Aberration",
        before_telescope=_SINGLET_80MM,
        before_source=_POINT,
        before_polychromatic=True,
        before_label="No seeing (space)",
        after_telescope=_SINGLET_80MM,
        after_source=_POINT,
        after_seeing_arcsec=2.5,
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
        id="aperture_vs_seeing",
        title="Aperture vs Seeing",
        act=2, act_label="Compounding Effects",
        description=(
            "Once aperture exceeds the critical value D\u2099\u1d63\u1d62\u209c = 1.22\u03bb/\u03b8\u209b\u1d49\u1d49\u1d4f\u1d5f\u1d57, "
            "the atmosphere limits resolution, not the mirror. Bigger aperture then only gathers "
            "more light \u2014 not more detail. See the simulation match this prediction."
        ),
        learn_more_section="Atmospheric Seeing",
        before_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=100.0, focal_length=500.0,
            enable_obstruction=False, spider_vanes=0,
        ),
        before_source=_POINT,
        before_seeing_arcsec=2.5,
        before_label="100 mm + seeing 2.5\"",
        after_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=400.0, focal_length=2000.0,
            enable_obstruction=False, spider_vanes=0,
        ),
        after_source=_POINT,
        after_seeing_arcsec=2.5,
        after_label="400 mm + seeing 2.5\" \u2192",
        plot_function="plot_source_image",
        theory_function="compute_aperture_vs_seeing_theory",
        tweakable_params=("diameter", "seeing"),
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
        id="fratio_coma",
        title="f-ratio and Coma",
        act=2, act_label="Compounding Effects",
        description=(
            "The coma-free field scales as f\u00b2: halving the f-ratio reduces usable field by 4\u00d7. "
            "Adjust the f-ratio and watch the coma-free field prediction update. "
            "This is why planetary imagers prefer slow telescopes."
        ),
        learn_more_section="Coma",
        before_telescope=_FAST_200MM,
        before_source=_POINT,
        before_label="f/4 — narrow coma-free field",
        after_telescope=_SLOW_200MM,
        after_source=_POINT,
        after_label="f/8 — wider coma-free field \u2192",
        plot_function="plot_coma_field_analysis",
        theory_function="compute_coma_fratio_theory",
        tweakable_params=("focal_length", "diameter"),
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
        id="jupiter_full",
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
        id="saturn_rings",
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
        id="starfield_resolution",
        title="Star Field Resolution",
        act=3, act_label="Real Objects",
        description=(
            "A random star field shows how aperture, seeing, and aberrations combine "
            "to determine how many stars are cleanly resolved. Point sources in a "
            "crowded field reveal overlapping PSF halos and diffraction spikes."
        ),
        learn_more_section="Diffraction",
        before_telescope=TelescopeConfig(
            telescope_type="Newtonian", diameter=200.0, focal_length=1000.0,
            enable_obstruction=False, spider_vanes=0,
        ),
        before_source=_STARFIELD,
        before_label="Ideal (no aberrations)",
        after_telescope=_SPIDER_200MM,
        after_source=_STARFIELD,
        after_seeing_arcsec=1.5,
        after_label="Realistic 200 mm Newtonian \u2192",
        plot_function="plot_source_image",
        theory_function=None,
        tweakable_params=("diameter", "focal_length", "obstruction_ratio",
                          "spider_vanes", "spider_vane_width", "seeing"),
        effect_toggles=("obstruction", "spider_vanes", "coma", "vignetting", "seeing"),
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

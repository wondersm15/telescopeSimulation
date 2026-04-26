# Plan: Tutorial Tab Bug Fixes + Physics Validation Pass

This plan covers the bugs surfaced by user testing of the Tutorial & Testing
tab, plus the design-feedback items, plus a content pass on the Parameters &
Physics tab. It is structured for sequential implementation by Sonnet.

The plan is divided into **investigation** (read-only), **physics-engine
fixes**, **GUI changes**, **tutorial design redesigns**, **new scenarios**,
**physics-tab content**, and **tests**. Implement in the order given. Run the
full test suite after each phase.

---

## Phase 0 — Investigation (read-only)

### I0.1 — Trace why aperture has zero effect on the rendered double-star/point image

**Confirmed by numerical test**: rendering a `PointSource` or `DoubleStar`
through a Newtonian at 100/200/400/800 mm produces **byte-identical** pixel
arrays. Peak normalises to 1.0; pixel-count above half-max is identical.

The agent's earlier theory (FOV doesn't scale with Airy radius) is necessary
but not sufficient — the FOV is fixed but the Airy *kernel* IS computed
correctly per aperture (Airy radius shrinks 1.4″ → 0.17″ from 100mm → 800mm).
Yet the kernel is somehow not making it onto the rendered image.

**What to investigate** in `telescope_sim/plotting/ray_trace_plot.py`:

1. Read `_render_source_through_telescope` end to end (~3020–3225). Identify
   every place a PSF is computed and convolved. Look for:
   - Whether the analytical method (`method="analytical"`, the default)
     actually convolves with a PSF kernel, or just calls `source.render_ideal`
     directly.
   - Whether the result is renormalised (`/ image.max()`, `/ image.sum()`)
     post-convolution in a way that wipes out aperture differences.
   - Whether the PSF kernel size depends on aperture but the kernel *contents*
     are normalised to a fixed peak.

2. Read `source.render_ideal` for `PointSource` and `DoubleStar` in
   `telescope_sim/source/sources.py`. Confirm whether this returns a delta
   spike (which would then be convolved with the PSF kernel) or a pre-blurred
   pattern (which would mask aperture differences).

3. The PSF kernel size in pixels likely scales with aperture (smaller kernel
   for bigger aperture). Convolving a delta with a kernel produces the kernel
   itself — but if the kernel is then normalised to peak 1.0 and placed on a
   fixed FOV, the *visual* size on the image depends on `kernel_pixels /
   total_pixels`. So bigger aperture → smaller kernel → smaller dot. That
   should produce visible difference. Unless...

4. ...the source isn't being rendered as a delta. Check
   `PointSource.render_ideal` — does it produce a delta or a small Gaussian?
   If a small Gaussian, its width may dominate the convolution result and
   wipe out aperture-dependent variation.

**Output of investigation**: identify the *exact* line where aperture
information is lost. Report findings before making any change.

---

## Phase 1 — Physics-engine fixes (one-liners + small touches)

### F1.1 — Spider vane angle bug (Bug 2)

**File**: `telescope_sim/physics/fft_psf.py`, line 48 inside
`build_pupil_mask`.

**Change**:
```python
# Before:
angle = k * np.pi / spider_vanes
# After:
angle = 2.0 * k * np.pi / spider_vanes
```

**Why**: `π/N` spacing places vanes at non-orthogonal angles; with N=4 you
get vanes at 0°, 45°, 90°, 135° — no two parallel — producing 8 distinct
spike directions. `2π/N` spacing places vanes at 0°, 90°, 180°, 270°;
opposite vanes are parallel and their spike pairs collapse, giving the
standard 4 spikes for an even N (and 2N for odd N).

**Test**: in `tests/test_fft_psf.py` (or create one), assert that with
`spider_vanes=4` the FFT PSF has bright peaks along x and y axes only, and
**not** along the 45° diagonals. A simple check:
1. Compute the PSF for `spider_vanes=4`.
2. Sum intensity along radial slices at 0°, 45°, 90°, 135°.
3. Assert the 0° and 90° sums are noticeably brighter than the 45° / 135°
   sums (e.g. ratio > 2.0).

### F1.2 — Polychromatic source-image gate inverted (Bug 3a)

**File**: `telescope_sim/plotting/ray_trace_plot.py`, lines 3163–3166 inside
`plot_source_image`.

**Change**:
```python
# Before:
_use_chromatic = (polychromatic
                  and hasattr(telescope, 'objective')
                  and not getattr(telescope, 'corrected_optics', False))
# After:
_use_chromatic = (polychromatic
                  and hasattr(telescope, 'objective'))
```

**Why**: corrected optics (achromat/apo) should still render polychromatically
in colour; the per-channel `chromatic_defocus()` already produces *smaller*
defocus for corrected designs (`f / 2500` vs full Cauchy for singlet), so
the visual difference will be smaller without being zero.

**Test**: in `tests/test_polychromatic.py` (create if missing), call
`plot_source_image` with a singlet refractor and an achromat refractor, both
`polychromatic=True`. Assert the achromat result has lower per-channel
deviation than the singlet.

### F1.3 — Display image_rgb instead of grayscale luminance (Bug 6)

**File**: `telescope_sim/plotting/ray_trace_plot.py`, around lines
3201–3204 and the call site that passes `image` to `_draw_source_on_axes`
(line ~3595).

**Change**: when `_use_chromatic` is true, pass `image_rgb` to
`_draw_source_on_axes` (or whichever draw call follows) instead of the
grayscale-collapsed `image`. Inspect `_draw_source_on_axes` to see how it
handles a 3-channel RGB array (it appears to already handle this — verify).

**Why**: per-channel chromatic rendering is computed but immediately
collapsed to luminance and displayed grayscale — the colour fringing
information is thrown away.

**Test**: render a polychromatic singlet PointSource through
`plot_source_image`, extract the saved figure as RGB, assert that the R/G/B
channels of the figure are not all equal in the central peak region (i.e.
colour information is present).

### F1.4 — Aperture-dependent PSF in source rendering (Bug 1)

**File**: To be determined by Phase 0 investigation.

**Two-part fix**:
1. **The kernel must visibly change the image** as aperture changes. Specific
   change depends on what investigation finds.
2. **FOV should scale with Airy radius** so a bigger aperture's tighter PSF
   is visibly tighter on screen, not just on a tighter axis. Modify in
   `_render_source_through_telescope` (~line 3065):
   ```python
   # Before:
   half_fov_arcsec = source.field_extent_arcsec / 2.0
   # After:
   airy_radius_arcsec = ...  # already computed nearby; reuse
   half_fov_arcsec = max(airy_radius_arcsec * 8.0, source.field_extent_arcsec / 2.0)
   ```
   This keeps the FOV at "10× source extent" for big sources but makes the
   FOV expand for tiny sources viewed through small apertures (where Airy is
   larger than source separation).

**Test**: render a PointSource at D=100mm and D=400mm. Assert the rendered
images differ (`np.allclose` should be False). Assert the half-fov differs
when a small aperture forces the Airy radius to dominate.

### F1.5 — Extended-source PSF kernel size (Bug 4)

**File**: `telescope_sim/plotting/ray_trace_plot.py`, around lines 3148–3152
inside `_render_source_through_telescope` (the extended-source branch).

**Change**: when `telescope.spider_vanes > 0`, increase `psf_angular_half`
to encompass the typical spike length, not just 8× Airy radius. Spider
spikes from FFT diffraction extend to roughly `lambda * f / vane_width` in
mm, which is a reasonable upper bound on spike extent. A simpler heuristic:
when spiders are active, use `psf_angular_half = max(default, 60 *
airy_radius_arcsec)`.

**Why**: the PSF kernel is currently sized to ~8× Airy radius. Spider
spikes physically extend much further; the kernel truncates them, so
convolving with Jupiter (~50″ disk) clips spikes at the kernel edge — they
don't show on the planet.

**Trade-off**: bigger kernel = slower convolution. For Jupiter/Saturn this
is acceptable (one-shot rendering, not animated). Cap kernel size at e.g.
`min(psf_n_img, 512)` to avoid pathological cases.

**Test**: render Jupiter through a 200mm Newtonian with spider_vanes=4,
confirm the resulting image has bright structure beyond the Jupiter disk
itself (spikes extending out).

### F1.6 — Verify chromatic ray-trace inset zoom is informative (Bug 3b)

**Status**: investigation showed the achromat/apo classes **do** trace rays
correctly per wavelength. The issue is purely visual: the focal-spread for
an 80mm f/8 achromat is ≈0.024mm vs ≈2.4mm for a singlet — the corrected
case is visually identical to "no aberration" in the current plot inset.

**Two options**:
- (A) Tune the inset zoom dynamically per objective so the spread is always
  visible at a similar fractional size.
- (B) Annotate the inset with the numerical focal spread (mm), so even when
  visually nil, the user sees the number.
- (C) Default the chromatic_aberration scenario to a faster, larger-aperture
  refractor (e.g. 100mm f/5 instead of 80mm f/8) where singlet aberration is
  more dramatic and achromat correction is more impressive in absolute terms.

**Recommended**: (B) + (C). Add a numerical readout label and switch the
default config to amplify the effect.

**File**: `telescope_sim/plotting/ray_trace_plot.py` `plot_polychromatic_ray_trace`
function (~lines 1398–1547). Add text annotation showing focal spread in
mm. Then in `scenario_registry.py`, change `_SINGLET_80MM` etc. to
`diameter=100, focal_length=500` (f/5).

---

## Phase 2 — GUI changes

### G2.1 — Both-sides-dynamic flag (Bug 5)

**File**: `telescope_gui/tutorial_mode/scenario_registry.py`. Add to
`ScenarioDefinition`:
```python
both_sides_dynamic: bool = False
```

**File**: `telescope_gui/tutorial_mode/tutorial_tab.py`. Modify
`_on_update_clicked`:
```python
def _on_update_clicked(self):
    if self._current_scenario and self._current_scenario.both_sides_dynamic:
        self._render_before(self._current_scenario)
    self._render_after()
```

Also mirror this in `_on_psf_view_changed` (already calls `_render_before`
unconditionally, leave as-is).

**Apply to**: `rayleigh_criterion` scenario only.

### G2.2 — Independent two-side parameter controls (for `obstruction_plus_spiders`)

The user wants `obstruction_plus_spiders` to allow tweaking *both* sides
independently. This is a one-off design where the comparison is between two
specific configurations, both of which should be tunable.

**Approach**: introduce optional `tweakable_params_before: tuple = ()` field
on `ScenarioDefinition`. When non-empty, the controls panel renders TWO
groups of widgets — one "Before" group and one "After" group — and
`_render_before` reads the before-group's values.

This is a non-trivial change. Sub-steps:

1. Add `tweakable_params_before` field to `ScenarioDefinition`.
2. Add a second `_tweak_widgets_before: dict[str, QWidget]` map in `TutorialTab`.
3. In `_rebuild_controls`, when `tweakable_params_before` is non-empty,
   build a second QGroupBox labelled "Before" for those controls, and label
   the existing one as "After".
4. Add `_collect_params_before` and use it to build a separate
   `before_telescope` in `_render_before`.
5. Handle widget cleanup symmetrically.

### G2.3 — Per-scenario PSF-toggle disable

Spider-vanes and obstruction+spiders scenarios should not show the 1D/2D
PSF toggle (1D radial profile washes out azimuthal structure).

**Approach**: add `show_psf_toggle: bool = True` to `ScenarioDefinition`.
Set `False` for `spider_vanes` and `obstruction_plus_spiders`. In
`_rebuild_controls`, only call `_add_psf_view_combo` when the field is true.

### G2.4 — Lock axes across all subplots in coma plots

`plot_coma_field_analysis` returns a multi-subplot figure. The current axis
lock only modifies `fig.axes[0]`. Modify
`tutorial_tab.py:_render_after` and `_render_before` axis-lock blocks to
iterate `for ax in fig.axes` and apply the captured xlim/ylim to each spot
diagram subplot. Also capture per-axis limits in `_render_before` so each
subplot is locked to its own pre-change limits, not the same value across
all subplots.

This requires `_before_axis_limits` to become a list of tuples instead of a
single tuple.

### G2.5 — Vignetting scenario: add curve-analysis subplot toggle

Add a "View" combo (similar to the PSF toggle) for the vignetting scenario:
"Star field" vs "Vignetting curve". When "Vignetting curve" is selected, the
plot shows illumination fraction vs field angle (a 1D plot the user can
read directly).

The vignetting curve doesn't currently have a plot function. Add
`plot_vignetting_curve(telescope, ...)` to
`telescope_sim/plotting/ray_trace_plot.py` — it's a one-screen function:
sample `telescope.compute_vignetting(angle)` over a range of angles, plot.

Wire this into `_call_plot_function` and into the vignetting scenario's
view-toggle handling.

---

## Phase 3 — Tutorial design redesigns

### D3.1 — Rayleigh: aperture-driven, separation tweakable on both sides

Redesign:
- **Before** side: 100mm aperture, source separation = X (slider)
- **After** side: 200mm aperture, source separation = X (same slider)
- Slider controls separation, applies to both
- Theory readout shows the Rayleigh limit for *each* aperture so the user
  sees "100mm needs ≥1.4″" vs "200mm needs ≥0.69″"

This requires:
- `before_telescope` and `after_telescope` to differ in aperture (both
  refractors or both Newtonians without obstruction is fine — keep them
  comparable on everything except aperture)
- `tweakable_params=("separation_arcsec",)` only — aperture not user-tunable
  (it's the lesson)
- `both_sides_dynamic=True` (G2.1)
- Theory readout to show two values — extend `TheoryReadoutPanel` to support
  showing two limits side-by-side, or display "Rayleigh: 1.40″ (D=100) /
  0.69″ (D=200)" as a single string.

### D3.2 — Vignetting: on/off toggle, drop aperture/focal-length tweaking

Currently the vignetting scenario has `tweakable_params=("diameter",
"focal_length")` — this confounds the lesson with resolution and coma
changes. Redesign:
- **Before** side: starfield, vignetting disabled (`before_apply_vignetting=False`)
- **After** side: starfield, vignetting enabled
- No tweakable telescope params; only the view toggle (G2.5) and the
  effect-toggle row (so the user can turn vignetting on/off on the after
  side as well)

### D3.3 — Obstruction + spiders: label and independent controls

Apply G2.2. Default config:
- **Before** side: obstruction-only (label shows "20% obstruction, 0 vanes")
- **After** side: obstruction + spiders (label shows current values)
- Both sides tweakable: `tweakable_params_before=("obstruction_ratio",)`
  and `tweakable_params=("obstruction_ratio", "spider_vanes",
  "spider_vane_width")`.

Update before/after labels to reflect parameter values dynamically — when
the user changes the "before" obstruction, the before-side label should
update to match.

### D3.4 — Chromatic + seeing: keep, but fix B&W (3a + 6) and amplify f-ratio

After F1.2 + F1.3, polychromatic singlet + seeing should now show colour
fringing in the rendered image. Verify visually. If still subtle, change
`_SINGLET_80MM` to a faster spec (F1.6 option C) so the colour is more
dramatic.

If the result is still unconvincing after fixes, the user offered the
fallback of removing or repurposing the scenario. Decision deferred until
post-fix verification.

### D3.5 — Coma scenario: locked axes (G2.4) + side-by-side starfield

`fratio_coma` currently uses `plot_coma_field_analysis` which is a spot-
diagram grid + RMS plot. The user wants:
- Left: existing `plot_coma_field_analysis` (spot grid) — keep
- Right: simulated star field at the same f-ratio, showing visible coma on
  off-axis stars

Approach: instead of overriding `plot_function` per scenario, allow a
secondary plot via `plot_function_secondary: str | None = None` field on
`ScenarioDefinition`. Render both into the before/after canvases:
`before` = primary plot of "before" telescope, `after` = secondary plot of
"after" telescope. (Or render both side-by-side as separate panels — TBD
based on canvas layout flexibility.)

Simpler alternative: split the user's "before/after" semantics for this
specific scenario into "spot diagram / starfield" — both sides show the
*same* telescope but in different visualisations. Add a flag
`paired_visualisation: bool = False` on `ScenarioDefinition` to indicate
this.

Simplest approach for first cut: just change the scenario to use
`plot_function="plot_source_image"` and `after_source = StarField()`, then
add a secondary panel (separate widget) for the coma-field-analysis plot.

### D3.6 — Star field resolution: single star + star field

Redesign:
- **Left** panel (was "before"): single PointSource through realistic 200mm
  Newtonian (shows PSF detail clearly)
- **Right** panel (was "after"): StarField through same telescope (shows
  population-level effects)

Both render the same telescope; the comparison is *single star detail* vs
*field-level effects*. Update labels accordingly. No change to plot
function.

### D3.7 — Real objects: investigate and document

After F1.5 (kernel size), re-render Jupiter and Saturn with all effects.
If spikes/rings now visible: done. If not: document in the scenario's
description that "PSF effects are confined within the Airy radius and don't
visibly affect extended sources at this scale" — convert the scenario into
an educational point about *when* PSF effects matter.

---

## Phase 4 — New scenarios

### N4.1 — Spherical aberration scenario

Already-implemented physics. Add new Act 1 scenario:
- ID: `spherical_aberration`
- Title: "Spherical Aberration"
- Description: spherical primary mirror does not focus all rays to a point;
  parabolic primary corrects this on-axis.
- Before: 200mm f/4 Newtonian, `primary_type="spherical"` —
  shows ~15″ blur
- After: same spec but `primary_type="parabolic"` — shows diffraction-limited
- Plot: `plot_psf_2d` or `plot_source_image` with PointSource
- Tweakable: `focal_length` (so user sees aberration shrinks with f-ratio³)
- Theory: add `compute_spherical_aberration_theory` returning Gauss formula
  `LSA ≈ D³/(128·f³)` in arcsec (convert to angular).

This adds a 14th scenario.

---

## Phase 5 — Physics tab content

The Parameters & Physics tab needs the following content additions. These
are pure text/formula updates; no logic changes.

### P5.1 — Diffraction section: Rayleigh vs Dawes

Add subsection distinguishing:
- Rayleigh: 1.22λ/D — first-zero of Airy disk; theoretical
- Dawes: ≈1.02λ/D (or ≈4.56″/D_inches) — empirical, equal-magnitude double
  stars

### P5.2 — Define f-ratio

Define `f = focal length / aperture`, explain its role in:
- Image-plane scale: `physical distance = f × tan(θ)`
- Coma-free field scaling: CFF ∝ f²
- Diffraction limit (per pixel) does not depend on f, only on aperture

### P5.3 — Units convention

Add a units table at the top of the tab:
- Angles: arcseconds (″)
- Image plane: mm
- Aperture/focal length: mm (with inches sometimes shown for amateur scopes)
- Wavelengths: nm

### P5.4 — Strehl ratio definition + (1−ε²)² explanation

Define Strehl as peak(actual PSF) / peak(unaberrated PSF). The (1−ε²)²
formula is the Strehl reduction for an annular aperture under the Maréchal
approximation: peak intensity drops as energy is redistributed into the
ring system. **Note**: this is not arbitrary scaling — the *integrated*
energy is conserved; only the on-axis peak drops because the PSF widens.

Add a note: obstruction *narrows* the central disk slightly (apparent
resolution improvement) at the cost of *contrast* (more energy in rings).
This is the standard trade-off; resolution and contrast are different
properties of the PSF.

### P5.5 — Sellmeier equation

Currently referenced but not shown. Add:
```
n²(λ) = 1 + Σᵢ (Bᵢ λ²) / (λ² − Cᵢ)
```
with the BK7 coefficients. Note the codebase uses the simpler Cauchy
equation `n(λ) = B + C/λ²` for tractability — call this out.

### P5.6 — Add vignetting section

Vignetting is referenced in the Vignetting tutorial but absent from the
physics tab. Add a section:
- Defined as fractional illumination at off-axis field angles
- Newtonian/Cassegrain: secondary mirror clips the converging beam at
  large field angles
- Refractor: only tube-wall vignetting in real scopes (not modelled)
- Formula: circle-circle overlap (link to the existing
  `vignetting.py` implementation)

### P5.7 — Add seeing section

Seeing is referenced in the aperture_vs_seeing tutorial but missing from
the tab.
- Atmospheric turbulence creates wavefront errors that scale as λ/r₀
  (Fried parameter)
- Long-exposure FWHM scales as λ^(-1/5) D^0 — independent of aperture once
  D > r₀
- Critical aperture: D_crit = 1.22λ/θ_seeing — bigger D buys light, not
  detail

### P5.8 — Seidel 3rd order explanation

Currently mentioned in the coma section without context. Add a one-paragraph
explainer: classical aberration theory expands wavefront error as a
polynomial in field angle and pupil radius; the third-order terms (5 of
them: spherical, coma, astigmatism, field curvature, distortion) dominate
in most amateur scopes.

### P5.9 — Note obstruction's resolution caveat

Add a callout: a 30%-obstructed 200mm scope has a marginally tighter Airy
disk than an unobstructed 200mm — but the surrounding ring contrast is
worse. The tighter disk can superficially make double stars look more
resolved while planetary detail (where contrast matters) is degraded.

---

## Phase 6 — Tests

### T6.1 — Update existing scenario count

`tests/test_tutorial_tab.py`:
- Update `test_thirteen_scenarios_total` → 14 (after spherical_aberration
  added).
- Update `test_acts_populated` Act 1 count: 6 → 7.
- Update `test_all_scenarios_implemented` to include `spherical_aberration`.

### T6.2 — Bug fix tests

For each fix, add a regression test:

- **F1.1 (spider vanes)**: assert 4-vane spike pattern is along x/y axes,
  not diagonals.
- **F1.2 + F1.3 (chromatic display)**: render polychromatic singlet, assert
  resulting image has non-trivial RGB channel variation.
- **F1.4 (aperture-dependent rendering)**: render PointSource at 100mm and
  400mm, assert pixel arrays are NOT close.
- **F1.5 (extended-source spikes)**: render Jupiter with spider_vanes=4
  through a 200mm scope, assert there is bright pixel content beyond the
  planet's disk extent.

### T6.3 — Theory function tests

- Add test for `compute_spherical_aberration_theory` returning a positive
  value that scales with D³/f³.

### T6.4 — Smoke tests for redesigned scenarios

After Phase 3 redesigns, ensure each scenario still passes its existing
smoke test (renders without error). New smoke test for
`spherical_aberration`.

---

## Implementation order summary

1. **Phase 0** — investigate Bug 1 (read code, report findings before fixing)
2. **Phase 1** — physics-engine fixes:
   F1.1 → F1.2 → F1.3 → F1.4 (after Phase 0) → F1.5 → F1.6
3. **Phase 2** — GUI changes:
   G2.1 → G2.3 → G2.4 → G2.5 → G2.2 (most invasive, last)
4. **Phase 3** — tutorial redesigns:
   D3.2 → D3.6 → D3.7 → D3.1 (uses G2.1) → D3.4 (uses F1.2/F1.3) →
   D3.3 (uses G2.2) → D3.5 (most complex)
5. **Phase 4** — new spherical aberration scenario
6. **Phase 5** — physics tab content
7. **Phase 6** — tests (incremental, after each change)

Run full test suite after each phase. Visual verification in the GUI after
each redesigned scenario.

---

## Open questions for user (raise if encountered)

- D3.4 chromatic+seeing fallback: if F1.2+F1.3 still don't produce
  convincing colour, do we drop the scenario or keep it with a documented
  caveat?
- D3.5 coma layout: does the user prefer the "spot diagram + starfield"
  side-by-side layout, or a tabbed switch?
- D3.7 real objects: if F1.5 still doesn't surface visible spikes on
  Jupiter, do we keep the scenario as an educational note about scale, or
  drop it?

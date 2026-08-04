# Tutorial Tab — Round 5 feedback ledger

**Branch:** `feature/tutorial-testing-tab` (Round 4 complete at commit `0deea48`).
**Rule (same as Rounds 3 & 4):** record every item verbatim; do NOT paraphrase away or
mark DONE without canvas-pipeline verification through the REAL GUI navigation.
Status: ⬜ open · 🔧 in progress · ✅ done+verified · ❓ needs decision/answer.

**Context:** Round 4 closed with 422 tests passing and 32 commits ahead of `main`,
unmerged. This round is explicitly gating the merge — user: *"there are still some
items that need work before merging."*

---

## Verbatim feedback (2026-08-02)

### R5.1 — Detector vs Eye (viewing_modes)
> "Detector vs eye: why is it orange? Is this level of orange a realistic thing
> anyone would ever see?"

- ⬜ (a) Star colour is unrealistically saturated.

### R5.2 — Central obstruction (linear mode / 2D PSF)
> "Central obstruction- linear viewing mode and 2d psf in general. When linear in
> variations of the 2d pattern- unless the exposure is turned up, we never really
> see the secondary diffraction spikes. From the 1d plots, it looks like this
> should be a few % of the amplitude of the main peak; I am surprised that we
> cannot see any signal that is 1% of the main peak. Does this seem right?"

- ⬜ (a) Answer the question in-module: is 1%-of-peak visibility correct?

### R5.3 — Chromatic aberration
> "The legends in the left canvas can be made bigger now that they are out of the
> main plot canvas. You can also remove the text saying which focal plane is being
> used in the left plot. It covers up the focal region and is sufficient to have
> that label on the right. In the Physics and Parameters, I still don't see much
> discussion of the different glasses used. From last time, In chromatic aberration
> parameters and physics, add a note on the different types of glasses that are
> used, how they relate to the achromat vs APO designs, including how they are
> applied in the tutorial module and relative costs/performance improvement for
> them."

- ⬜ (a) Enlarge left-canvas legends (now that they sit outside the plot).
- ⬜ (b) Remove the focal-plane text from the LEFT plot (it covers the focal
      region); the right-plot label is sufficient.
- ⬜ (c) **REPEAT ITEM from R4.5b** — glass-type discussion still not findable.

### R5.4 — Vignetting
> "Vignetting- for the tutorial module, also specify where typical eyepiece FOVs
> are- e.g., is 10,000 arcsec a lot or a little?"

- ⬜ (a) Add real eyepiece true-FOV context to the vignetting module.

### R5.5 — Spherical aberration
> "the narrative needs updated now that there are two plots on the right including
> the inset plot, which I think is on its side. Ensure consistent axis labeling
> (i.e., x, y, z) across all figures. Also, I think you should update the color
> zscale to not be symmetric- the plot is inherently not symmetric (i.e., the left
> side is positive and right side negative). You should have a color scheme that
> distinguishes clearly where each comes from, consistent across all figures."

- ⬜ (a) Narrative rewrite for the new two-plot right side.
- ⬜ (b) Inset plot appears rotated / "on its side".
- ⬜ (c) Consistent x/y/z axis labelling across ALL figures.
- ⬜ (d) Signed (diverging) pupil-zone colour scale, not `|h|`; consistent across
      all figures.

### R5.6 — Chromatic aberration + seeing
> "I am still not sure all the colors are correctly implemented. Are these colors
> too enhanced? With APO-triplet and no atmospheric seeing, each star also seems
> like it has multi-colors and is not uniformly colored across it. This requires
> serious review to ensure correctness. Extensively review the implementation here
> with a fresh perspective."

Follow-up detail (same session):
> "For the chromatic aberration and seeing, the coloring is also asymmetrical. For
> example the central star looks pink on its upper right and more yellow to its
> lower left. The lower right star has its upper right part more purple than the
> rest."

- ✅ (a) Colours possibly over-enhanced. **Yes, and the cause was found** — see
      "R5.6a" below. Residual singlet saturation is real physics, now explained
      in-module.
- ✅ (b) APO-triplet stars show multi-colour structure when they should be ~white.
- ✅ (c) **Directional colour asymmetry** — pink upper-right / yellow lower-left on
      the central star; purple upper-right on the lower-right star.
- ✅ (d) Full fresh-perspective review of the polychromatic star implementation.

### R5.7 — Coma
> "Coma field image on the left- the stars again seem like they have clear
> rectangular outlines when coma is enhanced. Go through everywhere and make sure
> we don't have these box artifacts anywhere."

- ⬜ (a) Box artifact still present at enhanced coma.
- ⬜ (b) Sweep EVERYWHERE for box artifacts (explicit cross-cutting instruction).

### R5.8 — Colour filters on Jupiter
> "with detector view as you vary exposure you can get what appears to be a high
> quality original image. With eye mode, it looks more like highlighter orange
> stripes again. Are we sure this is right? It looks worse than before in eye mode.
> I suppose this suggests eye viewing is worse than detector pictures. Aperture
> also does not change apparent brightness which seems wrong."

- ⬜ (a) Eye mode renders "highlighter orange stripes"; worse than before.
- ⬜ (b) Aperture does not change apparent brightness — verify + explain.

### R5.9 — NEW MODULE: magnification / exit pupil / FOV
> "I am realizing we should also have a new module that describes magnification,
> exit pupil, FOV stuff etc. Most things are autoscaled to take up most of the
> image, but changing eyepieces changes the actual size of the object which is an
> effect neglected in our tutorial. Propose a module to describe these eyepiece
> features which are not currently captured."

- ⬜ (a) Design + implement the eyepiece module (proposal below, awaiting sign-off).

---

## Diagnosis (2026-08-02) — pre-implementation investigation

### R5.6c — ROOT CAUSE FOUND AND MEASURED: per-channel pixel misregistration

`chromatic_psf_kernel` (`ray_trace_plot.py:4193–4198`) builds the defocus disk on a
grid centred on **integer index `n // 2`**, while the array's true centre for an even
`n` is `(n-1)/2`:

```python
center = psf_size_pixels // 2        # 128 for n=256
coords = np.arange(psf_size_pixels) - center   # -128 .. +127  (asymmetric!)
```

`psf_n = min(num_pixels, 256)` (line 4549) → **256, even** → the bug is live in the
default path.

Measured effect (symmetric Gaussian "star" convolved with the disk as built):

| defocus_radius_pix | output centroid offset |
|---|---|
| 0.6 | **+1.00, +1.00 px** |
| 1.5 | **+1.00, +1.00 px** |
| 4.0 | **+1.00, +1.00 px** |
| 12.0 | **+1.00, +1.00 px** |

The half-pixel disk offset compounds with `fftconvolve(..., mode="same")`'s
even-kernel convention into a **full one-pixel shift, up and to the right**.

**The channel-dependent part is the killer.** Line 4187 early-returns the *unshifted*
Airy PSF when `defocus_radius_pix < 0.5`:

- In-focus channel (G at `focus_wavelength_nm=550`) → early return → **no shift**.
- Defocused channels (R, B) → convolve branch → **shifted +1, +1**.

So R and B land one pixel up-and-right of G. That is exactly the reported
**"pink on its upper right and more yellow to its lower left"** — R+B (pink) displaced
into the upper right, G left behind with R (yellow) on the lower left.

It also explains **R5.6b**: for an APO triplet the residual defocus is tiny, so
different wavelengths straddle the 0.5 px early-return threshold unpredictably —
some channels shift, some don't. The misregistration is *worst* precisely when the
optics are *best*, which is why the triplet looks multi-coloured.

And **per-star variation** (R5.6c, the purple lower-right star): star centres are
placed with `cx = int(round(...))` (line ~4771), so each star carries a different
sub-pixel rounding residual, which combines differently with the fixed +1 px channel
offset — every star gets its own fringe direction and strength.

> **Note:** this is a genuine pixel-registration bug, NOT a physics/colour-palette
> problem. The channel normalisation (`common_peak`) and the intrinsic star tint
> (`star_color[ch]`, line 4884) both verified CORRECT. Do not "fix" the palette.

### Sibling sites — same `n // 2` centring idiom (AUDITED + MEASURED 2026-08-02)

| Line | What it does | Measured verdict |
|---|---|---|
| `2473`/`2485` | defocus disk in the chromatic profile plot | **SAFE** — `n_psf = 257`, odd, so `n//2 == (n-1)/2`. Correct by accident. |
| `1722` | `combined_2d[center, center:]` radial profile | **SAFE** — see below |
| `3042` | `combined_2d[center, center:]` radial profile | **SAFE** — see below |
| `4255` | SA geometric spot stamping origin | wavelength-independent → no colour artifact, but **fixed anyway** (odd grid) for uniformity |
| `4383` | coma geometric spot stamping origin | same → **fixed anyway** (odd Airy kernel) |

> **Correction to an earlier claim in this ledger.** I originally wrote that `3042`
> was depressing the 1D obstruction ring amplitudes the user reads in R5.2. That is
> **false**, and it was measured, not assumed: the `fftconvolve(mode="same")` +½ px
> output shift and the +½ px profile-sampling offset act in *opposite* directions and
> cancel. Peak error is **+0.067%**. R5.2's ring amplitudes are trustworthy as printed,
> so R5.2 is purely a narrative gap with no code defect behind it.

### R5.6b/c — FIX APPLIED AND VERIFIED THROUGH THE RENDER PIPELINE

Fix in `chromatic_psf_kernel`: build the defocus disk on its own **odd-sized** grid
sized to the radius, centre it on `(n-1)/2`, and replace the hard binary mask with an
anti-aliased coverage ramp (`clip(radius - r + 0.5, 0, 1)`), then normalise.

Two traps avoided, both real:
1. Odd size is *required* — merely re-centring on `(n-1)/2` with an even `n` still left
   +0.50 px, because `fftconvolve(mode="same")` slices at `(m-1)//2`.
2. A hard mask on a *symmetric* grid is **empty** for radii between 0.5 and 0.707 px
   (min `r` = 0.707), which would render a black star. The ramp prevents this and also
   removes small-radius centroid wander. Covered by `test_defocus_disk_never_empty`.

Measured on the real `MultiColorStarField` render (`info["image_rgb"]`, 3 stars each):

| Objective | chroma asymmetry pre → post | channel-centroid spread pre → post |
|---|---|---|
| achromat | 0.00018 → **0.00000** | 0.0044 → **0.0000 px** |
| apo_doublet | 0.0743 → **0.00000** | 0.905 → **0.0000 px** |
| apo_triplet | **0.0963** → **0.00000** | 0.897 → **0.0000 px** |

Pre-fix the triplet lost **9.6 percentage points of green** on one diagonal flank while
gaining red and blue on it — literally "pink on one side, yellow on the other", worst on
the *best* objective, exactly as reported. Post-fix every figure is identically zero.

Two measurement traps hit while verifying (recorded so they are not repeated):
- The 2-D value returned by `_render_source_through_telescope` is **not** the colour
  image; fabricating `dstack([img]*3)` from it forces every channel fraction to exactly
  1/3 and reports zero asymmetry both before and after. The RGB array is `info["image_rgb"]`.
- The displacement is along the `x = y` diagonal, so splitting the star into
  upper-right / lower-left halves puts the split line *parallel* to the displacement and
  reads exactly zero. The split must be **perpendicular** to it.

### R5.6a/d — SECOND, INDEPENDENT DEFECT: three delta wavelengths, not a spectrum

The fresh-perspective review found a bug the centring fix does not touch. The
renderer sampled exactly **three** wavelengths (656.3 / 550 / 486.1 nm) and poured
each into **one** RGB channel, 1:1. A star emits a continuum, and collapsing it onto
three deltas throws away everything in between — including the 500–640 nm light that
is barely defocused and therefore nearly as sharp as the focus wavelength.

Measured consequence, at each star's core pixel:

| Objective | before | after |
|---|---|---|
| singlet | hue 120.0°, **R and B numerically identical**, sat 0.46–0.67 | hue 120°, sat 0.75–0.84 (real — see below) |
| achromat | hue **299.7° ± 0.3 for every star**, sat 0.84–**0.98** | hue 71–82°, sat 0.59–0.71 |
| apo triplet | hue 149–195, no relation to star temperature | hue 93–192, tracks temperature |

The achromat case is the user's complaint exactly: every star rendered near-pure
magenta at up to **0.98 saturation**, with all five stars within 0.5° of the same hue
regardless of spectral type. The star's own colour had been annihilated.

**Fix:** new `telescope_sim/physics/colorimetry.py` — CIE 1931 2° colour-matching
functions, Planck's law for the stellar SED, linear-sRGB conversion. The visible band
is sampled in 9 slices; each slice gets its own chromatic-defocus PSF and contributes
to **all three** channels via its CMF weight. Star colour is now *integrated from*
the star's effective temperature rather than tabulated. Verified 9 slices ≈ 21 slices
(< 0.05 per channel), so the default is converged, not arbitrary.

Two side benefits:
- Kernels are now built **once per band for the whole field** instead of once per band
  *per star*. Despite tripling the band count the singlet render got *faster*
  (1.41 s → 1.05 s).
- Each band gets a grid sized to its **own** defocus. The old single shared grid had to
  choose between coarsening the pixel scale until the in-focus Airy core was unresolved,
  or clipping the violet disk square — the "big squares" artefact family (cf. R5.7).

**Not a defect — the singlet's green core.** Focused at 550 nm, a singlet's core is
nearly monochromatic, and near-monochromatic 550 nm is *outside the sRGB gamut*: the
raw conversion is (−0.13, 1.45, −0.17). Gamut-mapping instead of clipping moves it only
to (0.025, 1.0, 0.0), so no monitor can render it less saturated than full green. This
is a display limit, not an exaggeration, and it is now stated in the module text and in
PHYSICS.md §7.

**Verified through real GUI navigation** (sidebar → `chromatic_plus_seeing` → every
combo): 21 renders, 0 failures, and with no atmospheric seeing the hottest star
(22 400 K) renders hue 219.0 / sat 0.44 against a true-blackbody target of 223.6 / 0.60.

### R5.1 — root cause: R4.15 desaturation never propagated

`scenario_registry.py:343,353` hardcodes `spectral_rgb=(1.0, 0.7, 0.35)` — saturation
**0.65**. R4.15 desaturated the *star-field* palette via `_TINT_STRENGTH = 0.45`
(`sources.py:560`), reaching max saturation ~0.27, but this scenario bypasses the
palette with a literal tuple. Classic propagate-the-fix miss. A real mag-0 K star is a
pale amber; at mag 0 the core should burn to white with tint surviving only in the halo.
**Action:** route ALL scenario star colours through the shared palette; audit for other
hardcoded `spectral_rgb` literals.

### R5.2 — the simulation is right; the display is the honest limit

Computed unobstructed Airy ring peaks:

| Ring | Fraction of peak | 8-bit level |
|---|---|---|
| 1st | 1.750% | 4.5 / 255 |
| 2nd | 0.416% | 1.1 / 255 |
| 3rd | 0.160% | 0.4 / 255 |

At linear scale with the core at full white, the first ring is ~4/255 — indistinguishable
from black on any monitor, and the eye's own log response makes a 1.7% patch beside a
100% patch read as nothing. "Turn up exposure and they appear" is not a bug; it is the
reason astronomers stretch images. **This is a narrative gap, not a code bug.** (The `3042`
centring suspicion raised earlier was measured and cleared — 0.067% peak error; the 1D ring
amplitudes the user is comparing against are correct as printed.)

### R5.3c — the glass content EXISTS but is unreachable from where the user is sent

Full treatment (glass table, achromat vs APO, tutorial application, cost/performance) is
at `reference_tab.py:44–120` under **Telescope Types → Refractor**, near the *top* of the
page. The chromatic module's link reads *"Learn more → Parameters & Physics: **Chromatic
Aberration**"*, which points at §4 (`reference_tab.py:405`) far down the page — where
there is only a one-line cross-reference.

Compounding it: that "Learn more" is a plain `QLabel` (`tutorial_tab.py:173`), **not a
clickable link**, and the reference tab is a single long `QScrollArea` with no anchors or
table of contents.

**Action:** move/duplicate the glass content into §4 where the link points, AND make
"Learn more" actually navigate. Writing more prose in the wrong place will fail a third time.

### R5.8b — correct physics, invisible reasoning

`ray_trace_plot.py:5099–5107`: in eye mode for extended sources the D² collection factor
is deliberately divided back out and replaced by `(exit_pupil / EYE_PUPIL_MM)²`:

```python
eye_surface_brightness_factor = min(1.0, (exit_pupil_mm / EYE_PUPIL_MM) ** 2)
brightness_scale = eye_surface_brightness_factor / aperture_factor
```

A telescope can never raise a resolved object's surface brightness above the naked-eye
level — aperture buys resolution, not surface brightness. With no eyepiece control exposed,
`exit_pupil_mm` sits at its default, the factor is 1.0, and aperture appears inert **for no
visible reason**. The user's own conclusion ("eye viewing is worse than detector pictures")
is correct for planets. This resolves itself once R5.9 ships.

### R5.7 — mechanism in place, something escaping it

`_apply_circular_taper` (line 4442) is called at three star paths (4778, 4851, 5020), so
the fix exists and something specific is bypassing it. Leading hypothesis: at enhanced coma
the geometric spot exceeds the kernel and the `if 0 <= ix < num_pixels` guard clips it
square (the documented Pattern A footgun). **Must be reproduced by rendering before fixing.**

---

## Proposed module (R5.9) — "Magnification, Exit Pupil & True Field"

**Placement:** Act 1, immediately after *Viewing Modes*. Together they are "how the image
reaches your eye"; every later module assumes both.

**Key design constraint:** this module must **NOT autoscale**. Both panes render on a fixed
angular canvas showing the eyepiece's true-field circle, with the object at its actual
apparent size inside it. The contrast against every other module IS the lesson.

- **Left:** low power (e.g. 32 mm eyepiece) — wide true field, small bright object.
- **Right:** adjustable eyepiece focal length + apparent FOV. Shorten it and the object
  grows, the field circle shrinks, the image visibly dims.

**Live theory readout:**

| Quantity | Formula |
|---|---|
| Magnification | `M = f_tel / f_eye` |
| Exit pupil | `D / M = f_eye / f-ratio` |
| True FOV | `AFOV / M` |
| Surface brightness | `(exit_pupil / 7 mm)²` |
| Max useful mag | `≈ 2 × D(mm)` |
| Min useful mag | exit pupil ≤ 7 mm (else light spills past the iris) |

**What it resolves:** R5.8b's aperture-brightness confusion gets its actual explanation;
the R4.11 exit-pupil and ND-filter notes finally have a home; and "why does the Moon never
look crisp" becomes answerable (empty magnification — exit pupil below ~0.5 mm magnifies
blur, not detail). Also supplies the eyepiece FOV numbers R5.4 asks for.

---

## Plan — proposed batches

User (2026-08-02): **order doesn't matter.**

- **Batch M — star colour + obstruction narrative:** R5.1 (route all scenario star colours
  through the shared palette; audit hardcoded `spectral_rgb`), R5.2 (linear/dynamic-range
  narrative).
- **Batch N — chromatic presentation + P&P relocation:** R5.3a (bigger legends), R5.3b
  (drop left focal-plane text), R5.3c (**relocate** glass content to §4 + make "Learn more"
  clickable).
- **Batch O — pupil colour scale + spherical:** R5.5d (signed diverging colormap across ALL
  ray-fan/spot figures), R5.5a/b/c (narrative, inset orientation, x/y/z consistency).
- **Batch P — box-artifact sweep:** R5.7a/b — render every star path at extreme
  coma/defocus, find what escapes `_apply_circular_taper`.
- **Batch Q — chromatic colour correctness:** R5.6a–d. Fix the `n // 2` centring in
  `chromatic_psf_kernel`, audit all five sibling sites, add a regression test asserting
  per-channel centroid alignment.
- **Batch R — Jupiter eye mode:** R5.8a/b.
- **Batch S — new eyepiece module:** R5.9 + R5.4 (vignetting FOV context).

**Rough size:** ~8–9 focused sessions. M–P are well understood; Q's root cause is now
measured but the sibling audit may expand; R is still an open investigation.

---

## R5.1 / R5.2 — BATCH M: FIX APPLIED AND VERIFIED THROUGH THE RENDER PIPELINE

### R5.1 — the diagnosis above was right but INCOMPLETE

The hardcoded `spectral_rgb=(1.0, 0.7, 0.35)` was real, and fixing it was
necessary. It was not sufficient. Answering the user's *second* question — "is
this level of orange a realistic thing anyone would ever see?" — turned up a
deeper defect that the propagate-the-palette framing would have missed
entirely.

**(a) The tint was not a star colour at all.** Saturation 0.65 exceeds *any*
stellar blackbody. Derived properly (Planck → CIE 1931 → linear sRGB), a
4300 K K-giant is `(1.00, 0.91, 0.66)`, saturation **0.34**. The scenario now
declares `temperature_k=4300.0` and `PointSource` derives the colour, so the
physical quantity is what's stated and the colour falls out.

**(b) The eye view was displaying colour where no eye could see any.** Human
colour vision is band-pass in luminance — below the cone threshold only the
rods respond, and rods are a single receptor class, so scotopic vision is
genuinely achromatic. The renderer modelled only the *bright* end (cone
bleaching → white core). Nothing removed chroma at the *faint* end. And
because the eye view's asinh stretch is deliberately chroma-preserving, it
lifted the star's faint outer halo to near-full display brightness **while
keeping its full saturation** — painting the frame with vivid orange that no
observer could ever perceive. That, not the tint value, is why it read as
"highlighter orange".

Measured on the eye pane, mag-0 star through a 100 mm scope:

| Radius | sat BEFORE | sat AFTER |
|---|---|---|
| core (r=0) | 0.109 | 0.105 |
| r = 10 px  | 0.232 | 0.194 |
| r = 20 px  | 0.333 | **0.044** |
| r = 40 px  | 0.335 | **0.024** |

The bright end is untouched (by construction — the bleach term reproduces the
old `I/(I+0.5)` exactly). The faint halo drains to grey. A thin amber annulus
survives in between, which is what an observer actually sees.

New `colorimetry.mesopic_chroma_gain` / `apply_mesopic_desaturation`.
⚠️ The shape is real physiology; the two thresholds are tuned display
parameters, because the renderer works in normalised flux, not cd/m². Flagged
in the module docstring, PHYSICS.md §7b, and the module narrative.

**(c) Detector vs eye now genuinely disagree, which is the module's whole
point.** The desaturation is eye-view only: a camera has no cones and records
the same chromaticity at any flux. Measured through the GUI:

| Pane | r=0 | r=10 | r=20 | r=40 |
|---|---|---|---|---|
| Eye (log)       | 0.105 | 0.194 | 0.044 | 0.024 |
| Detector (linear) | 0.337 | 0.337 | 0.337 | 0.337 |

The detector row is flat at exactly `blackbody_linear_srgb(4300)`.

### R5.1 — SIBLING AUDIT (per the standing "check elsewhere" instruction)

Sweeping for the same defect class — *a colour asserted by hand where physics
could derive it, or a perceptual effect baked into the source data* — found
two more instances, both fixed:

1. **`_SPECTRAL_PALETTE_RAW` (`sources.py`)** — six hand-written class tints.
   Demonstrably wrong, not merely approximate: it gave class F a **warm** tint
   (hue 38°) when a 7000 K blackbody is slightly **blue** of the sRGB white
   point (hue 211°), because sRGB white is D65 ≈ 6500 K. Replaced by
   `blackbody_linear_srgb` at each class's temperature.
2. **`MultiColorStarField.STARS`** — carried a hand-written RGB tint *next to*
   the true `T_eff`. Two disagreeing sources of truth: after Batch Q the
   polychromatic path derives colour from `T_eff` while the monochromatic path
   used the tint, so the same star changed colour when polychromatic was
   toggled. The tabulated "Antares" tint was `(1.00, 0.45, 0.10)` against a
   3500 K blackbody's `(1.00, 0.79, 0.43)`. Tint column removed; colour
   derived on both paths.

Also removed: `ShowcaseStarField`'s magnitude-dependent desaturation and
`_TINT_STRENGTH = 0.45`. Both were perceptual models living in the *source*,
which meant (i) they double-counted against the display-stage model in the eye
view and (ii) they wrongly desaturated the **detector** view, where a camera
would faithfully record a faint star's colour. The effect now exists once, at
the display stage, keyed off actual pixel flux — so a faint star fades to grey
in the eye pane and keeps its colour in the detector pane.

### R5.2 — narrative written, with the numbers

Confirmed the earlier finding: no code defect, the display is the honest
limit. Wrote the quantitative version into both places the user was looking —
*Viewing Modes* and *Central Obstruction*:

| Case | 1st ring | 8-bit level |
|---|---|---|
| Unobstructed | 1.75% | 4 / 255 |
| ε = 0.25 | 3.80% | 10 / 255 |
| ε = 0.33 | 5.40% | 14 / 255 |
| ε = 0.40 | 7.07% | 18 / 255 |
| ε = 0.50 | 9.63% | 25 / 255 |

2nd ring unobstructed: 0.42% → level 1. The narrative also names *why* the 1D
plot disagrees (its y-axis rescales per curve; the 2D image cannot) and gives
the asinh comparison: the same 1.75% maps to level **119** in the eye view,
~30× the displayed contrast for identical photons.

### Verification

- **481 tests pass** (was 468). New: 11 mesopic/eye-vs-detector tests in
  `test_colorimetry.py`, 2 rewritten to assert on the *rendered* image rather
  than the source array, 1 new detector-keeps-colour test.
- **Pre-fix failure demonstrated**: forcing `cone_threshold → 0` reproduces the
  old one-sided model exactly and gives halo saturation 0.333 against the
  test's `< 0.10` bound.
- **Real GUI navigation** (sidebar → 5 scenarios → every combo, checkbox and
  slider): **411 renders, 0 null figures.** Pane measurements above were read
  out of the figures the GUI actually produced.

### Carried into Batch R

R5.8's "highlighter orange stripes in eye mode" is the same family — Jupiter's
belts are dim in eye mode and were chroma-preserved through the asinh stretch.
Measured post-fix disk saturation is now p90 = 0.18 in eye mode vs 0.25 linear.
Whether that fully answers R5.8 needs its own visual check; the aperture-
brightness half of R5.8 is untouched and still open.

---

## R5.3 — BATCH N: FIX APPLIED AND VERIFIED THROUGH THE GUI

### R5.3a — legends and readouts enlarged (`plot_polychromatic_ray_trace`)

Now that R4 moved the legend out of the plot canvas, there is room for it:

| Element | Before | After |
|---|---|---|
| Left-panel legend | `fontsize="small"` (≈8.3 pt) | **11 pt** |
| Focal-offsets readout box | 7 pt | **9 pt** |
| "Idealised SA removed" note | 7 pt | **9 pt** |
| Focal-region zoom label (right panel) | 7 pt, alpha 0.9 | **9 pt**, alpha 0.95 |
| "zoomed → (focal-plane view)" box marker | 6.5 pt | **8 pt** |

The last one was not in the user's list — it was the *smallest* text in the same figure
and unreadable at the tutorial's canvas size. It is anchored `ha="left"` from the zoom
box's **right edge**, so growing it does not re-occlude the focal region R5.3b just cleared.

### R5.3b — left-plot focal-plane label removed

The `axhline` marking the chosen focal plane stays (its colour still encodes the
wavelength); only the text that sat across the focal region is gone. The paired
zoom panel on the right carries the label, reworded `"focal plane (550 nm)"` →
**`"focused at 550 nm"`** so the single remaining instance reads as a statement of
which plane the after-side plots were taken at.

### R5.3c — the third attempt: RELOCATE + LINK, not more prose

Two failed rounds wrote glass content the user never saw, because it lived under
*Telescope Types → Refractor* near the top of the page while the module's "Learn more"
line named **Chromatic Aberration**, ~4000 px further down. Both halves are now fixed.

**Half 1 — the content moved to where the link points.** The 71-line block (design
comparison table + cost/performance ladder + the "APOs stay ≤150 mm" paragraph) now sits
in §4 Chromatic Aberration under `<h4>The glasses, and what each design class buys you</h4>`.
The Refractor entry keeps a two-sentence summary and a pointer. Three cross-references that
the move made stale or circular were rewritten (§4's opening no longer sends the reader
*back* to Telescope Types; the block no longer cites "see Implemented Physics → Chromatic
aberration" from inside that very section).

The tutorial module's own description also gained the cost/performance sentence R5.3
asked for ("each rung buys 3–5× less colour error for a similar jump in price"), so the
answer is present *in the module* as well as behind the link.

**Half 2 — "Learn more" is now a working deep link.**

| Piece | Change |
|---|---|
| `reference_tab.py` | `_make_section` splits each body at top-level `<h3>` into one QLabel per subsection, so every heading is an addressable widget |
| `reference_tab.py` | `_section_tokens` / `_match_anchor` / `_register_anchor` — 46 anchors registered |
| `reference_tab.py` | `ParametersPhysicsTab.resolve_section()` / `.scroll_to_section()` |
| `tutorial_tab.py` | label is now `<a href='reference:<section>'>`, emits `learn_more_requested` |
| `main_window.py` | `_show_reference_section` adds Reference **beside** Tutorial and jumps to the heading |

**Why token matching rather than an alias table.** The hints are human strings
("Coma", "Spider Vanes") and the headings are numbered and longer
("5. Coma & Seidel Aberrations", "3. Spider Vane Diffraction"). An alias table rots
silently the moment a heading is edited. Matching normalises both sides (strip markup,
drop leading numbering, lowercase, crude de-pluralise) and ranks candidates by
*exact → heading-starts-with-hint → numbered physics section → fewest extra words*.
That ordering is load-bearing:

- **"Diffraction"** → `1. Diffraction (Wave Optics)`, not `3. Spider Vane Diffraction`
  (decided by the prefix rule)
- **"Coma"** → `5. Coma & Seidel Aberrations`, not the `Coma Field Analysis` plot
  description (decided by the numbered rule)
- **"Vignetting"** → `7. Vignetting`, not `Vignetting (diagram)` (exact match)

Deleting those two tie-break terms makes `test_ambiguous_hints_pick_the_physics_heading`
fail — checked, not assumed.

**Navigation preserves state.** Following the link adds Reference as a second tab in
Tutorial mode instead of switching the mode radio, so the scenario the reader is in the
middle of is not destroyed. The tab is built lazily (constructing it renders the
vignetting diagram) and reused on later clicks.

**One registry hint upgraded.** `spherical_aberration` pointed at the whole
`"Implemented Physics"` section; it now points at `"Spherical Aberration"` →
`6. Spherical Aberration`. `saturn_rings` legitimately has no single heading and keeps
the section-level hint.

### Verification

- **All 17 implemented scenarios navigated via the sidebar**, link activated on each:
  0 failures, 0 unmatched hints, Reference tab opened and brought to front every time.
- **11 distinct hints → 11 distinct scroll positions, in document order**
  (Diffraction 3711 < Central Obstruction 3918 < Spider Vane 4260 < Chromatic 4425 <
  Coma 5190 < Spherical 5427 < Vignetting 5760 < Seeing 5937 < Photometry 6156).
  Monotonicity is the evidence the anchors point at the right places, not merely at
  *some* widget.
- **Rendering unchanged by the split.** Splitting one QLabel into many costs each `<h3>`
  its top margin (Qt drops a leading block margin at the start of a document): the page
  measured 8630 px before, 8251 px after. `layout.setSpacing(10)` restores it to 8601 px
  — within 0.3%. Verified by rendering the full page both ways and comparing crops.
- **489 tests pass** (8 new in `TestLearnMoreDeepLink`), up from 481.

### Carried forward

The left-hand ray-trace panel labels its x-axis but not its y-axis. That is R5.5c's
"consistent axis labelling (x, y, z) across all figures" — logged here, fixed in **Batch O**.

---

## R5.5 — BATCH O: FIX APPLIED AND VERIFIED THROUGH THE GUI

> **User feedback (verbatim).** *"the narrative needs updated now that there are two
> plots on the right including the inset plot, which I think is on its side. Ensure
> consistent axis labeling (i.e., x, y, z) across all figures. Also, I think you should
> update the color zscale to not be symmetric- the plot is inherently not symmetric
> (i.e., the left side is positive and right side negative). You should have a color
> scheme that distinguishes clearly where each comes from, consistent across all
> figures."*

Four distinct defects, all in the Spherical Aberration module but three of them
project-wide.

### R5.5d — the colour scale (the substantive one)

**What was wrong.** `_pupil_colormap_colors` mapped **|h|** onto viridis. A ray entering
the pupil at −80 mm and one entering at +80 mm therefore got the *same* colour — on a
figure whose entire point is that those two rays land on **opposite** sides of the
focus. The reader could see how far out in the pupil a ray came from but not which
half it came from, which is exactly the asymmetry the feedback names.

**The scheme now.** Colour carries both facts about the entry point:

| Channel | Meaning |
|---|---|
| **Hue** | which side — `Blues` for h < 0 (below axis), `Oranges` for h > 0 (above) |
| **Depth** | how far out — pale near the axis, deep at the mirror edge |

Both wings start at `_PUPIL_RAMP_FLOOR = 0.40` rather than 0, so a paraxial ray is
never near-white on a white panel (`#94c4df` / `#fda762` at the seam). The norm is
`Normalize(-h_max, +h_max)`, so h = 0 always sits at the middle of the colourbar.

Applied at all four **meridional** call sites — `_draw_ray_fan_panel`,
`_draw_sa_caustic_panel`, `plot_ray_trace_pupil_colored`, `_draw_coma_ray_fan_panel`.

**The deliberate exception.** 2D spot diagrams (`_draw_spot_diagram`,
`_draw_coma_spot_grid`) replicate each pupil zone around all 36 azimuths, so a dot
there has a radius but no "above/below" — a signed scale would be a lie. They keep a
magnitude ramp, built as the **positive wing of the same map** (`_pupil_magnitude_cmap`),
so both families speak one colour language. Their colourbars now say so
(`PUPIL_ZONE_CBAR_LABEL`), and the stale claim that the spot grid used "the same scale
as the ray fan" was corrected.

Two knock-on fixes found while checking the rendered result rather than the code:

- The coma spot grid was drawn on a **near-black** panel because viridis put its
  *bright* end at the mirror edge. The shared ramp *deepens* toward the edge, so a deep
  brown on `#101010` would have hidden the very rays the caption points at. The panels
  are now light (`#fbfbfb`) with a dark dashed Airy circle.
- The pupil-coloured ray trace drew its mirrors in **steel-blue**, and blue now *means*
  "ray from below the axis". That figure alone draws its optics in neutral `#444444`.

### R5.5b — the caustic was on its side

`_draw_sa_caustic_panel` plotted Δz **horizontally** while the ray trace beside it and
the chromatic zoom panel both plot the optical axis **vertically**. Same picture,
rotated 90°, which is what the feedback describes. It is now axis-vertical: transverse
x (µm) across, Δz from paraxial focus (mm) up, light climbing the page exactly as in
the trace on the left. `plot_spherical_focal_analysis` is used by that one scenario
(a Newtonian), so "light travels up the page" is a true statement there, not a
generic one.

### R5.5c — axis labelling

Three conventions coexisted. The project now uses the standard optical one — **z is
the optical axis, x and y are transverse** — everywhere:

| Figure kind | Was | Now |
|---|---|---|
| Side views (ray trace, chromatic zoom) | `x (mm)` / **`y (mm)`** | `x, transverse (mm)` / `z, along optical axis (mm)` |
| Spot diagram | `Position on focal plane (mm)` ×2 | `x on focal plane (mm)` / `y on focal plane (mm)` |
| PSF / focal-plane images (×4 sites) | `Position (mm)` ×2 | `x on focal plane (mm)` / `y on focal plane (mm)` |
| Coma spot grid | `µm` ×2 | `x (µm)` / `y (µm)` |
| Rendered scene | `Field angle (arcsec)` ×2 | `Field angle, x (arcsec)` / `Field angle, y (arcsec)` |
| SA caustic | `Δz` on x, `x` on y | `x` on x, `Δz` on y (see R5.5b) |

The old `y (mm)` for the optical axis was the collision: it meant something different
from the `y` of every focal-plane view. The convention is now documented in the
reference under **Axis and colour conventions in the figures**, reachable from the
module's Learn-more link.

### R5.5a — the narrative

The description still described one right-hand plot and a magnified **inset** that
R4.7 had already deleted. Rewritten to state the axis convention, state the colour
convention, and walk the two right-hand panels separately — including *why* the top
explains the bottom (the edge rays have already crossed by the time they reach the
paraxial plane, so at that plane they are diverging again and their Δx is large and of
opposite sign — which is what bends the fan into an S). The side label went from
"Ray fan (h vs Δx) →" to "Focal caustic (top) + ray fan (bottom) →".

### Found while verifying, fixed in the same batch

- **Ray fan annotation boxes sat on the data.** The cheat-sheet was pinned upper-left
  and the RMS box lower-right — precisely the two corners the spherical S-curve
  occupies. Moved to lower-left / upper-right, the two corners free for both an S-curve
  and a flat (corrected) fan.
- **Coma figure caption overprinted the in-panel verdict.** The verdict sat at
  `y = -0.22` in axes coordinates, i.e. inside the figure caption's band. Moved inside
  the axes on a translucent background; caption re-flowed to explicit lines.
- **Coma panel titles collided** with each other and with the suptitle at GUI render
  size. Titles set to 10 pt and `wspace` 0.3 → 0.38 (the right panel's y-label lives in
  that gap).
- **The caustic panel was broken in the PARABOLIC state** — the `primary_type`
  dropdown's other value, i.e. exactly the "skipping state combinations" failure mode.
  Found by rendering it; invisible in the source. Three separate defects, all in the
  corrected case:
  1. **Degenerate axis.** `z_span` floored at `1e-3` mm, which is not a physical
     scale. A parabolic primary puts every crossing at Δz ≈ 0, so the panel zoomed to
     ±1 µm of numerical noise. Now floored at 3× the **Rayleigh depth of focus**,
     `±2λN²` — real physics, and the yardstick the panel needed anyway.
  2. **The converging cone collapsed to one vertical line.** The per-ray slope came
     from `-Δx/z_cross`, which is algebraically right but 0/0 when the ray crosses at
     the paraxial plane; the code fell back to `slope = 0`. Now taken directly from
     the convergence geometry, `dx/dz = -h/f` — identical wherever the old form was
     defined, and correct where it wasn't.
  3. **The title asserted an effect that wasn't there.** "marginal rays cross BELOW ★"
     is simply false for a parabola. Now state-aware: "No caustic — every ray crosses
     at ★, inside the depth of focus" when corrected, and in the aberrated case it
     *quantifies* the error against the tolerance ("by 80× the depth of focus")
     instead of leaving a bare millimetre figure with no scale.

  A green depth-of-focus band is now drawn in both states, and the narrative explains
  it — the same "is this a lot or a little?" context R5.4 asks for on vignetting.

  Checked for other instances of the same pattern: no other figure derives a line
  slope from a crossing point, and the only other effect-asserting title (the coma
  ray-fan verdict) was already state-aware.

### Verification

- **511 tests pass**, up from 489. 22 new across five classes:
  `TestPupilColourLanguage`, `TestFigureAxisConventions`,
  `TestSphericalCausticOrientation`, `TestCausticInTheCorrectedState`,
  `TestSphericalNarrativeMatchesTheFigures`.
- **The new tests are load-bearing**: run against the pre-Batch-O files, **16 of 17**
  of the first round fail; all **5** of `TestCausticInTheCorrectedState` fail against
  the pre-fix caustic panel. The 17th
  (`test_marginal_rays_cross_below_the_paraxial_focus`) passed
  coincidentally because the old horizontal ylim spanned ±210 µm and so contained the
  −1.36 mm crossing; it was tightened to assert the vertical axis is on the Δz scale,
  which is what actually fails if the panel is rotated back.
- **Rendered through the real GUI**, sidebar navigation, not a `_load_scenario` bypass:
  spherical (both primaries), coma (both view modes), chromatic. Read the PNGs; that
  is how the three knock-on defects above were found — none of them are visible in the
  source.
- **Full control sweep** over all 17 implemented scenarios — sidebar navigation, then
  every combo index, every checkbox state and every slider at min/mid/max — auditing
  every figure that reaches a canvas: **2475 renders, 0 null figures, 0 banned axis
  labels, 0 stale colourbar labels**, and 14 distinct (xlabel, ylabel) pairs, all
  conforming to the z-is-the-optical-axis convention. The spherical module was swept
  again on its own after the depth-of-focus fix landed (40 renders across both
  primaries and both slider extremes, same clean audit).

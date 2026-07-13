# Tutorial Tab — Round 3 feedback ledger (VERBATIM)

**Created:** 2026-07-12
**Branch:** `feature/tutorial-testing-tab`
**Why this file exists:** the user reported that clear requests were repeatedly
ignored across rounds and asked that **every** item be explicitly recorded for
future agents to review and verify. This is the authoritative, verbatim record.
**Do not paraphrase away an item. Do not mark DONE without canvas-pipeline
verification of the exact reachable UI state (every toggle/combo value).**

## Why items were missed before (root causes — must not repeat)
1. **Verified the default state only, not every reachable state.** Central
   obstruction: labels were added and verified in the 2D view, but the 1D
   toggle was never exercised — so the 1D per-side normalisation description was
   never actually added/checked. (My own lessons file warns about exactly this
   "skip a toggle state" failure.)
2. **Batch-level tracking let listed sub-actions slip.** The vignetting
   obstruction-ratio label was written as an action item but never implemented,
   and nothing forced a per-item "done + verified" confirmation.
**Corrective process (this round):** item-level ledger below; each item gets a
status + verification note; verify EVERY reachable toggle/combo state; propagate
each fix to all affected modules.

Status legend: ⬜ open · 🔧 in progress · ✅ done+verified (canvas) · ❓ needs
user input · 💤 deferred by user.

---

## R3.1 — Airy disc
> "the right figure appears overly pixelated in comparison with the left;
> especially at smaller apertures. Does the overlay tab still do anything?"
- ⬜ (a) Right (after) PSF looks pixelated vs left, worse at small apertures.
- ⬜ (b) Does the overlay toggle still do anything? (audit / remove if dead)

## R3.2 — Rayleigh criterion
> "the plot size continues to change whenever you change the separation angle.
> In other words the spatial extent of the plot (not the scale) but the size of
> the plot changes. Stop this from happening."
- ⬜ Changing separation must NOT change the plot's spatial extent (FOV).

## R3.3 — Eye-mode realism (diffraction rings) + general realism audit
> "In eye mode the diffraction rings are clearly visible in a way that seems
> hard to believe. Is this correct? [Fable: more generally, identify where
> realism is lacking, and propose options for what it would take to improve the
> realism and simply labeling the shortcomings (in some cases accepting less
> realism is ok to isolate an effect or avoid overly difficult upgrade)]"
- ⬜ (a) Are the eye-mode diffraction rings physically believable? Assess.
- ⬜ (b) General realism audit: list where realism is lacking + options to
  improve vs. label the shortcoming (accepting less realism is sometimes ok).

## R3.4 — Linear detector vs logarithmic eye (Parameters & Physics)
> "Linear detector behavior vs logarithmic eye behavior. Describe this in the
> parameters and physics with evidence that the eye behaves logarithmically."
- ⬜ Add a P&P section: detector linear vs eye logarithmic, WITH evidence the
  eye is logarithmic (Weber–Fechner / Pogson magnitudes / references).

## R3.5 — Central obstruction  **(CALLED OUT as previously ignored)**
> "On the 1d presentation, it still does not describe the normalization basis
> for each side. This is very concerning that this was a clearly specified thing
> to fix and it has not been fixed. Why was this not fixed? … The unobstructed
> vs obstructed legend also obscures part of each plot. This should be pulled
> outside the plot to not block it to be in the same region/column as the
> metrics and formulas. More broadly this is repeated occurrence, more things
> need to be brought outside the main plot and to the side of the canvas like as
> in the metrics to not block things. Overall the approach is good- in 2d mode
> show unobstructed on the left and obstructed on the right. In 1d mode, show the
> overlay of obstructed and unobstructed with a different normalization approach
> on left and right as previously discussed."
- ⬜ (a) **1D: describe the normalisation basis for EACH side.** (confirmed
  still missing 2026-07-12)
- ⬜ (b) Move the legend OUT of the plot, into the side column with metrics/
  formulas (don't block the curves).
- ⬜ (c) GENERAL: pull legends/overlays out of plots to the side across modules.
- ⬜ (d) 2D: unobstructed left / obstructed right (already so — verify).
- ⬜ (e) 1D: overlay of obstructed+unobstructed with a DIFFERENT normalisation
  on left vs right (as previously discussed).

## R3.6 — Chromatic aberration
> "Here again we see the legend obscuring part of the ray trace on the left plot
> with plenty of white space in the canvas to the side. Pull the legends out of
> that plot and into the adjacent white space on the canvas. There is so much
> white space this can be done without having to shrink the ray traces.
> The ray trace on the left also has weird artifacts of additional green and
> blue rays appearing to start near the focal point and (only) red rays
> diverging significantly after it.
> On the right focal region zoom in (the top plot) add a note above it saying
> that this is the zoomed in version of the left plot. On the left plot add a box
> outline showing what region is zoomed in on.
> The bottom right zoom approach is good. For the close version- how was +/- 12
> degrees decided? It seems like it could be zoomed even further, at least down
> to +/-10 degrees."
- ⬜ (a) Move the left ray-trace legend out into the canvas white space (don't
  shrink the ray trace).
- ⬜ (b) Fix artifact: extra green/blue rays starting near focal point + only
  red rays diverging strongly after it. (likely the idealize_sa convergence)
- ⬜ (c) Right focal-region zoom (top): add a note "zoomed version of the left
  plot"; on the left add a box outline of the zoomed region.
- ⬜ (d) Close-zoom: justify ±12″ (note: user says "degrees" but axis is
  arcsec) or zoom further, at least ±10.

## R3.7 — Vignetting  **(CALLED OUT as previously ignored)**
> "In the description of the module, note there is also a diagram in Parameters
> and Physics to help explain this. The diagram is also still kind of confusing-
> perhaps a couple of ray traces on the left plot would help in addition to the
> unclear cones that are shown. It is not clear what the secondary clear aperture
> is (i.e., what that means) and if the red box is part of it, covering it up or
> outside of it. Is the secondary clear aperture not the part being covered up by
> the secondary mirror (that's what it looks like). The obstruction ratio on the
> left plot is also still not labeled in the module despite my clear instructions
> to do so. Again this is highly concerning that you are simply ignoring
> straightforward and clear requests."
- ⬜ (a) Module description: note the diagram in Parameters & Physics.
- ⬜ (b) Diagram Panel A confusing — add a couple of actual ray traces; clarify
  what "secondary clear aperture" means and the red box's relationship to it
  (inside/covering/outside). User reads it as the part covered by the secondary.
- ⬜ (c) **Label the obstruction ratio on the module's left plot.** (confirmed
  still missing 2026-07-12)

## R3.8 — Spherical aberration
> "You note that the bright marginal rays intersect the axis differently, but
> this can't be seen on the left plot. We should make another plot highlighting
> the focal region as with chromatic aberration to illustrate this.
> In the ray fan, you mention defocus/tilt but this is not mentioned anywhere
> else. Am I correct? Should that aberration be mentioned somewhere? At least in
> parameter and physics?
> The y-axis of the ray fan remains confusing too. Should that be delta-X not
> delta-Y? Ensure consistency with the axis labels of the left plot in the
> module. In the description, more clearly describe what exactly the 'transverse
> focal plane offset' is."
- ⬜ (a) Add a focal-region zoom plot (like chromatic) showing marginal rays
  crossing the axis short of paraxial.
- ⬜ (b) Ray fan mentions defocus/tilt — mention those aberrations somewhere
  (at least Parameters & Physics).
- ⬜ (c) Ray-fan y-axis: Δx vs Δy? Make axis labels consistent with the left
  plot; clearly describe "transverse focal-plane offset" in the description.

## R3.9 — Chromatic aberration + seeing  **(CALLED OUT, repeated)**
> "everything is still way too dim to see anything – you can't even see the
> stars, except in the singlet. This is another clear thing I have repeatedly
> requested fixing and you have ignored."
- ⬜ Stars too dim to see (achromat/apo); only singlet shows anything. Make the
  stars clearly visible. (confirmed still dim 2026-07-12)

## R3.10 — Aperture vs seeing
> "The two plots being the same is redundant. For the right plot (only), make it
> so that seeing and aperture resolution can be toggled on/off. Have the relevant
> circular overlays toggle on and off with that too. For the left plot, keep it
> as it is currently designed. Actually this module nicely shows the impact of
> eye resolution too, so the overall focus is resolution effects: aperture vs
> seeing vs eye integration. In the physics and parameters when you describe
> detector vs eye (linear vs logarithmic) differences, also describe the impact
> of the eye resolution/blurring."
- ⬜ (a) Right plot: toggle seeing and aperture-resolution on/off, with their
  circular overlays toggling too. Left plot unchanged.
- ⬜ (b) Reframe module focus = resolution effects: aperture vs seeing vs eye
  integration.
- ⬜ (c) P&P: in the detector-vs-eye section also describe eye resolution/blur.

## R3.11 — F-ratio and coma
> "we have already implemented the ray fan plot and referenced it. Make the left
> plot able to switch between that and its current implementation with the ray
> fan as the default. Additionally the cyan and yellow color of the existing left
> panel has always been confusing. Replace those two with a color coding that
> shows where the contribution of the coma effect comes from consistent with the
> color scale of the ray fan (i.e., you can see where more marginal rays come
> from etc.)."
- ⬜ (a) Left plot: switchable between the ray-fan plot (DEFAULT) and the current
  spot-grid implementation.
- ⬜ (b) Replace the cyan/yellow colouring with pupil-zone colour coding
  consistent with the ray-fan colormap (show where marginal-ray contribution
  comes from).

## R3.12 — Exposure & Saturation
> "Note that the aperture affects both the detector and eye mode. Also the lesson
> is not that exposure is just a detector concept. The point is to illustrate the
> behavior/brightness influences and in particular saturation. The right plot
> appears to be toggleable between modes, but it should stay fixed as the eye
> view per the description of the module (though allow it to toggle on/off eye
> blurring). As such, swap the order so eye is on the left and detector on the
> right."
- ⬜ (a) Aperture affects BOTH detector and eye mode (fix the model/description —
  NOT "exposure is detector-only" framing).
- ⬜ (b) Lesson = brightness influences + saturation (reframe, not "exposure is
  detector-only").
- ⬜ (c) Right plot stays fixed as Eye view (toggle eye-blur on/off only), not
  freely mode-switchable.
- ⬜ (d) Swap order: Eye on the LEFT, Detector on the RIGHT.

## R3.13 — ND filter on the Moon
> "the live ephemeris should apply to the left plot when checked too. The exit
> pupil- what it is and how it affects things should be further described in the
> module description. The moon never gets crystal clear on the right regardless
> of settings- is this intended or do things need modification? Is magnification
> included here as a factor? If so is a note required noting that?"
- ⬜ (a) Live ephemeris must also apply to the LEFT plot when checked.
- ⬜ (b) Describe exit pupil (what it is + how it affects things) in the module
  description.
- ⬜ (c) Moon never gets crystal clear on the right — intended or needs fixing?
- ⬜ (d) Is magnification a factor here? If so, add a note.

## R3.14 — Colour filters on Jupiter
> "the red filter just makes everything look red. Additionally you say this is
> rescaled- should we not rescale? To more clearly show what actually happens?
> The left Jupiter plot also appears to be sort of more artificially colored now,
> with the great red spot being almost highlighter orange color. Re-review that
> the filters are doing what they are supposed to, that the module is
> appropriately designed to show the effect (the red filter does not appear to be
> showing anything), and that planetary and lunar objects are being implanted
> correctly/well with their original basis definition."
- ⬜ (a) Red filter just makes everything red (not showing the intended effect).
- ⬜ (b) Rescaling — consider NOT rescaling, to show what actually happens.
- ⬜ (c) Left Jupiter looks artificially coloured now (GRS almost highlighter
  orange). Re-review the planet texture basis.
- ⬜ (d) Re-review: filters do what they should; module design shows the effect;
  planet/lunar objects constructed well vs their original basis definition.

## R3.15 — Bright + dim: dynamic range
> "specify what 'HDR' is. Again if the intent is for left to be detector and
> right to be eye, then the right plot should not be toggleable to detector view.
> This also does not show saturation well. It just looks like as the exposure is
> increased the image gets better. Perhaps for stars the saturation is not a bad
> thing? Or more likely, perhaps several stars with different brightness are
> necessary to actually show this. Re-evaluate what this is trying to show."
- ⬜ (a) Define "HDR" in the description.
- ⬜ (b) Right plot should stay Eye (not toggleable to detector) if L=detector/
  R=eye is the intent.
- ⬜ (c) Doesn't show saturation well (just "brighter as exposure up"). Re-
  evaluate — maybe several stars of different brightness are needed.

## R3.16 — Star-field showcase  **(CALLED OUT, repeated)**
> "Same feedback from last time: We also appear to have lost the star-field –
> this is perhaps the most important module where we can showcase and toggle
> on/off all the physics influences on a well-constructed star field (i.e.,
> including off-axis stars that can show coma, some nearby double stars for
> resolution, variable brightnesses, etc.) Bring this back with a extensively
> thought out starfield to best show all effects. How has this not been
> reimplemented? This is crazy how clear this directive was and that you did not
> even do this."
- ❓ **STATUS DISCREPANCY:** `ShowcaseStarField` WAS implemented + wired into the
  "Star Field Showcase" scenario (Act 4) in commit 75453bf, and renders richly
  (colour, spikes, doubles, coma edge stars, brightness range) in the current
  code. Either the user is not on 75453bf, or the scenario looks "lost" in their
  build. **Action: confirm with user which build they're on / whether the Act 4
  "Star Field Showcase" scenario appears; if it's failing in their environment,
  run that down.** Do NOT close until the user confirms they see it.

## R3.17 — Planet/Moon/Saturn construction
> "Are we sure that the Jupiter, moon, Saturn images are appropriately
> constructed- with the high resolution version and the more standard version?
> (Or perhaps we should always start with the highest possible version and let
> the telescope simulation effects blur/make more realistic the image."
- ⬜ Re-confirm planets start at highest intrinsic resolution then degrade
  (validated in R2 §B14, but re-verify given R3.14 texture concern).

## R3.18 — Propagation
> "Make sure repeated error findings are propagated across all cases."
- ⬜ Propagate every fix across all affected modules (legends-outside-plot,
  brightness, view-order, etc.).

---

## Progress log (append per session)
- 2026-07-12: ledger created; confirmed R3.5a/b, R3.7c, R3.9 still open via
  canvas render. R3.16 is a status discrepancy (code has it) — awaiting user.
- 2026-07-12 (same session): fixed and canvas-verified:
  - **R3.5 (a,b,d,e) ✅** — 1D central-obstruction now states the per-side
    normalisation basis (LEFT = each curve to own peak = shape; RIGHT =
    obstructed scaled to Strehl vs reference = peak loss) and moves the legend
    OUT of the plot into the side column (`_obstruction_overlay` +
    `_find_reference_side_panel` in theory_computations.py; removed the leftover
    in-plot "PSF = Airy" legend; gated the 2D-only "Reference…" note to 2D).
    Verified in BOTH 1D and 2D toggle states.
  - **R3.7c ✅** — obstruction ratio ε now labelled on the vignetting curve
    (title + info box). **R3.7a ✅** — module description points to the P&P
    diagram.
  - Still OPEN (this round): R3.5c (propagate legends-out to other modules),
    R3.6, R3.7b, R3.8, R3.9, R3.10–R3.15, R3.17, R3.18, R3.1–R3.4.
  - R3.16: verified the "Star Field Showcase" (Act 4) IS present in code
    (commit 75453bf) and renders richly — **awaiting user confirmation of which
    build they're viewing.**
- 2026-07-12 (cont.): **R3.16 ROOT CAUSE FOUND + FIXED.** The user was on
  75453bf but saw NO Act 4 in the sidebar at all. Cause: `scenario_sidebar.py`
  had `for act_num in [1, 2, 3]` (hardcoded) + a stale `act_titles` dict — so
  **all of Act 4 (Jupiter Full, Saturn with Rings, Star Field Showcase) was
  unreachable**, and Act 3 was mislabelled "Real Objects". Fixed: sidebar now
  iterates `sorted(get_scenarios_by_act().keys())` and takes each heading from
  the scenarios' own `act_label` (can't desync from the registry again); added
  an Act 4 colour. Verified through the ACTUAL sidebar widget (not a
  programmatic load): all 4 acts + 18 scenarios listed & enabled. Regression
  test `TestScenarioSidebarActs`. **394 tests pass.**
  - **PROCESS LESSON (added to root causes):** I verified scenarios by calling
    `tab._load_scenario(...)` directly, which BYPASSES the sidebar — so I never
    saw that Act 4 wasn't navigable. Future: verify through the real UI
    navigation path (build the sidebar, check the act headings + buttons), not
    just programmatic loads. This is why "it's implemented" was true yet useless.
  - R3.16 now awaits user confirmation that Act 4 appears in their sidebar after
    this fix (they must be on a tree that includes it).
- 2026-07-12 (cont. 2): user confirmed Act 4 now visible. New items + progress:
  - **R3.19 ✅** — planets "too big / need scrolling": ROOT CAUSE = the control
    row for planet scenarios had a hard min width ~1389px (6 tweakables + all
    combos, no wrap), forcing the whole page wider than the viewport and
    stretching the Expanding before/after canvases to that width. Fixed by
    wrapping the controls in their own horizontal scroll strip
    (`controls_scroll`); page min width dropped 1389→645. Not planet-specific in
    cause (planets just have the most controls). Verified via widget metrics.
  - **R3.21 ✅** — dropped `jupiter_full` (Act 4): redundant with `saturn_rings`
    (same toggles, better ring structure) + `color_filter_jupiter` (Act 3).
    17 scenarios now; tests updated (count 18→17, Act 4 count 3→2).
  - **R3.20 (star field) — findings, OPTIONS NEEDED:**
    - **Coma:** at f/4, 135″ off-axis, coma = 0.53″ — SMALLER than the 0.69″
      Airy disk. Edge stars are essentially round; there is genuinely almost no
      coma to show at these params (physics, not a render bug). Even f/3 → ~0.9″.
      To show comet-shaped coma needs a much faster/bigger scope or a zoomed
      edge view. → PROPOSE: (A) faster+bigger showcase scope (e.g. 250mm f/3),
      (B) keep realistic + note coma is subtle, point to fratio_coma, (C) reduce
      FOV. Awaiting user steer (this is exactly the R3.3b realism tradeoff).
    - **Spider spikes:** subtle at these params (on-axis star H-reach 10px vs
      diagonal 5px) — reads as soft cross/halo, not dramatic spikes; user sees
      it as "general blurring, more than obstruction." Needs a rendering look.
    - **Colour:** every star fully saturated spectral tint — unrealistic (real
      fields: mostly white, only bright stars tinted). → PROPOSE desaturate
      toward white with brightness-dependent tint.
- 2026-07-12 (cont. 3): **user chose coma option B** — keep realistic 200 mm
  f/4, accept coma is correctly invisible under seeing, add a note pointing to
  the f-ratio & Coma scenario. Detailed implementation plan written below (§I).
- 2026-07-12 (Batch A DONE): star field rework —
  - **Spider spikes ✅** ROOT CAUSE of the "general blurring": the spider FFT
    PSF's high-frequency ring structure ALIASED into a checkerboard moiré when
    the per-star kernel was bilinear-downsampled to the canvas. Fixed with a
    Gaussian anti-alias pre-filter before downsampling (both the per-star and
    generic-fallback resample paths). Bright stars now show clean, sharp
    spikes; background is clean black (verified crop, seeing on & off).
  - **Colour ✅** magnitude-dependent desaturation in ShowcaseStarField: bright
    stars keep their tint, faint stars trend near-white (realistic). Test
    `test_faint_stars_more_desaturated_than_bright`.
  - **Coma ✅ (option B)** description corrected — coma (~0.5″) is smaller than
    Airy + seeing at f/4, so edge stars stay round (realistic); points to the
    f-ratio & Coma scenario for the dramatic version. Removed the false
    "comet-shaped coma appears" claim.
  - 393 tests pass. Verified the full showcase render through the tab.
- 2026-07-12 (Batch B start): **R3.9 dimness ✅** ROOT CAUSE: the chromatic
  per-star path used SUM-normalised kernels (low peak) while the monochrome
  path uses PEAK-normalised (high peak) → chromatic stars rendered ~6× too
  faint (peak 0.16 vs 0.89). Fixed by rescaling the 3 channel kernels by the
  sharpest channel's peak → in-focus channel peak‑normalised (matches the
  monochrome brightness anchor); defocused channels keep their lower relative
  peaks (chromatic halos preserved). Now peak 0.83. Contained to the chromatic
  per-star path (chromatic_plus_seeing only; B4 uses a different path).
  - **COUPLED ISSUE surfaced:** with the stars now bright, the deferred B7
    GREEN-CORE is prominent (every star has a green core; singlet = green
    blobs). log_integrated does NOT fix it (1″ integration ≪ 5–8″ chromatic
    spread). This is the achromat-secondary-spectrum over-defocus. **Needs user
    decision: un-defer and fix (reduce achromat defocus / render SED core) or
    leave green.**
- **R3.12 (Exposure reframe) — CLARIFICATION NEEDED:** the feedback says both
  "the right plot should stay fixed as the eye view" AND "swap the order so eye
  is on the left and detector on the right" — apparent contradiction. Need the
  intended final layout before building (it's a redesign: pin both panes, drop
  the View combo, add an eye-blur toggle).
- 2026-07-12 (Batch B cont.): **Decision 1 = keep (a)** — grounded by data: the
  green core is the REAL chromatic signature and fades to the star's true colour
  as objective improves (singlet/achromat green → apo-triplet ≈ true blue-white;
  R/B defocus 5000→30 µm). No change; the objective selector already teaches it.
  User may still opt (c) later.
  **Decision 2 = 2a.** **R3.12 ✅** implemented: new `after_display_stretch`
  (pins the After pane + hides the View combo) and `show_eye_blur_toggle` +
  `_add_eye_blur_check`. exposure_demo is now Eye LEFT (pinned, eye-blur toggle)
  / Detector RIGHT (pinned linear, exposure acts). Reframed the description:
  APERTURE affects BOTH panes; EXPOSURE is the detector's time-integration knob
  (one of several brightness influences), not "the whole lesson". Verified via
  tab: no View combo, eye-blur present, exposure changes only the detector,
  aperture changes both. Test updated. 394 pass.
- **Batch B remaining: R3.15 (Bright+Dim — reuse the fixed Eye/Detector layout,
  define HDR, multi-star source), R3.4 (P&P linear-vs-log-eye + evidence).**

---

## §I — Implementation plan & execution order (2026-07-12)

**Verification rule for every item:** check through the REAL GUI navigation /
widget (build the tab, load via the sidebar path, toggle EVERY reachable
combo/checkbox state), not a programmatic `_load_scenario` bypass. Run pytest +
update this ledger's status per item. Commit per batch.

Remaining open items grouped into 7 batches. Each batch = implement → verify →
test → ledger → commit.

### Batch A — Star field rework (R3.20)  [decision: coma = B]
- Coma: keep 200 mm f/4; add an on-plot/description note "coma is smaller than
  the seeing disk here — see f-ratio & Coma (Act 2) for the dramatic version".
- Spider spikes: rework so bright stars show recognisable spikes, not a soft
  cross/blur; make the spider toggle's effect read as spikes. Re-tune
  spider_vane_width / kernel so it's not disproportionately strong vs
  obstruction.
- Colour: brightness-dependent desaturation (faint stars → near-white, only
  bright stars carry tint). Add a `color_saturation`-style control in
  ShowcaseStarField.
- Verify: load "Star Field Showcase" via sidebar; toggle each of
  obstruction/spider/coma/seeing ON and OFF; confirm each reads correctly.

### Batch B — Brightness / eye-vs-detector reframing (R3.12, R3.15, R3.9, R3.4)
- R3.12 Exposure & Saturation: reframe — the lesson is BRIGHTNESS & SATURATION,
  not "exposure is detector-only". Aperture affects BOTH detector and eye
  (already true in the model — fix the framing/annotation). Right pane stays Eye
  (toggle eye-blur only, not free mode switch); SWAP order → Eye left, Detector
  right. Re-check the "exposure N/A in eye" annotation wording.
- R3.15 Bright + Dim: define "HDR" in the description; right pane fixed to Eye
  (not toggleable to detector); redesign the source to SEVERAL stars spanning a
  brightness range (not one pair) so dynamic-range compression actually shows;
  make saturation visible.
- R3.9 Chromatic + seeing dimness: make the stars clearly visible (investigate:
  80 mm aperture² factor + chromatic flux spreading; likely boost source
  magnitudes/brightness for this scenario, or lift the eye-view floor).
- R3.4 P&P: add "Linear detector vs logarithmic eye" section WITH evidence
  (Weber–Fechner; Pogson magnitude scale is logarithmic by definition; cite).
- Verify each scenario's Eye/Detector states + exposure/aperture sweeps.

### Batch C — Chromatic + Spherical ray-trace modules (R3.6, R3.8, R3.5c)
- R3.6a: move the chromatic ray-trace legend OUT into canvas whitespace.
- R3.6b: fix the green/blue-rays-from-focal-point + only-red-diverging artifact
  (in the idealize_sa extension drawing).
- R3.6c: on the right focal-region zoom (top), add "zoomed view of the left
  plot"; draw a box on the left ray trace marking the zoomed region.
- R3.6d: close-zoom range ±12″ → ±10″ (or justify); it's arcsec not degrees.
- R3.8a: add a focal-region zoom plot for spherical (marginal vs paraxial axis
  crossing), analogous to chromatic.
- R3.8c: ray-fan y-axis — relabel transverse offset consistently with the left
  plot's transverse axis (Δx, not Δy); describe "transverse focal-plane offset"
  clearly in the description.
- R3.5c: audit ALL modules for in-plot legends blocking data; move them to the
  side column (reuse the R3.5 pattern).
- Verify via each module's toggles.

### Batch D — Resolution modules (R3.10, R3.11, R3.2, R3.1)
- R3.10 Aperture vs Seeing: right pane gets on/off toggles for seeing and
  aperture-resolution, with their circular overlays toggling too; left pane
  unchanged; reframe as aperture vs seeing vs eye-integration.
- R3.11 f-ratio & Coma: left pane switchable ray-fan (DEFAULT) vs current
  spot-grid; recolour with the pupil-zone colormap (drop cyan/yellow).
- R3.2 Rayleigh: fix so the plot's spatial extent (FOV) does NOT change with
  separation (fixed FOV; only the star positions move).
- R3.1 Airy: (a) fix the pixelated after-PSF at small apertures (oversample /
  interpolate); (b) audit whether the overlay toggle does anything; fix/remove.

### Batch E — Filters & planets (R3.13, R3.14, R3.17)
- R3.13 ND Moon: live ephemeris applies to the LEFT pane too; describe exit
  pupil in the module; investigate why the Moon never gets crisp (seeing?
  resolution cap? magnification?) and note magnification's role.
- R3.14 Colour filters Jupiter: re-review the filter application (red filter
  should reveal/deepen features, not flatten to uniform red); consider a
  no-rescale mode to show true dimming; review the Jupiter texture (GRS
  "highlighter orange"); confirm planet/lunar textures are honest.
- R3.17: re-verify planets render highest-res then degrade (given R3.14).

### Batch F — Parameters & Physics docs + diagram clarity (R3.3, R3.7b, R3.8b, R3.10c)
- R3.3b: realism-audit section — list idealisations (no atmospheric dispersion,
  Gaussian seeing, geometric coma, parametric planet textures, perceptual eye
  model, etc.) with "to improve it would take X / accepted shortcoming because
  Y". R3.3a: assess the eye-mode ring visibility; note.
- R3.7b: rework the vignetting diagram Panel A — add real ray traces; clearly
  define "secondary clear aperture" and the red (clipped) region's relationship
  to it (the confusion: is the red inside/covering/outside the secondary?).
- R3.8b: mention defocus/tilt aberrations in P&P.
- R3.10c: describe eye resolution/integration in the detector-vs-eye P&P section.

### Batch G — Propagation + final pass (R3.18)
- Apply every cross-cutting fix (legends-out, brightness framing, view order,
  live-ephemeris-both-sides) to ALL affected modules; walk every scenario via
  the sidebar and every toggle state; confirm nothing regressed.

**Rough size:** ~6–8 focused sessions. Batches A/B first (user-facing star field
+ the brightness reframing that several items depend on), then C–G.

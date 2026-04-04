# Next Steps — Tutorial & Testing Tab

**Date**: 2026-04-03
**Status**: Approved plan — implementing on `feature/tutorial-testing-tab` branch
**Previous**: Original plan (2026-03-28) was refined through brainstorming session

---

## Overview

A new "Tutorial & Testing" GUI mode that:
1. **Teaches users** optical physics through guided experiments with before/after images
2. **Validates physics** with "Theory predicts X / Simulation shows Y" comparisons
3. **Shows the Python API** in a scoped terminal panel so users learn the programmatic interface

---

## Key Design Decisions

- **Layout**: Guided scenario navigator — left sidebar with scenario list, main area with before/after canvases, theory readout, tweakable controls, terminal panel
- **Interactivity (Option C)**: Before image is static baseline. After side is live — user can tweak parameters.
- **Three-act progression**: Isolated effects → Compounding effects → Real objects with effect toggles
- **Theory comparison**: Both visual overlay on images AND numeric readout
- **Terminal panel**: Scoped to tutorial tab only (not global)
- **Theory computation**: Local to tutorial tab (NOT in telescope_sim physics engine)
- **Physics reference**: Brief inline (2-3 sentences) + "Learn more →" link to Parameters & Physics tab
- **Test objects**: Simplified sources (point source, double star) to isolate effects; same pipeline ensures validity

---

## Scenario Inventory

### Act 1 — Isolated Effects (test objects, one variable)
| # | ID | Title | v1? |
|---|---|---|---|
| 1 | `airy_disk` | Airy Disk | YES |
| 2 | `rayleigh_criterion` | Rayleigh Criterion (DoubleStar) | no |
| 3 | `central_obstruction` | Central Obstruction & Strehl | YES |
| 4 | `spider_vanes` | Spider Vane Diffraction | no |
| 5 | `chromatic_aberration` | Chromatic Aberration | no |
| 6 | `coma` | Coma | no |

### Act 2 — Compounding Effects (multiple variables)
| # | ID | Title | v1? |
|---|---|---|---|
| 7 | `obstruction_plus_spiders` | Obstruction + Spider Vanes | no |
| 8 | `chromatic_plus_seeing` | Chromatic + Seeing | no |
| 9 | `aperture_vs_seeing` | Aperture vs Seeing | YES |
| 10 | `fratio_coma` | f-ratio + Coma | YES |

### Act 3 — Real Objects (effect toggling)
| # | ID | Title | v1? |
|---|---|---|---|
| 11 | `jupiter_full` | Jupiter Full Simulation | YES |
| 12 | `saturn_rings` | Saturn with Rings | no |
| 13 | `starfield_resolution` | Star Field Resolution | no |

**v1 scope**: 5 fully implemented scenarios. Remaining 8 are placeholders ("coming soon").

---

## Implementation Phases

### Phase 1: Foundation
- Add `DoubleStar` source to `telescope_sim/source/sources.py`
- Create `telescope_gui/tutorial_mode/` with scenario dataclasses and registry
- Create local theory computation functions

### Phase 2: Widgets
- Scenario sidebar, before/after panel, theory readout, terminal panel, effect toggles

### Phase 3: Core Logic
- Scenario runner (builds telescopes, calls plot functions, computes theory)
- Add `apply_coma`/`apply_vignetting` toggle params to rendering pipeline

### Phase 4: Assembly & Integration
- Main `TutorialTab` widget wiring everything together
- Register in `main_window.py` as new mode

### Phase 5: Scenarios
- Implement 5 v1 scenarios with theory overlays and terminal commands

### Phase 6: Polish & Test
- End-to-end testing, placeholder verification, unit tests

---

## Branch

All work on `feature/tutorial-testing-tab`. Do NOT merge to main without explicit user approval.

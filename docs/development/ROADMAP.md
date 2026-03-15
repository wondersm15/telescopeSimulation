# Development Roadmap

**Last updated**: March 2026

## Design Philosophy

This simulator emphasizes **realism over idealization**. The goal is to create a useful tool that accurately shows how celestial objects appear through real telescopes, including all physical limitations and atmospheric effects. This realism enables:

- Informed telescope design decisions based on actual performance
- Authentic learning experiences for astronomy and optics
- Realistic expectations for observing conditions and equipment

All features should maintain this commitment to physical accuracy.

---

## Rating System

Each feature is rated on three dimensions:

- **Priority**: High / Medium / Low — development priority and user value
- **Complexity**: High / Medium / Low — implementation effort and technical difficulty
- **Impact**: High / Medium / Low — effect on realism, usability, or educational value

---

## 1. Physics Improvements

Physics enhancements to improve optical realism and expand the range of modeled effects. See [PHYSICS.md](../technical/PHYSICS.md) for detailed technical specifications.

### Geometric Optics

| Feature | Priority | Complexity | Impact | Notes |
|---------|----------|------------|--------|-------|
| **Elliptical mirrors** (Ritchey-Chrétien) | Medium | Medium | Medium | Professional wide-field design; requires ellipse ray intersection |
| **Surface errors** | Low | Medium | Medium | Manufacturing imperfections; wavefront distortion |

### Wave Optics

| Feature | Priority | Complexity | Impact | Notes |
|---------|----------|------------|--------|-------|
| **Wavefront error & Zernike polynomials** | Medium | High | High | Precise aberration analysis; replaces approximate Strehl calculation |
| **Interference and coherence** | Low | High | Low | Niche applications; not critical for astronomical imaging |

### Atmospheric Effects

| Feature | Priority | Complexity | Impact | Notes |
|---------|----------|------------|--------|-------|
| **Kolmogorov/Moffat seeing profile** | Medium | Medium | Medium | More realistic than current Gaussian; broader wings affect MTF |
| **Atmospheric refraction** | Low | Low | Low | Altitude-dependent bending; affects horizon observations |
| **Atmospheric extinction** | Low | Low | Medium | Dimming/reddening near horizon; color and brightness changes |
| **Sky background brightness** | Medium | Medium | High | Light pollution; critical for extended object contrast |

### Visual Perception & Brightness

| Feature | Priority | Complexity | Impact | Notes |
|---------|----------|------------|--------|-------|
| **Surface brightness vs magnification** | High | Low | High | Objects dim at high mag; affects color saturation |
| **Eye adaptation (Purkinje shift)** | Low | Medium | Low | Dark-adapted color sensitivity; blue shift at low light |
| **Human eye resolution limit** | Medium | Low | Medium | ~1 arcmin; detail loss at low magnification |

### Eyepiece Optics

| Feature | Priority | Complexity | Impact | Notes |
|---------|----------|------------|--------|-------|
| **Ray-traced eyepiece model** | Low | High | Medium | Field curvature, astigmatism, edge aberrations |
| **Eyepiece chromatic aberration** | Low | Medium | Low | Simple designs (Plössl) vs apochromats |

### Extended Sources & Detector

| Feature | Priority | Complexity | Impact | Notes |
|---------|----------|------------|--------|-------|
| **Deep-sky objects** | Medium | Medium | High | Nebulae, galaxies, clusters; educational value |
| **Pixel sampling, noise, QE** | Low | Medium | Low | Astrophotography focus; not visual observing |

**Summary**: Physics improvements focus on atmospheric realism (sky glow, seeing profiles) and visual perception (surface brightness changes). Most critical for authentic observing simulation.

---

## 2. GUI Application

**Priority**: High | **Complexity**: High | **Impact**: High

Transform the command-line simulation into an interactive graphical application for easier access and exploration.

### Core Features

- **Interactive parameter controls**: Sliders/dropdowns for aperture, focal length, telescope type, seeing conditions
- **Real-time visualization**: Update ray traces and images as parameters change
- **Tabbed interface**:
  - Ray trace view
  - PSF analysis
  - Simulated images
  - Comparison mode
  - Educational content (see section 5)
- **Terminal integration**:
  - Embedded terminal window showing executed commands
  - Buttons generate and display terminal commands before execution
  - Helps users learn the underlying API
- **Export capabilities**: Save images, configurations, and reports

### Technical Approach

- **Framework**: Consider PyQt6, Tkinter, or web-based (Streamlit/Dash)
- **Backend**: Existing telescope_sim package (no major refactor needed)
- **Progressive enhancement**: Start with simple GUI, add features iteratively

### Why This Matters

Currently, users must edit `main.py` to change configurations. A GUI would:
- Lower barrier to entry for non-programmers
- Enable rapid design iteration and "what-if" exploration
- Make the tool accessible for educational settings (classrooms, outreach)
- Maintain transparency (terminal window) for learning

---

## 3. Real-World Integration

**Priority**: High | **Complexity**: Medium-High | **Impact**: High

Connect the simulator to real-world astronomical data for authentic observing planning and location-aware simulations.

### Features

| Feature | Priority | Complexity | Impact | Description |
|---------|----------|------------|--------|-------------|
| **Location-based observing conditions** | High | Medium | High | Weather API integration; current seeing, cloud cover, humidity |
| **Time-based ephemeris** | High | Medium | High | Planetary positions, lunar phase, rise/set times |
| **Live object distances** | Medium | Low | Medium | Current Earth-object distances; affects angular size |
| **Altitude/azimuth calculations** | High | Low | High | What's visible now from user location |
| **Atmospheric model** | Medium | Medium | Medium | Location altitude, temperature, pressure; affects refraction |

### Implementation Notes

- **Parallel to standard definitions**: Don't replace fixed test cases; add real-world mode as option
- **APIs**: Consider `astropy` (ephemeris), `skyfield` (positions), weather APIs
- **Caching**: Store ephemeris data locally to minimize API calls
- **Offline fallback**: Continue working without internet connection using cached data

### Use Cases

- **Observing tonight**: "What will Jupiter look like through my 8\" SCT tonight at 10pm?"
- **Planning**: "When is Mars closest? How much bigger will it appear?"
- **Site evaluation**: "How does seeing at my location affect planetary imaging?"

---

## 4. Constellation System

**Priority**: Medium | **Complexity**: Medium | **Impact**: High (educational)

Add constellation visualization and identification to help users learn the night sky and contextualize observations.

### Features

| Feature | Priority | Complexity | Impact | Description |
|---------|----------|------------|--------|-------------|
| **Star pattern definitions** | High | Low | High | Constellation line patterns (IAU boundaries) |
| **Field overlay** | High | Medium | High | Show constellation lines in simulated FOV |
| **Constellation identification** | Medium | Low | Medium | "You are looking at Orion" |
| **Star field rendering** | Medium | Medium | High | Realistic star magnitudes and colors in FOV |
| **Interactive learning mode** | Medium | Low | High | Click on constellation for info (see section 5) |

### Data Sources

- **Star catalogs**: Hipparcos, Yale Bright Star Catalog, Gaia DR3 (subset)
- **Constellation data**: IAU constellation boundaries, stick figures
- **Integration**: Overlay on telescope FOV based on pointing direction

### Educational Value

- **Learn by observing**: "What constellation is that bright star in?"
- **Context**: See how telescope FOV relates to larger constellation patterns
- **Planning**: "Can I fit the Orion Nebula and Trapezium in my eyepiece FOV?"

---

## 5. Educational Features

**Priority**: Medium | **Complexity**: Low-Medium | **Impact**: High (educational)

Transform the simulator into a comprehensive learning tool with integrated explanations and reference material.

### Features

| Feature | Priority | Complexity | Impact | Description |
|---------|----------|------------|--------|-------------|
| **Constellation notes** | Medium | Low | High | Mythology, bright stars, notable DSOs in each constellation |
| **Telescope design explanations** | High | Low | High | "Why Cassegrain vs Newtonian?" with diagrams and tradeoffs |
| **Physics tooltips** | Medium | Low | Medium | Hover over "Airy disk" → see definition and formula |
| **Guided tutorials** | Medium | Medium | High | Step-by-step lessons: "Understanding diffraction limits" |
| **Comparison explanations** | High | Low | High | Auto-generated text: "The achromat shows less color fringing because..." |

### Implementation (GUI Context)

- **Educational tab**: Dedicated GUI panel with:
  - Telescope design reference (types, tradeoffs, typical uses)
  - Constellation guide (notes, mythology, DSO highlights)
  - Physics primer (optics concepts, formulas, intuition)
- **Contextual help**: Right-click on any element → "Learn more"
- **Interactive diagrams**: Click on ray trace → highlight and explain that optical element

### Content Organization

- **Beginner**: "What is an f-ratio?" "Why can't I see nebula colors?"
- **Intermediate**: "Cassegrain vs Ritchey-Chrétien" "How does coma affect imaging?"
- **Advanced**: "Wavefront error analysis" "Optimizing secondary obstruction"

### Why This Matters

The simulator already models realistic physics. Adding explanations transforms it from a **tool** into a **teacher**:
- Users understand *why* a 6\" achromat shows less color than a 6\" singlet
- Learners connect ray diagrams to actual performance
- Design decisions become informed rather than trial-and-error

---

## Summary Table

| Category | Priority | Complexity | Impact | Key Value |
|----------|----------|------------|--------|-----------|
| **Physics Improvements** | Medium | Medium | High | Optical realism |
| **GUI Application** | High | High | High | Accessibility |
| **Real-World Integration** | High | Medium-High | High | Practical utility |
| **Constellation System** | Medium | Medium | High | Sky navigation |
| **Educational Features** | Medium | Low-Medium | High | Learning tool |

---

## Implementation Strategy

### Phase 1: Foundation (High Priority, Lower Complexity)
1. **Surface brightness vs magnification** (physics)
2. **Sky background brightness** (physics)
3. **Educational content** (telescope descriptions, constellation notes)

### Phase 2: Real-World Connection (High Impact)
1. **Location-based conditions** (weather API, seeing)
2. **Time-based ephemeris** (planetary positions)
3. **Constellation overlay** (star patterns in FOV)

### Phase 3: GUI (High Impact, High Effort)
1. Basic GUI with parameter controls
2. Terminal integration
3. Tabbed interface
4. Educational tab

### Phase 4: Advanced Physics (Medium Priority)
1. Kolmogorov/Moffat seeing
2. Wavefront error analysis
3. Elliptical mirrors (Ritchey-Chrétien)

---

## Contributing

When implementing features from this roadmap:
- Maintain the **realism-first** philosophy
- Document approximations clearly in code and outputs
- Add tests for new physics implementations
- Update [PHYSICS.md](../technical/PHYSICS.md) when adding new models
- Update this roadmap to track progress

For questions or suggestions, see [devlog.md](devlog.md) for development history and context.

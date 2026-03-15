# Telescope Simulation Project

A physics-based telescope simulation tool for optical design and visualization.

## Overview

This project simulates optical telescope systems from first principles, enabling both practical design decisions and educational visualization. The simulator performs ray tracing through realistic telescope geometries, models wave optics (diffraction), and produces simulated astronomical images.

### Goals

- **Design Tool**: Make informed telescope design decisions (focal ratio, aperture, optical configuration)
- **Visualization**: Ray tracing through mirrors, lenses, and apertures with realistic physics
- **Image Simulation**: Generate authentic views of celestial objects (planets, Moon, etc.) as they would appear through different telescope designs
- **Realism**: Emphasize accurate physics over idealized representations to support real-world design and observing decisions

### Key Capabilities

- **Multiple telescope types**: Newtonian, Cassegrain, Maksutov-Cassegrain, Schmidt-Cassegrain, Refractor (singlet and achromat)
- **Realistic optics**: Parabolic/spherical/hyperbolic mirrors, refractive lenses with dispersion
- **Chromatic aberration**: Multi-wavelength ray tracing and color fringing for refractors
- **Wave optics**: Airy diffraction patterns, central obstruction effects, spider vane diffraction
- **Atmospheric effects**: Configurable seeing conditions
- **Extended sources**: Jupiter, Moon with realistic textures and proper angular size
- **Visual observing**: Eyepiece field of view, magnification, exit pupil effects

## Quick Start

### Installation

1. Clone this repository and navigate to the project directory
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Simulation

With the virtual environment active:
```bash
python main.py
```

This opens matplotlib windows showing:
- 2D ray trace through the telescope optical system
- Point spread function (PSF) analysis
- Simulated astronomical images (if a source is configured)

Edit `main.py` to configure telescope parameters, source objects, and visualization options. The file includes detailed comments and examples.

### Running Tests

```bash
python -m pytest tests/ -v
```

## Documentation

- **[User Guide](docs/user/USER_GUIDE.md)** - Comprehensive guide to telescope types, features, and examples
- **[Physics Reference](docs/technical/PHYSICS.md)** - Detailed physics implementation inventory
- **[Formulas Reference](docs/technical/FORMULAS.md)** - Mathematical formulas and derivations
- **[Development Roadmap](docs/development/ROADMAP.md)** - Planned features and priorities
- **[Development Log](docs/development/devlog.md)** - Session-by-session development history

## Project Structure

```
telescopeSimulationProject/
├── main.py                # Entry point — configure and run simulations
├── requirements.txt       # Python dependencies
├── telescope_sim/         # Main package
│   ├── physics/          # Ray class, reflection, refraction
│   ├── geometry/         # Mirror/lens types, telescope assembly
│   ├── source/           # Light source and astronomical object definitions
│   └── plotting/         # Visualization and image rendering
├── tests/                # Unit and integration tests
└── docs/                 # Documentation (see above)
```

## Design Philosophy

This simulator emphasizes **realism over idealization**:
- Real optical aberrations (spherical, chromatic, coma)
- Atmospheric seeing and turbulence
- Finite aperture diffraction
- Wavelength-dependent refraction
- Manufacturing approximations noted in code and outputs

The goal is to provide an authentic representation of how telescopes perform in practice, supporting real design decisions and teaching how optical systems work.

## License

(Add license information as appropriate)

# Telescope Simulation Project

## Project Description & Goals
* The goal is to make a virtual telescope simulation tool that is both useful to
help design a telescope that I am making (i.e., for practical purposes like choosing
a focal ratio); and to simulate and visualize the optical process in the telescope and
to produce simulated images (i.e., for fun/cool purposes).
* It should have cool visualization capabilities like being able to show the light ray
tracing coming into the telescope and bouncing off mirrors and going through apertures,
within a specified telescope geometry. It should also be able to produce simulated images
like what Jupiter would look like through a defined telescope.
* It should be able to model important physics for telescope design like diffraction.
If it is too difficult to model from first principles, standalone/ad hoc/empirical modules
can be used to understand things like focal ratio impact on image quality.
* A stretch/long-term goal would be to link to real-time data to simulate images.


## Project Architecture
### Modules
Implemented modules can change but envisioned modules include:
* Geometry (defining the telescope geometry)
* Source (defining what we are looking at such as a planet to produce the photon source)
* Physics (defining relevant physics processes to be implemented like reflection)
* Plotting and visualization (implementing the desired image production)


## Language Preferences
Primary language is python


## Physics Policy
* Use real physics everywhere possible so the simulation can inform real design decisions.
* Where real physics is not used (e.g., approximations or placeholders), flag it clearly
  in code comments and in plot/output text so the user knows the limitation.
* See PHYSICS.md for a detailed inventory of what physics is and isn't yet implemented.


## Coding Conventions & Style
* Follow PEP 8 conventions: snake_case for functions, methods, and variables; PascalCase for class names; UPPER_SNAKE_CASE for constants.
* Where possible, reduce duplication of code so that specific logic only needs to be implemented
once rather than multiple times in multiple places.
* Let's use good coding practices to help me become a better coder.


## General Preferences
* Claude should make a log (e.g., possibly in some text file) of what it has done to help me understand, keep track and remember over time. This should include logging things installed, tasks completed, etc.
* Claude should try to facilitate context persistency across sessions, perhaps by making a chat history summary file (which would also help me).
* If anything is impacting performance of Claude Code (for example if history logging is taking up
too many tokens or things are not optimized), let me know so we can try to improve it.
* Before beginning a long coding session, make a plan and summarize it with an estimated time it will take. When doing this coding session, continue on without asking for permission until done.
* Track and tell me how my usage is going and if I am likely to run out of tokens or usage soon
(or during a long coding session that is about to start)

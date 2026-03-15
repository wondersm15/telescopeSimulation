# Claude Code Instructions — Telescope Simulation Project

> See README.md for project overview and goals. This file contains coding conventions and preferences for AI assistance.

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
* Entry-point scripts (main.py) should expose options with descriptive comments and
commented-out alternatives so users can discover and toggle features easily.

# Telescope Simulation Project — Quick Reference Guide

## Getting Started

### Virtual Environment
Always activate the virtual environment before working on the project:
```bash
source venv/bin/activate
```
You should see `(venv)` at the start of your terminal prompt when it's active.

To deactivate when you're done:
```bash
deactivate
```

### Installing Packages
With the virtual environment active, install packages using pip:
```bash
pip install <package-name>
```
To save your current dependencies to a file (so they can be reproduced):
```bash
pip freeze > requirements.txt
```
To install from an existing requirements file:
```bash
pip install -r requirements.txt
```

## Working with Claude Code
- Launch Claude Code from the project directory (`~/Work/telescopeSimulationProject`) so it picks up the project context
- Check `devlog.md` for a history of what's been done across sessions
- Check `CLAUDE.md` for project rules and conventions — update it as preferences evolve

## Project Structure
```
telescopeSimulationProject/
├── CLAUDE.md        # Instructions for Claude Code
├── GUIDE.md         # This file — reference guide for you
├── devlog.md        # Development log across sessions
├── venv/            # Python virtual environment (don't edit or commit)
└── ...              # Source code to come
```

## Things to Remember
- Activate the virtual environment before installing packages or running code
- Don't edit files inside `venv/` — it's managed automatically
- If you add a new dependency, run `pip freeze > requirements.txt` to track it
- When starting a new Claude Code session, mention where you left off or check `devlog.md`

# Prompt for the deploying agent: Telescope Simulator

Paste the text below into the Public Apps Deployment session.

---

Please integrate the Telescope Simulator at `/apps/telescope-simulation/`.

**Get the files.** Everything is in git, built and checked, with no build
step needed.
- Repository: https://github.com/wondersm15/telescopeSimulation
- Branch: `feature/web-app`. Use this branch, not main.
- Folder: `deploy/telescope-simulation/`

```sh
git clone --depth 1 --branch feature/web-app https://github.com/wondersm15/telescopeSimulation.git telescope-src
cp -R telescope-src/deploy/telescope-simulation/ "/Users/marcwonders/Documents/Codex/Projects/Public Apps Deployment/artifacts/incoming/telescope-simulation/"
```

**What it contains.**
- The folder follows the handoff format: `index.html` at the root, plus
  `assets/` and `data/` (and `about.html`).
- All paths are app-relative.
- It is static only. At runtime it makes no requests to any other origin.

**Read `deploy/HANDOFF.md` on the same branch.** It covers:
- the source version;
- the build and preview commands;
- the validation results;
- the distribution approval and licences;
- the external services and headers.

In short:
- `.wasm` must be served as `application/wasm`.
- No COOP/COEP headers are needed.
- If a Content-Security-Policy is set, it must allow `'wasm-unsafe-eval'`.
  Pyodide may also need `'unsafe-eval'`, so test with the CSP enabled.
- Long cache lifetimes are fine for `assets/pyodide/`, `assets/py/wheels/`
  and `data/`.
- The largest file is 16.8 MB (`data/de421.bsp`). The first visit downloads
  about 43 MB.

**Check after integrating.** Open `/apps/telescope-simulation/` and wait for the mode bar; it
takes 10–30 s on first load. Reload the page; it must come back. Check that
the "About · download the desktop app · credits" link opens `about.html`
and that the zip download works.

**Approval.** Do not publish publicly until Marc confirms the distribution
approval listed in HANDOFF.md.

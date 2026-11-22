// Headless smoke test of the browser build, run in Node from web/dist.
//
//   node web/tools/smoke_node.mjs [scenario-key ...]
//
// Loads the self-hosted Pyodide runtime, the pinned wheels and the frozen
// desktop code (py/app.zip) exactly as the browser will, runs tutorial
// scenarios, and writes each figure's data arrays to web/smoke/<key>.npz so
// web/tools/compare_desktop.py can check them against the desktop app.
// With no arguments every scenario runs.

import { readFile, writeFile, mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const dist = path.resolve(here, "..", "dist");
const outDir = path.resolve(here, "..", "smoke");
const { loadPyodide } = await import(path.join(dist, "pyodide", "pyodide.mjs"));

// Pyodide wants plain typed arrays, not Node Buffers.
const readBytes = async (file) => new Uint8Array(await readFile(file));

const t0 = performance.now();
const lap = (label, since) =>
  console.log(`${label.padEnd(28)} ${((performance.now() - since) / 1000).toFixed(2)} s`);

const pyodide = await loadPyodide({ indexURL: path.join(dist, "pyodide") + "/" });
lap("runtime", t0);

let t = performance.now();
await pyodide.loadPackage(["numpy", "scipy", "matplotlib", "pillow"]);
const manifest = JSON.parse(await readFile(path.join(dist, "py", "manifest.json")));
const sitePackages = pyodide.runPython("import site; site.getsitepackages()[0]");
for (const wheel of manifest.wheels) {
  const buf = await readBytes(path.join(dist, "py", "wheels", wheel));
  pyodide.unpackArchive(buf, "wheel", { extractDir: sitePackages });
}
lap("packages", t);

t = performance.now();
pyodide.unpackArchive(await readBytes(path.join(dist, "py", "app.zip")), "zip",
                      { extractDir: "/home/pyodide" });
pyodide.FS.mkdirTree("/home/pyodide/.skyfield");
pyodide.FS.writeFile("/home/pyodide/.skyfield/de421.bsp",
                     await readBytes(path.join(dist, manifest.ephemeris)));
lap("app + ephemeris", t);

const keys = process.argv.slice(2);
pyodide.globals.set("REQUESTED_KEYS", pyodide.toPy(keys));
pyodide.globals.set("FIG_ARRAYS_SOURCE",
                    await readFile(path.join(here, "fig_arrays.py"), "utf8"));
const report = pyodide.runPython(`
import sys, time, io, json
sys.path.insert(0, "/home/pyodide")
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

t = time.perf_counter()
from telescope_gui.tutorial_mode.scenario_registry import SCENARIOS
from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
exec(FIG_ARRAYS_SOURCE)  # defines figure_arrays — shared with compare_desktop.py
import_s = time.perf_counter() - t

results = {}
items = SCENARIOS.items() if isinstance(SCENARIOS, dict) else enumerate(SCENARIOS)
for key, s in items:
    key = str(key)
    if REQUESTED_KEYS and key not in REQUESTED_KEYS:
        continue
    t = time.perf_counter()
    fig, info, err = run_scenario_side(
        s.after_telescope, s.after_source, s.plot_function,
        wavelength_nm=s.after_wavelength_nm,
        seeing_arcsec=s.after_seeing_arcsec,
        polychromatic=s.after_polychromatic,
        display_stretch=s.after_display_stretch or "linear")
    compute_s = time.perf_counter() - t
    t = time.perf_counter()
    png = io.BytesIO()
    if fig is not None:
        fig.savefig(png, format="png", dpi=80)
    draw_s = time.perf_counter() - t
    plt.close("all")
    arrays = figure_arrays(fig)
    np.savez(f"/tmp/{key}.npz", **arrays)
    results[key] = dict(title=s.title, compute_s=compute_s, draw_s=draw_s,
                        error=str(err) if err else None,
                        n_arrays=len(arrays), png_bytes=png.tell())

# Live-sky ephemeris, through skyfield + the bundled DE421.
t = time.perf_counter()
from telescope_sim.source.realtime import jupiter_angular_diameter
jup = jupiter_angular_diameter()
realtime = dict(jupiter_arcsec=jup, seconds=time.perf_counter() - t)

json.dumps(dict(import_s=import_s, scenarios=results, realtime=realtime,
                python=sys.version.split()[0], numpy=np.__version__))
`);
const data = JSON.parse(report);

await mkdir(outDir, { recursive: true });
for (const [key, r] of Object.entries(data.scenarios)) {
  await writeFile(path.join(outDir, `${key}.npz`), pyodide.FS.readFile(`/tmp/${key}.npz`));
}
await writeFile(path.join(outDir, "report.json"), JSON.stringify(data, null, 2));

console.log(`python ${data.python}, numpy ${data.numpy}; imports ${data.import_s.toFixed(2)} s`);
let total = 0;
for (const [key, r] of Object.entries(data.scenarios)) {
  total += r.compute_s + r.draw_s;
  console.log(`${(r.compute_s + r.draw_s).toFixed(2).padStart(6)} s  ` +
              `(draw ${r.draw_s.toFixed(2)})  ${String(r.n_arrays).padStart(3)} arrays  ` +
              `${key.padStart(2)} ${r.title} ${r.error ?? ""}`);
}
console.log(`scenarios total ${total.toFixed(1)} s`);
console.log(`realtime Jupiter ${data.realtime.jupiter_arcsec.toFixed(2)}″ ` +
            `in ${data.realtime.seconds.toFixed(2)} s`);
lap("TOTAL", t0);

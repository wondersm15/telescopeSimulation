// Pyodide worker: keeps the page responsive while Python runs.
// Loads the self-hosted runtime + the frozen desktop code (py/app.zip).
import { loadPyodide } from "./pyodide/pyodide.mjs";

// Manifest paths are relative to the site root, one level above assets/.
const root = new URL("../", import.meta.url);
const say = (text) => postMessage({ type: "log", text });
const fetchBytes = async (rel) =>
  new Uint8Array(await (await fetch(new URL(rel, root))).arrayBuffer());
const secs = (t) => ((performance.now() - t) / 1000).toFixed(2) + " s";

self.onmessage = async ({ data }) => {
  try {
    let t = performance.now();
    const pyodide = await loadPyodide({ indexURL: new URL("./pyodide/", import.meta.url).href });
    say(`runtime ${secs(t)}`);

    t = performance.now();
    await pyodide.loadPackage(["numpy", "scipy", "matplotlib", "pillow"]);
    const manifest = await (await fetch(new URL("./py/manifest.json", import.meta.url))).json();
    const site = pyodide.runPython("import site; site.getsitepackages()[0]");
    for (const wheel of manifest.wheels) {
      pyodide.unpackArchive(await fetchBytes(wheel), "wheel",
                            { extractDir: site });
    }
    pyodide.unpackArchive(await fetchBytes(manifest.app_zip), "zip",
                          { extractDir: "/home/pyodide" });
    say(`packages + app ${secs(t)}`);

    t = performance.now();
    pyodide.FS.mkdirTree("/home/pyodide/.skyfield");
    pyodide.FS.writeFile("/home/pyodide/.skyfield/de421.bsp",
                         await fetchBytes(manifest.ephemeris));
    const jup = pyodide.runPython(`
import sys; sys.path.insert(0, "/home/pyodide")
from telescope_sim.source.realtime import jupiter_angular_diameter
jupiter_angular_diameter()`);
    say(`ephemeris: Jupiter now ${jup.toFixed(2)}″ (${secs(t)})`);

    for (const key of data.scenarios) {
      t = performance.now();
      pyodide.globals.set("KEY", key);
      const out = pyodide.runPython(`
import io, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from telescope_gui.tutorial_mode.scenario_registry import SCENARIOS
from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side
s = SCENARIOS[KEY]
fig, info, err = run_scenario_side(
    s.after_telescope, s.after_source, s.plot_function,
    wavelength_nm=s.after_wavelength_nm, seeing_arcsec=s.after_seeing_arcsec,
    polychromatic=s.after_polychromatic,
    display_stretch=s.after_display_stretch or "linear")
buf = io.BytesIO()
if fig is not None:
    fig.savefig(buf, format="png", dpi=80)
plt.close("all")
(s.title, buf.getvalue(), err)`).toJs();
      const [title, png, err] = out;
      if (err) throw new Error(err);
      postMessage({ type: "figure", title, png }, [png.buffer]);
      say(`${title}: ${secs(t)}`);
    }
    postMessage({ type: "done", text: `ok ${data.scenarios.length} scenarios` });
  } catch (e) {
    postMessage({ type: "error", text: String(e).slice(0, 2000) });
  }
};

// Loads Python (Pyodide, self-hosted) and starts the desktop interface.
//
// All URLs are relative to this file, so the site works under any base
// path (e.g. /apps/telescope-simulation/) and on refresh. Nothing is
// fetched from another origin.
//
// Pyodide runs on the page's main thread because the interface code
// manipulates the page directly (see web/py/qtshim/dom.py).
import { loadPyodide } from "./pyodide/pyodide.mjs";

const base = new URL("./", import.meta.url);
const logEl = document.getElementById("load-log");
const progress = document.getElementById("load-progress");
const t0 = performance.now();
const secs = () => ((performance.now() - t0) / 1000).toFixed(1) + " s";
const step = (text) => {
  progress.value += 1;
  logEl.textContent += `${text} (${secs()})\n`;
};
const fetchBytes = async (rel) => {
  const res = await fetch(new URL(rel, base));
  if (!res.ok) throw new Error(`${rel}: HTTP ${res.status}`);
  return new Uint8Array(await res.arrayBuffer());
};

let pyodide;
let manifest;
let ephemerisReady = false;

function writeEphemeris(bytes) {
  if (ephemerisReady) return;
  pyodide.FS.mkdirTree("/home/pyodide/.skyfield");
  pyodide.FS.writeFile("/home/pyodide/.skyfield/de421.bsp", bytes);
  ephemerisReady = true;
}

// Called from Python (web_app.py) if live sky is used before the
// background download has finished. Synchronous binary XHR is the only way
// to block for a file on the main thread; it happens at most once.
function loadEphemerisNow() {
  if (ephemerisReady) return;
  const xhr = new XMLHttpRequest();
  xhr.open("GET", new URL(manifest.ephemeris, base), false);
  xhr.overrideMimeType("text/plain; charset=x-user-defined");
  xhr.send();
  if (xhr.status !== 200) throw new Error(`ephemeris: HTTP ${xhr.status}`);
  const text = xhr.responseText;
  const bytes = new Uint8Array(text.length);
  for (let i = 0; i < text.length; i++) bytes[i] = text.charCodeAt(i) & 0xff;
  writeEphemeris(bytes);
}

window.telescopeApp = { loadEphemerisNow, status: "loading" };

async function main() {
  pyodide = await loadPyodide({ indexURL: new URL("pyodide/", base).href });
  step("Python runtime");

  manifest = await (await fetch(new URL("py/manifest.json", base))).json();
  await pyodide.loadPackage(manifest.pyodide_packages, { messageCallback: () => {} });
  step("numpy, scipy, matplotlib");

  const site = pyodide.runPython("import site; site.getsitepackages()[0]");
  for (const wheel of manifest.wheels) {
    pyodide.unpackArchive(await fetchBytes(`py/wheels/${wheel}`), "wheel",
                          { extractDir: site });
  }
  for (const archive of [manifest.app_zip, manifest.web_zip]) {
    pyodide.unpackArchive(await fetchBytes(archive), "zip",
                          { extractDir: "/home/pyodide" });
  }
  step("simulator code");

  pyodide.runPython(`
import sys
sys.path.insert(0, "/home/pyodide")
import web_app, qtshim
qtshim.install()
import telescope_gui.main_window`);
  step("interface modules");

  const mode = location.hash.replace(/^#/, "") || null;
  const app = document.getElementById("app");
  pyodide.globals.get("web_app").start(app, mode);
  step("interface ready");

  // Live-sky ephemeris: fetched after start-up so it doesn't delay the page.
  fetchBytes(manifest.ephemeris).then(writeEphemeris).catch((e) =>
    console.warn("ephemeris prefetch failed; will retry on demand", e));

  document.documentElement.dataset.status = "ready";
  window.telescopeApp.status = "ready";
  console.log(`Telescope Simulator ready in ${secs()}`);
}

main().catch((e) => {
  logEl.textContent += `\nFailed to start: ${e}\n`;
  console.error(e);
  document.documentElement.dataset.status = "error";
  window.telescopeApp.status = "error";
});

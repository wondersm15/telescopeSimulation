// Real-browser check of web/dist, served under the production base path.
//
//   node web/tools/browser_check.mjs [--screenshot out.png] [--reload]
//
// Serves web/dist at http://127.0.0.1:<port>/apps/telescope-simulation/ (a
// plain static server, like Cloudflare), opens it in headless Chrome via the
// DevTools protocol, waits for the page to set document.title to "DONE …" or
// "ERROR …", and prints the page log. --reload also reloads the page once to
// confirm the entry page survives a refresh at that URL.

import { createServer } from "node:http";
import { readFile, stat, writeFile, mkdtemp } from "node:fs/promises";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { tmpdir } from "node:os";
import path from "node:path";

const BASE_PATH = "/apps/telescope-simulation/";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const TIMEOUT_MS = 180_000;
const MIME = {
  ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript",
  ".json": "application/json", ".wasm": "application/wasm",
  ".zip": "application/zip", ".whl": "application/zip",
  ".png": "image/png", ".css": "text/css", ".bsp": "application/octet-stream",
};

const here = path.dirname(fileURLToPath(import.meta.url));
const dist = path.resolve(here, "..", "dist");
const args = process.argv.slice(2);
const screenshotPath = args.includes("--screenshot")
  ? path.resolve(args[args.indexOf("--screenshot") + 1]) : null;

// ── Static server ─────────────────────────────────────────────────────
let bytesServed = 0;
const server = createServer(async (req, res) => {
  const url = new URL(req.url, "http://x");
  if (!url.pathname.startsWith(BASE_PATH)) { res.writeHead(404).end(); return; }
  let rel = decodeURIComponent(url.pathname.slice(BASE_PATH.length)) || "index.html";
  const file = path.join(dist, rel);
  if (!file.startsWith(dist)) { res.writeHead(403).end(); return; }
  try {
    if ((await stat(file)).isDirectory()) throw new Error("dir");
    const body = await readFile(file);
    bytesServed += body.length;
    res.writeHead(200, { "Content-Type": MIME[path.extname(file)] ?? "application/octet-stream" });
    res.end(body);
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise((ok) => server.listen(0, "127.0.0.1", ok));
const pageUrl = `http://127.0.0.1:${server.address().port}${BASE_PATH}`;

// ── Headless Chrome over the DevTools protocol ────────────────────────
const profile = await mkdtemp(path.join(tmpdir(), "chrome-check-"));
const chrome = spawn(CHROME, ["--headless=new", "--remote-debugging-port=0",
  `--user-data-dir=${profile}`, "--window-size=1100,1400", "about:blank"],
  { stdio: ["ignore", "ignore", "pipe"] });
const wsUrl = await new Promise((ok, fail) => {
  let err = "";
  chrome.stderr.on("data", (d) => {
    err += d;
    const m = err.match(/DevTools listening on (ws:\/\/\S+)/);
    if (m) ok(m[1]);
  });
  setTimeout(() => fail(new Error("Chrome did not start")), 20_000);
});
const browserWs = new WebSocket(wsUrl);
await new Promise((ok) => browserWs.addEventListener("open", ok, { once: true }));

let nextId = 1;
const pending = new Map();
browserWs.addEventListener("message", ({ data }) => {
  const msg = JSON.parse(data);
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg);
    pending.delete(msg.id);
  }
});
const send = (method, params = {}, sessionId) => new Promise((ok) => {
  const id = nextId++;
  pending.set(id, ok);
  browserWs.send(JSON.stringify({ id, method, params, sessionId }));
});

const { result: { targetId } } = await send("Target.createTarget", { url: "about:blank" });
const { result: { sessionId } } = await send("Target.attachToTarget", { targetId, flatten: true });
const evaluate = async (expr) =>
  (await send("Runtime.evaluate", { expression: expr, returnByValue: true }, sessionId))
    .result?.result?.value;

async function loadAndWait(label) {
  const t0 = performance.now();
  await send("Page.navigate", { url: pageUrl }, sessionId);
  let title = "";
  while (!/^(DONE|ERROR)/.test(title)) {
    if (performance.now() - t0 > TIMEOUT_MS) { title = "ERROR timeout"; break; }
    await new Promise((ok) => setTimeout(ok, 500));
    title = (await evaluate("document.title")) ?? "";
  }
  const log = await evaluate("document.getElementById('log')?.textContent ?? ''");
  console.log(`── ${label}: ${title} (${((performance.now() - t0) / 1000).toFixed(1)} s wall)`);
  console.log(log);
  return title.startsWith("DONE");
}

let ok = await loadAndWait("first load");
console.log(`served ${(bytesServed / 1e6).toFixed(1)} MB (uncompressed, no cache)`);
if (screenshotPath) {
  const shot = await send("Page.captureScreenshot",
    { format: "png", captureBeyondViewport: true }, sessionId);
  await writeFile(screenshotPath, Buffer.from(shot.result.data, "base64"));
  console.log(`screenshot → ${screenshotPath}`);
}
if (args.includes("--reload")) ok = (await loadAndWait("refresh at same URL")) && ok;

chrome.kill();
server.close();
process.exit(ok ? 0 : 1);

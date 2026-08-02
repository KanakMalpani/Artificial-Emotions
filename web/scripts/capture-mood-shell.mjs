/**
 * Capture mood-shell presets → docs/media/mood-shell.gif
 *
 * Visits /?mood=bored|anxious|pleasant, screenshots [data-testid="mood-shell"],
 * then assembles a palette-optimized GIF (Pillow) under ~2–3 MB.
 *
 * Usage (from web/):
 *   node scripts/capture-mood-shell.mjs
 *
 * Optional env:
 *   MOOD_SHELL_BASE_URL  — default http://127.0.0.1:5173 (starts Vite if needed)
 *   MOOD_SHELL_OUT       — override output path
 */
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdir, writeFile, unlink } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const { chromium } = require("@playwright/test");

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = path.resolve(__dirname, "..");
const REPO_ROOT = path.resolve(WEB_ROOT, "..");
const MEDIA_DIR = path.join(REPO_ROOT, "docs", "media");
const OUT_GIF =
  process.env.MOOD_SHELL_OUT || path.join(MEDIA_DIR, "mood-shell.gif");
const BASE_URL = process.env.MOOD_SHELL_BASE_URL || "http://127.0.0.1:5173";
const MOODS = ["bored", "anxious", "pleasant"];
const VIEWPORT = { width: 720, height: 540 };
const HOLD_MS = 1200;
const FADE_STEPS = 2;
const MAX_WIDTH = 520;
const COLORS = 64;

async function waitForServer(url, timeoutMs = 90_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url, { signal: AbortSignal.timeout(2000) });
      if (res.ok || res.status === 404) return true;
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  return false;
}

async function ensureDevServer() {
  if (await waitForServer(BASE_URL, 3_000)) {
    return null;
  }
  const isWin = process.platform === "win32";
  const child = spawn(
    isWin ? "npm.cmd run dev -- --host 127.0.0.1 --port 5173" : "npm",
    isWin ? [] : ["run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
    {
      cwd: WEB_ROOT,
      stdio: "ignore",
      shell: isWin,
      env: { ...process.env },
    },
  );
  const ok = await waitForServer(BASE_URL, 120_000);
  if (!ok) {
    try {
      child.kill();
    } catch {
      /* ignore */
    }
    throw new Error(`Vite did not become ready at ${BASE_URL}`);
  }
  return child;
}

function runPython(args) {
  return new Promise((resolve, reject) => {
    const py = spawn("python", args, { stdio: "inherit", cwd: REPO_ROOT });
    py.on("error", reject);
    py.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`python exited ${code}`));
    });
  });
}

async function captureFrames(browser) {
  const page = await browser.newPage({
    viewport: VIEWPORT,
    deviceScaleFactor: 1,
  });
  const frames = [];
  for (const mood of MOODS) {
    await page.goto(`${BASE_URL}/?mood=${mood}`, {
      waitUntil: "networkidle",
    });
    const shell = page.getByTestId("mood-shell");
    await shell.waitFor({ state: "visible" });
    await page.getByTestId("affect-enabled-flag").waitFor({ state: "visible" });
    // Settle CSS transitions
    await page.waitForTimeout(450);
    const buf = await shell.screenshot({ type: "png", animations: "disabled" });
    frames.push({ mood, buf });
  }
  await page.close();
  return frames;
}

async function main() {
  await mkdir(MEDIA_DIR, { recursive: true });
  const server = await ensureDevServer();
  const browser = await chromium.launch({ headless: true });
  let framePaths = [];
  try {
    const frames = await captureFrames(browser);
    framePaths = [];
    for (const { mood, buf } of frames) {
      const p = path.join(MEDIA_DIR, `_mood-${mood}.png`);
      await writeFile(p, buf);
      framePaths.push(p);
      console.log(`captured ${mood} → ${p} (${buf.length} bytes)`);
    }

    const assemblePy = path.join(REPO_ROOT, "scripts", "assemble_mood_shell_gif.py");
    await runPython([
      assemblePy,
      "--out",
      OUT_GIF,
      "--hold-ms",
      String(HOLD_MS),
      "--fade-steps",
      String(FADE_STEPS),
      "--max-width",
      String(MAX_WIDTH),
      "--colors",
      String(COLORS),
      ...framePaths,
    ]);
  } finally {
    await browser.close();
    for (const p of framePaths) {
      if (existsSync(p)) await unlink(p).catch(() => {});
    }
    if (server && !server.killed) {
      try {
        server.kill("SIGTERM");
      } catch {
        /* ignore */
      }
    }
  }
  console.log(`wrote ${OUT_GIF}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

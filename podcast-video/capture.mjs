import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const DIR = path.dirname(new URL(import.meta.url).pathname);
const FRAMES = path.join(DIR, 'frames');
fs.rmSync(FRAMES, { recursive: true, force: true });
fs.mkdirSync(FRAMES, { recursive: true });

const PORT = 9223;
const chrome = spawn('google-chrome', [
  '--headless=new', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
  `--remote-debugging-port=${PORT}`, `--user-data-dir=/tmp/cdp-profile-${Date.now()}`,
  '--window-size=1920,1080', '--hide-scrollbars', '--force-device-scale-factor=1',
  '--remote-allow-origins=*', 'about:blank'
], { stdio: 'ignore' });

const sleep = ms => new Promise(r => setTimeout(r, ms));
async function waitPort() {
  for (let i = 0; i < 60; i++) {
    try { const r = await fetch(`http://127.0.0.1:${PORT}/json/version`); if (r.ok) return; } catch {}
    await sleep(500);
  }
  throw new Error('chrome did not start');
}
await waitPort();
const targets = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const page = targets.find(t => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
let id = 0;
const pending = new Map();
const events = [];
ws.onmessage = e => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  else if (m.method) events.push(m);
};
const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const waitEvent = method => new Promise(res => {
  const chk = () => { const i = events.findIndex(e => e.method === method); if (i >= 0) res(events.splice(i, 1)[0]); else setTimeout(chk, 50); };
  chk();
});

await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });
const loaded = waitEvent('Page.loadEventFired');
await send('Page.navigate', { url: 'file://' + path.join(DIR, 'scene.html') });
await loaded;
await sleep(800);

const FPS = 30, N = FPS * 5;
for (let i = 0; i < N; i++) {
  const t = i / FPS;
  await send('Runtime.evaluate', { expression: `render(${t.toFixed(4)})` });
  const shot = await send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(path.join(FRAMES, `f_${String(i).padStart(4, '0')}.png`), Buffer.from(shot.result.data, 'base64'));
  if (i % 15 === 0) console.log(`frame ${i}/${N}`);
}
console.log('capture done');
ws.close();
chrome.kill('SIGKILL');
process.exit(0);

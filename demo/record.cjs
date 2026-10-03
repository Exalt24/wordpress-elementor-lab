// Records the README hero clip: the real Elementor editor holding the page, the published page scrolling, then the audit's before and after output
// (both are the real files in docs/). Usage: node demo/record.cjs <out_dir>
const fs = require('fs');
const path = require('path');
const { chromium } = require('C:/Users/' + process.env.USERNAME + '/AppData/Roaming/npm/node_modules/playwright');
const BASE = 'http://localhost:8087';
const out = process.argv[2];
const before = fs.readFileSync(path.join(__dirname, '..', 'docs', 'seo_before.txt'), 'utf8').split(/\r?\n/).filter((l) => l.trim());
const after = fs.readFileSync(path.join(__dirname, '..', 'docs', 'seo_after.txt'), 'utf8').split(/\r?\n/).filter((l) => l.trim());

const termHtml = (title) => `<!doctype html><meta charset="utf-8"><style>
html,body{margin:0;background:#0d1117;color:#c9d1d9;font:14px/1.5 Consolas,'Cascadia Mono',monospace}
header{padding:12px 20px;background:#161b22;border-bottom:1px solid #30363d;color:#e6edf3;font-size:14px}
#t{padding:14px 20px;white-space:pre-wrap}.ok{color:#3fb950}.bad{color:#f85149}.dim{color:#8b949e}</style>
<header>${title}</header><div id="t"></div>`;

async function play(p, lines, ms) {
  for (const l of lines) {
    await p.evaluate((l) => {
      const d = document.createElement('div');
      const m = l.match(/^(PASS|FAIL)\s+(.*)$/);
      const esc = (s) => s.replace(/</g, '&lt;');
      d.innerHTML = m ? `<span class="${m[1] === 'PASS' ? 'ok' : 'bad'}">${m[1]}</span>  ${esc(m[2])}` : `<span class="dim">${esc(l)}</span>`;
      document.getElementById('t').appendChild(d);
    }, l);
    await p.waitForTimeout(ms);
  }
}

(async () => {
  const b = await chromium.launch({ headless: true });
  const ctx = await b.newContext({ viewport: { width: 1280, height: 800 }, recordVideo: { dir: out, size: { width: 1280, height: 800 } } });
  const p = await ctx.newPage();
  await p.goto(BASE + '/wp-login.php');
  await p.fill('#user_login', 'admin');
  await p.fill('#user_pass', 'admin-local-only');
  await p.click('#wp-submit');
  await p.waitForURL(/wp-admin/);
  await p.goto(`${BASE}/wp-admin/post.php?post=5&action=elementor`, { waitUntil: 'domcontentloaded' });
  await p.waitForFunction(() => window.elementor && elementor.documents && elementor.documents.getCurrent(), null, { timeout: 90000 });
  await p.waitForTimeout(3500);
  // Elementor shows a promo dialog on a fresh install; close it so the editor is what the clip shows.
  for (const sel of ['[aria-label="Close"]', 'button[aria-label="Close"]', '.e-promotion-close', '[data-testid="close-button"]']) {
    const el = p.locator(sel).first();
    if (await el.isVisible().catch(() => false)) { await el.click().catch(() => {}); break; }
  }
  await p.keyboard.press('Escape');
  await p.waitForTimeout(2500);
  await p.goto(BASE + '/seller-audit/', { waitUntil: 'networkidle' });
  await p.addStyleTag({ content: '#wpadminbar{display:none!important}html{margin-top:0!important}' });
  await p.waitForTimeout(1200);
  for (let i = 0; i < 9; i++) { await p.mouse.wheel(0, 170); await p.waitForTimeout(450); }
  await p.waitForTimeout(800);
  await p.setContent(termHtml('python scripts/seo_audit.py http://localhost:8087/seller-audit/    (first run, straight after the build)'));
  await play(p, before, 170);
  await p.waitForTimeout(1300);
  await p.setContent(termHtml('after adding the three missing pieces (meta description, Open Graph, JSON-LD) and running it again'));
  await play(p, after, 170);
  await p.waitForTimeout(2200);
  await ctx.close();
  await b.close();
})();

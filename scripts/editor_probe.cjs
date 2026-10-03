// Opens the Elementor editor on the landing page in a real browser and dumps what the editor shows, so the build steps are written from the real UI.
// Usage: node scripts/editor_probe.cjs <out_dir> <page_id>
const { chromium } = require('C:/Users/' + process.env.USERNAME + '/AppData/Roaming/npm/node_modules/playwright');
const BASE = 'http://localhost:8087';
const [out, id] = [process.argv[2], process.argv[3]];
(async () => {
  const b = await chromium.launch({ headless: true });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await ctx.newPage();
  await p.goto(BASE + '/wp-login.php');
  await p.fill('#user_login', 'admin');
  await p.fill('#user_pass', 'admin-local-only');
  await p.click('#wp-submit');
  await p.waitForURL(/wp-admin/);
  await p.goto(`${BASE}/wp-admin/post.php?post=${id}&action=elementor`, { waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(15000);
  console.log('title:', await p.title());
  await p.screenshot({ path: out + '/editor_first.png' });
  const panel = await p.evaluate(() => {
    const els = [...document.querySelectorAll('#elementor-panel *')].filter((e) => e.children.length === 0 && (e.innerText || '').trim()).map((e) => (e.innerText || '').trim());
    return [...new Set(els)].slice(0, 80);
  });
  console.log('panel text:', JSON.stringify(panel));
  console.log('has elementor global:', await p.evaluate(() => typeof window.elementor + ' ' + (window.elementor && window.elementor.config ? window.elementor.config.version : '')));
  await b.close();
})();

// LIFESPAN: permanent
// Opens a generated draft in the real Elementor editor (headless Chromium, logged in as the lab admin) and reads the elements back from the editor.
// It fails when the editor reports an error, a widget type is unknown to the editor, or anything that was sent is missing, changed or reordered.
//   node scripts/verify_in_editor.cjs <post_id> <tree.json> [--shot out.png] [--base http://localhost:8087]
// Exit 0: the editor holds exactly what was sent. Exit 1: a mismatch (listed). Exit 2: the editor did not open or raised an error.
// The last line of stdout is one JSON object: {ok, elements, editorErrors, mismatches}.
const fs = require('fs');
const { execSync } = require('child_process');

function loadPlaywright() {
  try { return require('playwright'); } catch (e) { /* fall through to the global npm root */ }
  const root = execSync('npm root -g', { encoding: 'utf8' }).trim();
  return require(root + '/playwright');
}

const args = process.argv.slice(2);
const opt = (name, fallback) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : fallback; };
const [postId, treePath] = args;
const BASE = opt('--base', process.env.LAB_BASE || 'http://localhost:8087');
const USER = process.env.LAB_USER || 'admin';
const PASS = process.env.LAB_PASS || 'admin-local-only';
if (!postId || !treePath) { console.error('usage: verify_in_editor.cjs <post_id> <tree.json>'); process.exit(2); }
const sent = JSON.parse(fs.readFileSync(treePath, 'utf8'));

const { compareTree, countElements } = require('./editor_compare.cjs');

(async () => {
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const editorErrors = [];
  // WordPress's own session check (wp-auth-check.js) throws "reading 'hasClass'" on every admin page in headless Chromium, with or without
  // Elementor data (measured on a page built in the editor itself). Only an error whose stack is in that script is ignored.
  page.on('pageerror', (e) => { if (!/wp-auth-check/.test(String(e.stack || ''))) editorErrors.push('page error: ' + String(e.message || e).slice(0, 200)); });
  page.on('console', (m) => { if (m.type() === 'error' && !/favicon|Failed to load resource/.test(m.text())) editorErrors.push('console: ' + m.text().slice(0, 200)); });
  const finish = async (code, extra) => {
    const result = Object.assign({ ok: code === 0, editorErrors, mismatches: [], elements: 0 }, extra);
    console.log(JSON.stringify(result));
    await browser.close();
    process.exit(code);
  };
  try {
    await page.goto(BASE + '/wp-login.php');
    await page.fill('#user_login', USER);
    await page.fill('#user_pass', PASS);
    await page.click('#wp-submit');
    await page.waitForURL(/wp-admin/);
    await page.goto(`${BASE}/wp-admin/post.php?post=${postId}&action=elementor`, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => window.elementor && window.$e && elementor.documents && elementor.documents.getCurrent() && elementor.elements, null, { timeout: 90000 });
    // The editor builds its element models asynchronously: wait until the count stops moving.
    let last = -1, stable = 0;
    for (let i = 0; i < 100 && stable < 4; i++) {
      const n = await page.evaluate(() => { let c = 0; const walk = (col) => col.each((m) => { c++; const k = m.get('elements'); if (k) walk(k); }); walk(elementor.elements); return c; });
      stable = n === last ? stable + 1 : 0;
      last = n;
      await page.waitForTimeout(300);
    }
    const read = await page.evaluate(() => {
      const missing = [];
      const walkWidgets = (col) => col.each((m) => {
        const wt = m.get('widgetType');
        if (wt && !elementor.widgetsCache[wt]) missing.push(wt);
        const k = m.get('elements');
        if (k) walkWidgets(k);
      });
      walkWidgets(elementor.elements);
      return { tree: elementor.elements.toJSON({ remove: ['default'] }), unknownWidgets: missing };
    });
    if (opt('--shot')) await page.screenshot({ path: opt('--shot') });
    const mismatches = [];
    read.unknownWidgets.forEach((w) => mismatches.push('the editor has no widget named ' + w));
    compareTree(sent, read.tree, '', mismatches);
    if (editorErrors.length) return finish(2, { mismatches, elements: countElements(read.tree) });
    return finish(mismatches.length ? 1 : 0, { mismatches, elements: countElements(read.tree) });
  } catch (e) {
    editorErrors.push('editor did not open: ' + String(e.message || e).split('\n')[0].slice(0, 200));
    return finish(2, {});
  }
})();

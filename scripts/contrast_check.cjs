// Contrast, tap target, type and overflow check for a live page, from the colours the browser really computed.
//   node scripts/contrast_check.cjs <url> [<url> ...]        prints a report; exit code 1 when a text colour is under its WCAG AA ratio
// For each visible text element it takes the computed text colour and the first non transparent background found going up the tree
// (alpha is blended over what is behind it), then the WCAG 2 contrast ratio. AA needs 4.5 for normal text and 3 for large text
// (24 px and up, or 18.66 px and up when bold). A text sitting on an image or gradient is listed as "unknown background" and not scored.
// Tap targets are measured at 390 px wide: links, buttons and summaries under 44 px in height are listed. A link that sits inside
// a sentence or list item is reported apart, because WCAG 2.5.8 exempts links inside running text.
const { execSync } = require('child_process');
function pw() {
  try { return require('playwright'); } catch (e) { /* not a local dependency */ }
  return require(require('path').join(execSync('npm root -g', { encoding: 'utf8' }).trim(), 'playwright'));
}
const { chromium } = pw();

const page_fn = () => {
  const SKIP = '#wpadminbar, #marketingbar, .wpcom-masterbar, iframe';   // the free plan banner and WordPress.com's own bars are not part of the page
  const parse = (s) => { const m = s.match(/rgba?\(([^)]+)\)/); if (!m) return null; const [r, g, b, a] = m[1].split(',').map((x) => parseFloat(x)); return { r, g, b, a: a === undefined ? 1 : a }; };
  const over = (top, bottom) => ({ r: top.r * top.a + bottom.r * (1 - top.a), g: top.g * top.a + bottom.g * (1 - top.a), b: top.b * top.a + bottom.b * (1 - top.a), a: 1 });
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const bgOf = (el) => { // blend translucent layers down to the first opaque one
    const layers = []; let e = el, unknown = false;
    while (e) { const cs = getComputedStyle(e); if (cs.backgroundImage !== 'none') { unknown = true; break; } const c = parse(cs.backgroundColor); if (c && c.a > 0) { layers.push(c); if (c.a === 1) break; } e = e.parentElement; }
    if (unknown) return null;
    let base = { r: 255, g: 255, b: 255, a: 1 }; for (let i = layers.length - 1; i >= 0; i--) base = over(layers[i], base); return base;
  };
  const hex = (c) => '#' + [c.r, c.g, c.b].map((v) => Math.round(v).toString(16).padStart(2, '0')).join('');
  const text = [], seen = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const n = walker.currentNode, t = n.textContent.trim(); if (!t) continue;
    const el = n.parentElement; if (!el || ['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(el.tagName)) continue;
    const cs = getComputedStyle(el), r = el.getBoundingClientRect();
    if (cs.visibility === 'hidden' || cs.display === 'none' || r.width === 0 || r.height === 0) continue;
    if (el.closest(SKIP)) continue;
    const key = el.tagName + t.slice(0, 20) + cs.color; if (seen.has(key)) continue; seen.add(key);
    const fg0 = parse(cs.color), bg = bgOf(el); const op = parseFloat(cs.opacity);
    if (!fg0 || !bg) { text.push({ tag: el.tagName, t: t.slice(0, 40), unknown: true }); continue; }
    const fg = over({ ...fg0, a: fg0.a * (isNaN(op) ? 1 : op) }, bg);
    const size = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight, 10) >= 700, large = size >= 24 || (bold && size >= 18.66);
    const ra = ratio(fg, bg);
    text.push({ tag: el.tagName, t: t.slice(0, 40), fg: hex(fg), bg: hex(bg), size: +size.toFixed(1), bold, ratio: +ra.toFixed(2), need: large ? 3 : 4.5, pass: ra >= (large ? 3 : 4.5) });
  }
  const taps = [];
  for (const el of document.querySelectorAll('a[href], button, summary, [role="button"]')) {
    const r = el.getBoundingClientRect(), cs = getComputedStyle(el); if (r.width === 0 || r.height === 0 || cs.visibility === 'hidden') continue;
    if (el.closest(SKIP)) continue;
    const inline = !!el.closest('p, li') && !el.closest('.wp-block-button, .wp-block-navigation, summary') && cs.display === 'inline';
    taps.push({ t: (el.textContent || el.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 34), w: Math.round(r.width), h: Math.round(r.height), inline });
  }
  const bs = getComputedStyle(document.body), pEl = document.querySelector('main p, p'), ps = pEl ? getComputedStyle(pEl) : bs;
  return { text, taps, overflow: [document.documentElement.scrollWidth, document.documentElement.clientWidth], p: { size: ps.fontSize, lh: ps.lineHeight, weight: ps.fontWeight, family: ps.fontFamily.split(',')[0] } };
};

(async () => {
  const urls = process.argv.slice(2); if (!urls.length) { console.error('usage: node contrast_check.cjs <url> ...'); process.exit(2); }
  // CDP_PORT=9333 attaches to a browser that is already running (one automation browser at a time) and uses a fresh signed-out context
  const b = process.env.CDP_PORT ? await chromium.connectOverCDP('http://127.0.0.1:' + process.env.CDP_PORT) : await chromium.launch({ headless: true }); let bad = 0;
  for (const url of urls) for (const w of [1280, 390]) {
    const ctx = await b.newContext({ viewport: { width: w, height: 844 } }), p = await ctx.newPage();
    await p.goto(url, { waitUntil: 'networkidle', timeout: 45000 });
    const r = await p.evaluate(page_fn);
    const fails = r.text.filter((x) => !x.unknown && !x.pass), unk = r.text.filter((x) => x.unknown);
    const scored = r.text.filter((x) => !x.unknown), min = scored.reduce((m, x) => (x.ratio < m.ratio ? x : m), scored[0]);
    const small = r.taps.filter((x) => x.h < 44 && !x.inline), inl = r.taps.filter((x) => x.h < 44 && x.inline);
    console.log(`\n== ${url}  ${w}px`);
    console.log(`overflow: scrollWidth ${r.overflow[0]} / clientWidth ${r.overflow[1]} ${r.overflow[0] > r.overflow[1] ? 'HORIZONTAL SCROLL' : 'ok'}`);
    console.log(`paragraph: ${r.p.size} / line height ${r.p.lh} / weight ${r.p.weight} / ${r.p.family}`);
    console.log(`text colours scored: ${scored.length}, failing AA: ${fails.length}, lowest ratio: ${min ? min.ratio + ' (' + min.fg + ' on ' + min.bg + ', "' + min.t + '")' : 'n/a'}, unknown background: ${unk.length}`);
    for (const f of fails) console.log(`  FAIL ${f.ratio} < ${f.need}  ${f.fg} on ${f.bg}  ${f.size}px  <${f.tag}> ${f.t}`);
    console.log(`tap targets: ${r.taps.length} measured, under 44 px high (not in running text): ${small.length}, inside running text: ${inl.length}`);
    for (const s of small) console.log(`  SMALL ${s.w}x${s.h}  ${s.t}`);
    if (process.env.LIST_ALL) for (const x of scored) console.log(`  ${x.ratio}  ${x.fg} on ${x.bg}  ${x.size}px${x.bold ? ' bold' : ''}  ${x.t}`);
    bad += fails.length; await ctx.close();
  }
  if (!process.env.CDP_PORT) await b.close(); else await b.close().catch(() => {}); process.exit(bad ? 1 : 0);
})();

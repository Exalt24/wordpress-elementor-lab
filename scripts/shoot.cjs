// Screenshots the published page at desktop and phone width. Usage: node scripts/shoot.cjs <out_dir> <url>
const { chromium } = require('C:/Users/' + process.env.USERNAME + '/AppData/Roaming/npm/node_modules/playwright');
const [out, url] = [process.argv[2], process.argv[3]];
(async () => {
  const b = await chromium.launch({ headless: true });
  for (const [name, w, h] of [['desktop', 1280, 900], ['phone', 390, 844]]) {
    const ctx = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: name === 'phone' ? 2 : 1 });
    const p = await ctx.newPage();
    await p.goto(url, { waitUntil: 'networkidle' });
    await p.waitForTimeout(1500);
    const over = await p.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    console.log(name, 'horizontal overflow:', over);
    await p.screenshot({ path: `${out}/live_${name}.png`, fullPage: true });
    await ctx.close();
  }
  await b.close();
})();

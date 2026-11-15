// Loads the page built from the PSD mock-up at a desktop and a phone width and measures its layout.
//   node scripts/check_mockup.cjs <base url> <out dir>
// Wide: the picture sits beside the text. Phone: the picture sits under the text. The three colours the converter read from the PSD must be the
// computed colours on the page, and nothing may spill past the screen width. Prints PASS or FAIL per check and exits 1 on any FAIL.
const PW = require("C:/Projects/Professional/Operations/tools/playwright_path.cjs").playwrightPath() || "playwright";
const { chromium } = require(PW);
const fs = require("fs");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const [base, outDir] = process.argv.slice(2);
let bad = 0;
const check = (name, ok, detail) => { console.log((ok ? "PASS " : "FAIL ") + name + (!ok && detail ? " | " + detail : "")); if (!ok) bad++; };

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  for (const [label, width, height] of [["wide", 1280, 720], ["phone", 390, 800]]) {
    const page = await browser.newPage({ viewport: { width, height } });
    await page.goto(base + "/mockup/", { waitUntil: "domcontentloaded" });
    let n = 0;
    for (let i = 0; i < 24 && n === 0; i++) { await sleep(250); n = await page.locator(".mock-photo").count(); }   // polls every 250 ms, 6 s at most, then measures what is there
    const m = await page.evaluate(() => {
      const box = (s) => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom }; };
      const css = (s, p) => { const e = document.querySelector(s); return e ? getComputedStyle(e)[p] : null; };
      return {
        text: box(".mock-text"), photo: box(".mock-photo"), h1: document.querySelector(".mock-text h1")?.innerText,
        band: css(".mock-band", "backgroundColor"), cta: css(".mock-text a", "backgroundColor"), photoBg: css(".mock-photo", "backgroundColor"),
        scrollW: document.documentElement.scrollWidth, innerW: window.innerWidth,
      };
    });
    check(`${label}: the page has the converted section`, !!m.text && !!m.photo, JSON.stringify(m));
    if (m.text && m.photo) {
      if (label === "wide") check("wide: the picture sits beside the text", m.photo.l >= m.text.r - 1 && Math.abs(m.photo.t - m.text.t) < 400, JSON.stringify(m));
      else check("phone: the picture sits under the text", m.photo.t >= m.text.b - 1, JSON.stringify(m));
    }
    check(`${label}: nothing spills past the screen width`, m.scrollW <= m.innerW + 1, `${m.scrollW} > ${m.innerW}`);
    if (label === "wide") {
      check("the band colour is the PSD band colour (102a43)", m.band === "rgb(16, 42, 67)", m.band);
      check("the button colour is the PSD button colour (e85d04)", m.cta === "rgb(232, 93, 4)", m.cta);
      check("the picture colour is the PSD picture colour (7b9ea8)", m.photoBg === "rgb(123, 158, 168)", m.photoBg);
      check("the headline is the PSD layer text", m.h1 === "Fewer no-shows, fewer empty chairs", m.h1);
    }
    await page.screenshot({ path: `${outDir}/mockup-${label}.png`, fullPage: true });
    await page.close();
  }
  await browser.close();
  process.exit(bad ? 1 : 0);
})().catch((e) => { console.error("ERR " + e.message.split("\n")[0]); process.exit(1); });

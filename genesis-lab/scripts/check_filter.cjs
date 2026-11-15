// Drives the industry filter on the live DEV front page in a real browser.
//   node scripts/check_filter.cjs <base url> <out dir> '<oracle json: {"total": n, "terms": [{"slug","name","count"}]}>'
// The oracle comes from WordPress's REST API (term counts kept by core), so the expected card counts are not read from the page under test.
// Proves: the grid changes with no navigation (a marker set on window survives, no frame navigates), one admin-ajax request per click, a loading
// state and an error state, keyboard operation, a bad or missing nonce answers 403, an unknown or hostile industry answers an empty list and
// harms nothing, All restores the full grid, a phone width does not overflow, and with JavaScript off the full grid is still there.
// Prints PASS or FAIL per check and exits 1 on any FAIL.
const PW = require("C:/Projects/Professional/Operations/tools/playwright_path.cjs").playwrightPath() || "playwright";
const { chromium } = require(PW);
const fs = require("fs");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const [base, outDir, oracleJson] = process.argv.slice(2);
const oracle = JSON.parse(oracleJson);
const shotsOnly = process.argv[5] === "--shots-only";   // after the checks, with the temporary case studies gone: the two screenshots kept in docs/
const LIMIT = 6;
const expectFor = (n) => Math.min(n, LIMIT);
let bad = 0;
const check = (name, ok, detail) => { console.log((ok ? "PASS " : "FAIL ") + name + (!ok && detail ? " | " + detail : "")); if (!ok) bad++; };
async function until(fn, ms = 6000) { const end = Date.now() + ms; while (Date.now() < end) { if (await fn()) return true; await sleep(200); } return false; }

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  if (shotsOnly) {
    const pick = oracle.terms[oracle.terms.length - 1].name;
    for (const [label, width, height, touch] of [["wide", 1280, 720, false], ["phone", 390, 760, true]]) {
      const c = await browser.newContext({ viewport: { width, height }, hasTouch: touch, isMobile: touch });
      const p = await c.newPage();
      await p.goto(base + "/", { waitUntil: "load" });
      await p.getByRole("button", { name: pick, exact: true }).click();
      await until(async () => (await p.locator(".case-filter button[aria-pressed=true]").innerText()) === pick && (await p.locator("#lab-case-grid").getAttribute("aria-busy")) === "false");
      await p.mouse.move(width - 5, height - 5);   // keep the hover colour off the pressed button
      await p.screenshot({ path: `${outDir}/filter-${label}.png` });
      await c.close();
    }
    await browser.close();
    return;
  }
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  const ajax = [];
  let navigations = 0;
  page.on("request", (r) => { if (r.url().includes("admin-ajax.php")) ajax.push(r.postData() || ""); });
  await page.goto(base + "/", { waitUntil: "load" });
  page.on("framenavigated", () => { navigations++; });
  const cards = () => page.locator("#lab-case-grid .case-card").count();
  const titles = () => page.locator("#lab-case-grid .case-card h2").allInnerTexts();
  const pressed = async () => (await page.locator(".case-filter button[aria-pressed=true]").allInnerTexts()).join("|");
  const status = () => page.locator(".case-status").innerText();
  async function pick(label) {   // click by visible name, return the requests it caused
    const before = ajax.length;
    await page.getByRole("button", { name: label, exact: true }).click();
    await until(async () => (await pressed()) === label && (await page.locator("#lab-case-grid").getAttribute("aria-busy")) === "false");
    return ajax.length - before;
  }

  check("the filter bar is shown once the script has run", await until(async () => await page.locator(".case-filter").isVisible()));
  check(`the first load renders ${expectFor(oracle.total)} cards (the lab holds ${oracle.total}, a grid shows at most ${LIMIT})`, (await cards()) === expectFor(oracle.total), String(await cards()));
  const names = await page.locator(".case-filter button").allInnerTexts();
  check("the bar has All and one button per industry that has case studies", JSON.stringify(names) === JSON.stringify(["All", ...oracle.terms.map((t) => t.name)]), JSON.stringify(names));
  const kinds = await page.locator(".case-filter button").evaluateAll((bs) => bs.map((b) => [b.tagName, b.type, b.getAttribute("aria-pressed")]));
  check("every filter control is a real button of type button with aria-pressed", kinds.every((k) => k[0] === "BUTTON" && k[1] === "button" && (k[2] === "true" || k[2] === "false")), JSON.stringify(kinds));
  check("All is the pressed one on first load", (await pressed()) === "All", await pressed());
  const looks = await page.locator(".case-filter button").evaluateAll((bs) => bs.map((b) => [b.getAttribute("aria-pressed"), getComputedStyle(b).backgroundColor]));
  check("the pressed button looks different from the others (its own background colour)", looks.filter((l) => l[0] === "true").length === 1 && looks.filter((l) => l[0] === "true").every((l) => looks.filter((o) => o[0] === "false").every((o) => o[1] !== l[1])), JSON.stringify(looks));
  const hasJq = await page.evaluate(() => typeof window.jQuery === "function" && typeof window.jQuery.ajax === "function");
  const scriptSrcs = await page.locator("script[src]").evaluateAll((s) => s.map((e) => e.src));
  check("jQuery is WordPress's bundled copy from the site itself, loaded before the filter script", hasJq && scriptSrcs.some((s) => s.includes("jquery") && s.startsWith(base)) && !scriptSrcs.some((s) => !s.startsWith(base)), JSON.stringify(scriptSrcs));
  const firstTitles = await titles();
  await page.evaluate(() => { window.__labMarker = "survives-only-without-reload"; });
  const startUrl = page.url();

  // the loading state: hold the first answer for a moment and read the page while it is in flight
  await page.route("**/admin-ajax.php", async (route) => { await sleep(700); await route.continue(); });
  const slow = oracle.terms[0];
  const clickPromise = page.getByRole("button", { name: slow.name, exact: true }).click();
  await clickPromise;
  const busy = await until(async () => (await page.locator("#lab-case-grid").getAttribute("aria-busy")) === "true", 1500);
  const busyText = await status();
  check("while the request is in flight the grid is marked busy and the status says loading", busy && /Loading/.test(busyText), busyText);
  await until(async () => (await pressed()) === slow.name);
  await page.unroute("**/admin-ajax.php");
  check("the busy state clears when the answer arrives", (await page.locator("#lab-case-grid").getAttribute("aria-busy")) === "false");

  // every industry, one click each
  for (const t of oracle.terms) {
    if (t.slug === slow.slug) {
      check(`${t.name}: ${expectFor(t.count)} cards after the click`, (await cards()) === expectFor(t.count), String(await cards()));
      continue;
    }
    const n = await pick(t.name);
    check(`${t.name}: exactly one admin-ajax request for the click`, n === 1, String(n));
    check(`${t.name}: ${expectFor(t.count)} cards, the REST term count`, (await cards()) === expectFor(t.count), String(await cards()));
    const metas = await page.locator("#lab-case-grid .case-meta").allInnerTexts();
    check(`${t.name}: every card shown belongs to that industry`, metas.length === (await cards()) && metas.every((m) => m.includes(t.name)), JSON.stringify(metas));
  }
  check("the request carried the nonce, the action and the industry as a form post", ajax.every((p) => /action=lab_core_filter_cases/.test(p) && /nonce=[0-9a-f]{10}/.test(p) && /industry=/.test(p)), ajax[0]);
  check("the document never reloaded: the window marker survived every click", (await page.evaluate(() => window.__labMarker)) === "survives-only-without-reload");
  check("no frame navigated and the address did not change", navigations === 0 && page.url() === startUrl, `${navigations} ${page.url()}`);

  // keyboard: focus a button and press Enter, then Space
  const before = ajax.length;
  await page.getByRole("button", { name: "All", exact: true }).focus();
  await page.keyboard.press("Enter");
  await until(async () => (await pressed()) === "All");
  check("Enter on a focused button restores the full grid with one request", ajax.length - before === 1 && (await cards()) === expectFor(oracle.total), `${ajax.length - before} ${await cards()}`);
  check("the full grid is the same set of cards as on first load", JSON.stringify(await titles()) === JSON.stringify(firstTitles));
  const last = oracle.terms[oracle.terms.length - 1];
  await page.getByRole("button", { name: last.name, exact: true }).focus();
  await page.keyboard.press("Space");
  await until(async () => (await pressed()) === last.name);
  check("Space on a focused button filters by that industry", (await cards()) === expectFor(last.count), String(await cards()));

  // pressing the button that is already pressed asks for nothing
  const again = await (async () => { const b = ajax.length; await page.getByRole("button", { name: last.name, exact: true }).click(); await sleep(400); return ajax.length - b; })();
  check("clicking the pressed button makes no request", again === 0, String(again));

  // the error state: the server answers 500, the old grid stays and a message says so
  const gridBefore = JSON.stringify(await titles());
  const pressedBefore = await pressed();
  await page.route("**/admin-ajax.php", (route) => route.fulfill({ status: 500, contentType: "text/plain", body: "boom" }));
  await page.getByRole("button", { name: "All", exact: true }).click();
  const errShown = await until(async () => /could not be loaded/.test(await status()));
  check("a failed request shows an error message", errShown, await status());
  check("the error message is styled as an error and the busy state is cleared", (await page.locator(".case-status.is-error").count()) === 1 && (await page.locator("#lab-case-grid").getAttribute("aria-busy")) === "false");
  check("a failed request leaves the grid and the pressed button as they were", JSON.stringify(await titles()) === gridBefore && (await pressed()) === pressedBefore);
  await page.unroute("**/admin-ajax.php");
  await page.getByRole("button", { name: "All", exact: true }).click();
  await until(async () => (await pressed()) === "All");
  check("the next click works again and clears the error", (await page.locator(".case-status.is-error").count()) === 0 && (await cards()) === expectFor(oracle.total));

  // the endpoint on its own: bad nonce, missing nonce, unknown and hostile input
  const cfg = await page.evaluate(() => ({ url: window.labCoreFilter.ajaxUrl, nonce: window.labCoreFilter.nonce, action: window.labCoreFilter.action }));
  const post = async (form) => { const r = await ctx.request.post(cfg.url, { form }); const text = await r.text(); let json = null; try { json = JSON.parse(text); } catch (e) { /* not JSON */ } return { status: r.status(), type: r.headers()["content-type"] || "", text, json }; };
  let r = await post({ action: cfg.action, nonce: "0000000000", industry: "" });
  check("a wrong nonce answers 403 with a JSON error", r.status === 403 && r.json && r.json.success === false && typeof r.json.data.message === "string" && /json/.test(r.type), `${r.status} ${r.text.slice(0, 80)}`);
  check("a wrong nonce returns no case study", !r.text.includes("case-card"));
  r = await post({ action: cfg.action, industry: "" });
  check("a missing nonce answers 403 with a JSON error", r.status === 403 && r.json && r.json.success === false, `${r.status} ${r.text.slice(0, 80)}`);
  r = await post({ action: cfg.action, nonce: "", industry: oracle.terms[0].slug });
  check("an empty nonce answers 403", r.status === 403, String(r.status));
  r = await post({ action: cfg.action, nonce: cfg.nonce, industry: oracle.terms[0].slug });
  check("the right nonce and a real industry answers 200 with that industry's cards", r.status === 200 && r.json.success === true && r.json.data.count === expectFor(oracle.terms[0].count) && /json/.test(r.type), `${r.status} ${r.text.slice(0, 80)}`);
  r = await post({ action: cfg.action, nonce: cfg.nonce, industry: "no-such-industry" });
  check("an unknown industry answers 200 with an empty list, not an error", r.status === 200 && r.json.success === true && r.json.data.count === 0 && !r.json.data.html.includes("case-card"), `${r.status} ${r.text.slice(0, 120)}`);
  const hostile = ["<script>alert(1)</script>", "x' OR '1'='1' -- ", "1; DROP TABLE wp_posts; --", "' UNION SELECT user_pass FROM wp_users -- ", "%00../../etc/passwd", "\"><img src=x onerror=alert(2)>", "a".repeat(5000)];
  let allHarmless = true, detail = "";
  for (const h of hostile) {
    r = await post({ action: cfg.action, nonce: cfg.nonce, industry: h });
    const ok = r.status === 200 && r.json && r.json.success === true && r.json.data.count === 0 && /^[a-z0-9_%-]*$/.test(r.json.data.industry) && !/<script|<img|onerror|error in your SQL|Fatal error|Warning:|Notice:|Deprecated:|wpdb|Stack trace/i.test(r.text);
    if (!ok) { allHarmless = false; detail += `[${h.slice(0, 30)} -> ${r.status} ${r.text.slice(0, 100)}] `; }
  }
  check(`${hostile.length} hostile industry values (script tag, SQL strings, path, huge) each answer an empty list and echo nothing dangerous`, allHarmless, detail);
  r = await ctx.request.post(cfg.url, { data: `action=${cfg.action}&nonce=${cfg.nonce}&industry[]=a&industry[]=b`, headers: { "content-type": "application/x-www-form-urlencoded" } });
  const arr = await r.text();
  let arrJson = null; try { arrJson = JSON.parse(arr); } catch (e) { /* ignore */ }
  check("an industry sent as an array answers an empty list, not a PHP error", r.status() === 200 && arrJson && arrJson.data.count === 0, `${r.status()} ${arr.slice(0, 100)}`);
  const rest = await (await ctx.request.get(base + "/wp-json/wp/v2/case_study?per_page=1")).headers();
  check("after the hostile requests the database still holds every case study", Number(rest["x-wp-total"]) === oracle.total, rest["x-wp-total"]);
  const home = await ctx.request.get(base + "/");
  check("the front page still answers 200 with its full server-rendered grid", home.status() === 200 && ((await home.text()).match(/class="case-card"/g) || []).length === expectFor(oracle.total));

  // the filtered page at 1280, read afterwards as a screenshot
  await pick(oracle.terms[0].name);
  await page.screenshot({ path: `${outDir}/filter-wide.png`, fullPage: false });
  await ctx.close();

  // a phone: nothing spills sideways, the buttons are big enough to tap
  const phone = await browser.newContext({ viewport: { width: 390, height: 800 }, hasTouch: true, isMobile: true });
  const p2 = await phone.newPage();
  await p2.goto(base + "/", { waitUntil: "load" });
  await p2.locator(".case-filter").waitFor({ state: "visible", timeout: 6000 });
  const pickPhone = async (label) => { await p2.getByRole("button", { name: label, exact: true }).tap(); await until(async () => (await p2.locator(".case-filter button[aria-pressed=true]").innerText()) === label); };
  await pickPhone(oracle.terms[oracle.terms.length - 1].name);
  const geo = await p2.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth, minH: Math.min(...[...document.querySelectorAll(".case-filter button")].map((b) => b.getBoundingClientRect().height)), cards: document.querySelectorAll("#lab-case-grid .case-card").length }));
  check("phone: the filtered page does not spill past the screen width", geo.sw <= geo.iw + 1, JSON.stringify(geo));
  check("phone: the filter buttons are at least 40 pixels tall", geo.minH >= 40, JSON.stringify(geo));
  check(`phone: tapping an industry shows its ${expectFor(oracle.terms[oracle.terms.length - 1].count)} cards`, geo.cards === expectFor(oracle.terms[oracle.terms.length - 1].count), JSON.stringify(geo));
  await p2.screenshot({ path: `${outDir}/filter-phone.png`, fullPage: false });
  await phone.close();

  // JavaScript off: the full grid is on the page and the bar is not shown
  const nojs = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 1280, height: 900 } });
  const p3 = await nojs.newPage();
  await p3.goto(base + "/", { waitUntil: "load" });
  const n3 = await p3.locator("#lab-case-grid .case-card").count();
  check(`with JavaScript off the full grid still renders (${expectFor(oracle.total)} cards)`, n3 === expectFor(oracle.total), String(n3));
  check("with JavaScript off the filter bar is not shown, so there are no dead buttons", !(await p3.locator(".case-filter").isVisible()));
  await nojs.close();

  await browser.close();
  process.exit(bad ? 1 : 0);
})().catch((e) => { console.error("ERR " + e.message.split("\n")[0]); process.exit(1); });

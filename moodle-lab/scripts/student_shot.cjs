// Logs in to the lab Moodle as a student in a headless browser and saves a screenshot of one page, so a fix is checked the way the student sees it.
// Usage: LAB_USER=<username> LAB_PW=<password> node scripts/student_shot.cjs <path on the lab site> <out.png> [--wrong-pw]
// The password comes from the environment, never from the command line. --wrong-pw submits a wrong password instead (the locked out screen).
const path = require('path');
function loadPlaywright() {
  const tries = [process.env.PLAYWRIGHT_PATH, 'playwright',
    path.join(process.env.APPDATA || '', 'npm', 'node_modules', 'playwright'),
    'C:/Users/' + (process.env.USERNAME || '') + '/AppData/Roaming/npm/node_modules/playwright'].filter(Boolean);
  try { tries.push(path.join(require('child_process').execSync('npm root -g', { timeout: 15000 }).toString().trim(), 'playwright')); } catch (e) { /* no npm on the path */ }
  for (const t of tries) { try { return require(t); } catch (e) { /* try the next place */ } }
  throw new Error('playwright is not installed: npm install -g playwright');
}
const { chromium } = loadPlaywright();
const BASE = process.env.MOODLE_LAB_URL || 'http://localhost:8093';
const [pagePath, out] = [process.argv[2], process.argv[3]];
const wrong = process.argv.includes('--wrong-pw');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 } })).newPage();
  await page.goto(BASE + '/login/index.php', { waitUntil: 'networkidle' });
  // Moodle's login script wraps the password box when it starts and clears whatever was typed before that, so type, read the box back
  // and type again until the value is really there.
  const password = wrong ? 'not-the-password' : process.env.LAB_PW;
  for (let i = 0; i < 20; i++) {
    await page.fill('#username', process.env.LAB_USER);
    await page.fill('#password', password);
    if ((await page.inputValue('#password')) === password && (await page.inputValue('#username')) === process.env.LAB_USER) break;
    await page.waitForTimeout(250);
  }
  if ((await page.inputValue('#password')) !== password) throw new Error('the password box did not keep what was typed');
  await page.click('#loginbtn');
  // A normal login leaves the login page. A login that should be refused (a locked account, a wrong password) stays on it, so wait for the
  // red message to hold words instead.
  if (wrong || pagePath.includes('/login/')) {
    await page.waitForFunction(() => (document.querySelector('#loginerrormessage') || {}).textContent?.trim().length > 0, null, { timeout: 20000 }).catch(() => {});
  } else {
    // The first dashboard load after a fresh install builds Moodle's caches and can take a minute, so wait for the address, not the load event.
    await page.waitForURL((u) => !u.pathname.includes('/login/index.php'), { waitUntil: 'commit', timeout: 90000 }).catch(async () => {
      throw new Error('the login did not leave the login page at ' + page.url() + ': ' + (await page.innerText('body')).split(/\s+/).join(' ').slice(0, 200));
    });
  }
  if (!wrong && !pagePath.includes('/login/')) await page.goto(BASE + pagePath, { timeout: 90000 });   // a login page path means: stay on what the login attempt showed
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.screenshot({ path: out });
  console.log('saved ' + out + ' at ' + page.url());
  await browser.close();
})().catch((e) => { console.error(e.message); process.exit(1); });

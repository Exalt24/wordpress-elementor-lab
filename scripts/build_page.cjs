// Builds the landing page INSIDE the real Elementor editor (headless Chromium, logged in as the lab admin), using the editor's own command API
// ($e.run('document/elements/create')) so Elementor itself produces and saves the page data, then publishes with the editor's save command.
// Usage: node scripts/build_page.cjs <out_dir> <page_id>
const { chromium } = require('C:/Users/' + process.env.USERNAME + '/AppData/Roaming/npm/node_modules/playwright');
const BASE = 'http://localhost:8087';
const [out, id] = [process.argv[2], process.argv[3]];

const INK = '#16243a', ACCENT = '#e8590c', SOFT = '#f4f6fa', MUTED = '#51607a';

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
  await p.waitForFunction(() => window.elementor && window.$e && elementor.documents && elementor.documents.getCurrent() && elementor.getPreviewContainer, null, { timeout: 90000 });
  await p.waitForTimeout(4000);

  const result = await p.evaluate(({ INK, ACCENT, SOFT, MUTED }) => {
    const root = elementor.getPreviewContainer();
    const add = (container, model) => $e.run('document/elements/create', { container, model });
    const section = (settings) => add(root, { elType: 'container', settings: Object.assign({ content_width: 'full', flex_direction: 'column', flex_align_items: 'center', padding: { unit: 'px', top: '72', right: '24', bottom: '72', left: '24', isLinked: false } }, settings) });
    const inner = (parent, settings) => add(parent, { elType: 'container', settings: Object.assign({ content_width: 'boxed', boxed_width: { unit: 'px', size: 1100 }, flex_direction: 'column', flex_align_items: 'center', flex_gap: { unit: 'px', size: 18, column: '18', row: '18' } }, settings) });
    const w = (parent, widgetType, settings) => add(parent, { elType: 'widget', widgetType, settings });

    // HERO
    const hero = section({ background_background: 'classic', background_color: INK, _element_id: 'top' });
    const heroIn = inner(hero, {});
    w(heroIn, 'heading', { title: 'Find out why your Amazon listings are not converting', header_size: 'h1', align: 'center', title_color: '#ffffff', typography_typography: 'custom', typography_font_size: { unit: 'px', size: 52 }, typography_font_weight: '800', typography_line_height: { unit: 'em', size: 1.1 } });
    w(heroIn, 'text-editor', { editor: '<p style="text-align:center">A free, written audit of your listings, your advertising spend and your account health, with the three changes most likely to lift sales first.</p>', text_color: '#d6deee', typography_typography: 'custom', typography_font_size: { unit: 'px', size: 20 } });
    w(heroIn, 'button', { text: 'Request the free audit', link: { url: '#request', is_external: '', nofollow: '' }, align: 'center', background_color: ACCENT, button_text_color: '#ffffff', typography_typography: 'custom', typography_font_weight: '700', typography_font_size: { unit: 'px', size: 18 }, border_radius: { unit: 'px', top: '8', right: '8', bottom: '8', left: '8', isLinked: true }, button_padding: { unit: 'px', top: '16', right: '32', bottom: '16', left: '32', isLinked: false } });

    // WHAT THE AUDIT CHECKS
    const checks = section({ background_background: 'classic', background_color: '#ffffff' });
    const checksIn = inner(checks, { flex_gap: { unit: 'px', size: 28, column: '28', row: '28' } });
    w(checksIn, 'heading', { title: 'What the audit checks', header_size: 'h2', align: 'center', title_color: INK });
    const row = add(checksIn, { elType: 'container', settings: { content_width: 'full', flex_direction: 'row', flex_gap: { unit: 'px', size: 24, column: '24', row: '24' }, flex_justify_content: 'center', flex_wrap: 'wrap' } });
    const cards = [
      ['Listing quality', 'Titles, bullet points, images and A+ content compared against the top results for the same search terms.'],
      ['Advertising spend', 'Campaigns spending without selling, overlapping keywords and the search terms that never convert.'],
      ['Account health', 'Policy warnings, inventory limits and the complaints that quietly cap your visibility.'],
    ];
    for (const [t, d] of cards) {
      const card = add(row, { elType: 'container', settings: { content_width: 'full', width: { unit: '%', size: 30 }, flex_direction: 'column', flex_gap: { unit: 'px', size: 10, column: '10', row: '10' }, background_background: 'classic', background_color: SOFT, border_radius: { unit: 'px', top: '12', right: '12', bottom: '12', left: '12', isLinked: true }, padding: { unit: 'px', top: '28', right: '28', bottom: '28', left: '28', isLinked: true } } });
      w(card, 'heading', { title: t, header_size: 'h3', title_color: INK });
      w(card, 'text-editor', { editor: '<p>' + d + '</p>', text_color: MUTED });
    }

    // HOW IT WORKS
    const how = section({ background_background: 'classic', background_color: SOFT });
    const howIn = inner(how, { flex_gap: { unit: 'px', size: 24, column: '24', row: '24' } });
    w(howIn, 'heading', { title: 'How it works', header_size: 'h2', align: 'center', title_color: INK });
    w(howIn, 'icon-list', {
      icon_list: [
        { text: 'Send your seller account email and one product link', selected_icon: { value: 'fas fa-check', library: 'fa-solid' }, _id: 'a1b2c3d' },
        { text: 'We review the three areas above, read-only, within three working days', selected_icon: { value: 'fas fa-check', library: 'fa-solid' }, _id: 'e4f5a6b' },
        { text: 'You get a written report with the top three changes ranked by likely lift', selected_icon: { value: 'fas fa-check', library: 'fa-solid' }, _id: 'c7d8e9f' },
      ],
      text_color: INK, icon_color: ACCENT, icon_typography_typography: 'custom', text_indent: { unit: 'px', size: 12 },
    });

    // REQUEST
    const req = section({ background_background: 'classic', background_color: INK, _element_id: 'request' });
    const reqIn = inner(req, {});
    w(reqIn, 'heading', { title: 'Request the free audit', header_size: 'h2', align: 'center', title_color: '#ffffff' });
    w(reqIn, 'text-editor', { editor: '<p style="text-align:center">Email <a href="mailto:audit@example.com" style="color:#ffb27a">audit@example.com</a> with your seller account name and one product link.</p>', text_color: '#d6deee' });

    // FOOTER NOTE
    const foot = section({ background_background: 'classic', background_color: '#0e1828', padding: { unit: 'px', top: '24', right: '24', bottom: '24', left: '24', isLinked: true } });
    w(foot, 'text-editor', { editor: '<p style="text-align:center;font-size:13px">Demo page built to practise an Elementor build. Not a live service.</p>', text_color: '#8fa0bd' });

    return { children: root.children.length };
  }, { INK, ACCENT, SOFT, MUTED });
  console.log('sections created:', JSON.stringify(result));

  await p.waitForTimeout(3000);
  await p.screenshot({ path: out + '/editor_built.png' });

  // Publish with the editor's own save command, then confirm.
  await p.evaluate(async () => { await $e.run('document/save/publish'); });
  await p.waitForTimeout(5000);
  console.log('saved; document status:', await p.evaluate(() => elementor.documents.getCurrent().config.status ? elementor.documents.getCurrent().config.status.value : 'n/a'));
  await b.close();
})().catch((e) => { console.error('BUILD FAILED', e); process.exit(1); });

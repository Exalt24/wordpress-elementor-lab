// Block tree for the design pass on the launched WordPress.com sample site (docs/launched-site.md, section "Design pass").
// It builds plain descriptions of blocks ({ name, attrs, inner }) and nothing else: no browser, no network, no login.
// Turning the tree into saved markup is done by the block editor itself in the page (wp.blocks.createBlock, then wp.blocks.serialize),
// so every block is written the way the editor writes it and shows as valid when a person opens the page.
//   const { buildAll } = require('./design_pass_blocks.cjs');   // { pages: {7: tree, ...}, header: tree, footer: tree, template: markup }
// Every colour below was checked with scripts/contrast_check.cjs against the colours the browser computed on the live pages.

const C = {
  navy: '#0f2540',      // dark bands, footer, headings, button text on light
  deep: '#0a1b30',      // last band and footer
  ink: '#14243a',       // body text
  muted: '#41546b',     // secondary text on white and on the tint
  tint: '#eef3f8',      // light section and fact cards
  line: '#c5d2e0',      // card and row borders
  link: '#0b5cad',      // links on light backgrounds
  amber: '#ffc857',     // the one primary button, on dark bands
  teal: '#00677a',      // small caps labels on light backgrounds, card top rule
  tealOnDark: '#8fd8e6',// small caps labels on dark bands
  onDark: '#dbe6f2',    // lead text on dark bands
  white: '#ffffff',
};
// WordPress turns a plain px font size into a fluid clamp() that shrinks to 80 percent on a phone (18 px became 14.4 px at 390 wide),
// so every size is written as max(px, rem): the same size at every width, and not rewritten by the theme.
const F = { 16: 'max(16px, 1rem)', 18: 'max(18px, 1.125rem)', 20: 'max(20px, 1.25rem)', 22: 'max(22px, 1.375rem)' };
const SIDE = '1.5rem';                       // page side padding, 24 px
const SECTION = 'clamp(3rem, 8vw, 5rem)';    // section top and bottom padding, 48 to 80 px
const T = {                                  // type scale: 16 / 18 / 20 / 22 / 32 / 48
  label: { fontSize: F[16], fontWeight: '700', lineHeight: '1.5', letterSpacing: '0.08em', textTransform: 'uppercase' },
  body: { fontSize: F[18], lineHeight: '1.5', fontWeight: '400' },
  lead: { fontSize: F[20], lineHeight: '1.5', fontWeight: '400' },
  h3: { fontSize: F[22], lineHeight: '1.3', fontWeight: '700' },
  h2: { fontSize: 'clamp(1.75rem, 4vw, 2rem)', lineHeight: '1.2', fontWeight: '700' },
  h1: { fontSize: 'clamp(2rem, 5.5vw, 3rem)', lineHeight: '1.15', fontWeight: '700', letterSpacing: '-0.01em' },
  small: { fontSize: F[16], lineHeight: '1.5', fontWeight: '400' },
};

const b = (name, attrs = {}, inner = []) => ({ name, attrs, inner });
const p = (content, typo = T.body, extra = {}) => b('core/paragraph', { content, style: Object.assign({ typography: typo }, extra) });
const h = (level, content, typo, extra = {}) => b('core/heading', Object.assign({ level, content, style: Object.assign({ typography: typo }, extra.style || {}) }, extra.attrs || {}));
const label = (text, color) => p(text, T.label, { color: { text: color } });
const spacing = (o) => ({ spacing: o });

// Full width band with a centred 1100 px column. Children that are not "wide" sit in that column.
const band = (inner, { bg, text, top = SECTION, bottom = SECTION, anchor, link } = {}) => b('core/group', {
  align: 'full', anchor,
  style: Object.assign({ spacing: { padding: { top, bottom, left: SIDE, right: SIDE }, blockGap: '1.5rem', margin: { top: '0', bottom: '0' } } },
    bg || text ? { color: Object.assign(bg ? { background: bg } : {}, text ? { text } : {}) } : {},
    link ? { elements: { link: { color: { text: link } } } } : {}),
  layout: { type: 'constrained', contentSize: '1100px', wideSize: '1100px' },
}, inner);
// A reading column of 720 px aligned to the left edge of the 1100 px column.
const prose = (inner, gap = '1rem') => b('core/group', {
  style: { spacing: { blockGap: gap } },
  layout: { type: 'constrained', contentSize: '720px', justifyContent: 'left' },
}, inner);
const h2in = (text, first) => h(2, text, T.h2, { style: { color: { text: C.navy }, spacing: { margin: { top: first ? '0' : '2.5rem', bottom: '0' } } } });

const buttons = (items, justify = 'left') => b('core/buttons', { layout: { type: 'flex', justifyContent: justify }, style: { spacing: { blockGap: '0.75rem 1rem' } } },
  items.map((i) => b('core/button', i)));
const BTN_PAD = { top: '0.8rem', bottom: '0.8rem', left: '1.75rem', right: '1.75rem' };   // 13 px + 27 px line + 13 px = 53 px tall
const btnPrimary = (text, url) => ({ text, url, style: { color: { background: C.amber, text: C.navy }, border: { radius: '6px' }, spacing: { padding: BTN_PAD }, typography: { fontSize: F[18], fontWeight: '700', lineHeight: '1.5' } } });
const btnLight = (text, url) => ({ text, url, className: 'is-style-outline', style: { color: { text: C.white }, border: { radius: '6px', width: '2px', color: '#9fb3c8' }, spacing: { padding: BTN_PAD }, typography: { fontSize: F[18], fontWeight: '600', lineHeight: '1.5' } } });
const btnOutline = (text, url) => ({ text, url, className: 'is-style-outline', style: { color: { text: C.navy }, border: { radius: '6px', width: '2px', color: C.navy }, spacing: { padding: BTN_PAD }, typography: { fontSize: F[18], fontWeight: '600', lineHeight: '1.5' } } });

const card = (inner, extra = {}) => b('core/group', {
  style: { color: { background: extra.bg || C.white }, border: extra.border || { top: { width: '4px', color: C.teal, style: 'solid' }, right: { width: '1px', color: C.line, style: 'solid' }, bottom: { width: '1px', color: C.line, style: 'solid' }, left: { width: '1px', color: C.line, style: 'solid' }, radius: '8px' }, spacing: { padding: { top: '1.5rem', bottom: '1.5rem', left: '1.5rem', right: '1.5rem' }, blockGap: '0.75rem' } },
  layout: extra.layout || { type: 'flex', orientation: 'vertical', justifyContent: 'stretch', verticalAlignment: 'space-between' },
}, inner);
// Auto fitting grid: 3 columns when the 1100 px column allows it, one column on a phone (a fixed column count does not collapse).
const grid = (inner, n) => b('core/group', { align: 'wide', style: { spacing: { blockGap: '1.5rem' } }, layout: { type: 'grid', minimumColumnWidth: n === 3 ? '17rem' : '24rem' } }, inner);
const notice = () => b('core/group', {
  style: { color: { background: C.tint }, border: { left: { width: '4px', color: C.teal, style: 'solid' }, radius: '4px' }, spacing: { padding: { top: '1rem', bottom: '1rem', left: '1.25rem', right: '1.25rem' } } },
}, [p('Sample site notice: the text on this page is placeholder text, the organisation is invented, and nothing here is medical advice. Check the official rules of the body that sets them before you rely on anything.', T.small, { color: { text: C.ink } })]);
const nav = (label, links, extra = {}) => b('core/navigation', Object.assign({
  ariaLabel: label, overlayMenu: 'never', layout: { type: 'flex', orientation: 'vertical', justifyContent: 'left' },
  style: { typography: { fontSize: F[18], lineHeight: '2.5', fontWeight: '500' }, spacing: { blockGap: '0' } },
}, extra), links.map(([t, u]) => b('core/navigation-link', { label: t, url: u, kind: 'custom', type: 'custom', isTopLevelLink: true })));

// Page header band used by the five inner pages.
const pageHead = (eyebrow, title, lead) => band([
  prose([label(eyebrow, C.tealOnDark), h(1, title, T.h1, { style: { color: { text: C.white } } }), p(lead, T.lead, { color: { text: C.onDark } })], '1rem'),
], { bg: C.navy, text: C.white, top: 'clamp(2.5rem, 7vw, 4rem)', bottom: 'clamp(2.5rem, 7vw, 4rem)' });

const related = (links) => [h2in('Related pages'), buttons(links.map(([t, u]) => btnOutline(t, u)))];
const ALL = { home: ['Emergency medicine CME, the main page of this sample', '/'], acls: ['ACLS recertification online', '/acls-recertification-online/'], cme: ['CME requirements for physicians', '/cme-requirements/'], us: ['Ultrasound courses for emergency physicians', '/ultrasound-courses/'], q: ['Questions', '/questions/'], about: ['About this sample', '/about-this-sample/'] };
const rel = (...keys) => keys.map((k) => ALL[k]);

const facts = (items, n) => grid(items.map(([t, d]) => card([h(3, t, T.h3, { style: { color: { text: C.navy } } }), p(d, T.body, { color: { text: C.ink } })], { bg: C.tint, border: { radius: '8px' }, layout: { type: 'default' } })), n);

function buildAll() {
  const pages = {};

  // Front page
  pages[7] = [
    band([
      b('core/columns', { align: 'wide', verticalAlignment: 'center', style: { spacing: { blockGap: { top: '2rem', left: '3rem' } } } }, [
        b('core/column', { width: '58%', verticalAlignment: 'center' }, [
          b('core/group', { style: { spacing: { blockGap: '1rem' } }, layout: { type: 'default' } }, [
            label('A sample site with placeholder text', C.tealOnDark),
            h(1, 'Emergency medicine CME: a sample guide', T.h1, { style: { color: { text: C.white } } }),
            p('This sample shows how a keyword plan becomes a set of connected pages that are easy to read on a phone and easy for a team to update.', T.lead, { color: { text: C.onDark } }),
            buttons([btnPrimary('ACLS recertification online', '/acls-recertification-online/'), btnLight('Read the questions', '/questions/')]),
          ]),
        ]),
        b('core/column', { width: '42%', verticalAlignment: 'center' }, [
          b('core/group', { style: { color: { background: C.white, text: C.ink }, border: { radius: '8px' }, spacing: { padding: { top: '1.5rem', bottom: '1.5rem', left: '1.5rem', right: '1.5rem' }, blockGap: '1rem' } } }, [
            label('At a glance', C.teal),
            p('<strong>Six pages</strong><br>A front page, three topic pages, a questions page and an about page.', T.body, { color: { text: C.ink } }),
            p('<strong>Placeholder text</strong><br>Every description and answer is a stand in.', T.body, { color: { text: C.ink } }),
            p('<strong>Invented organisation</strong><br>No real course, price, accreditation or medical advice.', T.body, { color: { text: C.ink } }),
          ]),
        ]),
      ]),
    ], { bg: C.navy, text: C.white, top: 'clamp(3rem, 8vw, 5rem)', bottom: 'clamp(3rem, 8vw, 5rem)' }),
    band([
      prose([h(2, 'Start with a topic', T.h2, { style: { color: { text: C.navy }, spacing: { margin: { top: '0', bottom: '0' } } } }),
        p('Three placeholder pages show the page types a clinician education site needs. Each opens a page with the same layout.', T.body, { color: { text: C.ink } })]),
      grid([
        ['Course page', 'ACLS recertification online', 'A placeholder course page about renewing a life support card online.', 'Open the course page', '/acls-recertification-online/'],
        ['Topic page', 'CME requirements', 'A placeholder topic page about credit requirements for physicians.', 'Open the topic page', '/cme-requirements/'],
        ['Course page', 'Ultrasound courses', 'A placeholder course page about ultrasound training for emergency physicians.', 'Open the course page', '/ultrasound-courses/'],
      ].map(([kind, title, desc, btn, url]) => card([
        b('core/group', { style: { spacing: { blockGap: '0.75rem' } }, layout: { type: 'default' } }, [label(kind, C.teal), h(3, title, T.h3, { style: { color: { text: C.navy } } }), p(desc, T.body, { color: { text: C.ink } }), p('Credits and length: placeholder', T.small, { color: { text: C.muted } })]),
        buttons([btnOutline(btn, url)]),
      ])), 3),
    ], { bg: C.tint }),
    band([
      prose([h(2, 'About emergency medicine CME', T.h2, { style: { color: { text: C.navy }, spacing: { margin: { top: '0', bottom: '0' } } } }),
        p('Emergency medicine CME is the main topic of this sample site. In the keyword research behind it, people also add words such as conferences, online, free and requirements. On a real site this page would link to every course and topic page, which is what the three cards above do.', T.body, { color: { text: C.ink } }),
        p('Every page here follows one plan: one topic, one title, one main heading, a short description and links back to this page.', T.body, { color: { text: C.ink } })], '1rem'),
    ]),
    band([
      prose([h(2, 'Have a question first?', T.h2, { style: { color: { text: C.white }, spacing: { margin: { top: '0', bottom: '0' } } } }),
        p('The questions page lists what people type into search, with placeholder answers and links to the matching page.', T.lead, { color: { text: C.onDark } }),
        buttons([btnPrimary('Go to the questions', '/questions/')])], '1rem'),
    ], { bg: C.deep, text: C.white }),
  ];

  // Course and topic pages
  const course = (eyebrow, title, lead, forTitle, forText, holdTitle, holdItems, n, extraTitle, extraText, relKeys) => [
    pageHead(eyebrow, title, lead),
    band([
      prose([h2in('What this page is for', true), p(forText, T.body, { color: { text: C.ink } })]),
      h2in(holdTitle), facts(holdItems, n),
      prose([h2in(extraTitle, true), p(extraText, T.body, { color: { text: C.ink } })]),
      ...related(rel(...relKeys)),
      notice(),
    ], { link: C.link }),
  ];
  pages[8] = course('Course page', 'ACLS Recertification Online', 'This is a placeholder course page. The text shows page structure and does not inform anyone.', null,
    'It targets the search phrase ACLS recertification online. People also type free ACLS recertification online, best ACLS recertification online and ACLS recertification online course, so a real page would cover those wordings.',
    'What a real page would hold', [['Course summary', 'A short course summary written and reviewed by the organisation.'], ['Audience', 'Who the course is for.'], ['Dates, format and price', 'Kept current.'], ['Official source', 'A link to the official body that sets the rules.']], 2,
    'Common wordings for the same topic', 'Searches also use ACLS online, ACLS certification and ACLS renewal. In the content map these are separate pages that link back to the main page, and they are not built in this sample.', ['home', 'cme', 'us', 'q']);
  pages[9] = course('Topic page', 'CME Requirements for Physicians', 'This is a placeholder topic page. The text shows page structure and does not state any real requirement.', null,
    'It targets the search phrase CME requirements for physicians. People also type what are CME requirements and CME requirements by state, so a real page would explain how requirements are organised and where to check them.',
    'What a real page would hold', [['Plain explanation', 'A plain explanation of what CME means.'], ['Table of sources', 'One row per authority, each linking to the official page.'], ['Date checked', 'The date the page was last checked.']], 3,
    'Questions people ask', 'How much CME per year and CME eligibility criteria are common searches. They are listed on the <a href="/questions/">questions page</a> with placeholder answers.', ['home', 'acls', 'us', 'q']);
  pages[10] = course('Course page', 'Ultrasound Courses for Emergency Physicians', 'This is a placeholder course page. The text shows page structure and does not describe any real course.', null,
    'It targets the search phrase ultrasound courses for emergency physicians. People also type ultrasound courses for physicians and ultrasound courses for doctors, so a real page would use those wordings too.',
    'What a real page would hold', [['Course summaries', 'A short summary of each course, written by the course provider.'], ['Format, length and location', 'Kept current.'], ['Provider link', 'A link to the provider for dates and booking.']], 3,
    'Related searches', 'Ultrasound course for physicians and ultrasound training courses for physicians are close variants. In the content map they are separate pages that link back to the main page, and they are not built in this sample.', ['home', 'acls', 'cme', 'q']);

  // Questions page: three groups, native details elements as the accordion
  const ans = (t, link) => p(link ? `Placeholder answer. See the <a href="${link[1]}">${link[0]}</a> page.` : t, T.body, { color: { text: C.ink }, typography: { fontSize: F[18], lineHeight: '1.5', fontWeight: '400' }, spacing: { margin: { top: '0', bottom: '1rem' } } });
  const acls = ['ACLS recertification online', '/acls-recertification-online/'], cme = ['CME requirements for physicians', '/cme-requirements/'];
  const q = (summary, link, text) => b('core/details', {
    summary, showContent: false,
    style: { typography: { fontSize: F[18], fontWeight: '700', lineHeight: '2.5' }, color: { text: C.navy }, border: { bottom: { width: '1px', color: C.line, style: 'solid' } }, spacing: { padding: { top: '0', bottom: '0', left: '0', right: '0' } } },
  }, [ans(text, link)]);
  const group = (id, title, qs) => [b('core/heading', { level: 2, anchor: id, content: title, style: { typography: T.h2, color: { text: C.navy }, spacing: { margin: { top: '2.5rem', bottom: '0.5rem' } } } }), ...qs];
  const aclsQs = ['What is ACLS recertification?', 'Can you recertify ACLS online?', 'How to get ACLS recertification', 'Can you do ACLS recertification online?', 'Can ACLS recertification be done online?', 'Is online ACLS certification valid?', 'How much does ACLS certification cost?', 'Can ACLS be renewed online?', 'How to recertify ACLS online'];
  pages[11] = [
    pageHead('Questions', 'Questions', 'These are the questions people type into search, taken from the keyword research. Every answer here is a placeholder. A real page would give a short, reviewed answer with a link to the official source.'),
    band([
      prose([p('Jump to a group', T.label, { color: { text: C.teal } })], '0.5rem'),
      buttons([btnOutline('ACLS questions (9)', '#acls-questions'), btnOutline('CME questions (2)', '#cme-questions'), btnOutline('Career question (1)', '#career-question')]),
      prose([
        ...group('acls-questions', 'ACLS questions', aclsQs.map((s) => q(s, s.includes('cost') ? null : acls, 'Placeholder answer. A real page would link to the provider for current prices.'))),
        ...group('cme-questions', 'CME questions', [q('What are CME requirements?', cme), q('How much CME per year?', cme)]),
        ...group('career-question', 'Career question', [q('How to become an emergency physician', null, 'Placeholder answer. A real page would link to the official training bodies.')]),
      ], '0'),
      ...related(rel('home', 'acls', 'cme', 'us')),
      notice(),
    ], { link: C.link }),
  ];

  // About page
  pages[1] = [
    pageHead('About', 'About This Sample', 'This site is a sample. It was built on the free WordPress.com plan by Daniel Alexis Cruz as part of a portfolio, to show a small multi page site made in the block editor.'),
    band([
      prose([h2in('What it shows', true)]),
      facts([['A plan in pages', 'A keyword plan turned into pages: one main page, three topic and course pages and a questions page.'], ['Menu and footer', 'A menu with every page and a footer on every page.'], ['Clear structure', 'Short titles, one main heading per page and a short description for each page.'], ['Phone ready', 'Pages that read well on a phone.']], 2),
      prose([h2in('What it is not', true), p('The organisation is invented. The text is placeholder text. The site gives no medical advice and states no prices, accreditation or requirements. Do not rely on anything written here.', T.body, { color: { text: C.ink } }),
        h2in('Where the plan came from'), p('The structure comes from a keyword research run on public autocomplete suggestions. The scripts and the recorded run are in the repository that holds this sample.', T.body, { color: { text: C.ink } })]),
      ...related(rel('home', 'acls', 'cme', 'us', 'q')),
      notice(),
    ], { link: C.link }),
  ];

  // Header and footer template parts
  // Header: site title, then the menu. From 782 px up the six links sit in the row. Below that the menu is a native "Menu" disclosure under the title,
  // because the theme's own menu button is a fixed 24 px icon with no way to change its size on this plan. Block visibility decides which one shows.
  const hide = (...v) => ({ blockVisibility: { viewport: Object.fromEntries(v.map((k) => [k, false])) } });
  const header = [b('core/group', { align: 'full', style: { color: { background: C.white }, border: { bottom: { width: '1px', color: C.line, style: 'solid' } }, spacing: { padding: { left: SIDE, right: SIDE } } }, layout: { type: 'constrained', contentSize: '1100px', wideSize: '1100px' } }, [
    b('core/group', { align: 'wide', style: { spacing: { padding: { top: '0.75rem', bottom: '0.75rem' } } }, layout: { type: 'flex', flexWrap: 'nowrap', justifyContent: 'space-between' } }, [
      b('core/site-title', { level: 0, style: { typography: { fontSize: F[18], fontWeight: '700', lineHeight: '1.3' }, elements: { link: { color: { text: C.navy } } } } }),
      b('core/navigation', { ref: 13, overlayMenu: 'never', metadata: hide('mobile', 'tablet'), layout: { type: 'flex', justifyContent: 'right', flexWrap: 'wrap' }, style: { typography: { fontSize: F[16], fontWeight: '600', lineHeight: '2.8' }, spacing: { blockGap: '1.25rem' }, elements: { link: { color: { text: C.navy } } } } }),
    ]),
    b('core/group', { align: 'wide', metadata: hide('desktop'), style: { spacing: { padding: { bottom: '0.75rem' } } } }, [
      b('core/details', { summary: 'Menu', showContent: false, style: { typography: { fontSize: F[18], fontWeight: '600', lineHeight: '2.5' }, color: { text: C.navy }, border: { width: '1px', color: C.line, radius: '6px' }, spacing: { padding: { top: '0', bottom: '0', left: '1rem', right: '1rem' } } } }, [
        b('core/navigation', { ref: 13, overlayMenu: 'never', layout: { type: 'flex', orientation: 'vertical', justifyContent: 'left' }, style: { typography: { fontSize: F[18], fontWeight: '500', lineHeight: '2.5' }, spacing: { blockGap: '0' }, elements: { link: { color: { text: C.navy } } } } }),
      ]),
    ]),
  ])];
  const col = (title, inner) => b('core/column', {}, [p(title, T.label, { color: { text: C.tealOnDark }, spacing: { margin: { bottom: '0.5rem' } } }), ...inner]);
  const footer = [b('core/group', { align: 'full', style: { color: { background: C.deep, text: C.white }, spacing: { padding: { top: 'clamp(2.5rem, 6vw, 4rem)', bottom: '2rem', left: SIDE, right: SIDE }, blockGap: '2rem' }, elements: { link: { color: { text: C.white } } } }, layout: { type: 'constrained', contentSize: '1100px', wideSize: '1100px' } }, [
    b('core/columns', { align: 'wide', style: { spacing: { blockGap: { top: '2rem', left: '3rem' } } } }, [
      b('core/column', { width: '40%' }, [
        p('Emergency Care Guide (sample site)', { fontSize: F[20], fontWeight: '700', lineHeight: '1.4' }, { color: { text: C.white } }),
        p('A portfolio sample site. The text is placeholder text, the organisation is invented, and nothing here is medical advice.', T.small, { color: { text: C.onDark }, spacing: { margin: { top: '0.5rem' } } }),
      ]),
      b('core/column', { width: '30%' }, [p('Pages', T.label, { color: { text: C.tealOnDark } }), nav('Course and topic pages', [['ACLS recertification online', '/acls-recertification-online/'], ['CME requirements', '/cme-requirements/'], ['Ultrasound courses', '/ultrasound-courses/']], { style: { typography: { fontSize: F[18], lineHeight: '2.5', fontWeight: '500' }, spacing: { blockGap: '0' }, elements: { link: { color: { text: C.white } } } } })]),
      b('core/column', { width: '30%' }, [p('Site', T.label, { color: { text: C.tealOnDark } }), nav('Site pages', [['Home', '/'], ['Questions', '/questions/'], ['About this sample', '/about-this-sample/']], { style: { typography: { fontSize: F[18], lineHeight: '2.5', fontWeight: '500' }, spacing: { blockGap: '0' }, elements: { link: { color: { text: C.white } } } } })]),
    ]),
    b('core/separator', { style: { color: { background: '#34506f' } }, className: 'is-style-default' }),
    p('Sample site for a portfolio. Placeholder text only. Not medical advice.', T.small, { color: { text: C.onDark } }),
  ])];

  // The wrapper that sets the base type for header, page and footer, and removes the gap between bands and footer.
  const template = '<!-- wp:group {"tagName":"div","style":{"typography":{"fontSize":"max(18px, 1.125rem)","lineHeight":"1.5","fontWeight":"400"},"color":{"text":"' + C.ink + '"},"elements":{"link":{"color":{"text":"' + C.link + '"}}},"spacing":{"blockGap":"0"}},"layout":{"type":"default"}} -->\n'
    + '<div class="wp-block-group has-text-color" style="color:' + C.ink + ';font-size:max(18px, 1.125rem);font-weight:400;line-height:1.5">\n'
    + '<!-- wp:template-part {"slug":"header","theme":"pub/twentytwentyfive"} /-->\n\n'
    + '<!-- wp:group {"tagName":"main","style":{"spacing":{"margin":{"top":"0"}}}} -->\n<main class="wp-block-group" style="margin-top:0"><!-- wp:post-content {"lock":{"move":false,"remove":true},"layout":{"type":"constrained","contentSize":"100%","wideSize":"100%"},"metadata":{"ignoredHookedBlocks":["jetpack/sharing-buttons","jetpack/like"]}} /--></main>\n<!-- /wp:group -->\n\n'
    + '<!-- wp:template-part {"slug":"footer","theme":"pub/twentytwentyfive"} /-->\n</div>\n<!-- /wp:group -->';
  return { pages, header, footer, template, C };
}

module.exports = { buildAll, C };

# Launched site: a public WordPress.com sample

This is a real public WordPress site with six pages, made on the free WordPress.com plan. It is built from the content map in [keyword-research-sample.md](keyword-research-sample.md). The Elementor page in this repo runs on a local Docker site. This one is on the internet and anyone can open it.

Public address: https://emergencycaretrainingguidesample.wordpress.com/

Host and plan: WordPress.com, free plan, free `wordpress.com` subdomain. Nothing was bought. No card was entered. The domain offer and every paid plan were declined. Launched on 2026-11-10 (Manila time).

Site title: Emergency Care Guide (sample site). Tagline: A portfolio sample site. Theme: Twenty Twenty-Five, which is free and is a block theme.

## How it was made

1. Signed up with the "Continue with Google" button on the WordPress.com sign up page. The email form on the same page shows an "I am not a robot" box. I did not touch it, because the Google route does not need it.
2. At the domain step I chose Skip, which gives the free address. At the plan step I chose "Start with a free plan".
3. Activated the free Twenty Twenty-Five theme. Set the site title and tagline in Settings, General.
4. Built the pages with the block editor's own block tools (heading, paragraph, list, buttons, group, columns). The page content, the menu, the footer and the page templates were loaded through the editor's API client from a script, not typed block by block. The one place a person types is the edit test further down, and that was done in the editor window.
5. Made the page called Emergency Medicine CME the front page, set each page excerpt, and launched the site from the Launch site button, which moved it from Coming Soon to public.
6. Deleted the default Hello World post, because it would have been a seventh page in the sitemap.

## What was built, page by page

| Page | Address | Type from the content map | Title tag length |
|---|---|---|---|
| Emergency Medicine CME (front page, one h1 inside a navy hero, three cards, a dark call to action) | `/` | pillar page | 60 |
| ACLS Recertification Online | `/acls-recertification-online/` | course page | 64 |
| CME Requirements for Physicians | `/cme-requirements/` | topic page | 68 |
| Ultrasound Courses for Emergency Physicians | `/ultrasound-courses/` | course page | 80 |
| Questions | `/questions/` | FAQ page from `tests/fixtures/questions.txt`, 12 questions | under 65 |
| About This Sample | `/about-this-sample/` | about page | under 65 |

Every page has the keyword in the page title, one h1, h2 sections, a short description (the page excerpt), a menu link and links back to the front page. The menu has Home, ACLS recertification, CME requirements, Ultrasound courses, Questions and About, so it shows all six pages. The footer on every page says plainly that this is a sample site built for a portfolio, that the text is placeholder text, that the organisation is invented and that nothing is medical advice. Each inner page repeats a short notice at the bottom.

The copy is short placeholder text. It states no medical claim, price, accreditation or requirement. Answers on the Questions page say "Placeholder answer" and point to the matching page.

Only six of the 14 rows in the content map are pages here. The rows for ACLS online, ACLS certification, ACLS renewal and the other variants are named on the pages as separate pages that are not built.

## Proof

Screenshots are in `docs/launched-site/`, loaded in a fresh browser context with no login (the page had no admin bar):

- `01-home-desktop-1280.png` and `02-home-phone-390.png`: the front page as first built (before the design pass below), at 1280 and 390 wide. On the phone the menu becomes the icon at the top right, the cards stack and the page does not scroll sideways (page width equals window width, 390).
- `03-inner-page-desktop-1280.png` and `04-inner-page-phone-390.png`: ACLS Recertification Online.
- `05` to `07`: the editor test, below.

The faint bar across the first card in the phone picture is a fixed WordPress.com widget that the full page screenshot caught. The blue strip at the top of every page is the free plan banner, listed below.

### SEO audit with `scripts/seo_audit.py`

Real output is saved next to the screenshots, one file per page.

| Page | Result | Failing checks |
|---|---|---|
| Front page (`seo_audit_home.txt`) | 13 of 15 | no JSON-LD, one link answers 403 |
| ACLS Recertification Online (`seo_audit_inner_acls.txt`) | 13 of 15 | no JSON-LD, one link answers 403 |
| CME Requirements for Physicians | 12 of 15 | title 68 characters, no JSON-LD, one link answers 403 |
| Ultrasound Courses for Emergency Physicians | 12 of 15 | title 80 characters, no JSON-LD, one link answers 403 |
| Questions | 13 of 15 | no JSON-LD, one link answers 403 |
| About This Sample | 13 of 15 | no JSON-LD, one link answers 403 |

Causes:

- Title length. A page title tag is the page title, a dash, then the site title (34 characters). Two page titles are long enough to pass 65 characters. I found no way to set the title tag apart from the page title on the free plan. I did not open the SEO panel that sits in the page sidebar, so I do not claim it is locked.
- JSON-LD. The pages carry none, and I added none. The Add Plugins page offers only paid marketplace plugins (see below), and I did not try any other way to add custom code.
- The link that answers 403. It is the login link in WordPress.com's own login widget, with a redirect back to the page. My audit script gets a 403 from it. It is not a link I wrote, and the other 12 links on each page returned 200.

Passing checks on all pages: status 200, no redirect chain, one h1, heading levels in order, images have alt text, canonical link, `lang="en"`, viewport, Open Graph title, description, type and url, a meta description within 70 to 160 characters (the page excerpt; 146 and 131 characters on the two pages shown), response under 1.5 seconds, HTML under 200 KB (102 and 91 KB on the two pages shown).

### Links, sitemap, robots and page source

`checks_links_sitemap_head.txt` holds the output. All six pages answer 200, so every menu link works. `/sitemap.xml` and `/robots.txt` both load. The sitemap lists the six pages. It also still listed the deleted Hello World address from a cache when I checked, and that address now answers 404. `robots.txt` has no rule against search engines and the pages carry no noindex tag.

In the page source of the front page and of an inner page: a title tag, a `meta name="description"` with the excerpt, a canonical link to the page itself, `og:title`, `og:description`, `og:type`, `og:url`, `og:site_name` and `twitter:card`. On the front page `og:description` is the tagline, not the excerpt.

### How a non technical editor changes a page

1. Sign in, open Pages, then click the page title. The block editor opens with the page as blocks.
2. Click the heading or paragraph, change the words, and press Save. A message says "Page updated".
3. Open the public page. The change is there.

I did this on ACLS Recertification Online. In the editor I changed the heading "What this page is for" to "What this page is for (edited in the block editor)" (`05-editor-heading-edited.png`), pressed Save (`06-editor-page-updated.png`), and fetched the public page, which showed the new heading. Then I changed it back the same way (`07-editor-heading-reverted.png`) and the public page showed the original heading. The three heading lines are in `editor_edit_readback.txt`, and the folder `design-pass/` (before, after and reference screenshots and the contrast check output, listed in the last section).

## What the free plan blocked or added

- A blue banner at the top of every page: "Create your own website, free on WordPress.com" with a Start free button. I found no free way to remove it.
- No custom domain. The address ends in `.wordpress.com`. The domain was offered at the first step and again at launch, and I declined both.
- No plugins. The Add Plugins page lists 56 marketplace items, each with an "Upgrade and purchase" button, including Yoast SEO Premium. So there is no SEO plugin, and nothing here for structured data.
- The theme page says style variations and your own fonts and colours need the Personal plan. The hero and card colours are set on the blocks themselves instead.
- The email sign up form shows a human check. I used the Google route and did not touch it.

## Limits

This is a sample. The text is placeholder text, the organisation is invented and nothing on the site is medical advice. It has no real course, price, accreditation or requirement. Six pages are built from a 14 row content map. The keyword research behind the map counts autocomplete suggestions and is not search volume. The site has no traffic history and no search ranking, and I make no claim about either. It runs on the free plan, so WordPress.com controls the banner and the hosting.

## Files in `docs/launched-site/`

`01` to `07` screenshots, `seo_audit_home.txt`, `seo_audit_inner_acls.txt` and four more `seo_audit_inner_*.txt` files, `checks_links_sitemap_head.txt`, `editor_edit_readback.txt`, and the folder `design-pass/` (before, after and reference screenshots and the contrast check output, listed in the last section).


## Design pass

After the first build I did a design pass, following the design half of the build-webapp routine: look at real sites in the same field, screenshot our own pages next to them at 1280 and 390 pixels wide, list the gaps, fix them in the block editor, and read every page again.

### What was compared

Three live sites, loaded in a browser with no login, top of the page at both widths (`design-pass/ref-*-top.png`, cropped to the first screen or two and saved only for comparison):

- Medscape Education (medscape.org): a trust line under the header saying the education is accredited and independent, a headline over a banner, then a stack of course cards where every card ends in a meta line such as "0.25 CME / ABIM MOC / CE, 15 MIN".
- American Heart Association CPR and First Aid (cpr.heart.org, the course list): one row per course with a short description, tag chips for format and credit type, and one solid button per row.
- ACEP (acep.org): a plain two part hero with a dark panel and a large dark headline, one solid primary button, widely spaced small capital labels over each section, and a dark footer in columns.

Our own twelve screenshots from before the pass (six pages, two widths) are `design-pass/before-*.png`.

### Gaps found

From the before screenshots set beside the three references:

1. Type. Body text was a thin weight, and the theme's fluid font size shrank an 18 px setting to 14.4 px on a phone. Headings were a light weight with little step between them and the body.
2. Hero and call to action. A flat purple block with two pill buttons. The first had purple text on white and the second a thin outline, so neither read as the one main action. The references use one solid button.
3. Spacing and alignment. The three cards ran wider than the text column above them, so the card edges did not line up with the headings. The sections had no rhythm: a black band, a white block and a plain footer.
4. Contrast. The lavender cards, grey text and purple on white buttons were never measured. The new colours are checked with `scripts/contrast_check.cjs` against the colours the browser computed.
5. Trust and structure. The references show credits, length and format on every course card and label each section in small capitals. The first build had neither.
6. Phone layout. The menu was a 24 px icon with no label, the cards were not a real grid, and the footer was one run of links.
7. Footer. One sentence and a row of links, where the references use a dark footer in columns.

### What changed

All of it was changed in the block editor on the live site: the page content of the six pages, the header, the footer and the page template.

- One type scale for the whole site: 16, 18, 20, 22, 32 and 48 px, body 18 px at line height 1.5 and weight 400 at every width, headings bold. Sizes are written as `max(18px, 1.125rem)` so the theme does not shrink them.
- A navy hero with a small capitals label, a bold white headline and one amber solid button, with an outline button beside it. On the front page a white "At a glance" card sits beside it and says plainly that this is a sample with placeholder text. The five other pages get a shorter navy header with a label, the h1 and a lead.
- Sections are full width bands with one 1100 px column and 48 to 80 px of padding top and bottom. Reading text sits in a 720 px column. Cards are a grid that fits three across, then two, then one, so the phone is a single column with no sideways scroll.
- Cards have a teal top rule, a small capitals label, a bold title and an outline button. Each front page card now has a line "Credits and length: placeholder", the pattern Medscape and the AHA list use, so a real site would show real figures there.
- Header: site title and the six links on one row from 782 px up, and a labelled "Menu" disclosure under the title below that. Footer: a dark footer in three columns with the sample notice. The questions page has native disclosure rows under three group headings, with a jump row of buttons.
- Colours: navy `#0f2540`, body `#14243a`, links `#0b5cad`, teal `#00677a` on white, light teal `#8fd8e6` on navy, amber `#ffc857` for the main button.
- The placeholder content stayed honest: every page still says it is placeholder text, the organisation is invented and nothing is medical advice. I added no claim, price, accreditation or testimonial.

How each page was saved: I opened the page in the block editor, put the new blocks in with the editor's own block API (the editor checked every block as valid), pressed Save and saw "Page updated", then loaded the public page signed out and read it at both widths. The block tree is in `scripts/design_pass_blocks.cjs`. I also found that the page template held one block the editor marked as invalid content (the template had been written as raw markup), and re-saved it through the editor, so it now opens cleanly. The theme's post template shows one nested block that the editor's parser flags in the same check; it belongs to the theme's own default post layout, no page uses it, and I left it.

### Result

- Contrast (`design-pass/contrast_check_after.txt`, six pages at both widths): 0 text colours under AA. The lowest ratio is 6.52 (teal on white).
- No sideways scroll on any page at 390 (page width equals window width).
- Tap targets under 44 px high, apart from links inside a sentence: only the hidden "Skip to content" link and WordPress.com's own floating widget button, which are not page content. Menu and question rows are 44 px or more.
- The 15 check SEO audit scores the same as before the pass (12 or 13 of 15, same causes), because the pass changed no title, excerpt or metadata.
- Before and after: `design-pass/before-home-1280.png` against `design-pass/after-home-1280.png`, and the same pair at 390 and for each inner page.
- On a phone a question that wraps onto two lines shows a wider gap between its two lines. I tried a tighter line height with padding, but the padding does not enlarge the part you tap, so I kept the 44 px tap row.

### Free plan limits hit

- Type face: the theme font stays. Changing the font or the style variation needs the Personal plan. Weight, size, line height, colour and spacing are all set per block, which the free plan allows.
- The theme's own phone menu button is a fixed 24 px icon with no setting to enlarge it. I replaced it with a labelled "Menu" disclosure shown only on a phone, using the editor's block visibility setting.
- WordPress.com turns a plain pixel font size into a fluid size that shrinks on a phone, and no setting turns that off. Writing the size as `max(18px, 1.125rem)` gives the same size at every width.
- The summary row of a disclosure block takes no padding of its own, so its tap height can only come from line height.
- The blue "Create your own website" banner and the small floating widget stay on every page, as before.
- Custom CSS: the Additional CSS box is present in the site editor. I did not use it, because the design is done with block settings, and I did not test whether the free plan applies it, so I make no claim either way.
- No photographs: the references use banner images, and a sample site with an invented organisation should not use stock pictures of people as if they were its staff. No plugin, domain or upload was needed or tried.
- The title tag length of two pages is still over the limit and there is still no JSON-LD, for the reasons given above.

### Files in `docs/launched-site/design-pass/`

`before-*.png` and `after-*.png` (home, acls, cme, ultrasound, questions and about, each at 1280 and 390), the `ref-medscape-*`, `ref-aha-*` and `ref-acep-*` top crops, and `contrast_check_after.txt`. Scripts: `scripts/contrast_check.cjs` (computed colour contrast, tap size and overflow for a live page, `CDP_PORT=<port>` attaches to a browser that is already running) and `scripts/design_pass_blocks.cjs` (the block tree).

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
| Emergency Medicine CME (front page, one h1 inside a purple hero, three cards, a dark call to action) | `/` | pillar page | 60 |
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

- `01-home-desktop-1280.png` and `02-home-phone-390.png`: the front page at 1280 and 390 wide. On the phone the menu becomes the icon at the top right, the cards stack and the page does not scroll sideways (page width equals window width, 390).
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

I did this on ACLS Recertification Online. In the editor I changed the heading "What this page is for" to "What this page is for (edited in the block editor)" (`05-editor-heading-edited.png`), pressed Save (`06-editor-page-updated.png`), and fetched the public page, which showed the new heading. Then I changed it back the same way (`07-editor-heading-reverted.png`) and the public page showed the original heading. The three heading lines are in `editor_edit_readback.txt`.

## What the free plan blocked or added

- A blue banner at the top of every page: "Create your own website, free on WordPress.com" with a Start free button. I found no free way to remove it.
- No custom domain. The address ends in `.wordpress.com`. The domain was offered at the first step and again at launch, and I declined both.
- No plugins. The Add Plugins page lists 56 marketplace items, each with an "Upgrade and purchase" button, including Yoast SEO Premium. So there is no SEO plugin, and nothing here for structured data.
- The theme page says style variations and your own fonts and colours need the Personal plan. The purple hero and card colours are set on the blocks themselves instead.
- The email sign up form shows a human check. I used the Google route and did not touch it.

## Limits

This is a sample. The text is placeholder text, the organisation is invented and nothing on the site is medical advice. It has no real course, price, accreditation or requirement. Six pages are built from a 14 row content map. The keyword research behind the map counts autocomplete suggestions and is not search volume. The site has no traffic history and no search ranking, and I make no claim about either. It runs on the free plan, so WordPress.com controls the banner and the hosting.

## Files in `docs/launched-site/`

`01` to `07` screenshots, `seo_audit_home.txt`, `seo_audit_inner_acls.txt` and four more `seo_audit_inner_*.txt` files, `checks_links_sitemap_head.txt`, `editor_edit_readback.txt`.

# QA defect report: two public sample sites, desktop and phone

Tested on 2026-11-10 by loading the live sites in headless Chromium (Playwright), the way a client's staff would open them: first at 1280 by 900 on desktop, then at 390 by 844 on a phone with touch and a mobile screen. Every screenshot named below is in [qa-defect-report/](qa-defect-report/). Nothing was fixed in this task. This is the report.

## Summary

| Site | Pages opened | Viewports |
|---|---|---|
| Emergency Care Guide (WordPress.com sample), https://emergencycaretrainingguidesample.wordpress.com/ | all 6 pages, the search results page and the 404 page | 1280 desktop, 390 phone |
| Seabreeze Roofing and Solar (sample), https://seabreeze-roofing-lab.pages.dev | all 34 pages reachable by links from the home page, at 390 only, plus the home page at 1280 | 390 phone, home page at 1280 |

Defects found: 9 in total, all reproduced more than once. None is a blocker or a major.

| Severity | Count | Ids |
|---|---|---|
| Blocker | 0 | |
| Major | 0 | |
| Minor | 6 | QA-01, QA-02, QA-03, QA-04, QA-05, QA-06 |
| Cosmetic | 3 | QA-07, QA-08, QA-09 |

Severity scale used here. Blocker: a visitor cannot finish the main task. Major: the main task works but a common path is broken or misleading. Minor: a visitor can finish, but meets a rough edge, a wrong statement or a missing cue. Cosmetic: looks or reads inconsistent, no task is affected.

Both sites are samples with placeholder text, so a missing price or course detail is not counted as a defect. The report only counts things that are wrong for the site as it is meant to work.

One limit of the test method, not a defect of the site. When the phone run sent a mobile browser identity string (an iPhone or an Android Chrome string) from headless Chromium, WordPress.com answered every page with a "Checking your browser" page and then a "Confirm you are human" checkbox (HTTP 403). I did not click it or work around it. The same pages loaded normally with a 390 wide touch screen and the browser's own identity string, and that is what the phone results below use. A real phone is not expected to see the check, but I could not test that here.

## Defects

### QA-01: Search results print every matching page in full

Severity: minor. The search finds the right pages, but the results page is a very long scroll with no short summaries, so a visitor cannot scan it.

Page: search results, `/?s=ACLS`. Viewport: phone 390 (also desktop 1280).

Steps to reproduce:
1. Open https://emergencycaretrainingguidesample.wordpress.com/no-such-page/ (or any page with the search box).
2. Type `ACLS` in the search box and press Enter.
3. Scroll the results page.

Expected: a short list. Each result is a title with one or two lines of description, as the page excerpts already written for each page.

Actual: the page returns all six pages, each printed in full, with its navy hero, every section and the footer notice. The results page is 16,225 px tall on the phone and 11,965 px on desktop, about 1,294 words. A search for `ACLS` also lists pages that only mention it in passing.

Evidence: `qa-01-search-results-full-pages-phone.png` shows the first screen: the result title is followed directly by the whole navy page hero.

Suggested fix: make the search results template show the excerpt instead of the full content.

### QA-02: The 404 page is the theme default, with a stock photo, and the search box falls below the first screen

Severity: minor. A visitor who mistypes an address gets a page that does not look like the site, and on a phone the only way out (the search box) is not in view.

Page: any missing address, for example `/no-such-page/`. Viewports: desktop 1280 and phone 390.

Steps to reproduce:
1. Open https://emergencycaretrainingguidesample.wordpress.com/no-such-page/ on a phone.
2. Look at the first screen without scrolling.

Expected: the page looks like the other six pages and shows the message and a way back (the menu, a link home or the search box) in the first screen.

Actual: a black and white stock photograph of a tree (alt text "Small totara tree on ridge above Long Point", 330 by 423 px on the phone) fills the screen. The heading "Page not found" starts at 673 px down, the message runs to the bottom edge, and the search box is below the fold (the first screen is 844 px). On desktop the photograph is 560 px wide and the heading starts about 700 px down, so the search box is at the bottom edge of a 900 px screen. The heading and button styles here are the theme default, not the bold type used on the six built pages. The menu at the top works.

Evidence: `qa-02-404-phone.png` and `qa-02-404-desktop.png`.

Suggested fix: edit the 404 template to remove the photograph and use the same hero and spacing as the inner pages, with a "Back to the home page" button.

### QA-03: The menu does not show which page you are on

Severity: minor. A visitor cannot tell from the menu where they are, which matters most on the phone menu, where the list covers the page.

Page: every page. Viewports: desktop 1280 and phone 390.

Steps to reproduce:
1. Open https://emergencycaretrainingguidesample.wordpress.com/cme-requirements/ on desktop.
2. Look at the header menu. On the phone, tap Menu and look at the list.

Expected: the item for the current page looks different (weight, colour, underline or marker).

Actual: all six items have the same colour (rgb 20, 36, 58), weight (600), no underline and no marker. The code marks the current item for screen readers (`aria-current="page"` is set on CME requirements), but nothing is drawn for sighted visitors. The phone list is the same.

Evidence: `qa-03-menu-current-page-desktop.png` (the current page item is boxed in red, it looks like the others).

Suggested fix: style the menu item that has `aria-current="page"` with an underline or a bold weight.

### QA-04: The CME requirements page says a topic is on the questions page, but it is not

Severity: minor. The page makes a statement that is wrong, and the link next to it sends a visitor to look for an answer that does not exist.

Page: `/cme-requirements/`, section "Questions people ask". Viewport: desktop 1280 (same text on phone).

Steps to reproduce:
1. Open https://emergencycaretrainingguidesample.wordpress.com/cme-requirements/ and find "Questions people ask".
2. Read the text: "How much CME per year and CME eligibility criteria are common searches. They are listed on the questions page with placeholder answers."
3. Click the link "questions page" and open the "CME questions (2)" group.

Expected: both topics are listed on the questions page.

Actual: the questions page lists only "What are CME requirements?" and "How much CME per year?". "CME eligibility criteria" is not there, in any group. A search of the page text for "eligib" finds nothing.

Evidence: `qa-04-cme-claim-vs-questions-page.png` (the sentence above, and the complete CME group below).

Suggested fix: add a question about CME eligibility criteria to the questions page, or remove it from the sentence.

### QA-05: The About page points to "the repository" with no link

Severity: minor. The page says where the proof is, and gives the visitor no way to get there.

Page: `/about-this-sample/`, section "Where the plan came from". Viewport: desktop 1280 (same on phone).

Steps to reproduce:
1. Open https://emergencycaretrainingguidesample.wordpress.com/about-this-sample/.
2. Read "The scripts and the recorded run are in the repository that holds this sample."
3. Try to click anything in that sentence, then check the page links.

Expected: the sentence links to the repository.

Actual: the sentence is plain text. No link on the page goes to GitHub or any repository (the page has links to the other five pages and the WordPress.com banner only).

Evidence: `qa-05-about-repository-no-link.png`.

Suggested fix: link the words "the repository" to https://github.com/Exalt24/wordpress-elementor-lab.

### QA-06: Two page titles are too long for a search result

Severity: minor. In a browser tab and in search results the title is cut off, and the cut falls inside the page name.

Pages: `/cme-requirements/` and `/ultrasound-courses/`. Viewport: both (the title does not depend on width).

Steps to reproduce:
1. Open each page and read the `<title>` text (browser tab, or `document.title` in the console).
2. Count the characters.

Expected: 60 characters or fewer, so a search result shows the whole title.

Actual, measured with `document.title.length`:

```
60  Emergency Care Guide (sample site) – A portfolio sample site
64  ACLS Recertification Online – Emergency Care Guide (sample site)
68  CME Requirements for Physicians – Emergency Care Guide (sample site)
80  Ultrasound Courses for Emergency Physicians – Emergency Care Guide (sample site)
46  Questions – Emergency Care Guide (sample site)
54  About This Sample – Emergency Care Guide (sample site)
```

The CME page is 68 and the ultrasound page is 80. WordPress adds the site title (34 characters with the separator) to every page title. The existing notes in [launched-site.md](launched-site.md) already list this, and it reproduces today. A title cannot be shown as a screenshot, so there is no image for this one.

Suggested fix: shorten the site title, for example to "Emergency Care Guide", which brings all six titles to 60 characters or fewer except the ultrasound page, which then also needs a shorter page title.

### QA-07: The menu and the footer name the same pages differently

Severity: cosmetic. Nothing is broken, but the same page has two names.

Page: every page. Viewport: desktop 1280 and phone 390.

Steps to reproduce:
1. Open the home page and read the header menu, then scroll to the footer.
2. Compare the labels, then open each page and read its heading.

Expected: one name per page.

Actual: the header says "About" and the footer says "About this sample" for the same page. The header says "ACLS recertification", the footer says "ACLS recertification online" and the page heading says "ACLS Recertification Online". Capitalisation also differs: the front page heading is "Emergency medicine CME: a sample guide" and its section headings are in sentence case, while the inner page headings are in title case ("CME Requirements for Physicians", "Ultrasound Courses for Emergency Physicians").

Evidence: `qa-07-nav-and-footer-labels-desktop.png`.

Suggested fix: pick one label per page and one capitalisation style, and use it in the menu, the footer and the headings.

### QA-08: Two WordPress.com controls are under 44 px on the phone

Severity: cosmetic. They are small, but they belong to the free plan and are not page content.

Page: every page. Viewport: phone 390.

Steps to reproduce:
1. Open any page on the phone.
2. Measure the "Start free" button in the blue banner and the "More options" button at the right edge (browser developer tools, or `getBoundingClientRect()`).

Expected: touch targets of at least 44 by 44 px.

Actual: "Start free" is 78 by 30 px on the phone (81 by 36 on desktop). "More options" is 32 by 26 px. Both are added by WordPress.com on the free plan. Every control the site's own pages add, the menu, the question rows, the buttons and the footer links, is 44 px high or more (see the clean list below). The same two controls were found by the earlier design pass, which listed them as not page content. They are reported here because a phone visitor still sees and taps them.

Evidence: `qa-08-wordpress-widgets-small-targets-phone.png` (both boxed in red).

Suggested fix: none on the free plan. A paid plan removes the banner.

### QA-09: Seabreeze link chips are 32 px tall on the phone

Severity: cosmetic. They are tappable, and the gaps between them are 6 px, so a thumb can hit the neighbour.

Site: https://seabreeze-roofing-lab.pages.dev. Page: home and 16 other pages (17 pages in all). Viewport: phone 390.

Steps to reproduce:
1. Open https://seabreeze-roofing-lab.pages.dev/ on a phone and scroll to "What we do".
2. Measure the service chips ("Asphalt shingle roofing", "Skylights" and the other five).

Expected: at least 44 px high.

Actual: all seven are 32 px high with 6 px between rows. The same 32 px chips are the neighbourhood list on `/areas/` (Ambleside, British Properties, Caulfeild, Dundarave), the service and material chips and the "More work in" link on all 11 project pages, and the service chips on all four area pages. The chip list on `/services/` is 41 px high, also under 44. The main controls (header links, buttons, phone number, email, privacy) are 44 px or more.

Evidence: `qa-09-seabreeze-link-chips-phone.png`.

Suggested fix: raise the chip height to 44 px with `min-height`, or add vertical padding.

## What was checked and found clean

Emergency Care Guide (6 pages at 1280 and at 390):

1. Every page answers 200 on first load at both widths, with one h1, headings in order (h1, then h2, then h3, no skipped level), `lang="en"` and a meta description.
2. All 131 visible links on the six desktop pages (about 22 per page) were listed with label and address and checked against the label. Every one points where its label says: the six pages, the jump links on the questions page, and the WordPress.com "Start free" banner link, which I did not follow. The three jump links on the questions page were clicked and each landed on its group heading. The six menu pages and the home page buttons ("ACLS recertification online", "Read the questions", the three "Open the ... page" buttons, "Go to the questions") were loaded by address, all 200.
3. No sideways scroll at 390 on any page (`scrollWidth` 390, window 390). Nothing is cut or overflows on the phone. The only element wider than the window is the hidden "Skip to content" link, which is off screen on purpose.
4. Images: the pages have no content images. The two image elements are a 6 px tracking pixel and an empty placeholder, both with empty alt text, which is correct for decoration. The 404 photograph has alt text.
5. Console and network: no console errors or warnings and no failed or 4xx or 5xx requests on any of the six pages at either width, other than the human check noted in the Summary.
6. Phone menu: the "Menu" button (308 by 45 px) opens and closes with a tap and shows six links, each 45 px high. The desktop menu shows all six links on one row.
7. Questions page: 12 questions in three groups, matching the counts on the jump buttons (9, 2, 1). Every row opens on a tap, rows are 45 px high (90 px when the question wraps to two lines). Ten answers link to the matching page, and two answers (cost, becoming a physician) have no link and say so in plain words.
8. Keyboard: the first Tab stop is "Skip to content", then the site title and menu in order, each with a visible 2 px outline.
9. Tap targets on the phone: every link and button from the site's own pages is 44 px high or more, apart from links inside a sentence. The exceptions are the two WordPress.com controls in QA-08.
10. Web address handling: `http://` redirects to `https://`, a missing trailing slash (`/cme-requirements`) redirects to the slash address, `/acls-recertification/` redirects to the ACLS page, the deleted `/hello-world/` and an invented address return a real 404.
11. The search works on both widths and finds the right pages (see QA-01 for how it prints them).
12. The text on all six pages was read against what it promises. Apart from QA-04 and QA-05 it matches: the notices say placeholder text, invented organisation, no medical advice, and the pages say the same on every page.

Seabreeze Roofing and Solar (34 pages at 390, home at 1280):

1. All 34 pages reached by following links from the home page answer 200 with one h1 each. There are no console errors and no failed requests.
2. No sideways scroll at 390 on any of the 34 pages, and none at 1280 on the home page.
3. Every image on every page has alt text (0 images without an alt attribute).
4. Header links, buttons, the phone number and the email are 44 px or more. The only external link is Google's partner sites policy, the contact method links are `tel:` and `mailto:` (the email domain is the reserved `.example`).
5. The quote form at `/contact/` is plainly labelled as not connected: the page says that nothing typed is sent or stored, and the submit button reads "Not connected in this sample" and has the `disabled` attribute. I did not treat that as a defect, since it is stated on the page. I did not submit it. All visible fields have labels, the two consent checkboxes have long labels that are tappable, and the spam trap field is placed off screen and out of the tab order.

Not tested: the form's real submission (it has none), the WordPress.com "Start free" page, the WordPress.com login, screen reader speech, any browser other than Chromium, and any width other than 1280 and 390.

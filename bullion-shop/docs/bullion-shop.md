# The bullion shop lab

A local WooCommerce shop with twelve invented gold and silver products, priced live from a stand-in metals feed. It is built to answer one question: what does a live price cost a page, and what does it take to make that cost small and safe.

Everything runs in Docker on one machine. The feed is a small Python server that serves made-up prices (`scripts/spot_server.py`), so there is no vendor account or key anywhere. The products, the brand "Ledger Mint" and the prices are invented. It is a lab, not a client store, and none of it has been under real traffic.

## What is in it

| Part | What it does |
|---|---|
| `docker-compose.yml`, `scripts/setup.sh` | WordPress 7, MariaDB 11, WooCommerce and the Storefront theme, the stand-in price feed, a Lighthouse container on the same network |
| `mu-plugins/bullion-lab.php` | The only file that touches WordPress. It connects the rules below to WooCommerce prices, a shortcode, a REST route, Product, Organization and FAQ markup, a feed, the lean assets and the hardening |
| `mu-plugins/bullion-lab/lib/` | The rules, with no WordPress in them: `spot.php` (cache, stale limit, bad readings), `pricing.php` (pence arithmetic), `schema.php`, `feed.php`, `limiter.php` (login limits), `ratelimit.php` (search and REST limits), `firewall.php` (probes for secrets and attack tool agents), `assets.php` (the lean asset rules), `headers.php` |
| `scripts/spot_server.py` | The stand-in feed. It can fail, answer with garbage, triple the gold price or answer after five seconds, on request, and it counts the calls it gets |
| `scripts/seed.php`, `scripts/make_images.py` | Twelve products (gold and silver bars and coins) with drawn pictures, two categories and a front page |
| `scripts/hardening_check.py` | Probes a running site the way a scanner would: 13 checks |
| `scripts/schema_check.py` | Checks the Product and Offer markup against the price printed on the page: 7 checks |
| `scripts/measure_pages.py`, `scripts/run_lighthouse.sh`, `scripts/lh_summary.py` | Page timings, the feed calls each page costs, and Lighthouse (mobile, performance) in a container |
| `scripts/live_checks.py` | Drives the running shop through the feed's bad days and checks the home page markup: 14 checks |
| `scripts/run_lab.sh` | One run, start to finish, that writes everything under `docs/` |
| `tests/test_logic.php`, `tests/test_scripts.py` | 85 PHP and 32 Python checks, offline |

## How a price gets to the page

A product stores its metal, the troy ounces it holds and a premium over spot. The price is not stored: it is computed when WooCommerce reads it, as spot per ounce times the ounces times one plus the premium, in whole pence. The same price feeds the page, the cart, the JSON-LD and the Merchant Center feed, so they cannot disagree.

The spot price comes from one saved reading. A reading younger than the TTL (10 seconds in the lab) is used as it is. An older one is replaced by a call to the feed, made by one request at a time (an atomic option lock), with a 2 second timeout. If the call fails, or the reply is not two positive numbers, or gold or silver moved more than 15 percent from the last good reading, the last good price is kept and the page says so. If the last good reading is older than the stale limit (40 seconds in the lab), the shop shows no price at all: the product page says the price is unavailable, there is no add to cart button, the JSON-LD has no Offer and the Merchant Center feed leaves the product out. A wrong price is never shown. The TTL and the limit are environment settings; a real shop would use longer ones.

A small script refreshes the shortcode `[spot_price metal="gold"]` every TTL seconds from `/wp-json/bullion/v1/spot`, which answers from the same saved reading with `Cache-Control: public, max-age=10`.

## Measured results

All numbers come from `bash bullion-shop/scripts/run_lab.sh` on one laptop, Docker Desktop, the stand-in feed answering after 150 ms. The same shop is measured in three states:

* **before**: the price integration written the obvious way (a feed call each time a price is read for a product, nothing saved), the theme's stock styles and scripts, and none of the hardening.
* **cache**: one saved reading for the prices. Nothing else changed.
* **after**: the saved reading, the hardening and the lean assets.

Raw outputs: `pages_*.txt`, `lighthouse_*.txt` and `hardening_*.txt` for each state.

### What a page costs the server

Median of 6 loads after a warm-up load. The feed count is the stand-in server's own counter.

| Page | Time to first byte, before | cache | Feed calls in 6 loads, before | cache |
|---|---|---|---|---|
| Home (a shortcode and 8 products) | 1.49 s | 0.08 s | 54 | 0 |
| Shop (12 products) | 1.92 s | 0.07 s | 72 | 0 |
| One product (with related products) | 0.70 s | 0.07 s | 24 | 0 |

### Lighthouse, mobile, the shop page, three runs each

| | before | cache | after |
|---|---|---|---|
| Performance score, each run | 89, 88, 89 | 91, 91, 91 | 99, 98, 98 |
| Server response time, median | 1969 ms | 233 ms | 245 ms |
| First Contentful Paint, median | 2.3 s | 2.3 s | 1.2 s |
| Largest Contentful Paint, median | 3.2 s | 3.2 s | 2.3 s |
| Speed Index, median | 4.0 s | 2.3 s | 1.2 s |
| Total Blocking Time, median | 0 ms | 0 ms | 0 ms |
| Cumulative Layout Shift, median | 0.000 | 0.000 | 0.038 |

Two different fixes, two different results, and the table keeps them apart. The saved reading removes the server wait: the server response time falls and the Speed Index with it, but the paint times are set by the theme's own render blocking files, so the score barely moves and the Largest Contentful Paint stays above 2.5 seconds. The lean assets are what move the paint times. Lighthouse named the blockers: Google Fonts (another origin to reach before the first paint), block styles and brand styles a shop page does not use, the jQuery Migrate shim, an icon font stylesheet of 15 KB that is 97 percent unused, and jQuery in the head. The plugin drops the first three, prints the icon stylesheet without blocking (with a noscript fallback) and moves jQuery to the footer. After that the Largest Contentful Paint is under the 2.5 second line Google calls good and the layout shift under 0.1. This is Lighthouse's simulated mobile throttling on a lab page, not field data from real visitors, which a lab does not have.

A check after the change: no console errors on the shop page, a product page and the home page (Lighthouse best practices), and an add to cart request through WooCommerce's AJAX route answers with the mini cart.

### Hardening, 13 probes from outside

| | before | after |
|---|---|---|
| Probes passed | 1 of 13 | 13 of 13 |

Before, the probes find: no security headers, a generator tag in the page, XML-RPC answering 200, scanner probes for `/.env`, a backup file and an attack tool agent getting a 404 or a 200 instead of a 403, the users list open at `/wp-json/wp/v2/users`, `?author=1` redirecting to `/author/admin/` (a login name), 45 quick searches never meeting a 429, the dashboard code editor open, and a correct password accepted after five wrong ones. After, each is closed. The login check is the strict one: five wrong passwords, then the correct password, which must still be refused while the address is locked. The search limit is 30 a minute and the REST limit 120, per connection address, and only search and REST are counted, so a customer or a search engine crawling products, the sitemap or robots.txt is never limited.

### The feed's bad days (`live_checks.txt`, 14 of 14)

Six page loads in ten seconds cost the feed one call. With the feed down, the page keeps the last good price marked stale and answers in well under a second. Past the stale limit there is no price, no button, no Offer and no feed line, and a recovered feed brings them back. A feed that triples the gold price or answers with a maintenance page never reaches a customer. A feed that answers after five seconds costs a page about 2.4 s, because the call is cut at 2 seconds.

### Product, Organization and FAQ markup (`schema_check.txt`, 7 of 7)

WooCommerce writes its own Product markup, with an `Offer` whose `priceValidUntil` is the end of the year. That is wrong for a price that changes every few seconds, so the plugin replaces the Offer: the same price as the page, the availability from stock, `priceValidUntil` set to the moment the saved reading expires, and no Offer at all when there is no trusted price. The check compares the offered price with a price printed on the page. The home page also carries Organization and FAQPage markup, and the questions in the markup are the ones printed on the page. WooCommerce already writes BreadcrumbList.

## Tests

```
php bullion-shop/tests/test_logic.php        85 checks on the rules
python bullion-shop/tests/test_scripts.py    32 checks: the feed, the hardening probe, the markup check
python tests/mutation_check.py               breaks one guard at a time and needs a test to go red
```

The PHP test needs no WordPress. The probe tests feed each probe a fake site with exactly one defect and expect exactly that probe to fail. The mutation run covers the older code and the bullion shop: 79 of 79 breaks caught. Its first run on the new code left two alive (the probe for author names could be fooled by either of two signals, and a login that logged in while printing the lock message passed), and each got a test.

## Limits

* It is a local lab with invented products and invented prices from a stand-in feed. It has not been tried against a real metals vendor, a real payment gateway or real traffic, and it is not a client store.
* There is no page cache. On a real shop a page cache would sit in front, and live prices would be refreshed by the REST route and the script, which is why that route exists and is cacheable.
* The stand-in feed answers in 150 ms. A real feed's latency and failure pattern will differ.
* The TTL (10 seconds) and the stale limit (40 seconds) are short on purpose, so the checks run in minutes.
* The Lighthouse numbers are three runs each on one theme (Storefront), in simulated mobile throttling. They are lab figures, not field data, and a different theme or a real product catalogue with photographs will paint differently.
* The hardening covers what a plugin can do from inside WordPress. Files Apache serves directly (`readme.html`, `license.txt`), a firewall in front of the site, bot management by reputation, backups and a content security policy are server level jobs and are not done here. HSTS is only sent over HTTPS, and the lab runs over plain HTTP.
* The login and request limits count per connection address. Behind a proxy every visitor shares one address unless the proxy's address is passed on properly, which this lab does not set up.
* Conversion rate, revenue and rankings are not measured, because there is no traffic to measure them on.

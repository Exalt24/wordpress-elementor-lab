<?php
/**
 * Offline tests for the bullion shop rules: live price caching and fallback, pricing, Product and Offer markup, the Merchant feed, login limits and headers.
 * Plain PHP, no WordPress and no network.   php bullion-shop/tests/test_logic.php
 * Every rule is checked on a good input and on a hostile or broken one.
 */
$lib = __DIR__ . '/../mu-plugins/bullion-lab/lib/';
foreach (['spot', 'pricing', 'schema', 'feed', 'limiter', 'headers', 'ratelimit', 'assets', 'firewall'] as $f) {
    require $lib . $f . '.php';
}

use Bullion\Assets;
use Bullion\Feed;
use Bullion\Firewall;
use Bullion\Headers;
use Bullion\Limiter;
use Bullion\Pricing;
use Bullion\RateLimit;
use Bullion\Schema;
use Bullion\Spot;

$failed = 0;
function check(string $name, bool $ok, string $detail = ''): void
{
    global $failed;
    echo ($ok ? 'PASS  ' : 'FAIL  ') . $name . ($ok ? '' : '   <- ' . $detail) . "\n";
    $failed += $ok ? 0 : 1;
}

$good = '{"currency":"GBP","gold":1650.5,"silver":21.4}';
$calls = 0;
$feedOk = function () use ($good, &$calls) { $calls++; return $good; };
$feedDown = function () use (&$calls) { $calls++; return null; };
$feedThrows = function () use (&$calls) { $calls++; throw new RuntimeException('timeout'); };
$last = ['prices' => ['gold' => 1650.0, 'silver' => 21.5], 'fetched_at' => 1000];

// parse
check('parse: a good reply gives both prices', Spot::parse($good) === ['gold' => 1650.5, 'silver' => 21.4]);
check('parse: not JSON is refused', Spot::parse('<html>maintenance</html>') === null);
check('parse: a missing metal is refused', Spot::parse('{"gold":1650.5}') === null);
check('parse: zero is refused', Spot::parse('{"gold":0,"silver":21.4}') === null);
check('parse: a negative price is refused', Spot::parse('{"gold":-5,"silver":21.4}') === null);
check('parse: a string price is refused', Spot::parse('{"gold":"1650","silver":21.4}') === null);
check('parse: null is refused', Spot::parse(null) === null);

// sane
check('sane: the first reading is accepted', Spot::sane(['gold' => 1650.0, 'silver' => 21.5], null));
check('sane: a 2 percent move is accepted', Spot::sane(['gold' => 1683.0, 'silver' => 21.5], $last));
check('sane: a 3x gold reading is refused', !Spot::sane(['gold' => 4950.0, 'silver' => 21.5], $last));
check('sane: a 50 percent silver drop is refused', !Spot::sane(['gold' => 1650.0, 'silver' => 10.7], $last));

// resolve
$calls = 0;
$r = Spot::resolve($feedOk, $last, 1005, 10, 40);
check('resolve: a reading inside the TTL is used with no feed call', $r['state'] === 'fresh' && $calls === 0 && !$r['fetched'] && $r['save'] === null);
$r = Spot::resolve($feedOk, $last, 1010, 10, 40);
check('resolve: at the TTL the feed is called and the new reading saved', $r['state'] === 'fresh' && $calls === 1 && $r['save']['fetched_at'] === 1010 && $r['prices']['gold'] === 1650.5);
$calls = 0;
$r = Spot::resolve($feedDown, $last, 1020, 10, 40);
check('resolve: a feed that is down gives the last good price, marked stale', $r['state'] === 'stale' && $r['prices']['gold'] === 1650.0 && $r['as_of'] === 1000 && $r['save'] === null);
$r = Spot::resolve($feedThrows, $last, 1020, 10, 40);
check('resolve: a feed that throws is the same as down', $r['state'] === 'stale');
$r = Spot::resolve($feedDown, $last, 1040, 10, 40);
check('resolve: stale is allowed up to the limit (40 seconds old)', $r['state'] === 'stale');
$r = Spot::resolve($feedDown, $last, 1041, 10, 40);
check('resolve: past the limit there is no price at all, never an old one', $r['state'] === 'unavailable' && $r['prices'] === null);
$r = Spot::resolve($feedDown, null, 1000, 10, 40);
check('resolve: no saved reading and no feed is unavailable', $r['state'] === 'unavailable');
$wild = function () { return '{"gold":4950,"silver":21.5}'; };
$r = Spot::resolve($wild, $last, 1020, 10, 40);
check('resolve: a reading that jumped 3x is not saved, the last good one stays', $r['state'] === 'stale' && $r['save'] === null && $r['prices']['gold'] === 1650.0);
$garbage = function () { return '<html>x</html>'; };
$r = Spot::resolve($garbage, $last, 1020, 10, 40);
check('resolve: a garbage reply is not saved', $r['state'] === 'stale' && $r['save'] === null);
$calls = 0;
$r = Spot::resolve($feedOk, $last, 1020, 10, 40, false);
check('resolve: a request that cannot take the fetch lock makes no feed call', $calls === 0 && $r['state'] === 'stale' && !$r['fetched']);
$r = Spot::resolve($feedOk, null, 1000, 10, 40, false);
check('resolve: with no lock and nothing saved there is no price', $r['state'] === 'unavailable');

// pricing
check('pricing: 1 oz at 1650.50 with 3.5 percent premium is 170827 pence', Pricing::sellPence(1650.5, 1.0, 3.5) === 170827, (string) Pricing::sellPence(1650.5, 1.0, 3.5));
check('pricing: a 100 oz silver bar rounds once, in pence', Pricing::sellPence(21.4, 100.0, 4.5) === 223630, (string) Pricing::sellPence(21.4, 100.0, 4.5));
check('pricing: buy back is below the metal value', Pricing::buyPence(1650.0, 1.0, 3.0) === 160050);
check('pricing: buy back never goes below zero', Pricing::buyPence(1650.0, 1.0, 150.0) === 0);
check('pricing: format has a pound sign, a thousands comma and two decimals', Pricing::format(170826) === '£1,708.26', Pricing::format(170826));

// schema
$p = ['name' => 'Bar </script><script>alert(1)</script>', 'sku' => 'GB1', 'description' => 'd', 'url' => 'http://x/p/', 'image' => 'http://x/i.png', 'pence' => 170826, 'currency' => 'GBP', 'in_stock' => true, 'as_of' => 1700000000];
$n = Schema::product($p, 10);
check('schema: a Product with an Offer carrying price, currency, availability and condition', $n['@type'] === 'Product' && $n['offers']['price'] === '1708.26' && $n['offers']['priceCurrency'] === 'GBP' && $n['offers']['availability'] === 'https://schema.org/InStock' && $n['offers']['itemCondition'] === 'https://schema.org/NewCondition');
check('schema: the price is valid until the cache expires, not the end of the year', $n['offers']['priceValidUntil'] === gmdate('Y-m-d\TH:i:s\Z', 1700000010), $n['offers']['priceValidUntil']);
$o = Schema::product(['in_stock' => false] + $p, 10);
check('schema: out of stock reads OutOfStock', $o['offers']['availability'] === 'https://schema.org/OutOfStock');
$u = Schema::product(['pence' => null, 'as_of' => null] + $p, 10);
check('schema: with no trusted price there is no Offer at all', !isset($u['offers']));
$tag = Schema::script($n);
check('schema: a hostile product name cannot close the script tag', substr_count($tag, '</script>') === 1 && !str_contains($tag, '<script>alert'), $tag);
preg_match('#<script type="application/ld\+json">(.*)</script>#s', $tag, $m);
check('schema: the output parses and keeps the name', (json_decode($m[1] ?? '', true)['name'] ?? '') === $p['name']);

// faq and organization
$faq = Schema::faq([['Q one?', 'A one.'], ['', 'orphan answer'], ['orphan question', ' '], ['Q two?', 'A two.']]);
check('faq: FAQPage with the pairs that have both parts', $faq['@type'] === 'FAQPage' && count($faq['mainEntity']) === 2 && $faq['mainEntity'][1]['name'] === 'Q two?' && $faq['mainEntity'][0]['acceptedAnswer']['text'] === 'A one.');
check('faq: no usable pair means no markup at all', Schema::faq([]) === null && Schema::faq([['', ''], ['q', '']]) === null);
$faqTag = Schema::script(Schema::faq([['Is </script><script>alert(1)</script> safe?', 'yes']]));
check('faq: a hostile question cannot close the script tag', substr_count($faqTag, '</script>') === 1);
$org = Schema::organization('Ledger Mint Lab', 'http://x/');
check('organization: name and url, and no logo key unless a logo is given', $org['@type'] === 'Organization' && $org['name'] === 'Ledger Mint Lab' && !isset($org['logo']) && Schema::organization('n', 'u', 'http://x/l.png')['logo'] === 'http://x/l.png');

// feed
$items = [
    ['id' => 'GB1', 'title' => 'Bar & "coin"', 'description' => 'd', 'link' => 'http://x/p/?a=1&b=2', 'image' => 'http://x/i.png', 'pence' => 170826, 'currency' => 'GBP', 'in_stock' => true],
    ['id' => 'GB2', 'title' => 'No price', 'description' => 'd', 'link' => 'http://x/q/', 'image' => '', 'pence' => null, 'currency' => 'GBP', 'in_stock' => true],
    ['id' => 'GB3', 'title' => 'Sold out', 'description' => 'd', 'link' => 'http://x/r/', 'image' => '', 'pence' => 500, 'currency' => 'GBP', 'in_stock' => false],
];
$xml = Feed::merchant($items, 'Shop & Co', 'http://x/');
$dom = new DOMDocument();
check('feed: the output is well formed XML with ampersands and quotes in titles', @$dom->loadXML($xml));
check('feed: an item with no trusted price is left out', substr_count($xml, '<item>') === 2 && !str_contains($xml, 'GB2'));
check('feed: the price carries two decimals and the currency', str_contains($xml, '<g:price>1708.26 GBP</g:price>') && str_contains($xml, '<g:price>5.00 GBP</g:price>'));
check('feed: stock is mapped to the Merchant Center words', str_contains($xml, '<g:availability>in stock</g:availability>') && str_contains($xml, '<g:availability>out of stock</g:availability>'));
check('feed: a link with an ampersand is escaped', str_contains($xml, 'a=1&amp;b=2'));

// limiter
$rec = null;
for ($i = 0; $i < 4; $i++) {
    $rec = Limiter::recordFail($rec, 1000 + $i);
}
check('limiter: four failures do not lock', !Limiter::isLocked($rec, 1004));
$rec = Limiter::recordFail($rec, 1004);
check('limiter: the fifth failure locks', Limiter::isLocked($rec, 1005) && Limiter::secondsLeft($rec, 1005) === 899);
check('limiter: the lock ends after 15 minutes', !Limiter::isLocked($rec, 1004 + 900));
$old = null;
for ($i = 0; $i < 4; $i++) {
    $old = Limiter::recordFail($old, 1000 + $i);
}
$old = Limiter::recordFail($old, 1000 + 901);
check('limiter: failures older than the window are forgotten', !Limiter::isLocked($old, 1902));
check('limiter: no record is not locked', !Limiter::isLocked(null, 1000));
check('limiter: the caller is its connection address', Limiter::key(['REMOTE_ADDR' => '10.0.0.5']) === '10.0.0.5');
check('limiter: a forged forwarding header does not change the key', Limiter::key(['REMOTE_ADDR' => '10.0.0.5', 'HTTP_X_FORWARDED_FOR' => '1.2.3.4']) === '10.0.0.5');

// rate limit
check('rate limit: search and the REST API are limited kinds', RateLimit::bucket('/', ['s' => 'gold']) === 'search' && RateLimit::bucket('/wp-json/wp/v2/posts', []) === 'rest' && RateLimit::bucket('/index.php', ['rest_route' => '/x']) === 'rest');
check('rate limit: ordinary pages, the sitemap and robots.txt are never limited', RateLimit::bucket('/shop/', []) === null && RateLimit::bucket('/sitemap.xml', []) === null && RateLimit::bucket('/robots.txt', []) === null && RateLimit::bucket('/product/gold-bar-1oz/', ['page' => '2']) === null);
$rl = null;
$allowed = 0;
for ($i = 0; $i < 30; $i++) {
    [$ok, $rl] = RateLimit::hit($rl, 1000 + $i, 'search');
    $allowed += $ok ? 1 : 0;
}
check('rate limit: 30 search requests in a minute are allowed', $allowed === 30, (string) $allowed);
[$ok31, $rl] = RateLimit::hit($rl, 1030, 'search');
check('rate limit: the 31st is refused', !$ok31);
[$okStill, $rl] = RateLimit::hit($rl, 1059, 'search');
check('rate limit: it stays refused until the window ends', !$okStill && RateLimit::retryAfter($rl, 1059) === 1);
[$okNext, $rl] = RateLimit::hit($rl, 1060, 'search');
check('rate limit: the next window starts clean', $okNext && $rl['count'] === 1);
$rest = null;
for ($i = 0; $i < 120; $i++) {
    [$okRest, $rest] = RateLimit::hit($rest, 2000, 'rest');
}
[$okRest121, $rest] = RateLimit::hit($rest, 2000, 'rest');
check('rate limit: the REST API allows 120 a minute and refuses the 121st', $okRest && !$okRest121);
check('rate limit: Retry-After is never below one second', RateLimit::retryAfter(['start' => 0, 'count' => 99], 500) === 1);

// firewall
foreach (['/.env', '/.git/config', '/wp-config.php.bak', '/backup.sql', '/site.zip', '/debug.log', '/phpinfo.php', '/shell.php', '/wp-content/uploads/2026/11/x.php'] as $bad) {
    check('firewall: ' . $bad . ' is refused', Firewall::reason($bad, 'Mozilla/5.0') === 'path');
}
check('firewall: upper case and percent encoding do not get past it', Firewall::reason('/.ENV', 'x') === 'path' && Firewall::reason('/%2eenv', 'x') === 'path' && Firewall::reason('/WP-CONFIG.PHP.BAK', 'x') === 'path');
foreach (['/', '/shop/', '/product/gold-bar-1oz/', '/sitemap.xml', '/robots.txt', '/wp-login.php', '/wp-json/bullion/v1/spot', '/category/environment/', '/en/envelope/'] as $good) {
    check('firewall: ' . $good . ' is let through', Firewall::reason($good, 'Mozilla/5.0 (compatible; Googlebot/2.1)') === null);
}
check('firewall: an attack tool is named by its user agent', Firewall::reason('/', 'sqlmap/1.7.2#stable') === 'agent' && Firewall::reason('/', 'Mozilla/5.00 (Nikto/2.1.6)') === 'agent');
check('firewall: an ordinary and an empty user agent pass', Firewall::reason('/', '') === null && Firewall::reason('/', 'Mozilla/5.0 (Windows NT 10.0) Chrome/120') === null);

// lean assets
$tag = "<link rel='stylesheet' id='storefront-icons-css' href='http://x/icons.css?ver=4.6.2' media='all' />\n";
$async = Assets::nonBlockingStyle($tag);
check('assets: a stylesheet tag starts as print media and switches to all when loaded', str_contains($async, "media='print' onload=\"this.media='all'\""));
check('assets: it keeps one media attribute and a noscript copy of the original', preg_match_all('/\smedia=/', explode('<noscript>', $async)[0]) === 1 && str_contains($async, '<noscript>' . $tag . '</noscript>'));
check('assets: a tag that is not a link for all media is left alone', Assets::nonBlockingStyle("<script src='x.js'></script>") === "<script src='x.js'></script>" && Assets::nonBlockingStyle("<link rel='stylesheet' href='p.css' media='print' />") === "<link rel='stylesheet' href='p.css' media='print' />");
check('assets: the dropped styles are the fonts, block and brand styles and not the main stylesheet', in_array('storefront-fonts', Assets::DROP_STYLES, true) && in_array('storefront-gutenberg-blocks', Assets::DROP_STYLES, true) && !in_array('storefront-style', Assets::DROP_STYLES, true) && !in_array('storefront-icons', Assets::DROP_STYLES, true));

// headers
$h = Headers::security(false);
check('headers: the four basic headers are set', isset($h['X-Content-Type-Options'], $h['X-Frame-Options'], $h['Referrer-Policy'], $h['Permissions-Policy']) && $h['X-Content-Type-Options'] === 'nosniff');
check('headers: no HSTS on plain http', !isset($h['Strict-Transport-Security']));
check('headers: HSTS on https', isset(Headers::security(true)['Strict-Transport-Security']));

echo "\n" . ($failed === 0 ? 'all passed' : "$failed failed") . "\n";
exit($failed === 0 ? 0 : 1);

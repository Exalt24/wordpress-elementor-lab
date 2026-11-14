<?php
/**
 * Offline tests for the SEO Lab markup builders. Plain PHP, no OpenCart and no network.
 *   php opencart/tests/test_markup.php
 * Every builder is checked on a good input and on a hostile or empty one.
 */
require __DIR__ . '/../extension/seolab/system/library/markup.php';

use Seolab\Markup;

$failed = 0;

function check(string $name, bool $ok, string $detail = ''): void {
	global $failed;
	echo ($ok ? 'PASS  ' : 'FAIL  ') . $name . ($ok ? '' : '   <- ' . $detail) . "\n";
	$failed += $ok ? 0 : 1;
}

// metaDescription
$d = Markup::metaDescription('<p>A  30 litre   daypack &amp; rain cover.</p>');
check('description: tags stripped, spaces collapsed, entities decoded', $d === 'A 30 litre daypack & rain cover.', $d);
$long = Markup::metaDescription(str_repeat('abcdefgh ', 30), 155);
check('description: cut at 155 or less on a whole word with an ellipsis', mb_strlen($long) <= 155 && str_ends_with($long, 'abcdefgh…'), $long);
check('description: empty stays empty', Markup::metaDescription('') === '');

// pageTitle
check('title: a short title gets the store name', Markup::pageTitle('Summit 30 Daypack', 'Pinewick Outfitters') === 'Summit 30 Daypack | Pinewick Outfitters');
check('title: a title already 30 characters is left alone', Markup::pageTitle('A title that is thirty chars!!', 'Pinewick Outfitters') === 'A title that is thirty chars!!');
check('title: the store name is not added twice', Markup::pageTitle('Pinewick Outfitters', 'Pinewick Outfitters') === 'Pinewick Outfitters');
check('title: no store name added when the result would pass 65', Markup::pageTitle('Short', str_repeat('x', 70)) === 'Short');
$t = Markup::pageTitle(str_repeat('abcd ', 20), 'S');
check('title: a long title is cut to 65 or less with an ellipsis', mb_strlen($t) <= 65 && str_ends_with($t, '…'), $t);

// jsonLd: the script can never be closed early by a product name
$ld = Markup::jsonLd([Markup::product(['name' => 'Bad </script><script>alert(1)</script>', 'description' => 'd', 'url' => 'http://x/p', 'price' => 79, 'currency' => 'USD', 'quantity' => 3])]);
check('json-ld: a hostile name cannot close the script tag', substr_count($ld, '</script>') === 1 && !str_contains($ld, '<script>alert'), $ld);
preg_match('#<script type="application/ld\+json">(.*)</script>#s', $ld, $m);
$decoded = json_decode($m[1] ?? '', true);
check('json-ld: the output parses and keeps the name', is_array($decoded) && $decoded['@graph'][0]['name'] === 'Bad </script><script>alert(1)</script>');

// product
$p = Markup::product(['name' => 'A', 'description' => '<b>d</b>', 'url' => 'http://x/p', 'price' => '79', 'currency' => 'USD', 'quantity' => 24, 'image' => 'http://x/i.png', 'model' => 'PW-1']);
check('product: price has two decimals and the currency', $p['offers']['price'] === '79.00' && $p['offers']['priceCurrency'] === 'USD');
check('product: in stock when quantity is above zero', $p['offers']['availability'] === 'https://schema.org/InStock');
$out = Markup::product(['name' => 'A', 'description' => '', 'url' => 'http://x/p', 'price' => 5, 'currency' => 'USD', 'quantity' => 0]);
check('product: out of stock at zero, and no image or sku invented', $out['offers']['availability'] === 'https://schema.org/OutOfStock' && !array_key_exists('image', $out) && !array_key_exists('sku', $out));
check('product: sku and image carried when present', $p['sku'] === 'PW-1' && $p['image'] === 'http://x/i.png');

// breadcrumbs
$b = Markup::breadcrumbs([['Home', 'http://x/'], ['Backpacks', 'http://x/b'], ['Pack', '']]);
check('breadcrumbs: positions run from 1 and the last crumb has no link', $b['itemListElement'][0]['position'] === 1 && $b['itemListElement'][2]['position'] === 3 && !array_key_exists('item', $b['itemListElement'][2]));

// openGraph
$og = Markup::openGraph('A "quoted" <title>', 'd', 'product', 'http://x/p');
check('open graph: values are escaped for an attribute', str_contains($og, 'A &quot;quoted&quot; &lt;title&gt;') && !str_contains($og, '<title>'), $og);
check('open graph: no image tag when there is no image', !str_contains($og, 'og:image') && str_contains(Markup::openGraph('t', 'd', 'website', 'http://x/', 'http://x/i.png'), 'og:image'));

// retagHeading
check('headings: an h4 becomes an h2 that keeps the h4 look', Markup::retagHeading('<h4>Pack</h4>', 4, 2) === '<h2 class="h4">Pack</h2>');
check('headings: a heading with attributes is left alone', Markup::retagHeading('<h4 id="x">Pack</h4>', 4, 2) === '<h4 id="x">Pack</h4>');
check('headings: two headings are both changed and the text between is kept', Markup::retagHeading('<h5>A</h5><p>x</p><h5>B</h5>', 5, 2) === '<h2 class="h5">A</h2><p>x</p><h2 class="h5">B</h2>');

// injectIntoHead
check('inject: the markup lands before </head>', Markup::injectIntoHead('<html><head><title>t</title></head><body></body></html>', '<m/>') === '<html><head><title>t</title><m/></head><body></body></html>');
check('inject: html with no head is returned untouched', Markup::injectIntoHead('<p>x</p>', '<m/>') === '<p>x</p>');

// canonicalUrl
check('canonical: sort, limit and language are dropped', Markup::canonicalUrl('http://x/en-gb/catalog/b?language=en-gb&sort=p.price&limit=100') === 'http://x/en-gb/catalog/b');
check('canonical: page 2 is kept, page 1 is the bare address', Markup::canonicalUrl('http://x/c?page=2&sort=x') === 'http://x/c?page=2' && Markup::canonicalUrl('http://x/c?page=1') === 'http://x/c');
check('canonical: a port is kept', Markup::canonicalUrl('http://localhost:8088/p?sort=1') === 'http://localhost:8088/p');
check('canonical: an entity-encoded ampersand is read as one', Markup::canonicalUrl('http://x/c?page=2&amp;sort=x') === 'http://x/c?page=2');

// sitemap
$xml = Markup::sitemap([['http://x/a?b=1&c=2', '2026-11-14 10:00:00'], ['http://x/b', '']]);
$doc = simplexml_load_string($xml);
check('sitemap: it is well-formed XML with both urls', $doc !== false && count($doc->url) === 2, $xml);
check('sitemap: an ampersand in an address is escaped and the date is cut to the day', str_contains($xml, 'b=1&amp;c=2') && str_contains($xml, '<lastmod>2026-11-14</lastmod>'));
check('sitemap: a url with no date has no lastmod', substr_count($xml, '<lastmod>') === 1);

echo "\n" . ($failed === 0 ? 'all tests passed' : $failed . ' FAILED') . "\n";
exit($failed === 0 ? 0 : 1);

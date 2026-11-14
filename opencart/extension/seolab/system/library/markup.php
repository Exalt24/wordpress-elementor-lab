<?php
/**
 * Pure markup builders for the SEO Lab extension. Nothing here touches OpenCart, so
 * tests/test_markup.php can load this one file and check every output in plain PHP.
 */
namespace Seolab;

final class Markup {
	/** A meta description from HTML: tags gone, spaces collapsed, cut on a word boundary with an ellipsis. */
	public static function metaDescription(string $html, int $max = 155): string {
		$text = trim(preg_replace('/\s+/u', ' ', html_entity_decode(strip_tags($html), ENT_QUOTES, 'UTF-8')));

		if (mb_strlen($text) <= $max) {
			return $text;
		}

		$cut = mb_substr($text, 0, $max - 1);
		$space = mb_strrpos($cut, ' ');

		return rtrim($space === false ? $cut : mb_substr($cut, 0, $space), " ,;:.-") . '…';
	}

	/** A page title of 30 to 65 characters: a short one gets " | Store name" added (when that fits), a long one is cut on a word boundary. */
	public static function pageTitle(string $title, string $store, int $min = 30, int $max = 65): string {
		$title = trim($title);

		if (mb_strlen($title) < $min && $store !== '' && mb_stripos($title, $store) === false) {
			$longer = $title . ' | ' . $store;

			return mb_strlen($longer) <= $max ? $longer : $title;
		}

		if (mb_strlen($title) > $max) {
			$cut = mb_substr($title, 0, $max - 1);
			$space = mb_strrpos($cut, ' ');

			return rtrim($space === false ? $cut : mb_substr($cut, 0, $space), " ,;:.-|") . '…';
		}

		return $title;
	}

	/** One JSON-LD script tag. JSON_HEX_TAG turns < and > into escapes so a product name can never close the script early. */
	public static function jsonLd(array $graph): string {
		$json = json_encode(['@context' => 'https://schema.org', '@graph' => $graph], JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_HEX_TAG | JSON_HEX_AMP);

		return '<script type="application/ld+json">' . $json . '</script>';
	}

	public static function organization(string $name, string $url, string $logo = ''): array {
		$node = ['@type' => 'Organization', '@id' => $url . '#org', 'name' => $name, 'url' => $url];

		if ($logo !== '') {
			$node['logo'] = $logo;
		}

		return $node;
	}

	public static function website(string $name, string $url): array {
		return ['@type' => 'WebSite', '@id' => $url . '#site', 'name' => $name, 'url' => $url, 'publisher' => ['@id' => $url . '#org']];
	}

	/** Product with one Offer. Stock decides the availability, and a missing image or SKU is left out, never faked. */
	public static function product(array $p): array {
		$node = [
			'@type'       => 'Product',
			'name'        => $p['name'],
			'description' => self::metaDescription($p['description'] ?? '', 300),
			'url'         => $p['url'],
			'offers'      => [
				'@type'         => 'Offer',
				'url'           => $p['url'],
				'price'         => number_format((float)$p['price'], 2, '.', ''),
				'priceCurrency' => $p['currency'],
				'availability'  => ((int)($p['quantity'] ?? 0) > 0) ? 'https://schema.org/InStock' : 'https://schema.org/OutOfStock'
			]
		];

		foreach (['image' => 'image', 'sku' => 'model'] as $field => $source) {
			if (!empty($p[$source])) {
				$node[$field] = $p[$source];
			}
		}

		return $node;
	}

	/** BreadcrumbList from [[name, url], ...]; the last crumb carries no link only when its url is empty. */
	public static function breadcrumbs(array $crumbs): array {
		$items = [];

		foreach (array_values($crumbs) as $i => $crumb) {
			$item = ['@type' => 'ListItem', 'position' => $i + 1, 'name' => $crumb[0]];

			if ($crumb[1] !== '') {
				$item['item'] = $crumb[1];
			}

			$items[] = $item;
		}

		return ['@type' => 'BreadcrumbList', 'itemListElement' => $items];
	}

	/** Open Graph meta tags, every value escaped for an attribute. */
	public static function openGraph(string $title, string $description, string $type, string $url, string $image = ''): string {
		$tags = ['og:title' => $title, 'og:description' => $description, 'og:type' => $type, 'og:url' => $url];

		if ($image !== '') {
			$tags['og:image'] = $image;
		}

		$out = '';

		foreach ($tags as $property => $content) {
			$out .= '<meta property="' . $property . '" content="' . htmlspecialchars($content, ENT_QUOTES, 'UTF-8') . '"/>' . "\n";
		}

		return $out;
	}

	/**
	 * Re-tag plain headings so the outline does not skip a level: every <h4>text</h4> becomes <h2 class="h4">text</h2>
	 * and looks the same, because Bootstrap's .h4 class carries the size. A heading that already has attributes is left alone.
	 */
	public static function retagHeading(string $html, int $from, int $to): string {
		return preg_replace('#<h' . $from . '>(.*?)</h' . $from . '>#is', '<h' . $to . ' class="h' . $from . '">$1</h' . $to . '>', $html);
	}

	/** Put markup just before </head>, once; HTML with no head is returned untouched. */
	public static function injectIntoHead(string $html, string $markup): string {
		$pos = stripos($html, '</head>');

		if ($pos === false || $markup === '') {
			return $html;
		}

		return substr($html, 0, $pos) . $markup . substr($html, $pos);
	}

	/** The canonical address of a page: the SEO url without query parameters that only change the view (sort, limit, language, tracking). */
	public static function canonicalUrl(string $url, array $keep = ['page']): string {
		$parts = parse_url(str_replace('&amp;', '&', $url));

		if (!is_array($parts) || empty($parts['host'])) {
			return $url;
		}

		parse_str($parts['query'] ?? '', $query);
		$query = array_intersect_key($query, array_flip($keep));

		if (isset($query['page']) && (int)$query['page'] <= 1) {
			unset($query['page']);
		}

		$out = ($parts['scheme'] ?? 'http') . '://' . $parts['host'] . (isset($parts['port']) ? ':' . $parts['port'] : '') . ($parts['path'] ?? '/');

		return $out . ($query ? '?' . http_build_query($query) : '');
	}

	/** An XML sitemap from [[loc, lastmod or ''], ...]; every loc escaped, and the document starts with the XML declaration. */
	public static function sitemap(array $urls): string {
		$xml = '<?xml version="1.0" encoding="UTF-8"?>' . "\n" . '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' . "\n";

		foreach ($urls as $row) {
			$xml .= "  <url><loc>" . htmlspecialchars($row[0], ENT_XML1 | ENT_QUOTES, 'UTF-8') . '</loc>';

			if (!empty($row[1])) {
				$xml .= '<lastmod>' . htmlspecialchars(substr($row[1], 0, 10), ENT_XML1, 'UTF-8') . '</lastmod>';
			}

			$xml .= "</url>\n";
		}

		return $xml . '</urlset>' . "\n";
	}
}

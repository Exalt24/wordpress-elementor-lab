<?php
namespace Bullion;

/** Product and Offer markup built from the same price the page shows. */
final class Schema
{
    /**
     * @param array $p ['name','sku','description','url','image','pence' => ?int,'currency','in_stock' => bool,'as_of' => ?int]
     * The offer is left out when there is no trusted price: a missing price is better than a wrong one. priceValidUntil is the moment the cached price expires,
     * not the end of the year, because the price changes every few seconds.
     */
    public static function product(array $p, int $ttl): array
    {
        $node = [
            '@context' => 'https://schema.org',
            '@type' => 'Product',
            'name' => $p['name'],
            'sku' => $p['sku'],
            'description' => $p['description'],
            'url' => $p['url'],
            'brand' => ['@type' => 'Brand', 'name' => 'Ledger Mint'],
        ];
        if (!empty($p['image'])) {
            $node['image'] = $p['image'];
        }
        if ($p['pence'] !== null && $p['as_of'] !== null) {
            $node['offers'] = [
                '@type' => 'Offer',
                'url' => $p['url'],
                'priceCurrency' => $p['currency'],
                'price' => sprintf('%.2f', $p['pence'] / 100),
                'priceValidUntil' => gmdate('Y-m-d\TH:i:s\Z', $p['as_of'] + $ttl),
                'availability' => $p['in_stock'] ? 'https://schema.org/InStock' : 'https://schema.org/OutOfStock',
                'itemCondition' => 'https://schema.org/NewCondition',
            ];
        }
        return $node;
    }

    /** FAQPage markup for questions that are also printed on the page. Pairs with an empty question or answer are dropped, and no pairs means no markup. */
    public static function faq(array $pairs): ?array
    {
        $items = [];
        foreach ($pairs as [$q, $a]) {
            $q = trim((string) $q);
            $a = trim((string) $a);
            if ($q !== '' && $a !== '') {
                $items[] = ['@type' => 'Question', 'name' => $q, 'acceptedAnswer' => ['@type' => 'Answer', 'text' => $a]];
            }
        }
        return $items === [] ? null : ['@context' => 'https://schema.org', '@type' => 'FAQPage', 'mainEntity' => $items];
    }

    public static function organization(string $name, string $url, string $logo = ''): array
    {
        $node = ['@context' => 'https://schema.org', '@type' => 'Organization', 'name' => $name, 'url' => $url];
        if ($logo !== '') {
            $node['logo'] = $logo;
        }
        return $node;
    }

    /** A script tag that no product name can close early. */
    public static function script(array $node): string
    {
        return '<script type="application/ld+json">' . json_encode($node, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_HEX_TAG | JSON_HEX_AMP) . '</script>';
    }
}

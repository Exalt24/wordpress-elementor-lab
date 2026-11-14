<?php
namespace Bullion;

/** A Google Merchant Center product feed (RSS 2.0 with g: fields) built from the live prices. */
final class Feed
{
    private static function x(string $s): string
    {
        return htmlspecialchars($s, ENT_XML1 | ENT_QUOTES, 'UTF-8');
    }

    /** @param array $items each ['id','title','description','link','image','pence' => ?int,'currency','in_stock' => bool]. An item with no trusted price is left out, never listed with a guess. */
    public static function merchant(array $items, string $shop, string $link): string
    {
        $xml = '<?xml version="1.0" encoding="UTF-8"?>' . "\n" . '<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0"><channel>';
        $xml .= '<title>' . self::x($shop) . '</title><link>' . self::x($link) . '</link><description>' . self::x($shop) . ' product feed</description>';
        foreach ($items as $i) {
            if ($i['pence'] === null) {
                continue;
            }
            $xml .= '<item>'
                . '<g:id>' . self::x($i['id']) . '</g:id>'
                . '<title>' . self::x($i['title']) . '</title>'
                . '<description>' . self::x($i['description']) . '</description>'
                . '<link>' . self::x($i['link']) . '</link>'
                . ($i['image'] !== '' ? '<g:image_link>' . self::x($i['image']) . '</g:image_link>' : '')
                . '<g:availability>' . ($i['in_stock'] ? 'in stock' : 'out of stock') . '</g:availability>'
                . '<g:price>' . sprintf('%.2f', $i['pence'] / 100) . ' ' . self::x($i['currency']) . '</g:price>'
                . '<g:condition>new</g:condition><g:brand>Ledger Mint</g:brand><g:identifier_exists>no</g:identifier_exists>'
                . '</item>';
        }
        return $xml . '</channel></rss>';
    }
}

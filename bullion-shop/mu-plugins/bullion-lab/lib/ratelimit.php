<?php
namespace Bullion;

/**
 * A request rate limit per caller and per kind of request, as pure functions over a small record.
 * It is aimed at what bots and scrapers hammer (site search, the REST API), never at ordinary pages, the sitemap or robots.txt, so a customer or a search engine
 * crawling the shop is not counted. A crawler is not let through by its user agent either, because the user agent is whatever the client says it is.
 */
final class RateLimit
{
    public const WINDOW = 60;
    public const LIMITS = ['search' => 30, 'rest' => 120];

    /** Which limited kind of request this is, or null for a request that is never limited. */
    public static function bucket(string $path, array $query): ?string
    {
        if (strpos($path, '/wp-json/') === 0 || isset($query['rest_route'])) {
            return 'rest';
        }
        if (isset($query['s'])) {
            return 'search';
        }
        return null;
    }

    /**
     * Counts one request in a fixed window.
     * @return array [bool allowed, array newRecord]
     */
    public static function hit(?array $rec, int $now, string $bucket): array
    {
        $limit = self::LIMITS[$bucket];
        if ($rec === null || $now - $rec['start'] >= self::WINDOW) {
            $rec = ['start' => $now, 'count' => 0];
        }
        $rec['count']++;
        return [$rec['count'] <= $limit, $rec];
    }

    public static function retryAfter(array $rec, int $now): int
    {
        return max(1, $rec['start'] + self::WINDOW - $now);
    }
}

<?php
namespace Bullion;

/**
 * The live price rules, with no WordPress and no network in them, so tests can drive every branch.
 * A price is shown only when it is fresh, or when it is the last good one and still young enough to trust. Anything else is "unavailable", never a wrong number.
 */
final class Spot
{
    public const METALS = ['gold', 'silver'];

    /** Reads a feed reply. Returns ['gold' => float, 'silver' => float] or null for anything that is not two positive finite numbers. */
    public static function parse($body): ?array
    {
        if (!is_string($body)) {
            return null;
        }
        $data = json_decode($body, true);
        if (!is_array($data)) {
            return null;
        }
        $out = [];
        foreach (self::METALS as $m) {
            $v = $data[$m] ?? null;
            if (!(is_int($v) || is_float($v)) || !is_finite((float) $v) || $v <= 0) {
                return null;
            }
            $out[$m] = (float) $v;
        }
        return $out;
    }

    /** A new reading that moved more than $maxJump from the last good one is treated as a feed fault, not as a market move. */
    public static function sane(array $new, ?array $last, float $maxJump = 0.15): bool
    {
        if ($last === null) {
            return true;
        }
        foreach (self::METALS as $m) {
            if (abs($new[$m] - $last['prices'][$m]) / $last['prices'][$m] > $maxJump) {
                return false;
            }
        }
        return true;
    }

    /**
     * @param callable $fetch   returns the raw reply body or null (it may throw)
     * @param ?array   $last    ['prices' => [...], 'fetched_at' => int] saved from the last good reading, or null
     * @param bool     $canFetch false when another request is already fetching: this one uses what it has
     * @return array ['state' => fresh|stale|unavailable, 'prices' => ?array, 'as_of' => ?int, 'save' => ?array, 'fetched' => bool]
     */
    public static function resolve(callable $fetch, ?array $last, int $now, int $ttl, int $staleMax, bool $canFetch = true): array
    {
        if ($last !== null && $now - $last['fetched_at'] < $ttl) {
            return ['state' => 'fresh', 'prices' => $last['prices'], 'as_of' => $last['fetched_at'], 'save' => null, 'fetched' => false];
        }
        $fetched = false;
        if ($canFetch) {
            $fetched = true;
            try {
                $parsed = self::parse($fetch());
            } catch (\Throwable $e) {
                $parsed = null;
            }
            if ($parsed !== null && self::sane($parsed, $last)) {
                $save = ['prices' => $parsed, 'fetched_at' => $now];
                return ['state' => 'fresh', 'prices' => $parsed, 'as_of' => $now, 'save' => $save, 'fetched' => true];
            }
        }
        if ($last !== null && $now - $last['fetched_at'] <= $staleMax) {
            return ['state' => 'stale', 'prices' => $last['prices'], 'as_of' => $last['fetched_at'], 'save' => null, 'fetched' => $fetched];
        }
        return ['state' => 'unavailable', 'prices' => null, 'as_of' => null, 'save' => null, 'fetched' => $fetched];
    }
}

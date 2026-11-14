<?php
namespace Bullion;

/** Login attempt limiting, as pure functions over a small record, so the rules can be tested without WordPress. */
final class Limiter
{
    public const MAX_FAILS = 5;
    public const WINDOW = 900;
    public const LOCK = 900;

    /** The caller is identified by the connection address only. A forwarding header is chosen by the client, so trusting it would let an attacker rotate it and never be counted. */
    public static function key(array $server): string
    {
        return (string) ($server['REMOTE_ADDR'] ?? 'unknown');
    }

    public static function isLocked(?array $rec, int $now): bool
    {
        return $rec !== null && ($rec['locked_until'] ?? 0) > $now;
    }

    public static function secondsLeft(?array $rec, int $now): int
    {
        return $rec === null ? 0 : max(0, ($rec['locked_until'] ?? 0) - $now);
    }

    /** Adds one failed attempt. Attempts older than the window are forgotten. The fifth inside the window starts a lock. */
    public static function recordFail(?array $rec, int $now): array
    {
        $fails = [];
        foreach (($rec['fails'] ?? []) as $t) {
            if ($now - $t < self::WINDOW) {
                $fails[] = $t;
            }
        }
        $fails[] = $now;
        $locked = $rec['locked_until'] ?? 0;
        if (count($fails) >= self::MAX_FAILS) {
            $locked = $now + self::LOCK;
            $fails = [];
        }
        return ['fails' => $fails, 'locked_until' => $locked];
    }
}

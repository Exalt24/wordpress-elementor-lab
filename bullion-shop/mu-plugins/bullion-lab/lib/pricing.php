<?php
namespace Bullion;

/** Product prices from a spot price. Money is whole pence all the way, so rounding happens once. */
final class Pricing
{
    /** The price a customer pays: spot per troy ounce x the ounces in the item x (1 + premium percent). */
    public static function sellPence(float $spotPerOz, float $oz, float $premiumPct): int
    {
        return (int) round($spotPerOz * $oz * (1 + $premiumPct / 100) * 100);
    }

    /** The price paid to a customer selling back: the metal value less a buy-back discount percent. Never below zero. */
    public static function buyPence(float $spotPerOz, float $oz, float $discountPct): int
    {
        return max(0, (int) round($spotPerOz * $oz * (1 - $discountPct / 100) * 100));
    }

    public static function format(int $pence, string $symbol = '£'): string
    {
        return $symbol . number_format($pence / 100, 2, '.', ',');
    }
}

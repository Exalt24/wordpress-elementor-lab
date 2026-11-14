<?php
namespace Bullion;

/** The small rules behind the lean assets, with no WordPress in them. */
final class Assets
{
    /** The style handles a shop page does not need: Google Fonts, block styles (a shop page has no blocks) and brand logo styles (none are used). */
    public const DROP_STYLES = ['storefront-fonts', 'storefront-gutenberg-blocks', 'storefront-woocommerce-brands-style'];

    /**
     * Turns a blocking stylesheet tag into one that loads without blocking the first paint: it starts as print media and switches to all media when it has loaded,
     * and a noscript copy keeps it working with scripts off. A tag that is not a stylesheet link for all media is returned as it was.
     */
    public static function nonBlockingStyle(string $tag): string
    {
        if (strpos($tag, "media='all'") === false || strpos($tag, '<link') === false) {
            return $tag;
        }
        return str_replace("media='all'", "media='print' onload=\"this.media='all'\"", $tag) . '<noscript>' . $tag . '</noscript>';
    }
}

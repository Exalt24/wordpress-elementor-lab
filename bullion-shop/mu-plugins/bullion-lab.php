<?php
/**
 * Plugin Name: Bullion lab
 * Description: Live spot-linked prices with a cache, a price shortcode and a cached REST route, Product and Offer markup, a Merchant Center feed, and basic hardening. A must-use plugin so it is always on.
 * The rules live in bullion-lab/lib (no WordPress in them, so they are unit tested); this file only connects them to WordPress and WooCommerce.
 *
 * Settings come from environment variables so one build can be run in the slow way and the fast way for a measurement:
 *   BULLION_PRICE_MODE  cached (default) or naive (one feed request per product, nothing saved: the integration written the obvious way)
 *   BULLION_HARDENING   on (default) or off
 *   BULLION_FEED_URL, BULLION_TTL (seconds a price counts as fresh), BULLION_STALE_MAX (seconds the last good price may still be shown, marked stale)
 */
if (!defined('ABSPATH')) {
    exit;
}

foreach (['spot', 'pricing', 'schema', 'feed', 'limiter', 'headers', 'ratelimit', 'assets', 'firewall'] as $f) {
    require_once __DIR__ . '/bullion-lab/lib/' . $f . '.php';
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

function bullion_cfg(string $key, $default)
{
    $v = getenv('BULLION_' . $key);
    return ($v === false || $v === '') ? $default : $v;
}

function bullion_ttl(): int
{
    return (int) bullion_cfg('TTL', 10);
}

function bullion_fetch_body(): ?string
{
    $res = wp_remote_get(bullion_cfg('FEED_URL', 'http://spot:8090/spot'), ['timeout' => 2, 'redirection' => 0]);
    if (is_wp_error($res) || wp_remote_retrieve_response_code($res) !== 200) {
        return null;
    }
    return wp_remote_retrieve_body($res);
}

/** The current prices for this request. In cached mode: one reading saved in the database, one feed call at most per TTL, and only one request at a time makes it. */
function bullion_spot(int $productId = 0): array
{
    static $memo = null;
    static $naive = [];
    $now = time();
    if (bullion_cfg('PRICE_MODE', 'cached') === 'naive') {
        // The obvious integration: ask the feed every time a price is read for a product, keep nothing.
        if (!isset($naive[$productId])) {
            $naive[$productId] = Spot::resolve('bullion_fetch_body', null, $now, 0, 0);
        }
        return $naive[$productId];
    }
    if ($memo !== null) {
        return $memo;
    }
    $last = get_option('bullion_last_good', null);
    $last = is_array($last) ? $last : null;
    $gotLock = false;
    if ($last === null || $now - $last['fetched_at'] >= bullion_ttl()) {
        // add_option is atomic: only the request that creates the lock fetches. A lock older than 10 seconds belongs to a request that died.
        $lock = (int) get_option('bullion_fetch_lock', 0);
        if ($lock && $now - $lock > 10) {
            delete_option('bullion_fetch_lock');
        }
        $gotLock = add_option('bullion_fetch_lock', $now, '', 'no');
    }
    $result = Spot::resolve('bullion_fetch_body', $last, $now, bullion_ttl(), (int) bullion_cfg('STALE_MAX', 40), $gotLock || !($last === null || $now - $last['fetched_at'] >= bullion_ttl()));
    if ($result['save'] !== null) {
        update_option('bullion_last_good', $result['save'], false);
    }
    if ($gotLock) {
        delete_option('bullion_fetch_lock');
    }
    return $memo = $result;
}

function bullion_product_pence(WC_Product $product, string $kind = 'sell'): ?int
{
    $metal = $product->get_meta('_bullion_metal');
    if ($metal === '') {
        return null;
    }
    $spot = bullion_spot($product->get_id());
    $perOz = $spot['prices'][$metal] ?? null;
    if ($perOz === null) {
        return null;
    }
    $oz = (float) $product->get_meta('_bullion_oz');
    return $kind === 'sell'
        ? Pricing::sellPence($perOz, $oz, (float) $product->get_meta('_bullion_premium'))
        : Pricing::buyPence($perOz, $oz, 3.0);
}

// ---- WooCommerce: the price of a spot-linked product is computed from the spot price when it is read ----
add_filter('woocommerce_product_get_price', 'bullion_filter_price', 20, 2);
add_filter('woocommerce_product_get_regular_price', 'bullion_filter_price', 20, 2);
add_filter('woocommerce_product_get_sale_price', function ($price, $product) {
    return $product->get_meta('_bullion_metal') !== '' ? '' : $price;
}, 20, 2);
function bullion_filter_price($price, $product)
{
    if ($product->get_meta('_bullion_metal') === '') {
        return $price;
    }
    $pence = bullion_product_pence($product);
    return $pence === null ? '' : sprintf('%.2f', $pence / 100);   // an empty price makes WooCommerce hide the price and refuse the cart
}
add_filter('woocommerce_empty_price_html', function () {
    return '<span class="bullion-unavailable">Price unavailable, please check back shortly</span>';
});
add_filter('woocommerce_get_price_html', function ($html, $product) {
    if ($product->get_meta('_bullion_metal') === '' || !is_product() || get_queried_object_id() !== $product->get_id()) {
        return $html;
    }
    $spot = bullion_spot($product->get_id());
    if ($spot['as_of'] === null) {
        return $html;
    }
    $sell = Pricing::format((int) round(((float) $product->get_price()) * 100));
    $buy = bullion_product_pence($product, 'buy');
    return $html . '<p class="bullion-asof" data-state="' . esc_attr($spot['state']) . '">Live price as of ' . esc_html(gmdate('H:i:s', $spot['as_of'])) . ' UTC'
        . ($spot['state'] === 'stale' ? ' (the feed is not answering, this is the last good price)' : '')
        . ($buy !== null ? '. We buy this back at ' . esc_html(Pricing::format($buy)) . '.' : '') . '</p>';
}, 20, 2);

// ---- Product and Offer markup from the same price ----
add_filter('woocommerce_structured_data_product', function ($markup, $product) {
    if ($product->get_meta('_bullion_metal') === '') {
        return $markup;
    }
    $spot = bullion_spot($product->get_id());
    $pence = bullion_product_pence($product);
    $node = Schema::product([
        'name' => $product->get_name(),
        'sku' => $product->get_sku(),
        'description' => wp_strip_all_tags($product->get_short_description() ?: $product->get_name()),
        'url' => get_permalink($product->get_id()),
        'image' => wp_get_attachment_url($product->get_image_id()) ?: '',
        'pence' => $pence,
        'currency' => get_woocommerce_currency(),
        'in_stock' => $product->is_in_stock(),
        'as_of' => $spot['as_of'],
    ], bullion_ttl());
    unset($node['@context']);   // WooCommerce adds the context itself
    return $node;
}, 20, 2);

// ---- FAQ and Organization markup: the questions are printed on the page, and the same text goes into the markup ----
const BULLION_FAQ = [
    ['Is the price on the page the price I pay?', 'Yes. Every price is worked out from the live gold or silver spot price when you view it, and the cart uses the same price.'],
    ['What happens if the price feed stops?', 'We show the last good price for a short time and mark it, then we show no price at all instead of a wrong one.'],
    ['Do you buy bullion back?', 'Yes. The product page shows the price we pay to buy an item back, worked out from the same live spot price.'],
];
add_shortcode('bullion_faq', function () {
    $html = '<section class="bullion-faq"><h2>Questions</h2>';
    foreach (BULLION_FAQ as [$q, $a]) {
        $html .= '<h3>' . esc_html($q) . '</h3><p>' . esc_html($a) . '</p>';
    }
    return $html . '</section>';
});
add_action('wp_head', function () {
    if (!is_front_page()) {
        return;
    }
    echo Schema::script(Schema::organization(get_bloginfo('name'), home_url('/'))) . "\n";
    $faq = Schema::faq(BULLION_FAQ);
    if ($faq !== null) {
        echo Schema::script($faq) . "\n";
    }
});

// ---- the shortcode [spot_price metal="gold"] and the cached REST route it refreshes from ----
$GLOBALS['bullion_shortcode_used'] = false;
add_shortcode('spot_price', function ($atts) {
    $a = shortcode_atts(['metal' => 'gold'], $atts);
    $metal = in_array($a['metal'], Spot::METALS, true) ? $a['metal'] : 'gold';
    $GLOBALS['bullion_shortcode_used'] = true;
    $spot = bullion_spot();
    $perOz = $spot['prices'][$metal] ?? null;
    $text = $perOz === null ? 'unavailable' : Pricing::format((int) round($perOz * 100)) . ' per oz';
    return '<span class="bullion-spot" data-metal="' . esc_attr($metal) . '" data-state="' . esc_attr($spot['state']) . '">' . esc_html($text) . '</span>';
});
add_action('wp_footer', function () {
    if (empty($GLOBALS['bullion_shortcode_used'])) {
        return;
    }
    $every = max(5, bullion_ttl()) * 1000;
    echo '<script>(function(){var u=' . wp_json_encode(rest_url('bullion/v1/spot')) . ';function t(){fetch(u).then(function(r){return r.json()}).then(function(d){document.querySelectorAll(".bullion-spot").forEach(function(e){var p=d.prices&&d.prices[e.dataset.metal];e.textContent=p==null?"unavailable":"£"+p.toLocaleString("en-GB",{minimumFractionDigits:2,maximumFractionDigits:2})+" per oz";e.dataset.state=d.state})}).catch(function(){})}setInterval(t,' . (int) $every . ')})();</script>';
});
add_action('rest_api_init', function () {
    register_rest_route('bullion/v1', '/spot', [
        'methods' => 'GET',
        'permission_callback' => '__return_true',
        'callback' => function () {
            $s = bullion_spot();
            return new WP_REST_Response(
                ['state' => $s['state'], 'prices' => $s['prices'], 'as_of' => $s['as_of'], 'currency' => 'GBP'],
                200,
                ['Cache-Control' => 'public, max-age=' . bullion_ttl()]
            );
        },
    ]);
});

// ---- Merchant Center feed: /?bullion_feed=merchant ----
add_action('template_redirect', function () {
    if (($_GET['bullion_feed'] ?? '') !== 'merchant') {
        return;
    }
    $items = [];
    foreach (wc_get_products(['limit' => -1, 'status' => 'publish']) as $p) {
        $items[] = [
            'id' => $p->get_sku() ?: (string) $p->get_id(),
            'title' => $p->get_name(),
            'description' => wp_strip_all_tags($p->get_short_description() ?: $p->get_name()),
            'link' => get_permalink($p->get_id()),
            'image' => wp_get_attachment_url($p->get_image_id()) ?: '',
            'pence' => bullion_product_pence($p),
            'currency' => get_woocommerce_currency(),
            'in_stock' => $p->is_in_stock(),
        ];
    }
    header('Content-Type: application/xml; charset=UTF-8');
    echo Feed::merchant($items, get_bloginfo('name'), home_url('/'));
    exit;
});

// ---- lean assets: what Lighthouse names as render blocking or unused on a shop page, removed ----
if (bullion_cfg('ASSETS', 'lean') === 'lean') {
    add_action('wp_enqueue_scripts', function () {
        foreach (Assets::DROP_STYLES as $handle) {
            wp_dequeue_style($handle);   // Google Fonts (another origin before the first paint), block styles and brand styles: none is used on a shop page
        }
    }, 100);
    add_action('wp_default_scripts', function ($scripts) {
        if (isset($scripts->registered['jquery'])) {
            $scripts->registered['jquery']->deps = array_diff($scripts->registered['jquery']->deps, ['jquery-migrate']);   // the old API shim, no code here uses it
        }
        foreach (['jquery', 'jquery-core'] as $h) {
            if (isset($scripts->registered[$h])) {
                $scripts->add_data($h, 'group', 1);   // printed in the footer, after the markup, so the head does not wait for it
            }
        }
    });
    // The icon font stylesheet is 15 KB, 97 percent unused on a shop page, and blocks the first paint: load it without blocking, with a noscript fallback.
    add_filter('style_loader_tag', function ($tag, $handle) {
        if ($handle !== 'storefront-icons') {
            return $tag;
        }
        return Assets::nonBlockingStyle($tag);
    }, 10, 2);
    remove_action('wp_head', 'print_emoji_detection_script', 7);
    remove_action('wp_print_styles', 'print_emoji_styles');
}

// ---- hardening ----
if (bullion_cfg('HARDENING', 'on') === 'on') {
    // The file is still on disk, so refuse it before WordPress does any work for it.
    $path = (string) parse_url($_SERVER['REQUEST_URI'] ?? '', PHP_URL_PATH);
    if (substr($path, -11) === '/xmlrpc.php') {
        http_response_code(403);
        header('Content-Type: text/plain; charset=UTF-8');
        echo 'XML-RPC is disabled.';
        exit;
    }
    // Probes for secrets and backups, and the names attack tools announce themselves with, are refused before WordPress does any more work.
    if (Firewall::reason($path, (string) ($_SERVER['HTTP_USER_AGENT'] ?? '')) !== null) {
        http_response_code(403);
        header('Content-Type: text/plain; charset=UTF-8');
        echo 'Forbidden.';
        exit;
    }
    if (!defined('DISALLOW_FILE_EDIT')) {
        define('DISALLOW_FILE_EDIT', true);   // no theme or plugin code editor in the dashboard, so a stolen admin login cannot write PHP
    }
    add_filter('xmlrpc_enabled', '__return_false');
    add_filter('wp_headers', function ($headers) {
        unset($headers['X-Pingback']);
        return $headers;
    });
    add_action('send_headers', function () {
        $https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off');
        foreach (Headers::security($https) as $name => $value) {
            header($name . ': ' . $value);
        }
    });
    remove_action('wp_head', 'wp_generator');
    add_filter('the_generator', '__return_empty_string');
    add_filter('rest_endpoints', function ($endpoints) {
        if (!is_user_logged_in()) {
            foreach (array_keys($endpoints) as $route) {
                if (strpos($route, '/wp/v2/users') === 0) {
                    unset($endpoints[$route]);
                }
            }
        }
        return $endpoints;
    });
    // ?author=1 and /author/name/ both reveal a login name.
    add_action('template_redirect', function () {
        if (is_author() || (isset($_GET['author']) && !is_admin())) {
            wp_safe_redirect(home_url('/'), 301);
            exit;
        }
    }, 0);
    add_action('parse_request', function () {
        if (isset($_GET['author']) && !is_admin()) {
            wp_safe_redirect(home_url('/'), 301);
            exit;
        }
    }, 0);
    // Bots and scrapers hammer site search and the REST API: a caller past the limit for that kind of request gets a 429 and a Retry-After. Ordinary pages are never counted.
    add_action('init', function () {
        if (is_user_logged_in()) {
            return;
        }
        $path = (string) parse_url($_SERVER['REQUEST_URI'] ?? '', PHP_URL_PATH);
        $bucket = RateLimit::bucket($path, $_GET);
        if ($bucket === null) {
            return;
        }
        $key = 'bullion_rl_' . md5(Limiter::key($_SERVER) . $bucket);
        $rec = get_transient($key);
        [$allowed, $rec] = RateLimit::hit(is_array($rec) ? $rec : null, time(), $bucket);
        set_transient($key, $rec, RateLimit::WINDOW);
        if (!$allowed) {
            http_response_code(429);
            header('Retry-After: ' . RateLimit::retryAfter($rec, time()));
            header('Content-Type: text/plain; charset=UTF-8');
            echo 'Too many requests. Try again in a minute.';
            exit;
        }
    }, 1);
    // Login limits: five failures from one address inside 15 minutes lock that address for 15 minutes, and a correct password is refused while it is locked.
    $bullion_rec = function () {
        $rec = get_transient('bullion_lim_' . md5(Limiter::key($_SERVER)));
        return is_array($rec) ? $rec : null;
    };
    add_filter('authenticate', function ($user) use ($bullion_rec) {
        $rec = $bullion_rec();
        if (Limiter::isLocked($rec, time())) {
            return new WP_Error('bullion_locked', 'Too many failed attempts. Try again in ' . ceil(Limiter::secondsLeft($rec, time()) / 60) . ' minutes.');
        }
        return $user;
    }, 99);
    add_action('wp_login_failed', function () use ($bullion_rec) {
        if (Limiter::isLocked($bullion_rec(), time())) {
            return;   // an attempt refused by the lock does not extend it
        }
        $rec = Limiter::recordFail($bullion_rec(), time());
        set_transient('bullion_lim_' . md5(Limiter::key($_SERVER)), $rec, Limiter::WINDOW + Limiter::LOCK);
    });
    add_action('wp_login', function () {
        delete_transient('bullion_lim_' . md5(Limiter::key($_SERVER)));
    });
}

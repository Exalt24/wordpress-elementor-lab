<?php
// LIFESPAN: permanent
// Seeds the invented catalogue: twelve gold and silver products priced from the spot price. Run with:  wp eval-file /lab-scripts/seed.php
// Each product stores its metal, the troy ounces it holds and a premium over spot; the price itself is computed live by the must-use plugin.
require_once ABSPATH . 'wp-admin/includes/file.php';
require_once ABSPATH . 'wp-admin/includes/image.php';

$items = [
    // slug, name, metal, troy oz, premium %, stock
    ['gold-bar-1oz', 'Ledger Mint 1 oz Gold Bar', 'gold', 1.0, 3.5, 40],
    ['gold-bar-100g', 'Ledger Mint 100 g Gold Bar', 'gold', 3.2151, 2.4, 12],
    ['gold-bar-10g', 'Ledger Mint 10 g Gold Bar', 'gold', 0.3215, 5.5, 60],
    ['gold-coin-1oz', 'Ledger Mint 1 oz Gold Coin', 'gold', 1.0, 4.8, 30],
    ['gold-coin-half', 'Ledger Mint 1/2 oz Gold Coin', 'gold', 0.5, 6.0, 25],
    ['gold-coin-tenth', 'Ledger Mint 1/10 oz Gold Coin', 'gold', 0.1, 11.0, 80],
    ['silver-bar-1kg', 'Ledger Mint 1 kg Silver Bar', 'silver', 32.1507, 6.0, 20],
    ['silver-bar-10oz', 'Ledger Mint 10 oz Silver Bar', 'silver', 10.0, 7.5, 35],
    ['silver-bar-100oz', 'Ledger Mint 100 oz Silver Bar', 'silver', 100.0, 4.5, 0],
    ['silver-coin-1oz', 'Ledger Mint 1 oz Silver Coin', 'silver', 1.0, 18.0, 200],
    ['silver-coin-tube', 'Ledger Mint 1 oz Silver Coin, tube of 25', 'silver', 25.0, 14.0, 15],
    ['silver-bar-1oz', 'Ledger Mint 1 oz Silver Bar', 'silver', 1.0, 15.0, 150],
];

$cats = [];
foreach (['gold' => 'Gold', 'silver' => 'Silver'] as $key => $label) {
    $term = term_exists($label, 'product_cat') ?: wp_insert_term($label, 'product_cat');
    $cats[$key] = (int) (is_array($term) ? $term['term_id'] : $term);
}

foreach ($items as [$slug, $name, $metal, $oz, $premium, $stock]) {
    $existing = get_page_by_path($slug, OBJECT, 'product');
    $product = $existing ? wc_get_product($existing->ID) : new WC_Product_Simple();
    $product->set_name($name);
    $product->set_slug($slug);
    $product->set_status('publish');
    $product->set_sku(strtoupper($slug));
    $product->set_category_ids([$cats[$metal]]);
    $product->set_short_description(sprintf('%s of %s, priced live from the spot price. Invented lab product, not for sale.', rtrim(rtrim(number_format($oz, 4), '0'), '.') . ' troy oz', $metal));
    $product->set_description($product->get_short_description());
    $product->set_regular_price('1');   // replaced at read time by the live price
    $product->set_manage_stock(true);
    $product->set_stock_quantity($stock);
    $product->set_stock_status($stock > 0 ? 'instock' : 'outofstock');
    $product->update_meta_data('_bullion_metal', $metal);
    $product->update_meta_data('_bullion_oz', (string) $oz);
    $product->update_meta_data('_bullion_premium', (string) $premium);
    if (!$product->get_image_id()) {
        $file = "/lab-build/img/$slug.png";
        if (file_exists($file)) {
            $up = wp_upload_bits("$slug.png", null, file_get_contents($file));
            $att = wp_insert_attachment(['post_mime_type' => 'image/png', 'post_title' => $name, 'post_status' => 'inherit'], $up['file']);
            update_post_meta($att, '_wp_attachment_image_alt', $name);
            wp_update_attachment_metadata($att, wp_generate_attachment_metadata($att, $up['file']));
            $product->set_image_id($att);
        }
    }
    $product->save();
}

$home = get_page_by_path('home');
$content = "<h1>Gold and silver bullion, priced live</h1>\n<p>Gold: [spot_price metal=\"gold\"] &nbsp; Silver: [spot_price metal=\"silver\"]</p>\n[products limit=\"8\" columns=\"4\"]\n[bullion_faq]";
$id = wp_insert_post(['ID' => $home ? $home->ID : 0, 'post_type' => 'page', 'post_title' => 'Home', 'post_name' => 'home', 'post_status' => 'publish', 'post_content' => $content]);
update_option('show_on_front', 'page');
update_option('page_on_front', $id);
echo count($items) . " products seeded, front page $id\n";

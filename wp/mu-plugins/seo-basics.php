<?php
/**
 * Plugin Name: SEO basics (lab)
 * Description: Prints a meta description (from the page excerpt), Open Graph tags and a Service JSON-LD block on singular pages. A must-use plugin so it is always on.
 * The audit in scripts/seo_audit.py found these three missing on the Elementor page; this is the fix.
 */
add_action('wp_head', function () {
    if (!is_singular()) {
        return;
    }
    $post = get_queried_object();
    $title = wp_strip_all_tags(get_the_title($post));
    $desc = wp_strip_all_tags(get_the_excerpt($post));
    $url = get_permalink($post);
    $site = get_bloginfo('name');
    if ($desc !== '') {
        echo '<meta name="description" content="' . esc_attr($desc) . '">' . "\n";
    }
    echo '<meta property="og:type" content="website">' . "\n";
    echo '<meta property="og:title" content="' . esc_attr($title) . '">' . "\n";
    echo '<meta property="og:description" content="' . esc_attr($desc) . '">' . "\n";
    echo '<meta property="og:url" content="' . esc_url($url) . '">' . "\n";
    echo '<meta property="og:site_name" content="' . esc_attr($site) . '">' . "\n";
    $schema = array(
        '@context' => 'https://schema.org',
        '@type' => 'Service',
        'name' => $title,
        'description' => $desc,
        'url' => $url,
        'provider' => array('@type' => 'Organization', 'name' => $site),
    );
    echo '<script type="application/ld+json">' . wp_json_encode($schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . '</script>' . "\n";
}, 5);

<?php
/**
 * Plugin Name: Lab Core
 * Description: The site's functionality, kept out of any theme so a theme change cannot lose it: a case study post type, an industry taxonomy, Advanced Custom Fields saved as JSON, the card renderer and the filters that shape a single case study.
 *
 * Presentation stays in the themes (lab-child on Genesis, lab-classic on a plain parent); this file only exposes lab_core_front_cards(), which each theme calls from its own hook.
 */

/** The case study post type and its taxonomy. Public, REST enabled, with an archive. */
add_action('init', function () {
    register_post_type('case_study', [
        'labels' => ['name' => 'Case studies', 'singular_name' => 'Case study'],
        'public' => true,
        'has_archive' => true,
        'show_in_rest' => true,
        'menu_icon' => 'dashicons-portfolio',
        'supports' => ['title', 'editor', 'excerpt', 'thumbnail', 'revisions'],
        'rewrite' => ['slug' => 'case-studies'],
    ]);
    register_taxonomy('industry', 'case_study', [
        'labels' => ['name' => 'Industries', 'singular_name' => 'Industry'],
        'public' => true,
        'hierarchical' => true,
        'show_in_rest' => true,
        'rewrite' => ['slug' => 'industry'],
    ]);
});

/** Advanced Custom Fields are saved as JSON next to this file, so a field change is a reviewed file change and a sync moves it. */
add_filter('acf/settings/save_json', function () {
    return __DIR__ . '/lab-core-acf-json';
});
add_filter('acf/settings/load_json', function ($paths) {
    unset($paths[0]);
    $paths[] = __DIR__ . '/lab-core-acf-json';
    return $paths;
});

/** Filter: a short excerpt on the archive, so the cards stay even. */
add_filter('excerpt_length', function () {
    return 28;
}, 99);

/** One card. Output is escaped at the point of printing, and a missing field prints nothing rather than a blank label. */
function lab_core_render_card($post)
{
    $client = function_exists('get_field') ? get_field('client_name', $post->ID) : '';
    $result = function_exists('get_field') ? get_field('headline_result', $post->ID) : '';
    $terms = wp_get_post_terms($post->ID, 'industry', ['fields' => 'names']);
    echo '<article class="case-card">';
    echo '<h2><a href="' . esc_url(get_permalink($post)) . '">' . esc_html(get_the_title($post)) . '</a></h2>';
    $meta = array_filter([$client, $terms ? implode(', ', $terms) : '']);
    if ($meta) {
        echo '<p class="case-meta">' . esc_html(implode(' | ', $meta)) . '</p>';
    }
    if ($result) {
        echo '<p class="case-result">' . esc_html($result) . '</p>';
    }
    echo '</article>';
}

/** The three newest case studies as cards. A theme calls this from whatever hook its parent gives it, on the front page only. */
function lab_core_front_cards()
{
    if (!is_front_page()) {
        return;
    }
    $q = new WP_Query(['post_type' => 'case_study', 'posts_per_page' => 3, 'no_found_rows' => true]);
    foreach ($q->posts as $p) {
        lab_core_render_card($p);
    }
    wp_reset_postdata();
}

/** Action: after a case study is saved, a transient that the front page might cache is cleared. */
add_action('save_post_case_study', function () {
    delete_transient('lab_core_front_cards');
});

/** Filter: the single case study shows its result first, ahead of the body, through the content filter. */
add_filter('the_content', function ($content) {
    if (!is_singular('case_study') || !in_the_loop() || !is_main_query() || !function_exists('get_field')) {
        return $content;
    }
    $result = get_field('headline_result');
    if (!$result) {
        return $content;
    }
    return '<p class="case-result">' . esc_html($result) . '</p>' . $content;
});

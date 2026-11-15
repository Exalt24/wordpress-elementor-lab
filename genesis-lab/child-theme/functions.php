<?php
/**
 * Lab Child: a Genesis child theme.
 * Four things live here and nothing else: the Genesis bootstrap, a case study post type with a taxonomy,
 * Advanced Custom Fields kept in code (acf-json), and the hooks, actions and filters that shape the front page.
 */
include_once get_template_directory() . '/lib/init.php';

add_action('after_setup_theme', function () {
    add_theme_support('html5', ['caption', 'comment-form', 'comment-list', 'gallery', 'search-form']);
    add_theme_support('genesis-responsive-viewport');
    add_theme_support('genesis-accessibility', ['skip-links', 'headings', 'drop-down-menu', 'search-form']);
});

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

/** Advanced Custom Fields are saved as JSON in this theme, so a field change is a reviewed file change and a sync moves it. */
add_filter('acf/settings/save_json', function () {
    return get_stylesheet_directory() . '/acf-json';
});
add_filter('acf/settings/load_json', function ($paths) {
    unset($paths[0]);
    $paths[] = get_stylesheet_directory() . '/acf-json';
    return $paths;
});

/** Filter: the footer credit line. */
add_filter('genesis_footer_creds_text', function () {
    return 'Lab Child on Genesis. Built and checked in a local Docker lab.';
});

/** Filter: a short excerpt on the archive, so the cards stay even. */
add_filter('excerpt_length', function () {
    return 28;
}, 99);

/** The front page lists the three newest case studies, placed with a Genesis hook and not a template fork. */
add_action('genesis_before_loop', function () {
    if (!is_front_page()) {
        return;
    }
    $q = new WP_Query(['post_type' => 'case_study', 'posts_per_page' => 3, 'no_found_rows' => true]);
    foreach ($q->posts as $p) {
        lab_child_render_card($p);
    }
    wp_reset_postdata();
});

/** One card. Output is escaped at the point of printing, and a missing field prints nothing rather than a blank label. */
function lab_child_render_card($post)
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

/** Action: after a case study is saved, a transient that the front page might cache is cleared. */
add_action('save_post_case_study', function () {
    delete_transient('lab_child_front_cards');
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

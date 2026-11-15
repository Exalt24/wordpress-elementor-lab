<?php
/**
 * Plugin Name: Lab Core
 * Description: The site's functionality, kept out of any theme so a theme change cannot lose it: a case study post type, an industry taxonomy, Advanced Custom Fields saved as JSON, the card renderer, the industry filter (an admin-ajax handler and its script) and the filters that shape a single case study.
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

/** How many cards a grid shows, on first load and after a filter. */
const LAB_CORE_CARD_LIMIT = 6;

/** The newest case studies, all of them or only one industry's. WP_Query reads the database; the industry goes in through a tax_query, never into SQL text. */
function lab_core_cases_query($industry_slug = '')
{
    // post_status is named on purpose: inside admin-ajax is_admin() is true, and a query with no status then returns drafts to a visitor
    $args = ['post_type' => 'case_study', 'post_status' => 'publish', 'posts_per_page' => LAB_CORE_CARD_LIMIT, 'no_found_rows' => true];
    if ($industry_slug !== '') {
        $args['tax_query'] = [['taxonomy' => 'industry', 'field' => 'slug', 'terms' => [$industry_slug]]];
    }
    return new WP_Query($args);
}

/** The industry buttons. Real buttons that report their state with aria-pressed. The bar starts hidden and the script shows it, so with JavaScript off the page shows the full grid and no dead buttons. */
function lab_core_filter_bar()
{
    $terms = get_terms(['taxonomy' => 'industry', 'hide_empty' => true]);
    if (is_wp_error($terms) || !$terms) {
        return;
    }
    echo '<div class="case-filter" role="group" aria-label="Filter case studies by industry" hidden>';
    echo '<button type="button" class="case-filter-button" aria-pressed="true" data-industry="">All</button>';
    foreach ($terms as $term) {
        echo '<button type="button" class="case-filter-button" aria-pressed="false" data-industry="' . esc_attr($term->slug) . '">' . esc_html($term->name) . '</button>';
    }
    echo '</div>';
}

/** The newest case studies as cards under the industry buttons. A theme calls this from whatever hook its parent gives it, on the front page only. */
function lab_core_front_cards()
{
    if (!is_front_page()) {
        return;
    }
    lab_core_filter_bar();
    echo '<div id="lab-case-grid" class="case-grid" aria-busy="false">';
    $q = lab_core_cases_query();
    foreach ($q->posts as $p) {
        lab_core_render_card($p);
    }
    wp_reset_postdata();
    echo '</div>';
}

/** The filter's script and style, with the ajax address and a nonce handed over by wp_localize_script. jQuery is a dependency, so WordPress's own copy loads first. */
add_action('wp_enqueue_scripts', function () {
    if (!is_front_page()) {
        return;
    }
    $dir = __DIR__ . '/lab-core-assets/';
    $url = plugins_url('lab-core-assets/', __FILE__);
    wp_enqueue_style('lab-core-filter', $url . 'cases-filter.css', [], (string) filemtime($dir . 'cases-filter.css'));
    wp_enqueue_script('lab-core-filter', $url . 'cases-filter.js', ['jquery'], (string) filemtime($dir . 'cases-filter.js'), true);
    wp_localize_script('lab-core-filter', 'labCoreFilter', [
        'ajaxUrl' => admin_url('admin-ajax.php'),
        'action' => 'lab_core_filter_cases',
        'nonce' => wp_create_nonce('lab_core_filter'),
    ]);
});

/**
 * The admin-ajax handler behind the industry buttons. A missing or wrong nonce is a 403 with a JSON error. The slug is sanitized, and a slug
 * that is not an industry is an empty result and not an error, so the endpoint tells a stranger nothing about the database.
 */
function lab_core_ajax_filter_cases()
{
    if (!check_ajax_referer('lab_core_filter', 'nonce', false)) {
        wp_send_json_error(['message' => 'The page is out of date. Reload it and try again.'], 403);
    }
    $raw = isset($_POST['industry']) ? $_POST['industry'] : '';
    $slug = is_string($raw) ? sanitize_title(wp_unslash($raw)) : '';
    $posts = [];
    // nothing sent means every industry; something sent that is not an industry (or sanitizes to nothing) means an empty list
    if (is_string($raw) && ($raw === '' || ($slug !== '' && term_exists($slug, 'industry')))) {
        $posts = lab_core_cases_query($slug)->posts;
    }
    ob_start();
    foreach ($posts as $p) {
        lab_core_render_card($p);
    }
    if (!$posts) {
        echo '<p class="case-empty">' . esc_html($slug === '' ? 'No case studies yet.' : 'No case studies for ' . $slug . ' yet.') . '</p>';
    }
    $html = ob_get_clean();
    wp_reset_postdata();
    wp_send_json_success(['industry' => esc_html($slug), 'count' => count($posts), 'html' => $html]);
}
add_action('wp_ajax_lab_core_filter_cases', 'lab_core_ajax_filter_cases');
add_action('wp_ajax_nopriv_lab_core_filter_cases', 'lab_core_ajax_filter_cases');

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

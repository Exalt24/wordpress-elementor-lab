<?php
/**
 * Lab Classic: a child theme of a plain classic parent (Twenty Twenty-One). Presentation only, the same job lab-child does on Genesis:
 * the cards go in through WordPress's own loop_start action and the credit line through wp_footer. The case study type, the fields and
 * the content filters live in mu-plugins/lab-core.php, shared with the Genesis child.
 */
add_action('wp_enqueue_scripts', function () {
    wp_enqueue_style('lab-classic-parent', get_template_directory_uri() . '/style.css', [], wp_get_theme(get_template())->get('Version'));
    wp_enqueue_style('lab-classic', get_stylesheet_uri(), ['lab-classic-parent'], wp_get_theme()->get('Version'));
});

/** The cards open the main loop on the front page, once. */
add_action('loop_start', function ($query) {
    static $done = false;
    if ($done || !$query->is_main_query() || !is_front_page()) {
        return;
    }
    $done = true;
    lab_core_front_cards();
});

/** The footer credit line. */
add_action('wp_footer', function () {
    echo '<p class="lab-credit">Lab Classic on a plain parent theme. Built and checked in a local Docker lab.</p>';
});

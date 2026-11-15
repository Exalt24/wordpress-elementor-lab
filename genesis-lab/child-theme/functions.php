<?php
/**
 * Lab Child: a Genesis child theme. Presentation only: the Genesis bootstrap, theme support and the Genesis hooks that place the cards and the footer credit.
 * The case study type, the fields and the content filters live in mu-plugins/lab-core.php, so a theme change cannot lose them.
 */
include_once get_template_directory() . '/lib/init.php';

add_action('after_setup_theme', function () {
    add_theme_support('html5', ['caption', 'comment-form', 'comment-list', 'gallery', 'search-form']);
    add_theme_support('genesis-responsive-viewport');
    add_theme_support('genesis-accessibility', ['skip-links', 'headings', 'drop-down-menu', 'search-form']);
});

/** Filter: the footer credit line. */
add_filter('genesis_footer_creds_text', function () {
    return 'Lab Child on Genesis. Built and checked in a local Docker lab.';
});

/** The cards go in with a Genesis hook and not a template fork. */
add_action('genesis_before_loop', 'lab_core_front_cards');

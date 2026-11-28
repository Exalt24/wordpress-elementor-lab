<?php
/**
 * Plugin Name: Elementor draft route (lab)
 * Description: Three REST routes that save a generated Elementor element tree as a draft page, delete a draft that failed its check, and promote a draft whose stored data still matches the hash that was verified.
 *
 * POST   /wp-json/lab/v1/elementor-draft             {title, slug, excerpt, data_json}  -> creates or replaces the draft, returns {id, hash}
 * DELETE /wp-json/lab/v1/elementor-draft/<id>                                          -> deletes a draft this route made
 * POST   /wp-json/lab/v1/elementor-draft/<id>/promote {verified_hash}                  -> publishes it when the stored data hashes to verified_hash
 *
 * Needs an authenticated user who can edit pages (an application password in the lab). It only touches posts it created (meta _lab_generated).
 */
if (!defined('ABSPATH')) {
    exit;
}

const LAB_ELEMENTOR_MAX_BYTES = 1048576;
const LAB_ELEMENTOR_MAX_DEPTH = 12;

/** Every element must carry the keys Elementor's own export carries. Returns an error string or null. */
function lab_elementor_check_tree($nodes, $depth = 0)
{
    if (is_array($nodes) && !$nodes) {
        return null; // a leaf's empty elements list is fine at any depth
    }
    if ($depth > LAB_ELEMENTOR_MAX_DEPTH) {
        return 'tree is nested deeper than ' . LAB_ELEMENTOR_MAX_DEPTH;
    }
    if (!is_array($nodes) || !array_is_list($nodes)) {
        return 'elements must be a list';
    }
    foreach ($nodes as $node) {
        if (!is_array($node) || !isset($node['id'], $node['elType'], $node['settings'], $node['elements'])) {
            return 'an element lacks id, elType, settings or elements';
        }
        // The D modifier: without it $ also matches before a final newline, and "abcdef0\n" would pass.
        if (!is_string($node['id']) || !preg_match('/^[0-9a-f]{7}$/D', $node['id'])) {
            return 'an element id is not 7 hex characters';
        }
        if (!in_array($node['elType'], array('container', 'widget'), true)) {
            return 'unknown elType ' . (is_string($node['elType']) ? $node['elType'] : '?');
        }
        if ($node['elType'] === 'widget' && empty($node['widgetType'])) {
            return 'a widget has no widgetType';
        }
        if (!is_array($node['settings'])) {
            return 'settings must be an object';
        }
        $err = lab_elementor_check_tree($node['elements'], $depth + 1);
        if ($err) {
            return $err;
        }
    }
    return null;
}

function lab_elementor_can()
{
    return current_user_can('edit_pages');
}

function lab_elementor_owned_draft($id)
{
    $post = get_post((int) $id);
    if (!$post || $post->post_type !== 'page' || !get_post_meta($post->ID, '_lab_generated', true)) {
        return null;
    }
    return $post;
}

function lab_elementor_clear_css($post_id)
{
    delete_post_meta($post_id, '_elementor_css');
    if (class_exists('\Elementor\Plugin') && isset(\Elementor\Plugin::$instance->files_manager)) {
        \Elementor\Plugin::$instance->files_manager->clear_cache();
    }
}

add_action('rest_api_init', function () {
    register_rest_route('lab/v1', '/elementor-draft', array(
        'methods' => 'POST',
        'permission_callback' => 'lab_elementor_can',
        'callback' => function (WP_REST_Request $req) {
            $json = $req->get_param('data_json');
            if (!is_string($json) || $json === '' || strlen($json) > LAB_ELEMENTOR_MAX_BYTES) {
                return new WP_Error('lab_bad_data', 'data_json must be a string of at most ' . LAB_ELEMENTOR_MAX_BYTES . ' bytes', array('status' => 400));
            }
            $tree = json_decode($json, true);
            $err = is_array($tree) ? lab_elementor_check_tree($tree) : 'data_json is not a JSON list';
            if ($err) {
                return new WP_Error('lab_bad_tree', $err, array('status' => 400));
            }
            $slug = sanitize_title((string) $req->get_param('slug'));
            $title = sanitize_text_field((string) $req->get_param('title'));
            if ($slug === '' || $title === '') {
                return new WP_Error('lab_bad_page', 'title and slug are required', array('status' => 400));
            }
            // A page with this slug that this route did not make is never replaced.
            $existing = get_posts(array('post_type' => 'page', 'name' => $slug, 'post_status' => 'any', 'numberposts' => 1));
            $id = 0;
            if ($existing) {
                if (!get_post_meta($existing[0]->ID, '_lab_generated', true)) {
                    return new WP_Error('lab_slug_taken', 'a page with this slug exists and was not generated here', array('status' => 409));
                }
                $id = $existing[0]->ID;
            }
            $args = array(
                'post_type' => 'page',
                'post_status' => 'draft',
                'post_title' => $title,
                'post_name' => $slug,
                'post_excerpt' => sanitize_textarea_field((string) $req->get_param('excerpt')),
            );
            if ($id) {
                $args['ID'] = $id;
                $id = wp_update_post($args, true);
            } else {
                $id = wp_insert_post($args, true);
            }
            if (is_wp_error($id)) {
                return $id;
            }
            update_post_meta($id, '_lab_generated', 1);
            update_post_meta($id, '_elementor_data', wp_slash($json));
            update_post_meta($id, '_elementor_edit_mode', 'builder');
            update_post_meta($id, '_elementor_template_type', 'wp-page');
            update_post_meta($id, '_wp_page_template', 'elementor_canvas');
            if (defined('ELEMENTOR_VERSION')) {
                update_post_meta($id, '_elementor_version', ELEMENTOR_VERSION);
            }
            lab_elementor_clear_css($id);
            return array('id' => (int) $id, 'status' => 'draft', 'hash' => hash('sha256', (string) get_post_meta($id, '_elementor_data', true)));
        },
    ));

    register_rest_route('lab/v1', '/elementor-draft/(?P<id>\d+)', array(
        'methods' => 'DELETE',
        'permission_callback' => 'lab_elementor_can',
        'callback' => function (WP_REST_Request $req) {
            $post = lab_elementor_owned_draft($req['id']);
            if (!$post) {
                return new WP_Error('lab_not_ours', 'not a page this route generated', array('status' => 404));
            }
            if ($post->post_status !== 'draft') {
                return new WP_Error('lab_not_draft', 'only a draft is deleted here', array('status' => 409));
            }
            wp_delete_post($post->ID, true);
            return array('deleted' => (int) $post->ID);
        },
    ));

    register_rest_route('lab/v1', '/elementor-draft/(?P<id>\d+)/promote', array(
        'methods' => 'POST',
        'permission_callback' => 'lab_elementor_can',
        'callback' => function (WP_REST_Request $req) {
            $post = lab_elementor_owned_draft($req['id']);
            if (!$post || $post->post_status !== 'draft') {
                return new WP_Error('lab_not_ours', 'not a draft this route generated', array('status' => 404));
            }
            $stored = hash('sha256', (string) get_post_meta($post->ID, '_elementor_data', true));
            $given = (string) $req->get_param('verified_hash');
            if ($given === '' || !hash_equals($stored, $given)) {
                return new WP_Error('lab_not_verified', 'the stored data does not match the verified hash, nothing is promoted', array('status' => 409));
            }
            wp_update_post(array('ID' => $post->ID, 'post_status' => 'publish'));
            lab_elementor_clear_css($post->ID);
            return array('id' => (int) $post->ID, 'status' => 'publish');
        },
    ));
});

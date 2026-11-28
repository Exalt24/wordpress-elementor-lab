<?php
// Offline tests for the element tree check in wp/mu-plugins/elementor-draft-route.php.  php tests/test_elementor_route.php
// The route file is loaded with WordPress functions stubbed out; only the pure check function is exercised.
define('ABSPATH', __DIR__);
function add_action($hook, $cb) {}
function current_user_can($cap) { return true; }
require __DIR__ . '/../wp/mu-plugins/elementor-draft-route.php';

$failures = 0;
$checks = 0;
function check($label, $actual, $expected)
{
    global $failures, $checks;
    $checks++;
    if ($actual !== $expected) {
        $failures++;
        echo "FAIL: $label\n  expected " . var_export($expected, true) . "\n  got      " . var_export($actual, true) . "\n";
    }
}

function widget($id = 'abcdef0', $extra = array())
{
    return array_merge(array('id' => $id, 'elType' => 'widget', 'widgetType' => 'heading', 'settings' => array('title' => 'x'), 'elements' => array()), $extra);
}
function container($id, $children = array())
{
    return array('id' => $id, 'elType' => 'container', 'isInner' => false, 'settings' => array(), 'elements' => $children);
}

check('a widget in a container is accepted', lab_elementor_check_tree(array(container('1234567', array(widget())))), null);
check('an empty list is accepted', lab_elementor_check_tree(array()), null);
check('empty settings (an empty JSON object decodes to an empty array) are accepted', lab_elementor_check_tree(array(container('1234567'))), null);

foreach (array('id', 'elType', 'settings', 'elements') as $key) {
    $w = widget();
    unset($w[$key]);
    check("missing $key is refused for what it is", lab_elementor_check_tree(array($w)), 'an element lacks id, elType, settings or elements');
    $w = widget();
    $w[$key] = null;
    check("null $key is refused for what it is", lab_elementor_check_tree(array($w)), 'an element lacks id, elType, settings or elements');
}

foreach (array('ABCDEF0', 'abcdef', 'abcdef01', 'abcdefg', '', 'abc def', "abcdef0\n", 12345678, null, array('abcdef0')) as $bad) {
    check('id ' . var_export($bad, true) . ' is refused', lab_elementor_check_tree(array(widget($bad))) !== null, true);
}
foreach (array('0000000', 'abcdef0', 'fffffff') as $good) {
    check("id $good is accepted", lab_elementor_check_tree(array(widget($good))), null);
}

foreach (array('section', 'column', 'Widget', 'CONTAINER', '', 'inner-section', 5, true) as $bad) {
    $w = widget();
    $w['elType'] = $bad;
    check('elType ' . var_export($bad, true) . ' is refused', lab_elementor_check_tree(array($w)) !== null, true);
}

$w = widget();
unset($w['widgetType']);
check('a widget without widgetType is refused', lab_elementor_check_tree(array($w)) !== null, true);
$w['widgetType'] = '';
check('a widget with an empty widgetType is refused', lab_elementor_check_tree(array($w)) !== null, true);
check('a container needs no widgetType', lab_elementor_check_tree(array(container('1234567'))), null);

foreach (array('text', 5, true) as $bad) {
    $w = widget();
    $w['settings'] = $bad;
    check('settings of ' . var_export($bad, true) . ' are refused', lab_elementor_check_tree(array($w)) !== null, true);
}
$w = widget();
$w['elements'] = array('a' => widget('1111111'));
check('elements as an object are refused', lab_elementor_check_tree(array($w)) !== null, true);
check('the top level as an object is refused', lab_elementor_check_tree(array('a' => widget())) !== null, true);
check('a node that is not an array is refused', lab_elementor_check_tree(array('text')) !== null, true);
check('a bad element nested three deep is found', lab_elementor_check_tree(array(container('1111111', array(container('2222222', array(container('3333333', array(widget('ZZZZZZZ'))))))))) !== null, true);

$deep = widget('aaaaaaa');
for ($i = 0; $i < LAB_ELEMENTOR_MAX_DEPTH; $i++) {
    $deep = container(str_pad(dechex($i), 7, '0', STR_PAD_LEFT), array($deep));
}
check('a tree at the depth limit is accepted', lab_elementor_check_tree(array($deep)), null);
check('a tree one level past the depth limit is refused', lab_elementor_check_tree(array(container('fffffff', array($deep)))) !== null, true);

$json = json_encode(array(container('1234567', array(widget()))));
check('a tree survives a JSON round trip', lab_elementor_check_tree(json_decode($json, true)), null);
$emptySettings = json_decode('[{"id":"1234567","elType":"container","isInner":false,"settings":{},"elements":[]}]', true);
check('a decoded empty settings object is accepted', lab_elementor_check_tree($emptySettings), null);

echo $failures === 0 ? "elementor route: $checks checks passed\n" : "elementor route: $failures of $checks checks FAILED\n";
exit($failures === 0 ? 0 : 1);

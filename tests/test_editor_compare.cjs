// Offline tests for the comparison the editor check relies on.  node tests/test_editor_compare.cjs
// Each change that the real editor could make to a tree that was sent (drop, rename, reorder, alter, retype) must be reported,
// and the editor adding its own default settings must not be.
const assert = require('assert');
const path = require('path');
const { compareTree, contains, countElements } = require(path.join(__dirname, '..', 'scripts', 'editor_compare.cjs'));

const base = () => [{
  id: 'aaaaaaa', elType: 'container', isInner: false, settings: { flex_direction: 'column', padding: { unit: 'px', top: '72' } },
  elements: [
    { id: 'bbbbbbb', elType: 'widget', widgetType: 'heading', settings: { title: 'One', header_size: 'h1' }, elements: [] },
    { id: 'ccccccc', elType: 'widget', widgetType: 'button', settings: { text: 'Go', link: { url: '#a' } }, elements: [] },
  ],
}];
const clone = (x) => JSON.parse(JSON.stringify(x));
const run = (have) => { const out = []; compareTree(base(), have, '', out); return out; };

let n = 0;
const test = (name, fn) => { fn(); n++; };

test('an identical tree has no mismatch', () => assert.deepStrictEqual(run(base()), []));

test('the editor adding default settings is not a mismatch', () => {
  const h = base();
  h[0].settings.flex_align_items = 'center';
  h[0].elements[0].settings.typography_typography = '';
  h[0].elements[0].extraKey = 1;
  assert.deepStrictEqual(run(h), []);
});

test('numbers and numeric strings compare as the same value', () => {
  const h = base();
  h[0].settings.padding.top = 72;
  assert.deepStrictEqual(run(h), []);
});

const breaks = {
  'a dropped widget': (h) => h[0].elements.pop(),
  'a dropped container': () => [],
  'an extra widget': (h) => h[0].elements.push({ id: 'ddddddd', elType: 'widget', widgetType: 'heading', settings: {}, elements: [] }),
  'reordered widgets': (h) => h[0].elements.reverse(),
  'a changed id': (h) => { h[0].elements[0].id = 'eeeeeee'; },
  'a changed elType': (h) => { h[0].elType = 'widget'; },
  'a changed widget type': (h) => { h[0].elements[0].widgetType = 'text-editor'; },
  'a dropped widget type': (h) => { delete h[0].elements[1].widgetType; },
  'a changed setting': (h) => { h[0].elements[0].settings.title = 'Two'; },
  'a dropped setting': (h) => { delete h[0].elements[0].settings.header_size; },
  'a dropped nested setting': (h) => { delete h[0].settings.padding.top; },
  'a changed nested setting': (h) => { h[0].elements[1].settings.link.url = '#b'; },
  'a setting turned into text': (h) => { h[0].settings.padding = 'x'; },
  'a setting turned into null': (h) => { h[0].settings.padding = null; },
  'a missing settings object': (h) => { delete h[0].elements[0].settings; h[0].elements[0].settings = undefined; },
  'elements turned into null': (h) => { h[0].elements = null; },
};
for (const [label, change] of Object.entries(breaks)) {
  test('reports ' + label, () => {
    const h = clone(base());
    const replaced = change(h);
    const have = label === 'a dropped container' ? [] : h;
    void replaced;
    const found = run(have);
    assert.ok(found.length > 0, label + ' was not reported');
  });
}

test('a list setting of a different length is reported', () => {
  const out = [];
  contains({ icon_list: [{ text: 'a' }, { text: 'b' }] }, { icon_list: [{ text: 'a' }] }, 'p', out);
  assert.strictEqual(out.length, 1);
  assert.match(out[0], /list length 2 became 1/);
});

test('a mismatch names the element and the setting', () => {
  const h = clone(base());
  h[0].elements[1].settings.text = 'Stop';
  assert.deepStrictEqual(run(h), ['/0/1.settings.text: sent "Go", the editor holds "Stop"']);
});

test('elements are counted at every depth', () => assert.strictEqual(countElements(base()), 3));

console.log('editor compare: ' + n + ' checks passed');

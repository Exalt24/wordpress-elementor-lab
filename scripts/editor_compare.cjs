// LIFESPAN: permanent
// The comparison the editor check relies on, kept apart from the browser so it can be tested offline (tests/test_editor_compare.cjs).
// `want` is the element tree that was sent, `have` is what the real Elementor editor holds after loading it.

// Everything in `want` must be in `have` with the same value; `have` may carry extra keys (the editor adds its own defaults).
function contains(want, have, path, out) {
  if (want !== null && typeof want === 'object') {
    if (have === null || typeof have !== 'object') { out.push(path + ': sent an object, the editor holds ' + JSON.stringify(have)); return; }
    if (Array.isArray(want)) {
      if (!Array.isArray(have) || have.length !== want.length) { out.push(path + ': list length ' + want.length + ' became ' + (Array.isArray(have) ? have.length : 'not a list')); return; }
      want.forEach((w, i) => contains(w, have[i], path + '[' + i + ']', out));
      return;
    }
    Object.keys(want).forEach((k) => contains(want[k], have[k], path + '.' + k, out));
    return;
  }
  // The editor stores numbers and numeric strings alike in some controls, so compare as text.
  if (String(want) !== String(have)) out.push(path + ': sent ' + JSON.stringify(want) + ', the editor holds ' + JSON.stringify(have));
}

// Same elements in the same order with the same id, type and widget, each holding every setting that was sent.
function compareTree(want, have, path, out) {
  if (!Array.isArray(have) || have.length !== want.length) { out.push(path + ': ' + want.length + ' elements sent, ' + (Array.isArray(have) ? have.length : 0) + ' in the editor'); return; }
  want.forEach((w, i) => {
    const h = have[i], here = path + '/' + i;
    ['id', 'elType', 'widgetType'].forEach((k) => { if ((w[k] || null) !== (h[k] || null)) out.push(here + '.' + k + ': sent ' + w[k] + ', the editor holds ' + h[k]); });
    contains(w.settings, h.settings || {}, here + '.settings', out);
    compareTree(w.elements, h.elements || [], here, out);
  });
}

function countElements(nodes) { return nodes.reduce((a, n) => a + 1 + countElements(n.elements || []), 0); }

module.exports = { contains, compareTree, countElements };

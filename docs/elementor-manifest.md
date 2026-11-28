---
type: reference
updated: 2026-11-28
---

# Layout manifest to Elementor draft

*A model is allowed to return a small JSON manifest. A plain builder turns it into Elementor's element tree, the lab saves it as a draft, and the real Elementor editor has to read the same elements back before anything is promoted.*

![The generated draft open in the Elementor editor, titled as a draft, with the hero, the three cards and five containers in the Structure panel](elementor-generated-draft.png)

## Why the model never writes `_elementor_data`

`_elementor_data` is a JSON string in the post meta. Every element carries an `id`, an `elType`, a `settings` object and an `elements` list, containers carry `isInner`, widgets carry `widgetType`, and a setting such as a colour or a padding has Elementor's own shape (`{"unit":"px","top":"72",...,"isLinked":false}`). A model asked for that string directly gets one of those wrong now and then, and the editor does not complain: it drops what it does not know and opens a page with parts missing. So the model returns the smaller thing.

## The parts

| File | What it does |
|---|---|
| `elementor/layout.schema.json` | The manifest's JSON schema: sections, five block kinds (heading, text, button, icon list, columns), every colour, size, gap, padding, weight and radius written as the **name** of a design token that matches `^[a-z][a-z0-9_]{0,23}$`. A raw `#ff0000`, `12px` or `Ink` does not validate. |
| `elementor/design-tokens.json` | The locked tokens: eight colours, four gaps, four paddings, font sizes and weights, two radii and the content width. |
| `elementor/seller-audit.layout.json` | The manifest for the lab's landing page: five sections, 28 elements. |
| `scripts/manifest_to_elementor.py` | Checks the manifest against the schema, resolves every token name from the tokens file, allow-lists the copy (plain text is escaped, HTML keeps only `p`, `a` with an http, https, mailto, anchor or site-path address, `strong`, `em`, `br`, `ul`, `ol`, `li`) and returns the element tree with ids made from a hash of the page slug and the element's position. Standard library only. |
| `wp/mu-plugins/elementor-draft-route.php` | Three REST routes under `lab/v1`. `POST /elementor-draft` checks the tree again (ids are seven hex characters, `elType` is container or widget, widgets have a `widgetType`, depth at most 12, at most a megabyte), saves a draft with `_elementor_data`, `_elementor_edit_mode`, `_elementor_template_type`, `_elementor_version` and the canvas template, and clears Elementor's cached CSS. `DELETE /elementor-draft/<id>` removes a draft the route made. `POST /elementor-draft/<id>/promote` publishes it only when the stored data hashes to the hash that was verified. |
| `scripts/verify_in_editor.cjs`, `scripts/editor_compare.cjs` | Logs in to the lab, opens the draft in the real editor in headless Chromium, waits for the element count to stop moving, then reads the elements back from the editor's own models and compares them with what was sent: same ids, types, widgets and order, every sent setting present with the same value (the editor may add its own defaults), every widget type known to the editor. |
| `scripts/elementor_draft.py` | The pipeline: build, save the draft, run the editor check, then delete the draft on a failure or leave it a draft (`--promote` publishes it). |

## Checked against what Elementor exports

`tests/fixtures/elementor_export_4.4.2.json` is `_elementor_data` read with WP-CLI from the lab page that `scripts/build_page.cjs` built **inside the editor** with Elementor's own command API (Elementor 4.4.2). `tests/test_manifest_to_elementor.py` builds the sample manifest and compares it with that export. They are equal except for the element ids and the HTML of the text widgets, which the editor rewrites. The same test file has the container and widget key sets, the `isInner` rule, id uniqueness, and a table generated from the list of token fields that tries each field with an unknown name, eight raw values and every known name.

## What a run looks like

```
$ python scripts/elementor_draft.py push elementor/seller-audit.layout.json
draft 11 saved, hash 7690375c22bde7df
EDITOR CHECK PASSED: 28 elements read back from the real editor match what was sent
left as a draft (use --promote to publish)
```

Two trees the editor cannot keep, pushed with `push-tree`:

```
== an unknown widget type
draft 12 saved, hash 496e54dffe340e19
EDITOR CHECK FAILED, 1 problem(s):
  /0/0: 3 elements sent, 2 in the editor
draft 12 deleted (200), nothing promoted
== a duplicate element id
draft 13 saved, hash 9d4444a5f3aa9002
EDITOR CHECK FAILED, 1 problem(s):
  /0/0: 3 elements sent, 2 in the editor
draft 13 deleted (200), nothing promoted
```

The editor drops an element with a widget type it does not have and the second of two elements with the same id, and says nothing. The count read back is what shows it. `tests/live_elementor_pipeline.py` runs all of this against the lab (25 checks, last run 25 of 25, output in [elementor_pipeline_run.txt](elementor_pipeline_run.txt)): the good manifest, the promotion, the two broken trees, a raw colour refused before any request, and the route's refusals (legacy `section` element, data that is not JSON or not a list, data over a megabyte, empty title or slug, a page it did not generate, a wrong or missing hash, no credentials).

## Tests

| Check | Count |
|---|---|
| `tests/test_manifest_to_elementor.py` (builder, schema subset, copy rules, command line) | 35 tests |
| `tests/test_editor_compare.cjs` (what the editor check reports) | 22 checks |
| `tests/test_elementor_route.php` (the route's tree check, in PHP) | 46 checks |
| `tests/live_elementor_pipeline.py` (needs the running lab, not in CI) | 25 checks |
| `tests/mutation_check.py` | 46 more guards broken one at a time, each turned a test red |

The tests found three defects while they were being written, all fixed: the route accepted an id with a trailing newline (PHP's `$` matches before a final newline), the route refused an empty `elements` list on a node at the depth limit, and the schema checker accepted `true` where the schema said `1` (Python's `True == 1`). The same newline case was then fixed in the schema checker's patterns.

## One error that is not ours

The editor page throws `Cannot read properties of undefined (reading 'hasClass')` in headless Chromium. Its stack is in WordPress's own `wp-auth-check.js`, and the same error appears on the page built in the editor itself, so the verifier ignores an error only when its stack is in that script. Any other page or console error fails the check.

## Limits

- The builder covers five block kinds. Another Elementor widget needs a schema entry and a builder branch, and the conformance test needs an export that contains it.
- The check proves the editor loads the draft and holds every element and setting that was sent. It does not judge how the page looks: the editor screenshot above and the published page are for that.
- A model is not called in this repository. The sample manifest is written by hand to match the lab's page; anything that can return JSON for the schema can feed the builder.
- Built and tested against a local WordPress 6 with Elementor 4.4.2 (free) and the Hello Elementor theme. The route authenticates with an application password, which WordPress only offers over plain http when `WP_ENVIRONMENT_TYPE` is `local`, so `scripts/setup.sh` sets that. It is a lab route and not meant for a public site.

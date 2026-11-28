"""Offline tests for the manifest to Elementor builder.  python tests/test_manifest_to_elementor.py

Three groups: the output matches what Elementor itself exported for the same page (tests/fixtures/elementor_export_4.4.2.json, taken from
the editor with WP-CLI), every refusal fires for every field it should (tables generated from one list of fields), and the copy rules
(HTML allow list, addresses) turn hostile input away. Nothing here needs WordPress or a browser.
"""
import copy
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import manifest_to_elementor as m2e  # noqa: E402

SAMPLE = os.path.join(ROOT, "elementor", "seller-audit.layout.json")
FIXTURE = os.path.join(HERE, "fixtures", "elementor_export_4.4.2.json")


def sample():
    return m2e.load_json(SAMPLE)


def walk(nodes):
    for n in nodes:
        yield n
        yield from walk(n["elements"])


def normalise(tree):
    """Ids are generated, and the editor rewrites the HTML of a text widget, so those two are masked before comparing."""
    tree = copy.deepcopy(tree)
    for n in walk(tree):
        n["id"] = "ID"
        if n.get("widgetType") == "text-editor":
            n["settings"]["editor"] = "HTML"
        if n.get("widgetType") == "icon-list":
            for item in n["settings"]["icon_list"]:
                item["_id"] = "ID"
    return tree


# One manifest that sets every token field once, and the list of those fields as (path, token group).
KITCHEN_SINK = {
    "version": 1,
    "page": {"title": "Kitchen sink", "slug": "kitchen-sink"},
    "sections": [{
        "background": "ink", "padding": "section", "gap": "sm", "anchor": "top",
        "blocks": [
            {"widget": "heading", "text": "Head", "level": "h3", "align": "left", "color": "white", "size": "h1", "weight": "bold", "line_height": "tight"},
            {"widget": "text", "text": "Body", "color": "muted", "size": "body_lg"},
            {"widget": "button", "text": "Go", "url": "#top", "background": "accent", "color": "white", "size": "button", "weight": "black", "radius": "button", "padding": "button"},
            {"widget": "icon_list", "items": ["One"], "color": "ink", "icon_color": "accent"},
            {"widget": "columns", "gap": "md", "columns": [
                {"width": 40, "background": "soft", "gap": "xs", "blocks": [{"widget": "heading", "text": "A"}]},
                {"width": 40, "background": "soft", "gap": "lg", "blocks": [{"widget": "text", "text": "B"}]}]},
        ],
    }]}
S = ("sections", 0)
B = ("blocks",)
TOKEN_FIELDS = [
    (S + ("background",), "color"), (S + ("padding",), "padding"), (S + ("gap",), "gap"),
    (S + B + (0, "color"), "color"), (S + B + (0, "size"), "font_size"), (S + B + (0, "weight"), "font_weight"), (S + B + (0, "line_height"), "line_height"),
    (S + B + (1, "color"), "color"), (S + B + (1, "size"), "font_size"),
    (S + B + (2, "background"), "color"), (S + B + (2, "color"), "color"), (S + B + (2, "size"), "font_size"), (S + B + (2, "weight"), "font_weight"),
    (S + B + (2, "radius"), "radius"), (S + B + (2, "padding"), "padding"),
    (S + B + (3, "color"), "color"), (S + B + (3, "icon_color"), "color"),
    (S + B + (4, "gap"), "gap"),
    (S + B + (4, "columns", 0, "background"), "color"), (S + B + (4, "columns", 0, "gap"), "gap"),
]


def with_value(manifest, path, value):
    out = copy.deepcopy(manifest)
    node = out
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return out


def refused(manifest, tokens=None):
    try:
        m2e.build(manifest, tokens)
    except m2e.ManifestError as exc:
        return str(exc)
    return None


class Conformance(unittest.TestCase):
    def test_sample_matches_what_elementor_exported(self):
        built = normalise(m2e.build(sample()))
        exported = normalise(m2e.load_json(FIXTURE))
        self.assertEqual(built, exported)

    def test_every_element_has_the_keys_elementor_exports(self):
        for n in walk(m2e.build(sample())):
            expected = {"id", "elType", "settings", "elements"} | ({"widgetType"} if n["elType"] == "widget" else {"isInner"})
            self.assertEqual(set(n), expected, n["id"])

    def test_top_level_containers_are_not_inner_and_nested_ones_are(self):
        tree = m2e.build(sample())
        self.assertTrue(all(n["isInner"] is False for n in tree))
        self.assertTrue(all(c["isInner"] is True for n in tree for c in walk(n["elements"]) if c["elType"] == "container"))

    def test_ids_are_seven_hex_characters_unique_and_stable(self):
        ids = [n["id"] for n in walk(m2e.build(sample()))]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(len(i) == 7 and set(i) <= set("0123456789abcdef") for i in ids))
        self.assertEqual(ids, [n["id"] for n in walk(m2e.build(sample()))])

    def test_a_different_slug_gives_different_ids(self):
        other = sample()
        other["page"]["slug"] = "another-page"
        self.assertNotEqual([n["id"] for n in walk(m2e.build(sample()))], [n["id"] for n in walk(m2e.build(other))])

    def test_an_id_collision_is_refused(self):
        class SameDigest:
            def __init__(self, data):
                pass

            def hexdigest(self):
                return "a" * 40
        real = m2e.hashlib.sha1
        m2e.hashlib.sha1 = SameDigest
        try:
            self.assertIn("collision", refused(sample()))
        finally:
            m2e.hashlib.sha1 = real

    def test_icon_list_item_ids_do_not_collide_with_element_ids(self):
        tree = m2e.build(sample())
        ids = [n["id"] for n in walk(tree)] + [i["_id"] for n in walk(tree) if n.get("widgetType") == "icon-list" for i in n["settings"]["icon_list"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_html_widget_keeps_link_and_applies_alignment(self):
        editors = [n["settings"]["editor"] for n in walk(m2e.build(sample())) if n.get("widgetType") == "text-editor"]
        self.assertIn('<p style="text-align:center">Email <a href="mailto:audit@example.com">audit@example.com</a> with your seller account name and one product link.</p>', editors)

    def test_the_tree_string_and_hash_agree(self):
        tree = m2e.build(sample())
        self.assertEqual(json.loads(m2e.tree_json(tree)), tree)
        self.assertEqual(m2e.tree_hash(tree), m2e.tree_hash(json.loads(m2e.tree_json(tree))))
        changed = copy.deepcopy(tree)
        changed[0]["settings"]["background_color"] = "#000000"
        self.assertNotEqual(m2e.tree_hash(tree), m2e.tree_hash(changed))

    def test_kitchen_sink_builds_and_resolves_every_token(self):
        tokens = m2e.load_json(m2e.TOKENS_PATH)
        tree = m2e.build(KITCHEN_SINK)
        section = tree[0]["settings"]
        self.assertEqual(section["background_color"], tokens["color"]["ink"])
        self.assertEqual(section["padding"]["top"], str(tokens["padding"]["section"][0]))
        self.assertEqual(section["_element_id"], "top")
        heading = tree[0]["elements"][0]["elements"][0]["settings"]
        self.assertEqual(heading["header_size"], "h3")
        self.assertEqual(heading["typography_font_size"]["size"], tokens["font_size"]["h1"])


class Refusals(unittest.TestCase):
    def test_every_token_field_refuses_an_unknown_name(self):
        for path, group in TOKEN_FIELDS:
            with self.subTest(path=path):
                message = refused(with_value(KITCHEN_SINK, path, "nope"))
                self.assertIsNotNone(message, "accepted an unknown token")
                self.assertIn("no " + group + " token named 'nope'", message)

    def test_every_token_field_refuses_a_raw_value(self):
        for path, _ in TOKEN_FIELDS:
            for raw in ("#ff0000", "red", "12px", "Ink", "ink;color:red", "", "ink ", "1ink"):
                with self.subTest(path=path, raw=raw):
                    message = refused(with_value(KITCHEN_SINK, path, raw))
                    self.assertIsNotNone(message, "accepted a raw value")
                    # a word that fits the token pattern ("red") passes the schema and is stopped by the token lookup instead
                    self.assertTrue("schema" in message or "token named" in message, message)

    def test_every_token_field_accepts_its_own_known_names(self):
        tokens = m2e.load_json(m2e.TOKENS_PATH)
        for path, group in TOKEN_FIELDS:
            for name in tokens[group]:
                with self.subTest(path=path, name=name):
                    self.assertIsNone(refused(with_value(KITCHEN_SINK, path, name)))

    def test_a_tokens_file_that_is_not_locked_is_refused(self):
        tokens = m2e.load_json(m2e.TOKENS_PATH)
        tokens["locked"] = False
        self.assertIn("not marked locked", refused(sample(), tokens))
        del tokens["locked"]
        self.assertIn("not marked locked", refused(sample(), tokens))

    def test_a_token_group_missing_from_the_file_is_refused_not_a_crash(self):
        tokens = m2e.load_json(m2e.TOKENS_PATH)
        del tokens["radius"]
        self.assertIn("no radius token", refused(sample(), tokens))

    def test_unknown_keys_are_refused_at_every_level(self):
        for path in (("extra",), ("page", "extra"), ("sections", 0, "extra"), ("sections", 0, "blocks", 0, "extra"),
                     ("sections", 0, "blocks", 4, "extra"), ("sections", 0, "blocks", 4, "columns", 0, "extra")):
            with self.subTest(path=path):
                self.assertIn("unknown key", refused(with_value(KITCHEN_SINK, path, 1)) or "")

    def test_missing_required_keys_are_refused(self):
        for path in (("version",), ("page",), ("sections",), ("page", "title"), ("page", "slug"), ("sections", 0, "background"), ("sections", 0, "padding"), ("sections", 0, "blocks")):
            with self.subTest(path=path):
                broken = copy.deepcopy(KITCHEN_SINK)
                node = broken
                for key in path[:-1]:
                    node = node[key]
                del node[path[-1]]
                self.assertIn("missing " + path[-1], refused(broken) or "")

    def test_widget_rules(self):
        cases = {
            "unknown widget": {"widget": "carousel", "text": "x"},
            "heading without text": {"widget": "heading"},
            "heading level h5": {"widget": "heading", "text": "x", "level": "h5"},
            "heading with markup": {"widget": "heading", "text": "a <b>b</b>"},
            "heading text of one angle bracket": {"widget": "heading", "text": "a > b"},
            "text with both forms": {"widget": "text", "text": "x", "html": "<p>x</p>"},
            "text with neither form": {"widget": "text"},
            "align justify": {"widget": "text", "text": "x", "align": "justify"},
            "button without url": {"widget": "button", "text": "x"},
            "icon list with markup": {"widget": "icon_list", "items": ["<img src=x>"]},
            "icon list empty": {"widget": "icon_list", "items": []},
            "columns of one": {"widget": "columns", "columns": [{"width": 50, "blocks": [{"widget": "text", "text": "x"}]}]},
            "columns over 100": {"widget": "columns", "columns": [{"width": 60, "blocks": [{"widget": "text", "text": "x"}]}, {"width": 60, "blocks": [{"widget": "text", "text": "y"}]}]},
            "columns inside columns": {"widget": "columns", "columns": [
                {"width": 40, "blocks": [{"widget": "columns", "columns": [{"width": 40, "blocks": [{"widget": "text", "text": "x"}]}, {"width": 40, "blocks": [{"widget": "text", "text": "y"}]}]}]},
                {"width": 40, "blocks": [{"widget": "text", "text": "z"}]}]},
        }
        for label, block in cases.items():
            with self.subTest(label=label):
                m = copy.deepcopy(KITCHEN_SINK)
                m["sections"][0]["blocks"] = [block]
                self.assertIsNotNone(refused(m), label + " was accepted")

    def test_a_trailing_newline_never_passes_a_pattern(self):
        for path in (("page", "slug"), S + ("anchor",), S + ("background",)):
            with self.subTest(path=path):
                node = KITCHEN_SINK
                for key in path:
                    node = node[key]
                self.assertIsNotNone(refused(with_value(KITCHEN_SINK, path, node + "\n")))

    def test_page_rules(self):
        for label, page in {"slug with capitals": {"title": "t", "slug": "Bad"}, "slug with a slash": {"title": "t", "slug": "a/b"},
                            "slug with a trailing dash": {"title": "t", "slug": "a-"}, "empty title": {"title": "", "slug": "a"},
                            "title too long": {"title": "t" * 121, "slug": "a"}}.items():
            with self.subTest(label=label):
                m = copy.deepcopy(KITCHEN_SINK)
                m["page"] = page
                self.assertIsNotNone(refused(m))

    def test_version_must_be_one(self):
        for v in (0, 2, "1", None, True):
            with self.subTest(v=v):
                self.assertIsNotNone(refused(with_value(KITCHEN_SINK, ("version",), v)))

    def test_not_an_object_is_refused(self):
        for value in ([], "text", 5, None):
            with self.subTest(value=value):
                self.assertIsNotNone(refused(value))

    def test_a_refusal_names_where_the_problem_is(self):
        message = refused(with_value(KITCHEN_SINK, S + B + (2, "background"), "nope"))
        self.assertIn("$.sections[0].blocks[2].background", message)


class CopyRules(unittest.TestCase):
    def build_text(self, **block):
        m = copy.deepcopy(KITCHEN_SINK)
        m["sections"][0]["blocks"] = [dict({"widget": "text"}, **block)]
        return next(n for n in walk(m2e.build(m)) if n.get("widgetType") == "text-editor")["settings"]["editor"]

    def test_plain_text_is_escaped(self):
        self.assertEqual(self.build_text(text='5 < 6 & "quoted"'), '<p>5 &lt; 6 &amp; "quoted"</p>')

    def test_plain_text_script_cannot_become_a_tag(self):
        self.assertEqual(self.build_text(text="<script>alert(1)</script>"), "<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>")

    def test_good_html_passes(self):
        for html_in, html_out in (
            ("<p>One <strong>two</strong> <em>three</em></p>", "<p>One <strong>two</strong> <em>three</em></p>"),
            ("<ul><li>a</li><li>b</li></ul>", "<ul><li>a</li><li>b</li></ul>"),
            ("<p>line<br>break</p>", "<p>line<br>break</p>"),
            ('<p><a href="https://example.com/a?b=1&amp;c=2">x</a></p>', '<p><a href="https://example.com/a?b=1&amp;c=2">x</a></p>'),
            ('<p style="text-align: right;">x</p>', '<p style="text-align:right">x</p>'),
            ("<p>5 &amp; 6 &copy; &#169;</p>", "<p>5 &amp; 6 &copy; &#169;</p>"),
        ):
            with self.subTest(html_in=html_in):
                self.assertEqual(self.build_text(html=html_in), html_out)

    def test_alignment_is_added_to_paragraphs_without_a_style_only(self):
        self.assertEqual(self.build_text(html="<p>a</p><p style=\"text-align:left\">b</p>", align="center"),
                         '<p style="text-align:center">a</p><p style="text-align:left">b</p>')

    def test_bad_html_is_refused_not_cleaned(self):
        for label, markup in {
            "script tag": "<p>x</p><script>alert(1)</script>",
            "iframe": "<iframe src=//evil></iframe>",
            "img with onerror": "<img src=x onerror=alert(1)>",
            "event handler on p": '<p onclick="x()">x</p>',
            "event handler on a": '<a href="#a" onmouseover="x()">x</a>',
            "style other than alignment": '<p style="position:fixed">x</p>',
            "style with an alignment and more": '<p style="text-align:center;position:fixed">x</p>',
            "class attribute": '<p class="x">x</p>',
            "a without allowed href scheme": '<a href="javascript:alert(1)">x</a>',
            "a with data url": '<a href="data:text/html,x">x</a>',
            "a with target": '<a href="#a" target="_blank">x</a>',
            "comment": "<p>x</p><!-- hi -->",
            "doctype": "<!doctype html><p>x</p>",
            "unclosed tag": "<p>x",
            "closing tag never opened": "<p>x</p></strong>",
            "crossed tags": "<p><strong>x</p></strong>",
            "div": "<div>x</div>",
            "style tag": "<style>p{}</style>",
            "form": "<form action=//evil></form>",
        }.items():
            with self.subTest(label=label):
                with self.assertRaises(m2e.ManifestError):
                    self.build_text(html=markup)

    def test_addresses(self):
        good = ["#request", "#", "/contact", "/a/b?c=1", "https://example.com", "http://example.com/x", "mailto:a@b.co", "HTTPS://EXAMPLE.COM"]
        bad = ["javascript:alert(1)", "JaVaScRiPt:alert(1)", " javascript:alert(1)", "java\tscript:alert(1)", "java\nscript:alert(1)", "data:text/html,x",
               "vbscript:x", "//evil.example", "///evil.example", "file:///etc/passwd", "ftp://x", "example.com", "", "https://", "/a b", "mailto:", "https://a b"]
        for url in good:
            with self.subTest(good=url):
                self.assertEqual(m2e.safe_url(url, "t"), url)
        for url in bad:
            with self.subTest(bad=url):
                with self.assertRaises(m2e.ManifestError):
                    m2e.safe_url(url, "t")

    def test_button_address_is_checked_through_the_builder(self):
        m = copy.deepcopy(KITCHEN_SINK)
        m["sections"][0]["blocks"] = [{"widget": "button", "text": "x", "url": "javascript:alert(1)"}]
        self.assertIn("is not an anchor", refused(m))


class SchemaChecker(unittest.TestCase):
    """The schema subset the builder implements, against the keywords the manifest schema uses."""

    def check(self, value, schema):
        return m2e.schema_errors(value, schema, schema)

    def test_each_keyword_in_both_directions(self):
        table = [
            ({"type": "string"}, "a", True), ({"type": "string"}, 1, False),
            ({"type": "integer"}, 1, True), ({"type": "integer"}, True, False), ({"type": "integer"}, 1.5, False),
            ({"type": "boolean"}, False, True), ({"type": "boolean"}, 0, False),
            ({"type": "array"}, [], True), ({"type": "array"}, {}, False),
            ({"type": "object"}, {}, True), ({"type": "object"}, [], False),
            ({"const": 1}, 1, True), ({"const": 1}, 2, False),
            ({"enum": ["a", "b"]}, "a", True), ({"enum": ["a", "b"]}, "c", False),
            ({"type": "string", "minLength": 2}, "ab", True), ({"type": "string", "minLength": 2}, "a", False),
            ({"type": "string", "maxLength": 2}, "ab", True), ({"type": "string", "maxLength": 2}, "abc", False),
            ({"type": "string", "pattern": "^a+$"}, "aa", True), ({"type": "string", "pattern": "^a+$"}, "ab", False),
            ({"type": "integer", "minimum": 5}, 5, True), ({"type": "integer", "minimum": 5}, 4, False),
            ({"type": "integer", "maximum": 5}, 5, True), ({"type": "integer", "maximum": 5}, 6, False),
            ({"type": "array", "minItems": 1}, [1], True), ({"type": "array", "minItems": 1}, [], False),
            ({"type": "array", "maxItems": 1}, [1], True), ({"type": "array", "maxItems": 1}, [1, 2], False),
            ({"type": "array", "items": {"type": "string"}}, ["a"], True), ({"type": "array", "items": {"type": "string"}}, ["a", 1], False),
            ({"type": "object", "required": ["a"]}, {"a": 1}, True), ({"type": "object", "required": ["a"]}, {}, False),
            ({"type": "object", "properties": {"a": {"type": "string"}}}, {"a": "x"}, True),
            ({"type": "object", "properties": {"a": {"type": "string"}}}, {"a": 1}, False),
            ({"type": "object", "properties": {}, "additionalProperties": False}, {}, True),
            ({"type": "object", "properties": {}, "additionalProperties": False}, {"z": 1}, False),
            ({"oneOf": [{"type": "string"}, {"type": "integer"}]}, "a", True), ({"oneOf": [{"type": "string"}, {"type": "integer"}]}, [], False),
            ({"oneOf": [{"type": "string"}, {"type": "string", "minLength": 1}]}, "a", False),
        ]
        for schema, value, ok in table:
            with self.subTest(schema=schema, value=value):
                self.assertEqual(not self.check(value, schema), ok)

    def test_a_shape_matching_two_branches_says_so(self):
        schema = {"oneOf": [{"type": "string"}, {"type": "string", "minLength": 1}]}
        self.assertEqual(self.check("a", schema), ["$: matches more than one allowed shape"])

    def test_ref_is_followed(self):
        schema = {"$defs": {"s": {"type": "string"}}, "type": "object", "properties": {"a": {"$ref": "#/$defs/s"}}}
        self.assertEqual(self.check({"a": "x"}, schema), [])
        self.assertTrue(self.check({"a": 1}, schema))

    def test_an_unsupported_type_is_an_error_not_a_pass(self):
        with self.assertRaises(m2e.ManifestError):
            self.check(1, {"type": "number"})


class CommandLine(unittest.TestCase):
    def run_main(self, manifest):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.json")
            out = os.path.join(tmp, "tree.json")
            with io.open(path, "w", encoding="utf-8") as fh:
                json.dump(manifest, fh)
            real, buffer = sys.stdout, io.StringIO()
            sys.stdout = buffer
            try:
                code = m2e.main([path, "--out", out])
            finally:
                sys.stdout = real
            written = None
            if os.path.exists(out):
                with io.open(out, encoding="utf-8") as fh:
                    written = fh.read()
            return code, buffer.getvalue(), written

    def test_a_good_manifest_exits_zero_and_writes_the_tree(self):
        code, text, written = self.run_main(sample())
        self.assertEqual(code, 0)
        self.assertIn("OK: 5 top level containers, 28 elements", text)
        self.assertEqual(json.loads(written), m2e.build(sample()))

    def test_a_bad_manifest_exits_one_and_writes_nothing(self):
        code, text, written = self.run_main(with_value(sample(), S + ("background",), "nope"))
        self.assertEqual(code, 1)
        self.assertTrue(text.startswith("REFUSED:"))
        self.assertIsNone(written)


if __name__ == "__main__":
    unittest.main(verbosity=1)

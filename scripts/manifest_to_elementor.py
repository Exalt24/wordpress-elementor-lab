# LIFESPAN: permanent
"""Turn a layout manifest into the Elementor element tree (the value of the `_elementor_data` post meta).

    python scripts/manifest_to_elementor.py elementor/seller-audit.layout.json            # check and print a summary
    python scripts/manifest_to_elementor.py elementor/seller-audit.layout.json --out tree.json

The manifest is what a language model is allowed to return. It carries copy and the NAMES of design tokens, never a raw colour, size or
HTML attribute. Three things are refused before any Elementor JSON exists: a manifest that breaks the JSON schema, a token name the locked
tokens file does not hold, and copy that carries markup outside a small allow list. Standard library only.
"""
import argparse
import hashlib
import html
import json
import os
import re
import sys
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SCHEMA_PATH = os.path.join(ROOT, "elementor", "layout.schema.json")
TOKENS_PATH = os.path.join(ROOT, "elementor", "design-tokens.json")


class ManifestError(ValueError):
    """The manifest cannot be turned into a tree. The message names the path of the first problem."""


# ---------------------------------------------------------------- the JSON schema subset the manifest schema uses

def _type_ok(value, name):
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "string":
        return isinstance(value, str)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "boolean":
        return isinstance(value, bool)
    raise ManifestError("schema uses an unsupported type: " + name)


def schema_errors(value, schema, root, path="$"):
    """Every problem found, as 'path: message' strings. Supports $ref, oneOf, const, enum, type, required, properties,
    additionalProperties false, items, minItems, maxItems, minLength, maxLength, pattern, minimum, maximum."""
    if "$ref" in schema:
        node = root
        for part in schema["$ref"].lstrip("#/").split("/"):
            node = node[part]
        return schema_errors(value, node, root, path)
    if "oneOf" in schema:
        results = [schema_errors(value, branch, root, path) for branch in schema["oneOf"]]
        matches = [r for r in results if not r]
        if len(matches) == 1:
            return []
        if len(matches) > 1:
            return [path + ": matches more than one allowed shape"]
        best = min(results, key=len)  # the closest branch explains the failure best
        return best or [path + ": matches no allowed shape"]
    errors = []
    # type() as well as ==, because Python says True == 1 and JSON does not
    if "const" in schema and (value != schema["const"] or type(value) is not type(schema["const"])):
        return [path + ": must be " + json.dumps(schema["const"])]
    if "enum" in schema and value not in schema["enum"]:
        return [path + ": must be one of " + ", ".join(json.dumps(v) for v in schema["enum"])]
    if "type" in schema and not _type_ok(value, schema["type"]):
        return [path + ": must be a " + schema["type"]]
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(path + ": is too short")
        if len(value) > schema.get("maxLength", 10 ** 9):
            errors.append(path + ": is too long")
        # JSON Schema patterns (ECMA) have a $ that does not match before a final newline; Python's does, so it is swapped for \Z
        pattern = schema["pattern"][:-1] + r"\Z" if schema.get("pattern", "").endswith("$") else schema.get("pattern")
        if pattern and not re.search(pattern, value):
            errors.append(path + ": does not match " + schema["pattern"])
    if isinstance(value, int) and not isinstance(value, bool):
        if value < schema.get("minimum", value):
            errors.append(path + ": is below " + str(schema["minimum"]))
        if value > schema.get("maximum", value):
            errors.append(path + ": is above " + str(schema["maximum"]))
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(path + ": needs at least " + str(schema["minItems"]) + " items")
        if len(value) > schema.get("maxItems", 10 ** 9):
            errors.append(path + ": allows at most " + str(schema["maxItems"]) + " items")
        if "items" in schema:
            for i, item in enumerate(value):
                errors += schema_errors(item, schema["items"], root, path + "[" + str(i) + "]")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(path + ": missing " + key)
        props = schema.get("properties", {})
        for key, item in value.items():
            if key in props:
                errors += schema_errors(item, props[key], root, path + "." + key)
            elif schema.get("additionalProperties") is False:
                errors.append(path + ": unknown key " + key)
    return errors


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------- copy: plain text and a small HTML allow list

ALLOWED_TAGS = {"p", "a", "strong", "em", "br", "ul", "ol", "li"}
VOID_TAGS = {"br"}
URL_OK = re.compile(r"^(#[A-Za-z0-9_-]*|/(?!/)[^\s]*|https?://[^\s]+|mailto:[^\s]+)$", re.I)
ALIGN_STYLE = re.compile(r"^text-align:\s*(left|center|right);?$", re.I)


def safe_url(url, where):
    cleaned = re.sub(r"[\x00-\x20]", "", url)  # browsers ignore control characters and spaces inside a scheme
    if cleaned != url or not URL_OK.match(cleaned):
        raise ManifestError(where + ": address '" + url[:40] + "' is not an anchor, a site path, http(s) or mailto")
    return url


class _Cleaner(HTMLParser):
    """Re-emits copy with only the allowed tags. a keeps href; p keeps a text-align style. Anything else is an error, not silently dropped."""

    def __init__(self, where, align):
        super().__init__(convert_charrefs=False)
        self.where, self.align, self.out, self.stack = where, align, [], []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            raise ManifestError(self.where + ": tag <" + tag + "> is not allowed")
        attrs = dict(attrs)
        keep = []
        for name, value in attrs.items():
            if tag == "a" and name == "href":
                keep.append(("href", safe_url(value or "", self.where)))
            elif tag == "p" and name == "style" and ALIGN_STYLE.match(value or ""):
                keep.append(("style", re.sub(r"\s+", "", value).rstrip(";")))
            else:
                raise ManifestError(self.where + ": attribute " + name + " on <" + tag + "> is not allowed")
        if tag == "p" and not any(n == "style" for n, _ in keep) and self.align:
            keep.append(("style", "text-align:" + self.align))
        self.out.append("<" + tag + "".join(' %s="%s"' % (n, html.escape(v, quote=True)) for n, v in keep) + ">")
        if tag not in VOID_TAGS:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if not self.stack or self.stack.pop() != tag:
            raise ManifestError(self.where + ": </" + tag + "> closes something that is not open")
        self.out.append("</" + tag + ">")

    def handle_data(self, data):
        self.out.append(html.escape(data, quote=False))

    def handle_entityref(self, name):
        self.out.append("&" + name + ";")

    def handle_charref(self, name):
        self.out.append("&#" + name + ";")

    def handle_comment(self, data):
        raise ManifestError(self.where + ": comments are not allowed")

    def handle_decl(self, decl):
        raise ManifestError(self.where + ": declarations are not allowed")

    def handle_pi(self, data):
        raise ManifestError(self.where + ": processing instructions are not allowed")


def clean_html(markup, where, align=None):
    cleaner = _Cleaner(where, align)
    cleaner.feed(markup)
    cleaner.close()
    if cleaner.stack:
        raise ManifestError(where + ": <" + cleaner.stack[-1] + "> is never closed")
    return "".join(cleaner.out)


# ---------------------------------------------------------------- the builder

class Builder:
    def __init__(self, tokens, slug):
        if tokens.get("locked") is not True:
            raise ManifestError("design tokens file is not marked locked")
        self.tokens, self.slug, self.ids = tokens, slug, set()

    def tok(self, group, name, where):
        table = self.tokens.get(group)
        if not isinstance(table, dict) or name not in table:
            raise ManifestError(where + ": no " + group + " token named '" + name + "' (known: " + ", ".join(sorted(table or {})) + ")")
        return table[name]

    def new_id(self, path):
        digest = hashlib.sha1((self.slug + "|" + path).encode("utf-8")).hexdigest()[:7]
        if digest in self.ids:
            raise ManifestError(path + ": element id collision, rename the page slug")
        self.ids.add(digest)
        return digest

    @staticmethod
    def box(top, right, bottom, left):
        return {"unit": "px", "top": str(top), "right": str(right), "bottom": str(bottom), "left": str(left),
                "isLinked": top == right == bottom == left}

    def padding(self, name, where):
        y, x = self.tok("padding", name, where)
        return self.box(y, x, y, x)

    def radius(self, name, where):
        r = self.tok("radius", name, where)
        return self.box(r, r, r, r)

    @staticmethod
    def gap(n):
        return {"unit": "px", "size": n, "column": str(n), "row": str(n)}

    def element(self, path, el_type, settings, elements, widget=None):
        node = {"id": self.new_id(path), "elType": el_type, "settings": settings, "elements": elements}
        if widget:
            node["widgetType"] = widget
        else:
            node["isInner"] = path.count("/") > 0
        return node

    def typography(self, block, where, size_group="font_size"):
        out = {}
        parts = {}
        if block.get("size"):
            parts["typography_font_size"] = {"unit": "px", "size": self.tok("font_size", block["size"], where + ".size")}
        if block.get("weight"):
            parts["typography_font_weight"] = self.tok("font_weight", block["weight"], where + ".weight")
        if block.get("line_height"):
            parts["typography_line_height"] = {"unit": "em", "size": self.tok("line_height", block["line_height"], where + ".line_height")}
        if parts:
            out["typography_typography"] = "custom"
            out.update(parts)
        return out

    def widget(self, block, path, where):
        kind = block["widget"]
        s = {}
        if kind == "heading":
            if re.search(r"[<>]", block["text"]):
                raise ManifestError(where + ".text: a heading is plain text, no markup")
            s["title"] = block["text"]
            if block.get("level", "h2") != "h2":
                s["header_size"] = block["level"]
            if block.get("align"):
                s["align"] = block["align"]
            if block.get("color"):
                s["title_color"] = self.tok("color", block["color"], where + ".color")
            s.update(self.typography(block, where))
            return self.element(path, "widget", s, [], "heading")
        if kind == "text":
            if ("text" in block) == ("html" in block):
                raise ManifestError(where + ": give exactly one of text and html")
            align = block.get("align")
            if "text" in block:
                style = ' style="text-align:%s"' % align if align else ""
                s["editor"] = "<p%s>%s</p>" % (style, html.escape(block["text"], quote=False))
            else:
                s["editor"] = clean_html(block["html"], where + ".html", align)
            if block.get("color"):
                s["text_color"] = self.tok("color", block["color"], where + ".color")
            s.update(self.typography({"size": block.get("size")}, where))
            return self.element(path, "widget", s, [], "text-editor")
        if kind == "button":
            s["text"] = block["text"]
            s["link"] = {"url": safe_url(block["url"], where + ".url"), "is_external": "", "nofollow": ""}
            if block.get("align"):
                s["align"] = block["align"]
            if block.get("background"):
                s["background_color"] = self.tok("color", block["background"], where + ".background")
            if block.get("color"):
                s["button_text_color"] = self.tok("color", block["color"], where + ".color")
            s.update(self.typography(block, where))
            if block.get("radius"):
                s["border_radius"] = self.radius(block["radius"], where + ".radius")
            if block.get("padding"):
                s["button_padding"] = self.padding(block["padding"], where + ".padding")
            return self.element(path, "widget", s, [], "button")
        if kind == "icon_list":
            items = []
            for i, text in enumerate(block["items"]):
                if re.search(r"[<>]", text):
                    raise ManifestError(where + ".items[" + str(i) + "]: list items are plain text")
                items.append({"text": text, "_id": self.new_id(path + "/item" + str(i))})
            s["icon_list"] = items
            if block.get("color"):
                s["text_color"] = self.tok("color", block["color"], where + ".color")
            if block.get("icon_color"):
                s["icon_color"] = self.tok("color", block["icon_color"], where + ".icon_color")
            s["icon_typography_typography"] = "custom"
            s["text_indent"] = {"unit": "px", "size": 12}
            return self.element(path, "widget", s, [], "icon-list")
        if kind == "columns":
            total = sum(c["width"] for c in block["columns"])
            if total > 100:
                raise ManifestError(where + ": column widths add up to " + str(total) + ", at most 100")
            cols = []
            for i, col in enumerate(block["columns"]):
                cwhere, cpath = where + ".columns[" + str(i) + "]", path + "/" + str(i)
                cs = {"content_width": "full", "width": {"unit": "%", "size": col["width"]}, "flex_direction": "column"}
                if col.get("gap"):
                    cs["flex_gap"] = self.gap(self.tok("gap", col["gap"], cwhere + ".gap"))
                if col.get("background"):
                    cs["background_background"] = "classic"
                    cs["background_color"] = self.tok("color", col["background"], cwhere + ".background")
                cs["border_radius"] = self.radius("card", cwhere)
                cs["padding"] = self.padding("card", cwhere)
                kids = [self.widget(b, cpath + "/" + str(j), cwhere + ".blocks[" + str(j) + "]") for j, b in enumerate(col["blocks"])]
                cols.append(self.element(cpath, "container", cs, kids))
            rs = {"content_width": "full", "flex_direction": "row"}
            if block.get("gap"):
                rs["flex_gap"] = self.gap(self.tok("gap", block["gap"], where + ".gap"))
            rs["flex_justify_content"] = "center"
            rs["flex_wrap"] = "wrap"
            return self.element(path, "container", rs, cols)
        raise ManifestError(where + ": unknown widget " + kind)

    def section(self, sec, index):
        where, path = "$.sections[" + str(index) + "]", str(index)
        s = {"content_width": "full", "flex_direction": "column", "flex_align_items": "center",
             "padding": self.padding(sec["padding"], where + ".padding"),
             "background_background": "classic",
             "background_color": self.tok("color", sec["background"], where + ".background")}
        if sec.get("anchor"):
            s["_element_id"] = sec["anchor"]
        gap = self.gap(self.tok("gap", sec["gap"], where + ".gap")) if sec.get("gap") else None
        if sec.get("inner", True):
            inner = {"boxed_width": {"unit": "px", "size": self.tokens["content_width"]}, "flex_direction": "column", "flex_align_items": "center"}
            if gap:
                inner["flex_gap"] = gap
            kids = [self.widget(b, path + "/0/" + str(j), where + ".blocks[" + str(j) + "]") for j, b in enumerate(sec["blocks"])]
            return self.element(path, "container", s, [self.element(path + "/0", "container", inner, kids)])
        if gap:
            s["flex_gap"] = gap
        kids = [self.widget(b, path + "/" + str(j), where + ".blocks[" + str(j) + "]") for j, b in enumerate(sec["blocks"])]
        return self.element(path, "container", s, kids)


def build(manifest, tokens=None, schema=None):
    """Validate the manifest, resolve every token name and return the list of top level containers."""
    schema = schema or load_json(SCHEMA_PATH)
    tokens = tokens or load_json(TOKENS_PATH)
    problems = schema_errors(manifest, schema, schema)
    if problems:
        raise ManifestError("manifest breaks the schema: " + "; ".join(problems[:5]))
    builder = Builder(tokens, manifest["page"]["slug"])
    return [builder.section(sec, i) for i, sec in enumerate(manifest["sections"])]


def tree_json(tree):
    """The exact string that is stored in the post meta and hashed, so both sides agree byte for byte."""
    return json.dumps(tree, separators=(",", ":"), ensure_ascii=False)


def tree_hash(tree):
    return hashlib.sha256(tree_json(tree).encode("utf-8")).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("manifest")
    ap.add_argument("--tokens", default=TOKENS_PATH)
    ap.add_argument("--out", help="write the element tree here")
    args = ap.parse_args(argv)
    try:
        tree = build(load_json(args.manifest), load_json(args.tokens))
    except ManifestError as exc:
        print("REFUSED: " + str(exc))
        return 1
    count = 0
    stack = list(tree)
    while stack:
        node = stack.pop()
        count += 1
        stack += node["elements"]
    print("OK: %d top level containers, %d elements, sha256 %s" % (len(tree), count, tree_hash(tree)[:16]))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(tree_json(tree))
    return 0


if __name__ == "__main__":
    sys.exit(main())

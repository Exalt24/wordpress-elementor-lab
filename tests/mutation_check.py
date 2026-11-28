# LIFESPAN: permanent
"""Deliberate breakage check for the keyword research and AI visibility scripts.

    python tests/mutation_check.py

Copies the scripts and tests to a temporary folder, breaks one guard at a time and runs both test files. A break counts as caught only
when a test goes red. The unbroken copy must pass first, and each break must match exactly one place in its file.
"""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TESTS = ["tests/test_keyword_research.py", "tests/test_ai_visibility.py", "tests/test_seo_audit.py", "tests/test_manifest_to_elementor.py", "bullion-shop/tests/test_scripts.py"]
PHP_TESTS = ["opencart/tests/test_markup.php", "bullion-shop/tests/test_logic.php", "tests/test_elementor_route.php"]
NODE_TESTS = ["tests/test_editor_compare.cjs"]
BU, EC, RT = "scripts/manifest_to_elementor.py", "scripts/editor_compare.cjs", "wp/mu-plugins/elementor-draft-route.php"
KR, AV, SA = "scripts/keyword_research.py", "scripts/ai_visibility.py", "scripts/seo_audit.py"
MK = "opencart/extension/seolab/system/library/markup.php"
BL = "bullion-shop/mu-plugins/bullion-lab/lib/"
SPOT, PRICING, SCHEMA, FEED, LIMITER, HEADERS, RL, AS, FW = (BL + n + ".php" for n in ("spot", "pricing", "schema", "feed", "limiter", "headers", "ratelimit", "assets", "firewall"))
HC, SC = "bullion-shop/scripts/hardening_check.py", "bullion-shop/scripts/schema_check.py"

MUTANTS = [
    (KR, "relevance guard removed", "if not seed_words & set(content_words(kw)):", "if False:"),
    (KR, "source agreement ignored", 'agreement = len(entry["sources"]) * 3', "agreement = 0"),
    (KR, "position ignored", 'position = sum(1.0 / (r + 1) for r in entry["ranks"])', "position = 0"),
    (KR, "intent cap removed", "intent = min(INTENT_CAP, sum(INTENT_WORDS.get(w, 0) for w in set(words(kw))))", "intent = sum(INTENT_WORDS.get(w, 0) for w in set(words(kw)))"),
    (KR, "word limit removed", "len(words(kw)) > MAX_WORDS", "False"),
    (KR, "FAQ rule removed", "if sum(1 for kw, _ in items if is_question(kw)) * 2 >= len(items):", "if False:"),
    (KR, "pillar not marked", 'rows[0]["type"] = "pillar page"', "pass"),
    (KR, "request errors not counted", "errors += 1", "errors += 0"),
    (KR, "wrong shape accepted", "not isinstance(data, list) or len(data) < 2 or not isinstance(data[1], list)", "False"),
    (KR, "case not folded", "str(text).strip().lower()", "str(text).strip()"),
    (KR, "never trimmed", "if len(text) <= limit:", "if True:"),
    (KR, "cluster not sorted by score", "groups[head].sort(key=lambda x: (-x[1], x[0]))", "groups[head].sort(key=lambda x: x[0])"),
    (KR, "short phrases offered as questions", "and len(words(kw)) >= 4]", "and len(words(kw)) >= 1]"),
    (KR, "one keyword pages kept", 'h != "other" and len(items) < MIN_CLUSTER_SIZE', "False"),
    (KR, "pillar does not link down", 'pairs += [(pillar["head"], r["head"]) for r in named[1:4]]', "pairs += []"),
    (AV, "no start boundary", 'r"(?<![a-z0-9])" + ', 'r"" + '),
    (AV, "no end boundary", '+ r"(?![a-z0-9])"', '+ r""'),
    (AV, "name not folded to lower case", "re.escape(entity.lower())", "re.escape(entity)"),
    (AV, "error treated as an answer", 'r["errors"] += 1\n                continue', 'r["errors"] += 1\n                text = ""'),
    (AV, "interval drops its second term", "z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))", "z * math.sqrt(p * (1 - p) / n)"),
    (AV, "no trials not handled", "if n <= 0:", "if False:"),
    (AV, "streaming left on", '"stream": False', '"stream": True'),
    (AV, "key not sent", '{"Authorization": "Bearer " + self.key}', "{}"),
    (AV, "no answers reported as zero percent", 'pct(k / total) if total else "n/a"', 'pct(k / total) if total else "0%"'),
    (SA, "base href ignored for relative links", "root = urllib.parse.urljoin(url, p.base) if p.base else url", "root = url"),
    (MK, "script can be closed by a product name", " | JSON_HEX_TAG | JSON_HEX_AMP", ""),
    (MK, "stock ignored", "((int)($p['quantity'] ?? 0) > 0) ? 'https://schema.org/InStock'", "true ? 'https://schema.org/InStock'"),
    (MK, "open graph values not escaped", "htmlspecialchars($content, ENT_QUOTES, 'UTF-8')", "$content"),
    (MK, "canonical keeps view parameters", "$query = array_intersect_key($query, array_flip($keep));", "$query = $query;"),
    (MK, "page one gets a page parameter", "if (isset($query['page']) && (int)$query['page'] <= 1) {", "if (false) {"),
    (MK, "store name added twice", "mb_stripos($title, $store) === false", "true"),
    (MK, "title may pass 65 characters", "return mb_strlen($longer) <= $max ? $longer : $title;", "return $longer;"),
    (MK, "headings with attributes retagged", "'#<h' . $from . '>(.*?)</h'", "'#<h' . $from . '[^>]*>(.*?)</h'"),
    (MK, "sitemap address not escaped", "htmlspecialchars($row[0], ENT_XML1 | ENT_QUOTES, 'UTF-8')", "$row[0]"),
    (MK, "sitemap date not cut to the day", "substr($row[1], 0, 10)", "$row[1]"),
    (MK, "description not cut on a word", 'rtrim($space === false ? $cut : mb_substr($cut, 0, $space), " ,;:.-") . \'…\'', "$cut . '…'"),
    (MK, "markup injected into html with no head", "$pos === false || $markup === ''", "$markup === ''"),
    (MK, "sku and image invented when missing", "if (!empty($p[$source])) {", "if (true) {"),
    (MK, "last crumb always linked", "if ($crumb[1] !== '') {", "if (true) {"),
    (SPOT, "a stale price is shown for ever", "if ($last !== null && $now - $last['fetched_at'] <= $staleMax) {", "if ($last !== null) {"),
    (SPOT, "a wild reading is accepted", "if ($parsed !== null && self::sane($parsed, $last)) {", "if ($parsed !== null) {"),
    (SPOT, "the cache lifetime is ignored", "if ($last !== null && $now - $last['fetched_at'] < $ttl) {", "if (false) {"),
    (SPOT, "the fetch lock is ignored", "if ($canFetch) {", "if (true) {"),
    (SPOT, "a zero price is accepted", "|| $v <= 0) {", "|| $v < 0) {"),
    (SPOT, "a string price is accepted", "if (!(is_int($v) || is_float($v)) || !is_finite", "if (!is_finite"),
    (SPOT, "a feed that throws is not caught", "catch (\\Throwable $e)", "catch (\\InvalidArgumentException $e)"),
    (SPOT, "the jump limit is far too wide", "float $maxJump = 0.15", "float $maxJump = 5.0"),
    (PRICING, "the premium is ignored", "(1 + $premiumPct / 100)", "1"),
    (PRICING, "buy back can go negative", "return max(0, (int) round(", "return ((int) round("),
    (SCHEMA, "the price claims to last the year", "$p['as_of'] + $ttl", "$p['as_of'] + 31536000"),
    (SCHEMA, "an Offer is written with no price", "if ($p['pence'] !== null && $p['as_of'] !== null) {", "if (true) {"),
    (SCHEMA, "a product name can close the script", " | JSON_HEX_TAG | JSON_HEX_AMP", ""),
    (SCHEMA, "stock is ignored", "$p['in_stock'] ? 'https://schema.org/InStock'", "true ? 'https://schema.org/InStock'"),
    (FEED, "an item with no price is listed", "if ($i['pence'] === null) {", "if (false) {"),
    (FEED, "feed text is not escaped", "htmlspecialchars($s, ENT_XML1 | ENT_QUOTES, 'UTF-8')", "$s"),
    (FEED, "the price loses its decimals", "sprintf('%.2f', $i['pence'] / 100)", "($i['pence'] / 100)"),
    (LIMITER, "the fifth failure does not lock", "if (count($fails) >= self::MAX_FAILS) {", "if (count($fails) > self::MAX_FAILS) {"),
    (LIMITER, "old failures are never forgotten", "if ($now - $t < self::WINDOW) {", "if (true) {"),
    (LIMITER, "a forged forwarding header picks the key", "(string) ($server['REMOTE_ADDR'] ?? 'unknown')", "(string) ($server['HTTP_X_FORWARDED_FOR'] ?? $server['REMOTE_ADDR'] ?? 'unknown')"),
    (LIMITER, "the lock holds one second too long", "($rec['locked_until'] ?? 0) > $now;", "($rec['locked_until'] ?? 0) >= $now;"),
    (HEADERS, "HSTS is sent on plain http", "if ($https) {", "if (true) {"),
    (HEADERS, "nosniff is not sent", "'X-Content-Type-Options' => 'nosniff'", "'X-Content-Type-Options' => ''"),
    (SCHEMA, "a question with no answer goes into the markup", "if ($q !== '' && $a !== '') {", "if (true) {"),
    (SCHEMA, "an empty FAQ still writes markup", "return $items === [] ? null :", "return false ? null :"),
    (AS, "a stylesheet is left blocking", "return str_replace(\"media='all'\", \"media='print' onload=\\\"this.media='all'\\\"\", $tag) . '<noscript>' . $tag . '</noscript>';", "return $tag;"),
    (AS, "the noscript copy is dropped", " . '<noscript>' . $tag . '</noscript>';", ";"),
    (AS, "the main stylesheet would be dropped", "'storefront-fonts', 'storefront-gutenberg-blocks',", "'storefront-fonts', 'storefront-gutenberg-blocks', 'storefront-icons',"),
    (FW, "an attack tool user agent passes", "if (preg_match(self::AGENT_PATTERN, strtolower($userAgent))) {", "if (false) {"),
    (FW, "the path is not lower cased", "$p = strtolower(rawurldecode($path));", "$p = rawurldecode($path);"),
    (FW, "the path is not percent decoded", "$p = strtolower(rawurldecode($path));", "$p = strtolower($path);"),
    (FW, "a secret file name is not matched", "'#(^|/)\\.(env|git|svn|hg|htpasswd|ds_store)(/|$)#',", "'#(^|/)\\.(git|svn|hg|htpasswd|ds_store)(/|$)#',"),
    (HC, "a site that refuses no scanner probe passes", 'add("scanner probes refused", s1 == 403 and s2 == 403 and s3 == 403,', 'add("scanner probes refused", True,'),
    (RL, "the 30th request in a minute is refused", "return [$rec['count'] <= $limit, $rec];", "return [$rec['count'] < $limit, $rec];"),
    (RL, "the window never rolls over", "if ($rec === null || $now - $rec['start'] >= self::WINDOW) {", "if ($rec === null) {"),
    (RL, "every page is limited as search", "if (isset($query['s'])) {", "if (true) {"),
    (HC, "a site that never rate limits passes", 'add("site search is rate limited", 429 in codes,', 'add("site search is rate limited", True,'),
    (HC, "author enumeration is never reported", '"/author/" not in final and', "True and"),
    (HC, "a login that succeeds after the failures passes", "not any(wrong) and not ok_login and", "not any(wrong) and"),
    (SC, "a price valid for any length of time passes", "MAX_VALID_SECONDS = 3600", "MAX_VALID_SECONDS = 10 ** 10"),
    (BU, "an unknown token name is accepted", 'if not isinstance(table, dict) or name not in table:', 'if False:'),
    (BU, "an unlocked tokens file is accepted", 'if tokens.get("locked") is not True:', 'if False:'),
    (BU, "true passes for the number one", ' or type(value) is not type(schema["const"])', ''),
    (BU, "a trailing newline passes a pattern", 'schema["pattern"][:-1] + r"\\Z" if schema.get("pattern", "").endswith("$") else schema.get("pattern")', 'schema.get("pattern")'),
    (BU, "unknown keys are accepted", 'elif schema.get("additionalProperties") is False:', 'elif False:'),
    (BU, "a shape that matches two branches passes", 'if len(matches) > 1:', 'if False:'),
    (BU, "required keys are not checked", 'if key not in value:', 'if False:'),
    (BU, "a minimum is not enforced", 'if value < schema.get("minimum", value):', 'if False:'),
    (BU, "a maximum length is not enforced", 'if len(value) > schema.get("maxLength", 10 ** 9):', 'if False:'),
    (BU, "a protocol relative address passes", '|/(?!/)[^\\s]*|', '|/[^\\s]*|'),
    (BU, "any tag passes", 'if tag not in ALLOWED_TAGS:', 'if False:'),
    (BU, "any attribute passes", 'raise ManifestError(self.where + ": attribute " + name + " on <" + tag + "> is not allowed")', 'pass'),
    (BU, "any style passes on a paragraph", 'elif tag == "p" and name == "style" and ALIGN_STYLE.match(value or ""):', 'elif tag == "p" and name == "style":'),
    (BU, "a link address is not checked", 'keep.append(("href", safe_url(value or "", self.where)))', 'keep.append(("href", value or ""))'),
    (BU, "a comment passes", 'raise ManifestError(self.where + ": comments are not allowed")', 'pass'),
    (BU, "an unclosed tag passes", 'if cleaner.stack:', 'if False:'),
    (BU, "alignment is not applied to html copy", 'if tag == "p" and not any(n == "style" for n, _ in keep) and self.align:', 'if False:'),
    (BU, "plain text is not escaped", 'html.escape(block["text"], quote=False))', 'block["text"])'),
    (BU, "a heading may carry markup", 'if re.search(r"[<>]", block["text"]):', 'if False:'),
    (BU, "a list item may carry markup", 'if re.search(r"[<>]", text):', 'if False:'),
    (BU, "column widths may pass 100", 'if total > 100:', 'if False:'),
    (BU, "text and html may both be given", 'if ("text" in block) == ("html" in block):', 'if False:'),
    (BU, "an id collision is ignored", 'if digest in self.ids:', 'if False:'),
    (BU, "a linked padding is not marked linked", '"isLinked": top == right == bottom == left}', '"isLinked": False}'),
    (BU, "inner containers are not marked inner", 'node["isInner"] = path.count("/") > 0', 'node["isInner"] = False'),
    (BU, "the boxed width is not the token", '"size": self.tokens["content_width"]}', '"size": 1000}'),
    (BU, "the default heading level is written", 'if block.get("level", "h2") != "h2":', 'if True:'),
    (BU, "the hash covers nothing", 'hashlib.sha256(tree_json(tree).encode("utf-8")).hexdigest()', 'hashlib.sha256(b"").hexdigest()'),
    (EC, "an object sent as text passes", "if (have === null || typeof have !== 'object') {", "if (false) {"),
    (EC, "a list that changed length passes", "if (!Array.isArray(have) || have.length !== want.length) { out.push(path + ': list length '", "if (false) { out.push(path + ': list length '"),
    (EC, "a dropped element passes", "if (!Array.isArray(have) || have.length !== want.length) { out.push(path + ': ' + want.length", "if (false) { out.push(path + ': ' + want.length"),
    (EC, "a changed id passes", "['id', 'elType', 'widgetType'].forEach", "['elType', 'widgetType'].forEach"),
    (EC, "a changed widget type passes", "['id', 'elType', 'widgetType'].forEach", "['id', 'elType'].forEach"),
    (EC, "settings are not compared", "contains(w.settings, h.settings || {}, here + '.settings', out);", ""),
    (EC, "children are not compared", "compareTree(w.elements, h.elements || [], here, out);", ""),
    (EC, "values are compared by type as well", "if (String(want) !== String(have)) out.push(", "if (want !== have) out.push("),
    (EC, "nested elements are not counted", "a + 1 + countElements(n.elements || [])", "a + 1"),
    (RT, "an id with a trailing newline passes", "'/^[0-9a-f]{7}$/D'", "'/^[0-9a-f]{7}$/'"),
    (RT, "any depth passes", "if ($depth > LAB_ELEMENTOR_MAX_DEPTH) {", "if (false) {"),
    (RT, "an empty leaf list is refused at the depth limit", "if (is_array($nodes) && !$nodes) {", "if (false) {"),
    (RT, "an object passes as a list", "if (!is_array($nodes) || !array_is_list($nodes)) {", "if (!is_array($nodes)) {"),
    (RT, "any elType passes", "if (!in_array($node['elType'], array('container', 'widget'), true)) {", "if (false) {"),
    (RT, "a widget needs no type", "if ($node['elType'] === 'widget' && empty($node['widgetType'])) {", "if (false) {"),
    (RT, "settings may be text", "if (!is_array($node['settings'])) {", "if (false) {"),
    (RT, "settings may be missing", "!isset($node['id'], $node['elType'], $node['settings'], $node['elements'])", "!isset($node['id'], $node['elType'], $node['elements'])"),
    (RT, "children are not checked", "$err = lab_elementor_check_tree($node['elements'], $depth + 1);", "$err = null;"),
]


def php_command(folder):
    """The command that runs the PHP tests: a local php when there is one, else the official php image with the folder mounted."""
    if shutil.which("php"):
        return ["sh", "-c", " && ".join("php " + t for t in PHP_TESTS)]
    return ["docker", "run", "--rm", "-v", folder + ":/lab", "-w", "/lab", "php:8.2-cli", "sh", "-c", " && ".join("php " + t for t in PHP_TESTS)]


def run_tests(folder):
    for t in TESTS:
        r = subprocess.run([sys.executable, "-I", os.path.join(folder, t)], cwd=folder, capture_output=True, text=True, encoding="utf-8", timeout=120)
        if r.returncode != 0:
            return False
    for t in NODE_TESTS:
        r = subprocess.run(["node", os.path.join(folder, t)], cwd=folder, capture_output=True, text=True, encoding="utf-8", timeout=60)
        if r.returncode != 0:
            return False
    r = subprocess.run(php_command(folder), cwd=folder, capture_output=True, text=True, encoding="utf-8", timeout=180)
    return r.returncode == 0


def main():
    base = tempfile.mkdtemp(prefix="mutcheck_")
    try:
        copy = os.path.join(base, "clean")
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("__pycache__", ".git", "docs", "demo", "build"))
        if not run_tests(copy):
            print("FAIL  the unbroken copy does not pass its own tests")
            return 1
        caught = ran = 0
        lo, hi = int(os.environ.get("MUT_FROM", 0)), int(os.environ.get("MUT_TO", len(MUTANTS)))   # a slice of the list, for a run that must be split
        for i, (rel, name, old, new) in enumerate(MUTANTS):
            if not lo <= i < hi:
                continue
            ran += 1
            folder = os.path.join(base, "m%d" % i)
            shutil.copytree(copy, folder)
            path = os.path.join(folder, rel)
            src = open(path, encoding="utf-8", newline="").read()
            if src.count(old) != 1:
                print("FAIL  %s: the text to break matches %d places, not 1" % (name, src.count(old)))
                return 1
            open(path, "w", encoding="utf-8", newline="").write(src.replace(old, new))
            red = not run_tests(folder)
            caught += red
            shutil.rmtree(folder, ignore_errors=True)
            print(("CAUGHT  " if red else "SURVIVED  ") + name)
        print("\n%d of %d breaks caught" % (caught, ran))
        return 0 if caught == ran else 1
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

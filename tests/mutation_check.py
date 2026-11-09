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
TESTS = ["tests/test_keyword_research.py", "tests/test_ai_visibility.py"]
KR, AV = "scripts/keyword_research.py", "scripts/ai_visibility.py"

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
]


def run_tests(folder):
    for t in TESTS:
        r = subprocess.run([sys.executable, "-I", os.path.join(folder, t)], cwd=folder, capture_output=True, text=True, encoding="utf-8", timeout=120)
        if r.returncode != 0:
            return False
    return True


def main():
    base = tempfile.mkdtemp(prefix="mutcheck_")
    try:
        copy = os.path.join(base, "clean")
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("__pycache__", ".git", "docs", "wp", "demo"))
        if not run_tests(copy):
            print("FAIL  the unbroken copy does not pass its own tests")
            return 1
        caught = 0
        for i, (rel, name, old, new) in enumerate(MUTANTS):
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
            print(("CAUGHT  " if red else "SURVIVED  ") + name)
        print("\n%d of %d breaks caught" % (caught, len(MUTANTS)))
        return 0 if caught == len(MUTANTS) else 1
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

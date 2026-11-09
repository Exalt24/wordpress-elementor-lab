# LIFESPAN: permanent
"""Offline tests for the keyword research script. The network function is replaced and the recorded responses are replayed.

    python tests/test_keyword_research.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import keyword_research as kr  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "suggestions.json")
results = []


def check(name, cond):
    results.append(bool(cond))
    print(("PASS  " if cond else "FAIL  ") + name)


def entry(sources, ranks):
    return {"sources": set(sources), "ranks": list(ranks), "seeds": {"s"}}


def test_parse():
    check("parse reads the suggestion list", kr.parse_suggestions('["q",["a","b"],[]]') == ["a", "b"])
    check("parse drops non-string items", kr.parse_suggestions('["q",["a",3,null,"b"]]') == ["a", "b"])
    check("parse gives nothing for a page that is not JSON", kr.parse_suggestions("<html>404</html>") == [])
    check("parse gives nothing for the wrong shape", kr.parse_suggestions('{"a":1}') == [] and kr.parse_suggestions('["q"]') == [] and kr.parse_suggestions('["q","x"]') == [])


def test_expand():
    out = kr.expand("  ACLS Renewal ")
    check("expand lower-cases and trims the seed", out[0] == "acls renewal")
    check("expand adds every prefix and suffix once", len(out) == 1 + len(kr.PREFIXES) + len(kr.SUFFIXES) and "how acls renewal" in out and "acls renewal cost" in out)


def test_collect():
    canned = {
        "emergency medicine cme": '["x",["emergency medicine cme online","emergency medicine symbol","cooking pasta recipes","  Emergency   Medicine CME  Courses "]]',
    }
    calls = []

    def fetch(url):
        calls.append(url)
        for q, body in canned.items():
            if "q=" + q.replace(" ", "+") + "&" in url + "&" or "query=" + q.replace(" ", "+") + "&" in url + "&":
                return body
        return '["x",[]]'

    entries, raw, requests, errors = kr.collect(["emergency medicine cme"], fetch=fetch, sleep=lambda s: None)
    check("collect keeps suggestions that share a word with the seed", "emergency medicine cme online" in entries)
    check("collect drops a suggestion with no word in common with the seed", "cooking pasta recipes" not in entries)
    check("collect normalises case and spaces", "emergency medicine cme courses" in entries)
    check("collect counts one request per query and source", requests == len(kr.expand("x")) * len(kr.SOURCES) and len(calls) == requests)
    check("a source that agrees is recorded", entries["emergency medicine cme online"]["sources"] == set(kr.SOURCES))

    def broken(url):
        raise OSError("down")

    entries2, _, req2, err2 = kr.collect(["emergency medicine cme"], fetch=broken, sleep=lambda s: None)
    check("a failing source is counted as an error and gives no keywords", entries2 == {} and err2 == req2 and req2 > 0)

    long_kw = "emergency medicine cme " + "word " * 12
    entries3, _, _, _ = kr.collect(["emergency medicine cme"], fetch=lambda u: json.dumps(["x", [long_kw.strip()]]), sleep=lambda s: None)
    check("a keyword longer than the word limit is dropped", entries3 == {})


def test_score():
    one = kr.score(entry(["google"], [0]), "plain thing")
    three = kr.score(entry(["google", "bing", "duckduckgo"], [0]), "plain thing")
    check("more sources score higher", three > one)
    top = kr.score(entry(["google"], [0]), "plain thing")
    low = kr.score(entry(["google"], [9]), "plain thing")
    check("an earlier position scores higher", top > low)
    intent = kr.score(entry(["google"], [0]), "cme credit course online")
    check("intent words add to the score", intent > top)
    capped = kr.score(entry(["google"], [0]), "cme credit course conference certification")
    check("intent is capped", capped - top <= kr.INTENT_CAP + 1e-9)
    check("the same words score the same in any order", kr.score(entry(["google"], [0]), "cme course") == kr.score(entry(["google"], [0]), "course cme"))


def test_cluster():
    entries = {k: entry(["google"], [i]) for i, k in enumerate([
        "acls renewal online", "acls renewal cost", "acls renewal near me", "pals course", "ultrasound course emergency", "pals course online"])}
    groups = kr.cluster(entries)
    check("keywords sharing a phrase land together", {"acls renewal online", "acls renewal cost", "acls renewal near me"} == {k for k, _ in groups["acls renewal"]})
    check("pals course keywords group", {"pals course", "pals course online"} == {k for k, _ in groups["pals course"]})
    check("a keyword with no shared phrase goes to other", [k for k, _ in groups["other"]] == ["ultrasound course emergency"])
    lone = kr.cluster({k: entry(["google"], [i]) for i, k in enumerate(["acls renewal online", "acls renewal cost", "acls renewal fast", "renewal online"])})
    check("a cluster of one keyword is folded into other", "renewal online" not in lone and "renewal online" in {k for k, _ in lone["other"]})
    check("a phrase made of stop words never names a cluster", all(h == "other" or not set(h.split()) & kr.STOP for h in groups))
    check("clusters are sorted by score", all(g[i][1] >= g[i + 1][1] for g in groups.values() for i in range(len(g) - 1)))


def test_plan():
    rows = kr.plan({
        "acls renewal": [("acls renewal online", 9.0), ("acls renewal cost", 8.0), ("acls renewal near me", 7.0)],
        "how to": [("how to renew acls", 5.0), ("what is acls", 4.0)],
        "cme conference": [("cme conference 2027", 6.0), ("cme conference hawaii", 3.0)],
        "other": [("lonely", 1.0)]})
    check("the highest scoring cluster is the pillar", rows[0]["head"] == "acls renewal" and rows[0]["type"] == "pillar page")
    check("other is listed last", rows[-1]["head"] == "other")
    types = {r["head"]: r["type"] for r in rows}
    check("a question heavy cluster is an FAQ page", types["how to"] == "FAQ page")
    check("a conference cluster is a conference page", types["cme conference"] == "conference page")
    pairs = kr.links(rows)
    check("every other page links to the pillar and the pillar links down", ("how to", "acls renewal") in pairs and ("acls renewal", "cme conference") in pairs and not any(a == "other" or b == "other" for a, b in pairs))
    title, meta = kr.draft("acls renewal", [("acls renewal online", 9.0), ("acls renewal cost", 8.0), ("acls renewal near me", 7.0)])
    check("title is within 60 characters and meta within 155", len(title) <= 60 and len(meta) <= 155 and meta.startswith("Guide to acls renewal online."))
    long_title, long_meta = kr.draft("x", [("word " * 30, 1.0), ("another long keyword " * 10, 1.0)])
    check("a very long keyword is trimmed on a word boundary", len(long_title) <= 60 and len(long_meta) <= 155 and not long_title.endswith("Wor"))
    check("no pages gives no links", kr.links([]) == [] and kr.plan({}) == [])


def test_questions():
    entries = {"how do i renew acls": entry(["google"], [0]), "acls renewal": entry(["google"], [0]), "what is acls": entry(["google"], [0])}
    check("only question keywords of four words or more are offered as questions", kr.question_keywords(entries, 5) == ["how do i renew acls"])


def test_replay():
    replay = json.load(open(FIXTURE, encoding="utf-8"))
    seeds = ["emergency medicine cme", "acls recertification online", "ultrasound course for emergency physicians"]

    def no_network(url):
        raise AssertionError("replay must not touch the network")

    entries, _, requests, errors = kr.collect(seeds, fetch=no_network, sleep=lambda s: None, replay=replay)
    rows = kr.plan(kr.cluster(entries))
    check("the recorded run replays offline with no requests", requests == 0 and errors == 0 and len(entries) > 30)
    check("the recorded run gives a pillar and several pages", rows[0]["type"] == "pillar page" and len([r for r in rows if r["head"] != "other"]) >= 5)
    again, _, _, _ = kr.collect(seeds, fetch=no_network, sleep=lambda s: None, replay=replay)
    check("a replay is deterministic", json.dumps(kr.plan(kr.cluster(again)), default=list, sort_keys=True) == json.dumps(rows, default=list, sort_keys=True))
    text = kr.render(seeds, entries, rows, 0, 0, "2000-01-01")
    check("the report names its date, sources and the volume caveat", "2000-01-01" in text and "not search volumes" in text and "## Content map" in text)


def main():
    test_parse()
    test_expand()
    test_collect()
    test_score()
    test_cluster()
    test_plan()
    test_questions()
    test_replay()
    ok = all(results)
    print("\n%d checks, %s" % (len(results), "all passed" if ok else "SOME FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

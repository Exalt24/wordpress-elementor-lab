# LIFESPAN: permanent
"""Keyword and topic research from keyless public suggestion endpoints, clustered into a content map.

    python scripts/keyword_research.py "emergency medicine cme" "acls recertification online" --out docs/keyword-research-sample.md
    python scripts/keyword_research.py --seeds-file seeds.txt --record fixtures.json     # save the raw responses
    python scripts/keyword_research.py --seeds-file seeds.txt --replay fixtures.json     # rerun offline from the saved responses

Sources: Google, Bing and DuckDuckGo autocomplete (no key, no account). Each seed is expanded with question and modifier words,
every suggestion is scored, grouped by its most shared two-word phrase, and turned into a page plan with a title and meta draft.
Suggestions are not search volumes: no keyless source gives volumes, so the score ranks by agreement and position only.
Low volume by design: one request per second and a User-Agent that says what this is. Standard library only.
"""
import argparse
import datetime
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter

UA = "seo-lab/1.0 (personal research, low volume; github.com/Exalt24/wordpress-elementor-lab)"
SOURCES = {
    "google": "https://suggestqueries.google.com/complete/search?client=firefox&q={q}",
    "bing": "https://api.bing.com/osjson.aspx?query={q}",
    "duckduckgo": "https://duckduckgo.com/ac/?q={q}&type=list",
}
PREFIXES = ["how", "what", "which", "can", "best", "free"]
SUFFIXES = ["vs", "for", "online", "requirements", "cost"]
QUESTION_WORDS = ("how", "what", "which", "can", "why", "when", "do", "does", "is", "are", "should")
INTENT_WORDS = {"cme": 2, "credit": 2, "credits": 2, "course": 2, "courses": 2, "conference": 2, "conferences": 2,
                "certification": 2, "recertification": 2, "renewal": 1, "online": 1, "requirements": 1, "cost": 1,
                "free": 0.5, "2026": 0.5, "2027": 0.5}
INTENT_CAP = 3
STOP = {"a", "an", "the", "of", "for", "and", "or", "to", "in", "on", "with", "is", "are", "do", "does", "how", "what",
        "which", "can", "best", "free", "vs", "near", "me", "my", "i", "you", "your", "it", "at", "by", "from", "why", "when"}
MAX_WORDS = 10
MIN_CLUSTER_SIZE = 2   # a cluster smaller than this is folded into 'other'


def normalise(text):
    return re.sub(r"\s+", " ", str(text).strip().lower())


def words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def content_words(text):
    return [w for w in words(text) if w not in STOP]


def parse_suggestions(raw):
    """The three endpoints answer [query, [suggestion, ...], ...]. Anything else yields no suggestions."""
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(data, list) or len(data) < 2 or not isinstance(data[1], list):
        return []
    return [s for s in data[1] if isinstance(s, str)]


def expand(seed):
    seed = normalise(seed)
    return [seed] + [p + " " + seed for p in PREFIXES] + [seed + " " + s for s in SUFFIXES]


def http_fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", "replace")


def key_of(source, query):
    return hashlib.sha1((source + "|" + query).encode()).hexdigest()[:16]


def collect(seeds, fetch=http_fetch, sleep=time.sleep, delay=1.0, replay=None):
    """Return ({keyword: {"sources": set, "ranks": [int], "seeds": set}}, raw responses by key, request count, error count)."""
    entries, raw_log, requests, errors = {}, {}, 0, 0
    for seed in seeds:
        seed_words = set(content_words(seed))
        for query in expand(seed):
            for source, template in SOURCES.items():
                k = key_of(source, query)
                if replay is not None:
                    raw = replay.get(k)
                    if raw is None:
                        continue
                else:
                    sleep(delay)
                    requests += 1
                    try:
                        raw = fetch(template.format(q=urllib.parse.quote_plus(query)))
                    except Exception:
                        errors += 1
                        continue
                raw_log[k] = raw
                for rank, sug in enumerate(parse_suggestions(raw)):
                    kw = normalise(sug)
                    if not kw or len(words(kw)) > MAX_WORDS:
                        continue
                    if not seed_words & set(content_words(kw)):
                        continue  # drifted away from the seed
                    e = entries.setdefault(kw, {"sources": set(), "ranks": [], "seeds": set()})
                    e["sources"].add(source)
                    e["ranks"].append(rank)
                    e["seeds"].add(seed)
    return entries, raw_log, requests, errors


def score(entry, kw):
    agreement = len(entry["sources"]) * 3
    position = sum(1.0 / (r + 1) for r in entry["ranks"])
    intent = min(INTENT_CAP, sum(INTENT_WORDS.get(w, 0) for w in set(words(kw))))
    return round(agreement + position + intent, 2)


def is_question(kw):
    w = words(kw)
    return bool(w) and w[0] in QUESTION_WORDS


def bigrams(kw):
    w = [x for x in words(kw)]
    return [(a, b) for a, b in zip(w, w[1:]) if a not in STOP and b not in STOP]


def cluster(entries):
    """Group each keyword under its most shared two-word phrase; keywords with no shared phrase go to 'other'."""
    counts = Counter(b for kw in entries for b in set(bigrams(kw)))
    groups = {}
    for kw in entries:
        shared = [(counts[b], b) for b in bigrams(kw)]
        head = " ".join(sorted(shared, key=lambda x: (-x[0], x[1]))[0][1]) if shared else "other"
        groups.setdefault(head, []).append((kw, score(entries[kw], kw)))
    for head in [h for h, items in groups.items() if h != "other" and len(items) < MIN_CLUSTER_SIZE]:
        groups.setdefault("other", []).extend(groups.pop(head))  # a page of one keyword is not a page
    for head in groups:
        groups[head].sort(key=lambda x: (-x[1], x[0]))
    return groups


def page_type(head, items):
    hw = set(words(head))
    if sum(1 for kw, _ in items if is_question(kw)) * 2 >= len(items):
        return "FAQ page"
    if hw & {"conference", "conferences"}:
        return "conference page"
    if hw & {"course", "courses", "online", "certification", "recertification"}:
        return "course page"
    return "topic page"


def trim(text, limit):
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",;:- ")


def draft(head, items):
    top = items[0][0]
    title = trim(top.title(), 60)
    rest = [kw for kw, _ in items[1:4]]
    meta = "Guide to " + top + "." + (" Covers " + ", ".join(rest[:-1]) + (" and " if len(rest) > 1 else "") + rest[-1] + "." if rest else "")
    return title, trim(meta, 155)


def plan(groups):
    rows = []
    for head, items in groups.items():
        total = round(sum(s for _, s in items), 2)
        title, meta = draft(head, items)
        rows.append({"head": head, "size": len(items), "total": total, "type": page_type(head, items), "title": title, "meta": meta, "items": items})
    rows = [r for r in rows if r["head"] != "other"] + [r for r in rows if r["head"] == "other"]
    rows.sort(key=lambda r: (r["head"] == "other", -r["total"], r["head"]))
    if rows and rows[0]["head"] != "other":
        rows[0]["type"] = "pillar page"
    return rows


def links(rows):
    named = [r for r in rows if r["head"] != "other"]
    if not named:
        return []
    pillar = named[0]
    pairs = [(r["head"], pillar["head"]) for r in named[1:]]
    pairs += [(pillar["head"], r["head"]) for r in named[1:4]]
    return pairs


def render(seeds, entries, rows, requests, errors, today, replayed=False):
    out = ["# Keyword research sample", "",
           "_%s %s from Google, Bing and DuckDuckGo autocomplete (no key). %d seeds, %d %s, %d request errors, %d distinct keywords. "
           "Scores rank by source agreement and position; these are suggestions, not search volumes._" % (
               "Built from a recorded live run of" if replayed else "Run on", today, len(seeds), requests, "responses replayed" if replayed else "requests", errors, len(entries)), "",
           "## Content map", "", "| Page | Type | Keywords | Score | Title draft |", "|---|---|---|---|---|"]
    for r in rows:
        out.append("| %s | %s | %d | %s | %s |" % (r["head"], r["type"], r["size"], r["total"], r["title"]))
    out += ["", "## Internal links", ""]
    for a, b in links(rows):
        out.append("- %s -> %s" % (a, b))
    out += ["", "## Clusters", ""]
    for r in rows:
        out += ["### %s (%s)" % (r["head"], r["type"]), "", "Meta draft: " + r["meta"], ""]
        for kw, s in r["items"][:8]:
            out.append("- %s (%s)" % (kw, s))
        out.append("")
    return "\n".join(out)


def question_keywords(entries, limit):
    qs = [(score(e, kw), kw) for kw, e in entries.items() if is_question(kw) and len(words(kw)) >= 4]
    qs.sort(key=lambda x: (-x[0], x[1]))
    return [kw for _, kw in qs[:limit]]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("seeds", nargs="*")
    ap.add_argument("--seeds-file")
    ap.add_argument("--record")
    ap.add_argument("--replay")
    ap.add_argument("--out")
    ap.add_argument("--questions-out")
    ap.add_argument("--questions", type=int, default=15)
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    a = ap.parse_args(argv)
    seeds = list(a.seeds)
    if a.seeds_file:
        seeds += [l.strip() for l in open(a.seeds_file, encoding="utf-8") if l.strip()]
    if not seeds:
        ap.error("give at least one seed")
    replay = json.load(open(a.replay, encoding="utf-8")) if a.replay else None
    entries, raw_log, requests, errors = collect(seeds, replay=replay)
    if a.record:
        json.dump(raw_log, open(a.record, "w", encoding="utf-8"), indent=0)
    rows = plan(cluster(entries))
    text = render(seeds, entries, rows, len(raw_log) if replay is not None else requests, errors, a.date, replayed=replay is not None)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text + "\n")
    else:
        print(text)
    if a.questions_out:
        open(a.questions_out, "w", encoding="utf-8").write("\n".join(question_keywords(entries, a.questions)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

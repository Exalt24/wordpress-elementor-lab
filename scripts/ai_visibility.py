# LIFESPAN: permanent
"""Measure how often named organisations appear in an AI model's answers to a list of questions.

    python scripts/ai_visibility.py --questions questions.txt --entities "ACEP,EM:RAP,Medscape" --engine ollama --model qwen3.5:9b --repeats 3
    python scripts/ai_visibility.py --questions questions.txt --entities "Brand" --engine openai --base-url https://api.groq.com/openai/v1 --model <id> --key-env GROQ_API_KEY

Each question is asked --repeats times; an answer counts a name when it appears as a whole word or phrase, ignoring case. The report
gives mentions out of answers with a 95 percent Wilson interval, because a model answers differently each time and one run proves little.
An engine error is counted as an error and never as 'not mentioned'. Engines: a local Ollama model, or any OpenAI compatible endpoint.
This asks a model; it is not a search engine. ChatGPT, Perplexity and Google AI Overviews are not queried by this script.
Standard library only.
"""
import argparse
import datetime
import json
import math
import os
import re
import sys
import urllib.request

SYSTEM = "Answer the question briefly. Name specific organisations, courses or websites where they are relevant."
Z = 1.96


def wilson(k, n, z=Z):
    """95 percent Wilson score interval for k successes in n trials."""
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def mentioned(text, entity):
    pattern = r"(?<![a-z0-9])" + re.escape(entity.lower()) + r"(?![a-z0-9])"
    return re.search(pattern, text.lower()) is not None


def post_json(url, body, headers, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=dict({"Content-Type": "application/json"}, **headers))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


class OllamaEngine:
    def __init__(self, model, base_url="http://localhost:11434", timeout=300):
        self.model, self.base_url, self.timeout = model, base_url.rstrip("/"), timeout
        self.label = "local Ollama model " + model

    def ask(self, question):
        data = post_json(self.base_url + "/api/chat", {"model": self.model, "stream": False, "think": False,
                         "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]}, {}, self.timeout)
        return data["message"]["content"]


class OpenAIEngine:
    def __init__(self, model, base_url, key, timeout=120):
        self.model, self.base_url, self.key, self.timeout = model, base_url.rstrip("/"), key, timeout
        self.label = "OpenAI compatible endpoint, model " + model

    def ask(self, question):
        data = post_json(self.base_url + "/chat/completions", {"model": self.model,
                         "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]},
                         {"Authorization": "Bearer " + self.key}, self.timeout)
        return data["choices"][0]["message"]["content"]


def run(questions, engine, entities, repeats):
    """{question: {"answers": n, "errors": e, "counts": {entity: k}}}"""
    results = {}
    for q in questions:
        r = {"answers": 0, "errors": 0, "counts": {e: 0 for e in entities}}
        for _ in range(repeats):
            try:
                text = engine.ask(q)
            except Exception:
                r["errors"] += 1
                continue
            r["answers"] += 1
            for e in entities:
                if mentioned(text, e):
                    r["counts"][e] += 1
        results[q] = r
    return results


def pct(x):
    return "%d%%" % round(x * 100)


def report(results, entities, label, today, repeats):
    total = sum(r["answers"] for r in results.values())
    errors = sum(r["errors"] for r in results.values())
    out = ["# AI answer visibility sample", "",
           "_Run on %s against %s. %d questions asked %d times each: %d answers, %d errors. "
           "A name counts when it appears as a whole word in the answer. Intervals are 95 percent Wilson._" % (today, label, len(results), repeats, total, errors), "",
           "## Share of answers naming each organisation", "", "| Name | Answers naming it | Rate | 95 percent interval |", "|---|---|---|---|"]
    for e in entities:
        k = sum(r["counts"][e] for r in results.values())
        lo, hi = wilson(k, total)
        out.append("| %s | %d of %d | %s | %s to %s |" % (e, k, total, pct(k / total) if total else "n/a", pct(lo), pct(hi)))
    out += ["", "## By question", "", "| Question | Answers | " + " | ".join(entities) + " |", "|---|---|" + "---|" * len(entities)]
    for q, r in results.items():
        out.append("| %s | %d | " % (q, r["answers"]) + " | ".join(str(r["counts"][e]) for e in entities) + " |")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--questions", required=True)
    ap.add_argument("--entities", required=True)
    ap.add_argument("--engine", choices=["ollama", "openai"], default="ollama")
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url")
    ap.add_argument("--key-env", default="OPENAI_API_KEY")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--out")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    a = ap.parse_args(argv)
    questions = [l.strip() for l in open(a.questions, encoding="utf-8") if l.strip()]
    entities = [e.strip() for e in a.entities.split(",") if e.strip()]
    if a.engine == "ollama":
        engine = OllamaEngine(a.model, a.base_url or "http://localhost:11434")
    else:
        key = os.environ.get(a.key_env, "")
        if not key or not a.base_url:
            ap.error("the openai engine needs --base-url and a key in the environment variable named by --key-env")
        engine = OpenAIEngine(a.model, a.base_url, key)
    text = report(run(questions, engine, entities, a.repeats), entities, engine.label, a.date, a.repeats)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

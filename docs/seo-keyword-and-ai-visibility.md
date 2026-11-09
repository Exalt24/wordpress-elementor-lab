# Keyword research and AI answer visibility

Two small scripts that cover the research half of an SEO plan: what people type, how to group it into pages, and whether a model names your organisation when someone asks. Both use the standard library only.

## Keyword and topic research

```
python scripts/keyword_research.py "emergency medicine cme" "acls recertification online" --out docs/keyword-research-sample.md
python scripts/keyword_research.py --seeds-file seeds.txt --record fixtures.json     # save the raw responses
python scripts/keyword_research.py --seeds-file seeds.txt --replay fixtures.json     # rerun offline, no requests
```

How it works:

1. Each seed is expanded with question and modifier words (how, what, which, can, best, free, vs, for, online, requirements, cost).
2. Every query goes to Google, Bing and DuckDuckGo autocomplete, one request per second, with a User-Agent that says what the script is. There is no key and no account.
3. A suggestion is kept only if it shares a word with its seed, so a drifting suggestion is dropped.
4. The score is three points for each source that returned the keyword, plus one over the rank for each appearance, plus a small capped bonus for words that signal a buyer (course, credit, certification, online, cost).
5. Each keyword is grouped under its most shared two-word phrase. A group of one keyword is not a page, so it moves to `other`.
6. The largest group is the pillar page. A group that is mostly questions becomes an FAQ page. Each page gets a title draft of 60 characters or fewer and a meta draft of 155 or fewer, and every page links to the pillar while the pillar links down to the next three.

`docs/keyword-research-sample.md` is one run for three seeds about emergency medicine training. `tests/fixtures/suggestions.json` holds the raw responses of that run, so the tests and the sample can be rebuilt offline.

## AI answer visibility

```
python scripts/ai_visibility.py --questions tests/fixtures/questions.txt --entities "ACEP,Medscape" --engine ollama --model qwen3.5:9b --repeats 3
```

Each question is asked several times. A name counts as mentioned when it appears as a whole word or phrase in the answer, ignoring case. The report gives mentions out of answers with a 95 percent Wilson interval, because one answer from a model proves little. A failed call is counted as an error and never as a miss. The engine can be a local Ollama model or any endpoint that speaks the OpenAI chat format.

`docs/ai-visibility-sample.md` is one run against a local model.

## Limits

- The suggestions are not search volumes. No keyless source gives volumes, so the score ranks by agreement and position only. A volume tool or Search Console data is the next step.
- The AI check asks a model. The sample run used a local model, which does not browse and is not ChatGPT or Perplexity. The same script runs against any OpenAI compatible endpoint when a key is available; it was not run against one here.
- Google AI Overviews have no API. Checking them means looking at result pages by hand or through a licensed SERP service, and this repo does neither.
- The questions in the sample come from the keyword step, and the names in the sample run are public medical education organisations chosen for the example.

## Tests

```
python tests/test_keyword_research.py
python tests/test_ai_visibility.py
python tests/mutation_check.py
```

The first two run offline: the keyword tests replay the recorded responses, and the AI tests talk to a stand-in server for both engine types. `mutation_check.py` copies the scripts and tests to a temporary folder, breaks one guard at a time and requires a test to go red each time.

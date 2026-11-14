# LIFESPAN: permanent
"""Prints the numbers that matter from Lighthouse JSON reports, one line per run and a median line.   python scripts/lh_summary.py <report.json>..."""
import json
import statistics
import sys

AUDITS = [("score", None), ("FCP s", "first-contentful-paint"), ("LCP s", "largest-contentful-paint"), ("TBT ms", "total-blocking-time"),
          ("CLS", "cumulative-layout-shift"), ("Speed Index s", "speed-index"), ("server response ms", "server-response-time")]


def read(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    row = [round(d["categories"]["performance"]["score"] * 100)]
    for _, key in AUDITS[1:]:
        v = d["audits"][key]["numericValue"]
        row.append(v if key in ("total-blocking-time", "server-response-time", "cumulative-layout-shift") else v / 1000.0)
    return row


def fmt(label, v):
    if label == "score":
        return "%d" % v
    if label == "CLS":
        return "%.3f" % v
    if label in ("TBT ms", "server response ms"):
        return "%d" % round(v)
    return "%.1f" % v


def main():
    rows = [read(p) for p in sys.argv[1:]]
    print("%-4s " % "run" + " ".join("%18s" % a[0] for a in AUDITS))
    for i, r in enumerate(rows, 1):
        print("%-4d " % i + " ".join("%18s" % fmt(a[0], v) for a, v in zip(AUDITS, r)))
    med = [statistics.median(c) for c in zip(*rows)]
    print("%-4s " % "med" + " ".join("%18s" % fmt(a[0], v) for a, v in zip(AUDITS, med)))


if __name__ == "__main__":
    main()

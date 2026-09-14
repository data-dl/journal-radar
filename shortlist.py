# -*- coding: utf-8 -*-
"""Choose the articles that get a hand-written plain-English translation, and
print their abstracts for writing against.

The picking rule, per journal: prefer articles that led an issue in the recent
window, then the ones the field itself has noticed (field-weighted citation
impact), then raw citations, then anything that arrived in the inbox.
Everything must have a real abstract -- there is nothing to translate otherwise.
"""
import json, os, sys
from collections import defaultdict
from journals import JOURNALS, BY_KEY

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
RECENT = "2026-05-11"          # the dashboard's default 120-day window

CAP = defaultdict(lambda: 5)
CAP.update(dict(lancet=9, nejm=9, synthese=8, philstudies=8, jamapsych=6,
                lancetpsych=6, aer=6, analysis=6, jpe=6, ajps=5, ppr=5,
                mind=5, ethics=5, nous=5, philreview=5, qje=5))


def score(a):
    s = 0.0
    if a.get("lead"):
        s += 3.0
    if a["d"] >= RECENT:
        s += 2.5
    if a.get("emailed"):
        s += 2.0
    s += min((a["fwci"] or 0), 8.0) * 0.8
    s += min(a["cited"], 60) * 0.05
    if a["kind"] == "review":
        s += 0.4
    if a.get("oa"):
        s += 0.3
    return s


def main():
    d = json.load(open(os.path.join(DATA, "articles.json"), encoding="utf-8"))
    arts = d["articles"]
    want = sys.argv[1] if len(sys.argv) > 1 else None

    picks = []
    for j in JOURNALS:
        pool = [a for a in arts
                if a["j"] == j["key"] and a["kind"] in ("research", "review")
                and len(a["ab"]) > 250 and not a["retracted"]]
        pool.sort(key=score, reverse=True)
        picks.extend(pool[:CAP[j["key"]]])

    picks.sort(key=lambda a: (BY_KEY[a["j"]]["field"], a["j"], -score(a)))
    json.dump([a["id"] for a in picks],
              open(os.path.join(DATA, "shortlist_ids.json"), "w"), indent=0)
    if want:
        picks = [a for a in picks if BY_KEY[a["j"]]["field"].lower().startswith(want.lower())]

    for a in picks:
        jn = BY_KEY[a["j"]]["name"]
        tags = []
        if a.get("lead"):
            tags.append("LEAD of %s %s:%s" % (jn, a["vol"], a["iss"]))
        if a.get("emailed"):
            tags.append("EMAILED " + a["emailed"])
        if a["design"]:
            tags.append(a["design"])
        print("\n" + "=" * 100)
        print("ID   %s" % a["id"])
        print("%s | %s | %s | cited %d | fwci %s%s"
              % (jn, a["d"], a["kind"], a["cited"],
                 ("%.1f" % a["fwci"]) if a["fwci"] is not None else "-",
                 (" | " + " | ".join(tags)) if tags else ""))
        print("T    %s" % a["t"])
        print("A    %s" % ", ".join(a["au"][:5]) + (" et al." if a["nau"] > 5 else ""))
        ab = a["ab"]
        print("AB   %s" % (ab[:1700] + ("..." if len(ab) > 1700 else "")))
    print("\n\n%d articles shortlisted%s" % (len(picks), (" for " + want) if want else ""))


if __name__ == "__main__":
    main()

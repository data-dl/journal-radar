# -*- coding: utf-8 -*-
"""Resolve every journal's OpenAlex source id from its ISSN and cross-check the
hard-coded id in journals.py.  Run this before a harvest; a wrong source id fails
silently (an empty shelf), which is the one failure mode worth spending a request on.
"""
import json, sys, time
from net import get_json
from journals import JOURNALS

W = "from_publication_date:2025-09-08,to_publication_date:2026-09-08"
out = {}
bad = []
for j in JOURNALS:
    resolved, name = None, None
    for issn in j["issn"]:
        try:
            s = get_json("https://api.openalex.org/sources/issn:" + issn)
            resolved = s["id"].rsplit("/", 1)[-1]
            name = s["display_name"]
            break
        except Exception:
            continue
    n_id = n_issn = -1
    if resolved:
        n_id = get_json("https://api.openalex.org/works?per-page=1&filter="
                        "primary_location.source.id:%s,%s" % (resolved, W))["meta"]["count"]
    issn_or = "|".join(j["issn"])
    n_issn = get_json("https://api.openalex.org/works?per-page=1&filter="
                      "primary_location.source.issn:%s,%s" % (issn_or, W))["meta"]["count"]
    flag = "" if resolved == j["openalex"] else "  <-- registry says %s" % j["openalex"]
    if resolved != j["openalex"]:
        bad.append((j["key"], j["openalex"], resolved))
    print("%-14s %-10s id=%5d issn=%5d  %s%s" % (j["key"], resolved, n_id, n_issn, name, flag))
    out[j["key"]] = dict(source_id=resolved, display_name=name, n_by_id=n_id, n_by_issn=n_issn)
    time.sleep(0.05)

json.dump(out, open("data/source_check.json", "w"), indent=1)
print("\n%d of %d registry ids disagree with OpenAlex" % (len(bad), len(JOURNALS)))
for k, was, now in bad:
    print("   %-14s %-12s -> %s" % (k, was, now))

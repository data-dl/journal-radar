# -*- coding: utf-8 -*-
"""Turn the raw harvest into the article list the dashboard reads.

Four jobs:

  1. Clean the titles.  Publishers deposit them with stray colons, trailing
     commas, italic markers and placeholder text.
  2. Sort every record into a kind -- research, review, book review, comment,
     correspondence, case report, erratum, front matter -- so that a shelf of
     "the latest research" is actually research.  Two thirds of a week of The
     Lancet is correspondence and news.
  3. Work out which article led its issue.
  4. Attach the email-alert record and score everything.
"""
import json, os, re, statistics, unicodedata
from collections import defaultdict

from journals import JOURNALS, BY_KEY

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
MED = {"lancet", "nejm", "lancetpsych", "jamapsych", "ajph"}

# Journals whose short, abstract-less items are book reviews rather than articles.
# Analysis is deliberately excluded: its articles really are four pages long.
REVIEW_SECTIONS = {"philreview", "jhp", "mind", "ethics", "pq", "nous", "ppr", "jphil"}

FRONT_MATTER = re.compile(
    r"^(issue information|front matter|back matter|editorial board|table of contents|"
    r"volume information|index to volume|notes on contributors|manuscript reviewers|"
    r"books received|books of interest|recent publications|jhp announcements|"
    r"acknowledg|contributors|masthead|title page|advertisement|list of referees|"
    r"referees for|announcements?$|erratum$|corrigendum$)", re.I)

BOOKREVIEW_PATTERNS = [
    re.compile(r"\(review\)\s*$", re.I),
    re.compile(r"^\s*(book\s+reviews?|review\s+essay)\s*$", re.I),
    re.compile(r"^\s*(review of|critical notice)\b", re.I),
    re.compile(r",\s*by\s+[A-Z][\w'’.\-]+", re.U),          # Mind house style
    re.compile(r"\.\s*(edited\s+by|translated\s+by)\s+[A-Z]", re.I),
]

ERRATUM = re.compile(r"^\s*(correction to|corrigendum|erratum|retraction|"
                     r"withdrawn|author correction|expression of concern)\b", re.I)

PT_ERRATUM = {"Published Erratum", "Retraction of Publication", "Retracted Publication",
              "Expression of Concern"}
PT_NEWS = {"News", "Obituary", "Biography", "Portrait", "Interview",
           "Historical Article", "Newspaper Article", "Personal Narrative",
           "Address", "Congress", "Introductory Journal Article"}
PT_REVIEW = {"Review", "Systematic Review", "Meta-Analysis", "Network Meta-Analysis",
             "Scoping Review", "Practice Guideline", "Guideline", "Consensus Development Conference"}
PT_TRIAL = {"Randomized Controlled Trial", "Clinical Trial", "Clinical Trial, Phase I",
            "Clinical Trial, Phase II", "Clinical Trial, Phase III", "Clinical Trial, Phase IV",
            "Controlled Clinical Trial", "Pragmatic Clinical Trial", "Equivalence Trial",
            "Multicenter Study", "Observational Study", "Comparative Study",
            "Adaptive Clinical Trial", "Clinical Trial Protocol", "Validation Study",
            "Evaluation Study", "Twin Study"}

DESIGN_LABEL = [
    ("Randomized Controlled Trial", "Randomised trial"),
    ("Network Meta-Analysis", "Network meta-analysis"),
    ("Meta-Analysis", "Meta-analysis"),
    ("Systematic Review", "Systematic review"),
    ("Clinical Trial, Phase III", "Phase 3 trial"),
    ("Clinical Trial, Phase II", "Phase 2 trial"),
    ("Clinical Trial, Phase I", "Phase 1 trial"),
    ("Pragmatic Clinical Trial", "Pragmatic trial"),
    ("Equivalence Trial", "Equivalence trial"),
    ("Observational Study", "Observational study"),
    ("Multicenter Study", "Multicentre study"),
    ("Case Reports", "Case report"),
]

ITALIC = re.compile(r"</?(i|em|b|strong|sub|sup|scp|span)[^>]*>", re.I)
TAGS = re.compile(r"<[^>]+>")
WS = re.compile(r"\s+")


def clean_title(t, journal):
    if not t:
        return ""
    t = ITALIC.sub("", t)
    t = TAGS.sub(" ", t)
    t = (t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
          .replace("&quot;", '"').replace("&apos;", "'").replace("&nbsp;", " ")
          .replace("&#x2018;", "‘").replace("&#x2019;", "’").replace("&#38;", "&"))
    t = WS.sub(" ", t).strip()
    t = re.sub(r"^[:\s]+", "", t)              # Ethics deposits reviews as ": Book Title"
    t = re.sub(r"\s+,", ",", t)                # Mind deposits "Title , by Author"
    t = re.sub(r"[\s,;:.]+$", "", t)
    return t.strip()


def page_span(row):
    """How many printed pages, or None when the publisher deposited no pagination."""
    fp, lp = row.get("first_page") or "", row.get("last_page") or ""
    if not fp and row.get("pages"):
        parts = row["pages"].split("-")
        fp = parts[0]
        lp = parts[1] if len(parts) > 1 else parts[0]
    try:
        a, b = int(re.sub(r"\D", "", fp)), int(re.sub(r"\D", "", lp or fp))
        if 0 < a <= b and b - a < 400:
            return b - a + 1
    except Exception:
        pass
    return None


def first_page_num(row):
    fp = row.get("first_page") or (row.get("pages") or "").split("-")[0]
    m = re.match(r"\s*[eE]?(\d+)", fp or "")
    return int(m.group(1)) if m else None


def classify(row, title, abstract):
    """(kind, study_design)."""
    pts = set(row.get("pub_types") or [])
    oat = (row.get("oa_type") or "").lower()
    jkey = row["journal"]

    if title.lower().startswith("title pending") or not title:
        return "junk", ""
    if ERRATUM.match(title) or oat in ("erratum", "retraction"):
        return "erratum", ""
    if FRONT_MATTER.match(title) or oat == "paratext":
        return "front matter", ""
    # AMA and Elsevier deposit section dividers whose "title" is just the journal's
    # own name. They are not articles and must never be eligible to lead an issue.
    if norm(title) == norm(BY_KEY[jkey]["name"]):
        return "front matter", ""

    if jkey in MED and not pts:
        # A medical item PubMed has no record of. Without its publication type the
        # only honest signal is whether there is a substantive abstract; the Lancet's
        # World Report and News pieces have none, and would otherwise sail through
        # as research and turn up flagged as an issue's lead article.
        return ("research", "") if len(abstract) >= 400 else ("comment", "")

    if pts:                                            # a medical journal
        if pts & PT_ERRATUM:
            return "erratum", ""
        design = next((lab for key, lab in DESIGN_LABEL if key in pts), "")
        if pts & PT_TRIAL or pts & PT_REVIEW:
            if pts & PT_REVIEW and not (pts & PT_TRIAL):
                return "review", design
            return "research", design
        if "Case Reports" in pts:
            return "case report", "Case report"
        if "Letter" in pts:
            return "correspondence", ""
        if pts & PT_NEWS:
            return "comment", ""
        if "Editorial" in pts or "Comment" in pts:
            return "comment", ""
        return ("research", design) if len(abstract) >= 400 else ("comment", design)

    if oat == "book-review":
        return "book review", ""
    for p in BOOKREVIEW_PATTERNS:
        if p.search(title):
            return "book review", ""
    if oat == "review":
        return "review", ""
    if oat in ("editorial",):
        return "comment", ""
    if oat == "letter":
        return "correspondence", ""

    # A humanities journal's review section: short, and no abstract deposited.
    span = page_span(row)
    if (row["journal"] in REVIEW_SECTIONS and len(abstract) < 120
            and span is not None and span <= 8):
        return "book review", ""
    return "research", ""


def norm(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def main():
    raw = json.load(open(os.path.join(DATA, "raw.json"), encoding="utf-8"))
    alerts = json.load(open(os.path.join(DATA, "alerts.json"), encoding="utf-8"))
    rows = raw["rows"]

    # ---- alert index: journal -> [(normalised title, is_prefix, date)]
    alert_titles = defaultdict(list)
    alert_dates = defaultdict(list)
    for a in alerts["alerts"]:
        alert_dates[a["journal"]].append(a["date"])
        for t in a.get("titles", []):
            if t.get("skip"):
                continue
            alert_titles[a["journal"]].append((norm(t["t"]), bool(t.get("prefix")), a["date"]))

    arts, dropped = [], 0
    for r in rows:
        title = clean_title(r["title"], r["journal"])
        abstract = WS.sub(" ", (r["abstract"] or "")).strip()
        kind, design = classify(r, title, abstract)
        if kind == "junk":
            dropped += 1
            continue

        emailed = None
        if r["journal"] in alert_titles:
            nt = norm(title)
            for at, is_pref, when in alert_titles[r["journal"]]:
                if not at:
                    continue
                if (nt.startswith(at) if is_pref else (nt == at or nt.startswith(at))):
                    emailed = when
                    break

        a = dict(
            id=r["doi"] or ("pmid:" + (r["pmid"] or "")) or title[:60],
            j=r["journal"], t=title, d=r["date"], y=r["year"],
            au=[x["name"] for x in r["authors"] if x["name"]][:12],
            inst=next((x["inst"] for x in r["authors"] if x.get("inst")), ""),
            nau=r["n_authors"],
            vol=r["volume"], iss=r["issue"],
            fp=first_page_num(r), span=page_span(r), pages=r["pages"],
            kind=kind, design=design,
            ab=abstract, absrc=r["abstract_source"],
            absec=r["abstract_sections"][:8],
            cited=r["cited"], fwci=r["fwci"], refs=r["refs"],
            topics=[t for t in (r["topics"] or []) if t][:3],
            mesh=r["mesh"][:8],
            oa=r["is_oa"], oastat=r["oa_status"],
            url=r["url"], pdf=r["pdf"], doi=r["doi"], pmid=r["pmid"],
            retracted=r["retracted"], emailed=emailed,
        )
        arts.append(a)

    # ---- lead article: first research item in an issue that has a real running order
    by_issue = defaultdict(list)
    for a in arts:
        if a["kind"] in ("research", "review") and a["fp"] is not None and a["vol"] and a["iss"]:
            by_issue[(a["j"], a["vol"], a["iss"])].append(a)
    n_lead = 0
    for key, group in by_issue.items():
        if len(group) < 3:
            continue                              # "led the issue" means nothing in a set of two
        group.sort(key=lambda x: x["fp"])
        for rank, a in enumerate(group, 1):
            a["pos"] = rank
            a["of"] = len(group)
        group[0]["lead"] = True
        n_lead += 1

    # ---- scores
    research = [a for a in arts if a["kind"] in ("research", "review")]
    fw = [a["fwci"] for a in research if a["fwci"] is not None]
    fw_sorted = sorted(fw)

    def pctile(v):
        if v is None or not fw_sorted:
            return None
        lo, hi = 0, len(fw_sorted)
        while lo < hi:
            mid = (lo + hi) // 2
            if fw_sorted[mid] < v:
                lo = mid + 1
            else:
                hi = mid
        return round(100.0 * lo / len(fw_sorted))

    for a in arts:
        a["fwpct"] = pctile(a["fwci"]) if a["kind"] in ("research", "review") else None

    # ---- per-journal roll-up
    stats = {}
    for j in JOURNALS:
        mine = [a for a in arts if a["j"] == j["key"]]
        res = [a for a in mine if a["kind"] in ("research", "review")]
        dates = sorted(a["d"] for a in mine if a["d"])
        cites = [a["cited"] for a in res]
        stats[j["key"]] = dict(
            total=len(mine), research=len(res),
            reviews=sum(1 for a in mine if a["kind"] == "book review"),
            other=len(mine) - len(res) - sum(1 for a in mine if a["kind"] == "book review"),
            with_abstract=sum(1 for a in res if len(a["ab"]) > 120),
            newest=dates[-1] if dates else None, oldest=dates[0] if dates else None,
            issues=len({(a["vol"], a["iss"]) for a in mine if a["vol"] and a["iss"]}),
            cited_total=sum(cites), cited_max=max(cites) if cites else 0,
            cited_median=round(statistics.median(cites), 1) if cites else 0,
            oa=sum(1 for a in res if a["oa"]),
            alerts=len(alert_dates.get(j["key"], [])),
            last_alert=max(alert_dates[j["key"]]) if alert_dates.get(j["key"]) else None,
        )

    out = dict(built=raw["harvested"], window=raw["window"],
               articles=arts, journal_stats=stats,
               alert_calendar={k: sorted(v) for k, v in alert_dates.items()})
    json.dump(out, open(os.path.join(DATA, "articles.json"), "w", encoding="utf-8"),
              ensure_ascii=False)

    from collections import Counter
    print("kept %d, dropped %d placeholders" % (len(arts), dropped))
    print("kinds:", Counter(a["kind"] for a in arts).most_common())
    print("lead articles marked: %d issues" % n_lead)
    print("research with a real abstract: %d of %d"
          % (sum(1 for a in research if len(a["ab"]) > 120), len(research)))
    print("emailed matches:", sum(1 for a in arts if a["emailed"]))


if __name__ == "__main__":
    main()

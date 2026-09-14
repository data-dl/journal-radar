# -*- coding: utf-8 -*-
"""Harvest twelve months of articles for every journal in the registry.

Three sources, each doing what it is best at:

  OpenAlex  -- the spine.  Every journal, every article: authors, affiliations,
               volume/issue/pages, citation count, field-weighted citation impact,
               topics, open-access status, landing page.
  Crossref  -- abstracts and exact pagination for the humanities and social-science
               journals, whose publishers deposit clean JATS abstracts.
  PubMed    -- abstracts AND publication types for the five medical journals.
               Neither The Lancet nor the NEJM deposits an abstract to Crossref, and
               OpenAlex calls all of their content "article", so PubMed is the only
               source that can tell an Original Article from a letter to the editor.

Window: twelve months back from TODAY.  The dashboard defaults to a much shorter
view, but harvesting a year serves two purposes -- four of the journals index so
slowly that a four-month window would show them empty, and citation counts need
time to accumulate before "most cited" means anything.
"""
import json, os, re, sys, time
from datetime import date, timedelta

from net import get_json, fetch, q
from journals import JOURNALS

TODAY = date.today()
FROM = (TODAY - timedelta(days=365)).isoformat()
TO = TODAY.isoformat()
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

OA_SELECT = ",".join([
    "id", "doi", "title", "display_name", "publication_date", "publication_year",
    "biblio", "type", "type_crossref", "cited_by_count", "fwci", "authorships",
    "primary_location", "best_oa_location", "open_access", "abstract_inverted_index",
    "topics", "referenced_works_count", "is_retracted", "language",
])


# ----------------------------------------------------------------- OpenAlex
def deinvert(idx):
    """Rebuild an abstract from OpenAlex's inverted index."""
    if not idx:
        return ""
    pos = []
    for word, places in idx.items():
        for p in places:
            pos.append((p, word))
    pos.sort()
    return " ".join(w for _, w in pos).strip()


def openalex_journal(j):
    issn_or = "|".join(j["issn"])
    filt = ("primary_location.source.issn:%s,from_publication_date:%s,"
            "to_publication_date:%s" % (issn_or, FROM, TO))
    out, cursor = [], "*"
    while cursor:
        url = ("https://api.openalex.org/works?filter=%s&per-page=200&cursor=%s&select=%s"
               % (filt, q(cursor), OA_SELECT))
        d = get_json(url)
        out.extend(d["results"])
        cursor = d["meta"].get("next_cursor")
        if not d["results"]:
            break
    return out


# ----------------------------------------------------------------- Crossref
JATS = re.compile(r"<[^>]+>")
WS = re.compile(r"\s+")


def clean_abstract(s):
    if not s:
        return ""
    s = re.sub(r"(?is)<jats:title>\s*abstract\s*</jats:title>", " ", s)
    s = re.sub(r"(?is)</jats:(p|sec|title)>", " ", s)
    s = JATS.sub(" ", s)
    s = (s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
          .replace("&quot;", '"').replace("&#x2018;", "‘").replace("&#x2019;", "’")
          .replace("&apos;", "'").replace("&nbsp;", " "))
    return WS.sub(" ", s).strip()


def crossref_journal(j):
    """All Crossref records for one journal in the window, keyed by lowercase DOI."""
    sel = ("DOI,title,subtitle,abstract,page,volume,issue,type,issued,published,"
           "is-referenced-by-count,author,container-title,link,URL,subject")
    rows = {}
    for issn in j["issn"]:
        cursor, seen_any = "*", False
        while cursor:
            url = ("https://api.crossref.org/journals/%s/works?filter=from-pub-date:%s,"
                   "until-pub-date:%s&rows=500&cursor=%s&select=%s"
                   % (issn, FROM, TO, q(cursor), q(sel)))
            try:
                d = get_json(url)
            except Exception:
                break
            items = d["message"]["items"]
            for it in items:
                rows[it["DOI"].lower()] = it
            seen_any = seen_any or bool(items)
            cursor = d["message"].get("next-cursor")
            if not items:
                break
        if seen_any:
            break          # the first ISSN that answers is enough
    return rows


# ------------------------------------------------------------------- PubMed
EUT = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
TAG = re.compile(r"<[^>]+>")


def _txt(s):
    s = TAG.sub("", s)
    s = (s.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
          .replace("&quot;", '"').replace("&apos;", "'"))
    return WS.sub(" ", s).strip()


def pubmed_journal(j):
    """PubMed records for one medical journal, keyed by lowercase DOI."""
    term = '"%s"[ta] AND %s:%s[dp]' % (j["pubmed"], FROM.replace("-", "/"), TO.replace("-", "/"))
    ids, retstart = [], 0
    while True:
        d = get_json(EUT + "esearch.fcgi?db=pubmed&retmode=json&retmax=500&retstart=%d&term=%s"
                     % (retstart, q(term)))
        batch = d["esearchresult"]["idlist"]
        ids.extend(batch)
        retstart += len(batch)
        if len(batch) < 500 or retstart >= int(d["esearchresult"]["count"]):
            break

    rows = {}
    for i in range(0, len(ids), 200):
        chunk = ids[i:i + 200]
        xml = fetch(EUT + "efetch.fcgi?db=pubmed&retmode=xml&id=" + ",".join(chunk))
        for m in re.finditer(r"<PubmedArticle>.*?</PubmedArticle>", xml, re.S):
            s = m.group(0)
            doi = re.search(r'<ArticleId IdType="doi">(.*?)</ArticleId>', s)
            pmid = re.search(r"<PMID[^>]*>(\d+)</PMID>", s)
            title = re.search(r"<ArticleTitle>(.*?)</ArticleTitle>", s, re.S)
            pgn = re.search(r"<MedlinePgn>(.*?)</MedlinePgn>", s)
            ptypes = [_txt(x) for x in
                      re.findall(r"<PublicationType[^>]*>(.*?)</PublicationType>", s, re.S)]
            mesh = [_txt(x) for x in
                    re.findall(r"<DescriptorName[^>]*>(.*?)</DescriptorName>", s, re.S)]
            secs = []
            for am in re.finditer(r"<AbstractText([^>]*)>(.*?)</AbstractText>", s, re.S):
                lab = re.search(r'Label="([^"]*)"', am.group(1))
                secs.append((lab.group(1).title() if lab else "", _txt(am.group(2))))
            rec = dict(pmid=pmid.group(1) if pmid else None,
                       title=_txt(title.group(1)) if title else "",
                       pages=_txt(pgn.group(1)) if pgn else "",
                       pub_types=ptypes, mesh=mesh[:12],
                       abstract_sections=[dict(label=l, text=t) for l, t in secs if t],
                       abstract=" ".join(("%s: %s" % (l, t)) if l else t for l, t in secs if t))
            if doi:
                rows[doi.group(1).lower()] = rec
            elif rec["pmid"]:
                rows["pmid:" + rec["pmid"]] = rec
    return rows


# --------------------------------------------------------------------- main
def main():
    os.makedirs(DATA, exist_ok=True)
    all_rows, report = [], []
    for j in JOURNALS:
        t0 = time.time()
        works = openalex_journal(j)
        cr = crossref_journal(j)
        pm = pubmed_journal(j) if j["pubmed"] else {}

        # Crossref rows OpenAlex missed entirely still deserve a place on the shelf.
        seen = set()
        for w in works:
            if w.get("doi"):
                seen.add(w["doi"].lower().replace("https://doi.org/", ""))
        extra = [d for d in cr if d not in seen]

        rows = []
        for w in works:
            doi = (w.get("doi") or "").lower().replace("https://doi.org/", "")
            rows.append(merge(j, w, cr.get(doi), pm.get(doi)))
        for doi in extra:
            rows.append(merge(j, None, cr[doi], pm.get(doi)))

        all_rows.extend(rows)
        report.append(dict(key=j["key"], name=j["name"], openalex=len(works),
                           crossref=len(cr), pubmed=len(pm), extra=len(extra),
                           total=len(rows), secs=round(time.time() - t0, 1)))
        print("%-14s oa=%5d cr=%5d pm=%5d +%3d  -> %5d  (%.0fs)"
              % (j["key"], len(works), len(cr), len(pm), len(extra), len(rows),
                 time.time() - t0))
        sys.stdout.flush()

    json.dump(dict(harvested=TODAY.isoformat(), window=[FROM, TO], rows=all_rows),
              open(os.path.join(DATA, "raw.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    json.dump(report, open(os.path.join(DATA, "harvest_report.json"), "w"), indent=1)
    print("\n%d rows -> data/raw.json" % len(all_rows))


def merge(j, w, c, p):
    """One article, from whichever of the three sources have it."""
    w = w or {}
    c = c or {}
    p = p or {}
    doi = (w.get("doi") or "").replace("https://doi.org/", "") or c.get("DOI", "")
    bib = w.get("biblio") or {}

    title = (w.get("display_name") or w.get("title") or "")
    if not title and c.get("title"):
        title = c["title"][0]
    if not title:
        title = p.get("title", "")

    # abstract: OpenAlex has the widest coverage, Crossref the cleanest text,
    # PubMed the only one for Lancet/NEJM.
    ab_oa = deinvert(w.get("abstract_inverted_index"))
    ab_cr = clean_abstract(c.get("abstract"))
    ab_pm = p.get("abstract", "")
    abstract, ab_src = "", ""
    for cand, src in ((ab_cr, "crossref"), (ab_pm, "pubmed"), (ab_oa, "openalex")):
        if len(cand) > len(abstract):
            abstract, ab_src = cand, src

    auths = []
    for a in (w.get("authorships") or [])[:24]:
        insts = [i.get("display_name") for i in (a.get("institutions") or []) if i.get("display_name")]
        auths.append(dict(name=(a.get("author") or {}).get("display_name") or "",
                          inst=insts[0] if insts else ""))
    if not auths and c.get("author"):
        for a in c["author"][:24]:
            nm = (" ".join(x for x in (a.get("given"), a.get("family")) if x)).strip()
            if nm:
                auths.append(dict(name=nm, inst=""))

    loc = w.get("primary_location") or {}
    oa = w.get("open_access") or {}
    best = w.get("best_oa_location") or {}

    date_s = w.get("publication_date") or ""
    if not date_s and c.get("issued", {}).get("date-parts"):
        dp = c["issued"]["date-parts"][0]
        date_s = "%04d-%02d-%02d" % (dp[0], dp[1] if len(dp) > 1 else 1,
                                     dp[2] if len(dp) > 2 else 1)

    return dict(
        journal=j["key"],
        doi=doi,
        pmid=p.get("pmid"),
        title=title,
        authors=auths,
        n_authors=len(w.get("authorships") or c.get("author") or []),
        date=date_s,
        year=w.get("publication_year"),
        volume=bib.get("volume") or c.get("volume") or "",
        issue=bib.get("issue") or c.get("issue") or "",
        first_page=bib.get("first_page") or "",
        last_page=bib.get("last_page") or "",
        pages=c.get("page") or p.get("pages") or "",
        oa_type=w.get("type") or "",
        cr_type=c.get("type") or w.get("type_crossref") or "",
        pub_types=p.get("pub_types") or [],
        mesh=p.get("mesh") or [],
        abstract=abstract,
        abstract_source=ab_src,
        abstract_sections=p.get("abstract_sections") or [],
        cited=w.get("cited_by_count", 0),
        fwci=w.get("fwci"),
        refs=w.get("referenced_works_count", 0),
        topics=[t.get("display_name") for t in (w.get("topics") or [])[:3]],
        subjects=c.get("subject") or [],
        is_oa=bool(oa.get("is_oa")),
        oa_status=oa.get("oa_status") or "",
        url=(loc.get("landing_page_url") or c.get("URL")
             or ("https://doi.org/" + doi if doi else "")),
        pdf=best.get("pdf_url") or loc.get("pdf_url") or "",
        retracted=bool(w.get("is_retracted")),
        language=w.get("language") or "",
    )


if __name__ == "__main__":
    main()

# Journal Radar

Twelve months of tables of contents from 27 peer-reviewed journals — fourteen in analytic
philosophy, five in economics, three in political science, five in medicine and psychiatry —
harvested from OpenAlex, Crossref and PubMed and read into one searchable page: **2,939
articles**, each with its citations, its field-weighted impact, whether it led its issue, and
for 148 of them a plain-English rendering of the abstract.

**Live page:** https://data-dl.github.io/journal-radar/

## Why three sources

No single index covers these journals. OpenAlex supplies the article list, citation counts and
field-weighted citation impact (FWCI: 1.0 is the world average for that field, year and article
type — the fair way to compare a philosophy paper with three citations against a clinical trial
with three hundred). Crossref supplies abstracts where the publisher deposits them. PubMed is not
optional for *The Lancet* and the *NEJM*: neither deposits an abstract to Crossref, and OpenAlex
types all their content as "article", so PubMed's `PublicationType` is the only thing that
separates an Original Article from a letter to the editor — and about two thirds of a Lancet week
is correspondence, comment and news. `net.py` wraps all three in a polite, cached client so a
repeat harvest is nearly free and a half-finished one resumes.

## What the harvest had to get right

- **A wrong journal identifier fails silently as an empty shelf**, not as an error. Eighteen of
  the twenty-seven OpenAlex source ids were wrong on the first pass. `verify_sources.py` resolves
  each journal from its ISSN and diffs the result before any harvest.
- **Two classification faults were only visible on the rendered page.** AMA and Elsevier deposit
  section dividers titled with the journal's own name (an "article" called *JAMA Psychiatry*),
  and Lancet items PubMed has no record of were falling through to "research", which put news
  squibs at the top flagged as lead articles. Both have explicit rules now; the fix moved the
  count from 3,130 to 2,939. The general lesson: sort by the flag you are least sure of and read
  the top twenty rows.
- **"Led its issue"** is the first research article in an issue by page number, in issues with at
  least three research items — the editors' running order, not a guess about importance.
- **Book reviews are inferred** for the humanities journals from the publisher's type, the title
  pattern and a short page span with no abstract; *Analysis* is excluded from the last rule
  because its articles really are four pages long.
- **A twelve-month window even though the page opens on four months**: *Econometrica* and *The
  Journal of Philosophy* index months late, and four-month-old articles have no citations to
  rank by.
- **Chicago deposits no abstracts at all** and its article pages refuse automated requests, so
  three journals are title-and-citation only. The page says so per article rather than leaving
  a blank.

## The page

Three views — a flat article list with six sort orders, the same articles grouped into the
issues they appeared in, and a shelf view of the publishing rhythm by field with a table of all
27 journals. Each journal has a front page (publisher, ISSN, cadence, founded, six figures for
the window, every lead article it ran). Search covers titles, authors, abstracts, the
plain-English text, journal names and topics; `/` jumps to it. "Not yet cited" appears instead
of a zero, because a zero in a column reads like a judgement and it isn't one.

`data/alerts.json` records which journals actually email a table-of-contents alert: only the
University of Chicago Press does, for three journals. The other 24 are silent, which is the one
finding worth acting on — every one of those publishers has a free alert on its own site.

## Rebuilding

```bash
export JOURNAL_RADAR_MAILTO=you@example.com   # polite-pool contact for OpenAlex/Crossref/NCBI
python verify_sources.py      # ISSN -> OpenAlex source id, diffed against journals.py
python harvest.py             # OpenAlex + Crossref + PubMed -> data/raw.json (cached under data/cache)
python enrich.py              # classify, FWCI, lead articles, book reviews -> data/articles.json
python shortlist.py           # pick the articles worth a plain-English rendering
python build.py               # data/*.json -> dist/journal-radar.html
```

`data/cache/` and `data/raw.json` are rebuilt by the harvest and are not committed;
`data/articles.json` and the plain-English files are, so `build.py` runs from a clone. The
plain-English paragraphs live in `data/plain_english*.json` keyed by DOI — add a file rather than
editing the existing three; they are merged by glob. [docs/NOTES.md](docs/NOTES.md) has the API
shapes and the seven traps.

## Provenance

Built in September 2026 with an AI coding assistant as pair programmer, as one of two parallel
builds from the same brief. The plain-English renderings were drafted with the assistant and
checked; the source choices and classification rules are mine. Article metadata belongs to the
publishers and indexes it came from. MIT licensed.

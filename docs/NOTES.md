# Notes for the next build

Written 8 September 2026, for whoever picks this up next.

## Where the shelf came from

Both browsers were read directly, not exported by hand:

- **Firefox** — `places.sqlite` in the profile folder. Copy the
  `-wal` and `-shm` files alongside it or the tables come back empty; the first
  attempt did exactly that and `moz_bookmarks` appeared not to exist.
- **Chrome** — `Default/AccountBookmarks`, not `Bookmarks`. The plain `Bookmarks`
  file can be absent when the browser is signed in; only `Bookmarks.bak` sits beside the account one.

There are seven folders named `Journals` across the two browsers, most of them
duplicates from old Vivaldi and Firefox imports, two of them in a `Trash` tree.
The union is 25 unique peer-reviewed journals plus nine links that are not journals.
Chrome's folder was imported from Firefox, so the two contribute the same set —
there is nothing in one that is missing from the other.

## The two journals that are not bookmarked

*Journal of Labor Economics* and *American Political Thought* are on the shelf
because the mailbox says they are followed, not because a bookmark says so. They carry
`bookmarked=False` in `journals.py` and are labelled in the UI. If anyone asks
"why are these here", that is the answer.

## Identifiers fail silently — always run verify_sources.py

Eighteen of the twenty-seven OpenAlex source ids were wrong on the first attempt.
A wrong id does not error; it returns an empty result set, which looks exactly like
a journal that published nothing. `verify_sources.py` resolves each id from the ISSN
and diffs it against the registry. Run it before any harvest.

Filtering by ISSN and by source id gave identical counts for all 27 journals, so
the harvester filters by ISSN and the stored ids are only a cross-check.

## What each source is for, and why all three

- **OpenAlex** is the spine: authors, affiliations, volume/issue/pages, citation
  counts, FWCI, topics, open-access status.
- **Crossref** supplies clean JATS abstracts for the humanities and social sciences.
- **PubMed** is not optional for the five medical journals. Neither The Lancet nor
  the NEJM deposits an abstract to Crossref, and OpenAlex types every one of their
  items as "article" — 1,352 of 1,432 Lancet items in a year. PubMed's
  `PublicationType` is the only field that separates an Original Article from a
  letter, an editorial, a case report or an obituary.

Semantic Scholar was tried as a fourth source for the Chicago abstract gap and is
not worth it: unauthenticated requests get 429s after one call, and the one that
succeeded had no abstract anyway. The Chicago article pages return 403 to scripted
requests. That gap is real and the page states it per article.

## Classification rules that took tuning

`enrich.py` sorts everything into research / review / book review / comment /
correspondence / case report / erratum / front matter. Two rules are heuristic and
worth knowing:

1. **Humanities book reviews.** Publishers deposit them as ordinary journal
   articles. The catch-all is: no abstract, page span of 8 or fewer, and the journal
   is one that runs a review section (`REVIEW_SECTIONS`). **Analysis is excluded**
   because its real articles are genuinely four pages — that exclusion is load
   bearing, and dropping it would misfile about 40 real papers a year.
2. **Medical "Journal Article" with nothing else.** Falls to research if the
   abstract is 400+ characters, otherwise comment. This is the only place where
   abstract length decides a type.

Ethics deposits its book reviews with the review's title stripped, leaving a
leading `": "` plus the book's title. Mind deposits them as `Title , by Author`.
Both are handled in `clean_title` and `BOOKREVIEW_PATTERNS`.

Philosophers' Imprint deposits placeholder records titled `Title Pending 9896` and
similar — 27 of them were dropped as junk.

## Lead articles

`lead` is the lowest first page among research and review items in an issue, and
only in issues with at least three such items — "led the issue" means nothing in a
set of two. 207 issues got one. Continuous-publication journals that deposit no
issue number get none, correctly.

## The Gmail side is a snapshot, not a feed

`data/alerts.json` was written by hand from a Gmail search on 8 Sep 2026 covering
400 days. The refresh script does **not** re-read the mail; `data/alerts.json` is written separately from a mailbox search. Article
titles from the alert bodies are matched by prefix because the ones taken from list
snippets are truncated mid-sentence; those carry `"prefix": true`.

Only `press.uchicago.edu` sends anything. That was checked broadly — searches
across OUP, Wiley, Springer, Elsevier, JAMA, NEJM, AEA, Duke and Annual Reviews
returned nothing but marketing.

## The plain-English layer

`data/plain_english*.json`, keyed by DOI, merged by `build.py` from every file
matching that glob — so add a fourth file rather than editing the first three.
`shortlist.py` picks and prints the candidates with their abstracts; it scores lead
articles, recency, inbox arrival and FWCI, and caps per journal so The Lancet does
not swallow the budget.

148 of 3,130 have one. If that number should grow, run `shortlist.py`, raise the
`CAP` values, and write against the printed abstracts. Do not generate them from
the abstract text at build time — the whole point is that a person wrote them.

## Design decisions that are deliberate

- **Light by default**, a standing preference. Both themes are defined at
  token level; the dark set is chosen, not inverted.
- **Field colours** are the dataviz reference palette's first four slots in its
  validated order — blue, orange, aqua, yellow. Three of them fall under 3:1 on
  the light paper ground, which is allowed only because the field name always sits
  beside the mark. Do not use these hues without the label.
- **The citation column shows "not yet cited" rather than 0.** A column of zeros
  down a list of new articles reads as a verdict.
- Two outputs: `dist/artifact.html` is a bare body for publishing, `dist/journal-radar.html`
  is wrapped with a doctype and `<meta charset>` for opening off disk. Without the
  charset, `Noûs` renders as mojibake — which is exactly what the first local
  preview showed.

## Published copy

https://data-dl.github.io/journal-radar/

Republish by passing that URL to the Artifact tool with `dist/artifact.html`.
Publishing without the URL makes a second, separate artifact.

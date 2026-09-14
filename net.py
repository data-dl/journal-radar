# -*- coding: utf-8 -*-
"""Polite HTTP with an on-disk cache.

Every source used here is free and open (OpenAlex, Crossref, NCBI E-utilities);
all three ask for a contact address in the User-Agent and give you a faster lane
for supplying one, which is what MAILTO does.  Responses are cached under
data/cache so a re-run costs nothing and a half-finished harvest resumes.
"""
import hashlib, json, os, time, urllib.error, urllib.parse, urllib.request

MAILTO = os.environ.get("JOURNAL_RADAR_MAILTO", "journal-radar@example.com")   # polite-pool contact for Crossref/OpenAlex
UA = {"User-Agent": "JournalRadar/1.0 (+https://github.com/data-dl/journal-radar; mailto:%s)" % MAILTO,
      "Accept": "application/json"}
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "cache")
_last = [0.0]
MIN_GAP = 0.11          # ~9 requests/second ceiling, well inside every published limit


def _throttle():
    dt = time.time() - _last[0]
    if dt < MIN_GAP:
        time.sleep(MIN_GAP - dt)
    _last[0] = time.time()


def _path(url):
    os.makedirs(CACHE, exist_ok=True)
    return os.path.join(CACHE, hashlib.sha1(url.encode("utf-8")).hexdigest() + ".txt")


def fetch(url, cache=True, tries=4):
    """Return the body of `url` as text, from disk if we have already asked."""
    p = _path(url)
    if cache and os.path.exists(p):
        with open(p, "r", encoding="utf-8") as fh:
            return fh.read()
    if "api.openalex.org" in url and "mailto=" not in url:
        url += ("&" if "?" in url else "?") + "mailto=" + MAILTO
    last = None
    for attempt in range(tries):
        try:
            _throttle()
            req = urllib.request.Request(url, headers=UA)
            body = urllib.request.urlopen(req, timeout=180).read().decode("utf-8", "replace")
            if cache:
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(body)
            return body
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (404, 400):
                raise
            time.sleep(2 ** attempt)
        except Exception as e:
            last = e
            time.sleep(2 ** attempt)
    raise last


def get_json(url, cache=True):
    return json.loads(fetch(url, cache=cache))


def q(s):
    return urllib.parse.quote(str(s), safe="")

# -*- coding: utf-8 -*-
"""Render the dashboard.

Reads data/articles.json plus the hand-written plain_english*.json files and
writes dist/journal-radar.html -- one self-contained page, no network calls.
"""
import glob, html, json, os, re
from collections import defaultdict, Counter
from datetime import date, datetime, timedelta

from journals import JOURNALS, BY_KEY, FIELDS, IGNORED

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
DIST = os.path.join(HERE, "dist")

FIELD_HUE = {                      # validated with the dataviz palette checker
    "Philosophy":           ("#2a78d6", "#3987e5"),
    "Economics":            ("#eb6834", "#d95926"),
    "Political science":    ("#1baf7a", "#199e70"),
    "Medicine & psychiatry": ("#eda100", "#c98500"),
}
KEEP = ("research", "review", "book review")

# Column order for the compact article payload. Kept in one place; the page
# decodes it once on load.
COLS = ["id", "j", "t", "au", "nau", "d", "vol", "iss", "fp", "span", "kind",
        "design", "ab", "pe", "cited", "fwci", "fwpct", "topics", "oa", "url",
        "lead", "pos", "of", "emailed", "absrc"]

# The Artifact host wraps the page in its own document, so that copy ships as a
# bare body. The desktop copy is opened straight off disk and needs a real one --
# without the charset declaration a browser renders "Noûs" as mojibake.
HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>html{color-scheme:light}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>
</head>
<body>
"""
FOOT = """
</body>
</html>
"""


def load_plain_english():
    pe = {}
    for f in sorted(glob.glob(os.path.join(DATA, "plain_english*.json"))):
        for k, v in json.load(open(f, encoding="utf-8")).items():
            if not k.startswith("_"):
                pe[k] = v
    return pe


def weeks_back(n=52):
    end = date.today()
    return [(end - timedelta(days=7 * (n - 1 - i))) for i in range(n)]


def build():
    d = json.load(open(os.path.join(DATA, "articles.json"), encoding="utf-8"))
    alerts = json.load(open(os.path.join(DATA, "alerts.json"), encoding="utf-8"))
    pe = load_plain_english()
    arts = [a for a in d["articles"] if a["kind"] in KEEP]
    built = d["built"]
    win_from, win_to = d["window"]

    # ---------------------------------------------------------------- payload
    rows = []
    for a in arts:
        au = a["au"][:6]
        rows.append([
            a["id"], a["j"], a["t"], au, a["nau"], a["d"], a["vol"], a["iss"],
            a["fp"], a["span"], a["kind"], a["design"],
            a["ab"][:1500], pe.get(a["id"], ""), a["cited"],
            (round(a["fwci"], 2) if a["fwci"] is not None else None), a["fwpct"],
            a["topics"][:2], 1 if a["oa"] else 0, a["url"],
            1 if a.get("lead") else 0, a.get("pos"), a.get("of"),
            a.get("emailed") or "", a["absrc"],
        ])

    # -------------------------------------------------------- journal rail
    wk = weeks_back(52)
    wk_start = wk[0]
    per_j_week = {j["key"]: [0] * 52 for j in JOURNALS}
    for a in arts:
        try:
            dt = datetime.strptime(a["d"], "%Y-%m-%d").date()
        except Exception:
            continue
        idx = (dt - wk_start).days // 7
        if 0 <= idx < 52:
            per_j_week[a["j"]][idx] += 1

    stats = d["journal_stats"]
    cal = d["alert_calendar"]
    jmeta = []
    for j in JOURNALS:
        s = stats[j["key"]]
        mine = [a for a in arts if a["j"] == j["key"]]
        jmeta.append(dict(
            k=j["key"], name=j["name"], field=j["field"], pub=j["publisher"],
            issn=j["issn"][0], home=j["home"], cadence=j["cadence"],
            founded=j["founded"], note=j["note"],
            bookmarked=1 if j["bookmarked"] else 0,
            n=len(mine),
            research=sum(1 for a in mine if a["kind"] != "book review"),
            reviews=sum(1 for a in mine if a["kind"] == "book review"),
            withab=sum(1 for a in mine if len(a["ab"]) > 120),
            newest=s["newest"], issues=s["issues"],
            cited=s["cited_total"], maxcited=s["cited_max"],
            oa=s["oa"], week=per_j_week[j["key"]],
            alerts=len(cal.get(j["key"], [])),
            lastalert=(max(cal[j["key"]]) if cal.get(j["key"]) else ""),
        ))

    # -------------------------------------------- publishing rhythm by field
    per_field_week = defaultdict(lambda: [0] * 52)
    for j in JOURNALS:
        for i, v in enumerate(per_j_week[j["key"]]):
            per_field_week[j["field"]][i] += v

    payload = dict(
        built=built, window=[win_from, win_to],
        cols=COLS, rows=rows, journals=jmeta,
        fields=FIELDS,
        hue={f: FIELD_HUE[f][0] for f in FIELDS},
        hueDark={f: FIELD_HUE[f][1] for f in FIELDS},
        rhythm={f: per_field_week[f] for f in FIELDS},
        weeks=[w.isoformat() for w in wk],
        alertCalendar=cal,
        alertNote=alerts["_finding"],
        ignored=[dict(t=t, u=u, why=w) for t, u, w in IGNORED],
        nTranslated=sum(1 for r in rows if r[COLS.index("pe")]),
    )

    js = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    body = TEMPLATE.replace("/*__DATA__*/", "window.RADAR=" + js + ";")

    os.makedirs(DIST, exist_ok=True)




    art = os.path.join(DIST, "artifact.html")
    with open(art, "w", encoding="utf-8") as fh:
        fh.write(body)

    out = os.path.join(DIST, "journal-radar.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(HEAD + body + FOOT)
    print("wrote %s  (%.1f MB)" % (out, os.path.getsize(out) / 1e6))
    print("wrote %s  (%.1f MB)  <- for publishing" % (art, os.path.getsize(art) / 1e6))
    print("  %d articles, %d journals, %d plain-English translations"
          % (len(rows), len(jmeta), payload["nTranslated"]))
    return out


TEMPLATE = r"""<title>Journal Radar</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,500;0,600;1,6..72,400&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{
  --ground:#f2f3ef; --surface:#fbfbfa; --sunken:#e9ebe5; --rail:#eeefe9;
  --ink:#1b2430; --ink-soft:#5a6472; --ink-faint:#8a929c;
  --rule:#dcdfd8; --rule-soft:#e6e8e1;
  --accent:#9c2b2b; --accent-soft:#f0e0dd; --accent-ink:#9c2b2b; --on-accent:#fbfbfa;
  --inbox:#1f6f6b; --inbox-soft:#dfeceb;
  --oa:#4a7a2b; --oa-soft:#e6eddc;
  --f0:#2a78d6; --f1:#eb6834; --f2:#1baf7a; --f3:#eda100;
  --shadow:0 1px 2px rgba(27,36,48,.06),0 8px 24px -16px rgba(27,36,48,.25);
  --serif:"Newsreader",Georgia,"Times New Roman",serif;
  --sans:"IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --ground:#171a1b; --surface:#1f2325; --sunken:#131617; --rail:#1b1f20;
    --ink:#e8eae4; --ink-soft:#a8b0ac; --ink-faint:#78807d;
    --rule:#2e3436; --rule-soft:#262b2d;
    --accent:#e0736e; --accent-soft:#3a2523; --accent-ink:#e8908b; --on-accent:#171a1b;
    --inbox:#5fb3ae; --inbox-soft:#1e2f2e;
    --oa:#8fbf62; --oa-soft:#232b1c;
    --f0:#3987e5; --f1:#d95926; --f2:#199e70; --f3:#c98500;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px -16px rgba(0,0,0,.7);
  }
}
:root[data-theme="dark"]{
  --ground:#171a1b; --surface:#1f2325; --sunken:#131617; --rail:#1b1f20;
  --ink:#e8eae4; --ink-soft:#a8b0ac; --ink-faint:#78807d;
  --rule:#2e3436; --rule-soft:#262b2d;
  --accent:#e0736e; --accent-soft:#3a2523; --accent-ink:#e8908b; --on-accent:#171a1b;
  --inbox:#5fb3ae; --inbox-soft:#1e2f2e;
  --oa:#8fbf62; --oa-soft:#232b1c;
  --f0:#3987e5; --f1:#d95926; --f2:#199e70; --f3:#c98500;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px -16px rgba(0,0,0,.7);
}
*{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);font-family:var(--sans);
  font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased}
a{color:inherit}
button{font:inherit;color:inherit}
h1,h2,h3{text-wrap:balance;margin:0}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:2px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}

/* ---------------------------------------------------------------- masthead */
.masthead{border-bottom:1px solid var(--rule);background:var(--surface)}
.mast-in{max-width:1440px;margin:0 auto;padding:22px 24px 18px;
  display:flex;flex-wrap:wrap;gap:24px;align-items:flex-start}
.mast-id{flex:1 1 380px;min-width:300px}
.kicker{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--ink-faint);display:flex;gap:10px;align-items:center}
.kicker .dot{width:5px;height:5px;border-radius:50%;background:var(--accent);flex:none}
h1{font-family:var(--serif);font-size:35px;font-weight:500;letter-spacing:-.015em;
  line-height:1.06;margin:7px 0 6px;font-optical-sizing:auto}
.sub{color:var(--ink-soft);font-size:13.5px;max-width:60ch}
.mast-figs{display:flex;gap:26px;flex-wrap:wrap;padding-top:6px}
.fig{min-width:74px}
.fig b{display:block;font-family:var(--mono);font-size:21px;font-weight:500;
  letter-spacing:-.02em;font-variant-numeric:tabular-nums;line-height:1.15}
.fig span{font-size:10.5px;font-family:var(--mono);letter-spacing:.07em;
  text-transform:uppercase;color:var(--ink-faint)}
.theme-btn{border:1px solid var(--rule);background:var(--surface);border-radius:6px;
  padding:5px 10px;font-size:11.5px;font-family:var(--mono);cursor:pointer;color:var(--ink-soft)}
.theme-btn:hover{border-color:var(--ink-faint);color:var(--ink)}

/* ------------------------------------------------------------------ layout */
.shell{max-width:1440px;margin:0 auto;padding:0 24px 72px;
  display:grid;grid-template-columns:268px minmax(0,1fr);gap:30px;align-items:start}
@media (max-width:1080px){.shell{grid-template-columns:1fr;gap:0}}

/* -------------------------------------------------------------------- rail */
.rail{position:sticky;top:12px;max-height:calc(100vh - 24px);overflow-y:auto;
  padding:14px 0 24px;scrollbar-width:thin}
@media (max-width:1080px){.rail{position:static;max-height:none;
  border-bottom:1px solid var(--rule);margin-bottom:8px}}
.railtop{position:sticky;top:0;z-index:3;background:var(--ground);padding-bottom:9px}
.rail h2{font-family:var(--mono);font-size:10.5px;letter-spacing:.13em;
  text-transform:uppercase;color:var(--ink-faint);margin:0 0 8px;font-weight:500}
#jfilter{width:100%;padding:6px 9px;border:1px solid var(--rule);border-radius:6px;
  background:var(--surface);color:var(--ink);font-size:12.5px;font-family:var(--sans)}
#jfilter::placeholder{color:var(--ink-faint)}
#jfilter:focus{outline:none;border-color:var(--accent)}
.cdiv{width:1px;height:20px;background:var(--rule);margin:0 3px}

/* ------------------------------------------------------- journal dossier */
.dossier{border:1px solid var(--rule);border-radius:10px;background:var(--surface);
  padding:18px 20px 16px;margin:14px 0 6px;border-top:3px solid var(--dossier-hue,var(--rule))}
.dossier .dtop{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:baseline}
.dossier h2{font-family:var(--serif);font-size:26px;font-weight:600;letter-spacing:-.015em;
  line-height:1.15;flex:1 1 auto;min-width:0}
.dossier .dsub{font-family:var(--mono);font-size:10.5px;color:var(--ink-faint);
  letter-spacing:.03em;margin-top:5px;display:flex;gap:7px;flex-wrap:wrap}
.dossier .dnote{font-size:13.5px;color:var(--ink-soft);max-width:74ch;margin:9px 0 0;line-height:1.55}
.dstats{display:flex;gap:22px;flex-wrap:wrap;margin:14px 0 0;padding:13px 0 0;
  border-top:1px solid var(--rule-soft)}
.dstat b{display:block;font-family:var(--mono);font-size:17px;font-weight:500;
  font-variant-numeric:tabular-nums;line-height:1.15;letter-spacing:-.02em}
.dstat span{font-size:9.5px;font-family:var(--mono);letter-spacing:.07em;
  text-transform:uppercase;color:var(--ink-faint)}
.dstat.mail b{color:var(--inbox)}
.dstat.none b{color:var(--ink-faint);font-size:13px;padding-top:3px}
.dact{display:flex;gap:8px;flex-wrap:wrap;margin-top:13px}
.dleads{margin:16px 0 0;padding:13px 0 0;border-top:1px solid var(--rule-soft)}
.dleads h4{font-family:var(--mono);font-size:9.5px;letter-spacing:.13em;text-transform:uppercase;
  color:var(--accent-ink);margin:0 0 8px;font-weight:500}
.leadlist{list-style:none;margin:0;padding:0;display:grid;
  grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:2px 20px}
.leadlist li{display:grid;grid-template-columns:auto minmax(0,1fr);gap:9px;
  align-items:baseline;padding:5px 0;border-bottom:1px solid var(--rule-soft)}
.leadlist .lp{font-family:var(--mono);font-size:9.5px;color:var(--ink-faint);
  font-variant-numeric:tabular-nums;white-space:nowrap}
.leadlist button{border:0;background:none;padding:0;text-align:left;cursor:pointer;
  font-family:var(--serif);font-size:14.5px;line-height:1.3;color:var(--ink)}
.leadlist button:hover{color:var(--accent-ink);text-decoration:underline;text-underline-offset:2px}
.dnolead{font-size:12.5px;color:var(--ink-faint);font-style:italic}
.field-group{margin-bottom:16px}
.field-head{display:flex;align-items:center;gap:7px;padding:0 6px 5px;
  border-bottom:1px solid var(--rule);margin-bottom:3px}
.field-head .swatch{width:9px;height:9px;border-radius:2px;flex:none}
.field-head b{font-size:11.5px;font-weight:600;letter-spacing:.01em;flex:1}
.field-head i{font-family:var(--mono);font-size:10.5px;color:var(--ink-faint);
  font-style:normal;font-variant-numeric:tabular-nums}
.jrow{width:100%;display:grid;grid-template-columns:1fr auto;gap:2px 8px;
  align-items:baseline;padding:5px 6px;border:0;background:none;border-radius:5px;
  cursor:pointer;text-align:left;transition:background .12s}
.jrow:hover{background:var(--rail)}
.jrow[aria-pressed="true"]{background:var(--accent-soft)}
.jrow .jn{font-family:var(--serif);font-size:14px;line-height:1.25;letter-spacing:-.005em}
.jrow[aria-pressed="true"] .jn{color:var(--accent-ink);font-weight:600}
.jrow .jc{font-family:var(--mono);font-size:11px;color:var(--ink-faint);
  font-variant-numeric:tabular-nums}
.jrow .spark{grid-column:1/-1;height:13px;display:block;margin-top:1px}
.jrow .jmeta{grid-column:1/-1;font-family:var(--mono);font-size:9.5px;
  color:var(--ink-faint);letter-spacing:.02em;display:flex;gap:7px;flex-wrap:wrap}
.jrow .mail{color:var(--inbox);font-weight:500}
.jrow .nobm{color:var(--accent-ink)}
.rail-note{font-size:11.5px;color:var(--ink-faint);padding:10px 6px 0;
  border-top:1px solid var(--rule);margin-top:6px;line-height:1.45}

/* ---------------------------------------------------------------- controls */
.controls{position:sticky;top:0;z-index:20;background:var(--ground);
  padding:12px 0 10px;border-bottom:1px solid var(--rule);margin-bottom:2px}
.crow{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.crow+.crow{margin-top:8px}
.search{flex:1 1 260px;min-width:190px;position:relative;display:flex;align-items:center}
.search input{width:100%;padding:8px 30px 8px 30px;border:1px solid var(--rule);
  border-radius:7px;background:var(--surface);color:var(--ink);font-size:14px;font-family:var(--sans)}
.search input::placeholder{color:var(--ink-faint)}
.search input:focus{outline:none;border-color:var(--accent)}
.search .mag{position:absolute;left:10px;color:var(--ink-faint);font-size:13px;pointer-events:none}
.search .slash{position:absolute;right:9px;font-family:var(--mono);font-size:10px;
  color:var(--ink-faint);border:1px solid var(--rule);border-radius:3px;padding:0 4px}
select{padding:7px 8px;border:1px solid var(--rule);border-radius:7px;
  background:var(--surface);color:var(--ink);font-size:12.5px;font-family:var(--sans);cursor:pointer}
select:focus{outline:none;border-color:var(--accent)}
.chip{border:1px solid var(--rule);background:var(--surface);border-radius:20px;
  padding:5px 11px;font-size:12px;cursor:pointer;color:var(--ink-soft);
  display:inline-flex;align-items:center;gap:5px;transition:.12s}
.chip:hover{border-color:var(--ink-faint);color:var(--ink)}
.chip[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
.chip .cn{font-family:var(--mono);font-size:10.5px;opacity:.75;font-variant-numeric:tabular-nums}
.chip.inbox[aria-pressed="true"]{background:var(--inbox);border-color:var(--inbox);color:var(--on-accent)}
.seg{display:inline-flex;border:1px solid var(--rule);border-radius:7px;overflow:hidden;background:var(--surface)}
.seg button{border:0;background:none;padding:6px 10px;font-size:12px;cursor:pointer;
  color:var(--ink-soft);font-family:var(--mono);letter-spacing:.02em}
.seg button+button{border-left:1px solid var(--rule)}
.seg button[aria-pressed="true"]{background:var(--sunken);color:var(--ink);font-weight:500}
.tally{font-family:var(--mono);font-size:11.5px;color:var(--ink-faint);
  margin-left:auto;font-variant-numeric:tabular-nums;white-space:nowrap}
.tally b{color:var(--ink);font-weight:500}
.clear{border:0;background:none;color:var(--accent-ink);font-size:12px;cursor:pointer;
  text-decoration:underline;text-underline-offset:2px;padding:4px}

/* ------------------------------------------------------------------- list */
/* Every row is its own grid, so the column widths have to be fixed rather than
   content-sized -- otherwise each title starts at a different x and the list
   rags down the left edge. Columns: field spine | content | metrics. */
.list{list-style:none;margin:0;padding:0;border-top:1px solid var(--rule)}
.art{border-bottom:1px solid var(--rule-soft);padding:14px 6px 14px 0;
  display:grid;grid-template-columns:14px minmax(0,1fr) 108px;
  column-gap:16px;row-gap:0;align-items:start;position:relative}
.art:hover{background:var(--rail)}
.art.open{background:var(--surface);box-shadow:var(--shadow);border-radius:8px;
  border-bottom-color:transparent;padding:16px 16px 18px 12px;margin:8px 0;
  border-left:2px solid var(--rule)}
.mark{grid-column:1;grid-row:1;align-self:stretch;display:flex;
  flex-direction:column;align-items:center;padding-top:5px}
.mark .fspine{width:3px;flex:1;min-height:34px;border-radius:2px;opacity:.85}
.abody{grid-column:2;grid-row:1;min-width:0}
.at{font-family:var(--serif);font-size:17px;line-height:1.32;font-weight:400;
  letter-spacing:-.008em;margin:0;cursor:pointer;font-optical-sizing:auto;
  text-wrap:pretty}
.art.open .at{font-weight:500}
.at:hover{color:var(--accent-ink)}
.art.is-lead .at{font-weight:500}
.aau{font-size:12.5px;color:var(--ink-soft);margin-top:3px}
.aau em{font-style:normal;color:var(--ink-faint)}
.acite{font-family:var(--mono);font-size:10.5px;color:var(--ink-faint);
  margin-top:6px;display:flex;gap:7px;flex-wrap:wrap;align-items:center;letter-spacing:.01em}
.acite .sep{opacity:.35}
.acite .jname{color:var(--ink-soft);font-family:var(--sans);font-size:11.5px;font-weight:500}
.badge{font-family:var(--mono);font-size:9px;letter-spacing:.07em;text-transform:uppercase;
  padding:2px 6px;border-radius:3px;line-height:1.5;font-weight:500;white-space:nowrap}
.b-lead{color:var(--accent-ink);background:var(--accent-soft)}
.b-mail{color:var(--inbox);background:var(--inbox-soft)}
.b-oa{color:var(--oa);background:var(--oa-soft)}
.b-plain{color:var(--ink-soft);background:var(--sunken)}
.b-design{color:var(--ink-soft);background:var(--sunken)}
.ametrics{grid-column:3;grid-row:1;text-align:right;padding-top:2px;display:flex;
  flex-direction:column;gap:0;align-items:flex-end}
.ametrics .cit{font-family:var(--mono);font-size:16px;font-variant-numeric:tabular-nums;
  line-height:1.1;font-weight:500;letter-spacing:-.02em}
.ametrics .citl{font-family:var(--mono);font-size:8.5px;letter-spacing:.08em;
  text-transform:uppercase;color:var(--ink-faint);margin-top:1px}
.ametrics .fw{font-family:var(--mono);font-size:9.5px;color:var(--ink-faint);margin-top:5px}
.ametrics .fwbar{width:56px;height:3px;background:var(--sunken);border-radius:2px;
  overflow:hidden;margin-top:3px}
.ametrics .fwbar i{display:block;height:100%;background:var(--ink-faint);border-radius:2px}
.ametrics .nocit{white-space:nowrap;color:var(--ink-faint);text-transform:none;
  letter-spacing:.01em;font-size:9.5px;font-family:var(--mono);padding-top:3px}

/* ---------------------------------------------------------------- expanded */
.detail{grid-column:2/4;grid-row:2;margin-top:14px;padding-top:13px;border-top:1px solid var(--rule)}
.detail h4{font-family:var(--mono);font-size:9.5px;letter-spacing:.13em;text-transform:uppercase;
  color:var(--ink-faint);margin:0 0 5px;font-weight:500}
.plain{background:var(--accent-soft);border-left:2px solid var(--accent);
  padding:11px 14px;border-radius:0 6px 6px 0;margin-bottom:13px}
.plain p{margin:0;font-size:14.5px;line-height:1.6;max-width:70ch}
.plain h4{color:var(--accent-ink)}
.abs{font-size:13.5px;line-height:1.62;color:var(--ink-soft);max-width:74ch;margin:0 0 12px}
.abs.none{font-style:italic;color:var(--ink-faint);font-size:13px}
.dgrid{display:flex;gap:8px;flex-wrap:wrap;align-items:center;
  padding-top:10px;border-top:1px solid var(--rule-soft)}
.dlink{border:1px solid var(--rule);background:var(--surface);border-radius:6px;
  padding:6px 11px;font-size:12.5px;text-decoration:none;color:var(--ink);
  display:inline-flex;align-items:center;gap:6px;transition:.12s}
.dlink:hover{border-color:var(--accent);color:var(--accent-ink)}
.dlink.primary{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
.dlink.primary:hover{opacity:.88;color:var(--on-accent)}
.dmeta{font-family:var(--mono);font-size:10.5px;color:var(--ink-faint);margin-left:auto;text-align:right}
.topics{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:11px}
.topic{font-size:11px;background:var(--sunken);border-radius:12px;padding:2px 9px;color:var(--ink-soft)}

/* ------------------------------------------------------------- issue view */
.issue-head{display:flex;align-items:baseline;gap:10px;margin:26px 0 2px;
  padding-bottom:6px;border-bottom:1.5px solid var(--ink)}
.issue-head:first-child{margin-top:8px}
.issue-head h3{font-family:var(--serif);font-size:19px;font-weight:600;letter-spacing:-.01em}
.issue-head .iss{font-family:var(--mono);font-size:11px;color:var(--ink-faint);
  font-variant-numeric:tabular-nums}
.issue-head .go{margin-left:auto;font-size:11.5px;color:var(--ink-faint);text-decoration:none}
.issue-head .go:hover{color:var(--accent-ink)}

/* ------------------------------------------------------------------ panel */
.panel{background:var(--surface);border:1px solid var(--rule);border-radius:10px;
  padding:18px 20px;margin:14px 0 4px}
.panel h3{font-family:var(--serif);font-size:19px;font-weight:600;margin-bottom:3px}
.panel p{font-size:13.5px;color:var(--ink-soft);max-width:74ch;margin:0 0 12px}
.rhythm{display:grid;grid-template-columns:repeat(auto-fit,minmax(272px,1fr));gap:18px 22px}
.rh h5{font-family:var(--mono);font-size:10px;letter-spacing:.09em;text-transform:uppercase;
  margin:0 0 1px;font-weight:500;display:flex;align-items:center;gap:6px;min-width:0}
.rh h5 .swatch{width:8px;height:8px;border-radius:2px;flex:none}
.rh h5 .fname{min-width:0;overflow-wrap:anywhere}
.rh .rhn{font-family:var(--mono);font-size:10.5px;color:var(--ink-faint);margin-bottom:5px;
  font-variant-numeric:tabular-nums}
.alertgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(168px,1fr));gap:5px 14px;margin-top:4px}
.ag{display:flex;align-items:baseline;gap:6px;font-size:12px;padding:2px 0}
.ag .tick{font-family:var(--mono);font-size:11px;width:14px;flex:none}
.ag .yes{color:var(--inbox)}
.ag .no{color:var(--ink-faint)}
.ag .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ag .n{font-family:var(--mono);font-size:10px;color:var(--ink-faint);margin-left:auto;flex:none}
table.src{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:6px}
table.src th{text-align:left;font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--ink-faint);font-weight:500;padding:4px 10px 4px 0;
  border-bottom:1px solid var(--rule)}
table.src td{padding:5px 10px 5px 0;border-bottom:1px solid var(--rule-soft);vertical-align:top}
table.src td.num{font-family:var(--mono);font-variant-numeric:tabular-nums;text-align:right;
  padding-right:14px;white-space:nowrap}
.scroller{overflow-x:auto}
.empty{padding:60px 20px;text-align:center;color:var(--ink-faint)}
.empty b{display:block;font-family:var(--serif);font-size:20px;color:var(--ink-soft);margin-bottom:6px}
.more{display:block;width:100%;margin:18px 0 0;padding:11px;border:1px dashed var(--rule);
  background:none;border-radius:8px;cursor:pointer;color:var(--ink-soft);font-size:13px}
.more:hover{border-color:var(--accent);color:var(--accent-ink)}
footer{max-width:1440px;margin:0 auto;padding:26px 24px 40px;border-top:1px solid var(--rule);
  font-size:12px;color:var(--ink-faint);line-height:1.7}
footer a{color:var(--ink-soft)}
footer b{color:var(--ink-soft);font-weight:500}
.tabs{display:flex;gap:2px;margin-bottom:0}
.tabs button{border:1px solid transparent;border-bottom:0;background:none;padding:7px 14px;
  font-size:13px;cursor:pointer;color:var(--ink-faint);border-radius:7px 7px 0 0}
.tabs button[aria-selected="true"]{background:var(--ground);border-color:var(--rule);
  color:var(--ink);font-weight:500}
.tabs button:hover{color:var(--ink)}
</style>

<header class="masthead">
  <div class="mast-in">
    <div class="mast-id">
      <div class="kicker"><span class="dot"></span><span>Journal Radar</span>
        <span id="k-built"></span></div>
      <h1>Journal Radar</h1>
      <p class="sub">Every peer-reviewed journal in the <b>Journals</b> bookmark folder,
        in Firefox and in Chrome &mdash; twelve months of their tables of contents in one
        place, with a plain-English rendering of the abstract where one exists.</p>
    </div>
    <div class="mast-figs" id="figs"></div>
    <button class="theme-btn" id="theme" type="button">theme</button>
  </div>
</header>

<div class="shell">
  <nav class="rail">
    <div class="railtop">
      <h2>27 journals on the shelf</h2>
      <input id="jfilter" type="search" placeholder="Filter this list&hellip;"
             autocomplete="off" spellcheck="false" aria-label="Filter the journal list">
    </div>
    <div id="rail"></div>
  </nav>
  <main>
    <div class="controls">
      <div class="tabs" role="tablist">
        <button role="tab" data-view="articles" aria-selected="true">Articles</button>
        <button role="tab" data-view="issues" aria-selected="false">New issues</button>
        <button role="tab" data-view="about" aria-selected="false">The shelf</button>
      </div>
      <div class="crow" style="margin-top:8px">
        <label class="search">
          <span class="mag">&#9906;</span>
          <input id="q" type="search" placeholder="Search titles, authors, abstracts, plain English&hellip;"
                 autocomplete="off" spellcheck="false">
          <span class="slash">/</span>
        </label>
        <select id="sort" aria-label="Sort by">
          <option value="new">Newest first</option>
          <option value="cited">Most cited</option>
          <option value="impact">Biggest impact for its field</option>
          <option value="lead">Lead articles first</option>
          <option value="mail">Most recently emailed</option>
          <option value="issue">Issue order</option>
        </select>
        <div class="seg" id="window" role="group" aria-label="Time window">
          <button data-days="30">30d</button>
          <button data-days="90">3mo</button>
          <button data-days="120" aria-pressed="true">4mo</button>
          <button data-days="182">6mo</button>
          <button data-days="400">1yr</button>
        </div>
      </div>
      <div class="crow">
        <select id="jpick" aria-label="Jump to a journal"></select>
        <select id="kind" aria-label="Kind">
          <option value="">Research &amp; reviews</option>
          <option value="research">Research articles</option>
          <option value="review">Review articles</option>
          <option value="book review">Book reviews</option>
          <option value="all">Everything</option>
        </select>
        <span class="cdiv" aria-hidden="true"></span>
        <button class="chip lead" id="f-lead" aria-pressed="false">Led its issue <span class="cn"></span></button>
        <button class="chip inbox" id="f-mail" aria-pressed="false">In your inbox <span class="cn"></span></button>
        <button class="chip" id="f-plain" aria-pressed="false">Plain English <span class="cn"></span></button>
        <button class="chip" id="f-oa" aria-pressed="false">Free to read <span class="cn"></span></button>
        <button class="clear" id="clear" hidden>Clear filters</button>
        <span class="tally" id="tally"></span>
      </div>
    </div>
    <div id="view"></div>
  </main>
</div>

<footer>
  <p id="foot-a"></p>
  <p id="foot-b"></p>
</footer>

<script>
/*__DATA__*/
</script>
<script>
(function(){
"use strict";
var D = window.RADAR, C = {};
D.cols.forEach(function(c,i){ C[c]=i; });
var A = D.rows, J = D.journals, JB = {};
J.forEach(function(j){ JB[j.k]=j; });
var FI = {}; D.fields.forEach(function(f,i){ FI[f]=i; });
var esc = function(s){ return String(s==null?"":s)
  .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); };
var $ = function(s){ return document.querySelector(s); };

/* ---------------------------------------------------------------- indexing */
var TODAY = new Date(D.built + "T00:00:00");
function daysAgo(ds){
  if(!ds) return 9999;
  return Math.round((TODAY - new Date(ds+"T00:00:00"))/864e5);
}
var blob = A.map(function(r){
  return (r[C.t]+" "+r[C.au].join(" ")+" "+r[C.ab]+" "+r[C.pe]+" "+
          JB[r[C.j]].name+" "+r[C.topics].join(" ")+" "+r[C.design]).toLowerCase();
});
var age = A.map(function(r){ return daysAgo(r[C.d]); });

/* ------------------------------------------------------------------- state */
var S = { q:"", sort:"new", days:120, kind:"", lead:false, mail:false,
          plain:false, oa:false, journal:"", field:"", view:"articles", limit:60,
          jfilter:"" };

function matches(i){
  var r = A[i];
  if(age[i] > S.days) return false;
  if(S.kind === ""){ if(r[C.kind] === "book review") return false; }
  else if(S.kind !== "all" && r[C.kind] !== S.kind) return false;
  if(S.journal && r[C.j] !== S.journal) return false;
  if(S.field && JB[r[C.j]].field !== S.field) return false;
  if(S.lead && !r[C.lead]) return false;
  if(S.mail && !r[C.emailed]) return false;
  if(S.plain && !r[C.pe]) return false;
  if(S.oa && !r[C.oa]) return false;
  if(S.q && blob[i].indexOf(S.q) < 0) return false;
  return true;
}
function currentIdx(){
  var out=[];
  for(var i=0;i<A.length;i++) if(matches(i)) out.push(i);
  return out;
}
// Counts for the rail and the journal picker deliberately ignore the journal
// filter itself. Otherwise picking one journal zeroes all 26 others and you
// cannot see where else there is anything to read.
function countsByJournal(){
  var save = S.journal, saveF = S.field;
  S.journal = ""; S.field = "";
  var c = {}, f = {};
  for(var i=0;i<A.length;i++){
    if(!matches(i)) continue;
    var k = A[i][C.j];
    c[k] = (c[k]||0)+1;
    var fd = JB[k].field; f[fd] = (f[fd]||0)+1;
  }
  S.journal = save; S.field = saveF;
  return {j:c, f:f};
}
var SORTS = {
  new:   function(a,b){ return A[b][C.d] < A[a][C.d] ? -1 : A[b][C.d] > A[a][C.d] ? 1 : A[b][C.cited]-A[a][C.cited]; },
  cited: function(a,b){ return A[b][C.cited]-A[a][C.cited] || (A[b][C.d]<A[a][C.d]?-1:1); },
  impact:function(a,b){ return (A[b][C.fwci]||0)-(A[a][C.fwci]||0) || A[b][C.cited]-A[a][C.cited]; },
  lead:  function(a,b){ return (A[b][C.lead]-A[a][C.lead]) || (A[b][C.d]<A[a][C.d]?-1:1); },
  mail:  function(a,b){ var x=A[a][C.emailed]||"", y=B(b); function B(k){return A[k][C.emailed]||"";}
           return y<x?-1:y>x?1:(A[b][C.d]<A[a][C.d]?-1:1); },
  issue: function(a,b){ var x=A[a],y=A[b];
           if(x[C.j]!==y[C.j]) return JB[x[C.j]].name < JB[y[C.j]].name ? -1 : 1;
           var xv=parseInt(x[C.vol]||0,10), yv=parseInt(y[C.vol]||0,10);
           if(xv!==yv) return yv-xv;
           var xi=parseInt(x[C.iss]||0,10), yi=parseInt(y[C.iss]||0,10);
           if(xi!==yi) return yi-xi;
           return (x[C.fp]||0)-(y[C.fp]||0); }
};

/* ------------------------------------------------------------------ pieces */
function hueVar(field){ return "var(--f"+FI[field]+")"; }
function fmtDate(ds){
  if(!ds) return "";
  var m = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  var p = ds.split("-");
  return parseInt(p[2],10)+" "+m[parseInt(p[1],10)-1]+" "+p[0];
}
function agoLabel(n){
  if(n<1) return "today"; if(n===1) return "yesterday";
  if(n<14) return n+" days ago";
  if(n<70) return Math.round(n/7)+" weeks ago";
  return Math.round(n/30.4)+" months ago";
}
function pageRange(r){
  var fp=r[C.fp], sp=r[C.span];
  if(!fp) return "";
  return sp && sp>1 ? "pp "+fp+"–"+(fp+sp-1) : "p "+fp;
}
function authorLine(r){
  var au=r[C.au], n=r[C.nau];
  if(!au.length) return "<em>author not deposited</em>";
  var s = au.slice(0,3).map(esc).join(", ");
  if(n > 3) s += " <em>and "+(n-3)+" other"+(n-3>1?"s":"")+"</em>";
  return s;
}
function sparkSVG(week, field, w, h){
  var mx = Math.max.apply(null, week) || 1, n = week.length;
  var bw = w/n, out = '<svg class="spark" viewBox="0 0 '+w+' '+h+'" preserveAspectRatio="none" aria-hidden="true">';
  for(var i=0;i<n;i++){
    if(!week[i]) continue;
    var bh = Math.max(1.2, (week[i]/mx)*h);
    out += '<rect x="'+(i*bw).toFixed(2)+'" y="'+(h-bh).toFixed(2)+'" width="'+
           Math.max(0.9,bw-0.6).toFixed(2)+'" height="'+bh.toFixed(2)+
           '" fill="'+hueVar(field)+'" opacity="0.75"></rect>';
  }
  return out + "</svg>";
}

/* -------------------------------------------------------------------- rail */
function drawRail(){
  var cb = countsByJournal(), counts = cb.j, fcounts = cb.f;
  fillJournalPicker(counts);
  var q = S.jfilter, shown = 0, h = [];
  D.fields.forEach(function(f){
    var mine = J.filter(function(j){
      return j.field === f && (!q || j.name.toLowerCase().indexOf(q) >= 0
                                  || j.pub.toLowerCase().indexOf(q) >= 0);
    });
    if(!mine.length) return;
    h.push('<div class="field-group">');
    h.push('<div class="field-head"><span class="swatch" style="background:'+hueVar(f)+'"></span>'+
           '<b>'+esc(f)+'</b><i>'+(fcounts[f]||0)+'</i></div>');
    mine.forEach(function(j){
      shown++;
      var n = counts[j.k]||0;
      var bits = [];
      if(j.newest) bits.push(agoLabel(daysAgo(j.newest)));
      else bits.push("nothing indexed");
      if(j.alerts) bits.push('<span class="mail">&#9993; '+j.alerts+'/yr</span>');
      if(!j.bookmarked) bits.push('<span class="nobm">by email only</span>');
      h.push('<button class="jrow" data-j="'+j.k+'" aria-pressed="'+(S.journal===j.k)+'">'+
        '<span class="jn">'+esc(j.name)+'</span>'+
        '<span class="jc">'+n+'</span>'+
        sparkSVG(j.week, j.field, 240, 13)+
        '<span class="jmeta">'+bits.join('<span style="opacity:.4">&middot;</span>')+'</span>'+
        '</button>');
    });
    h.push('</div>');
  });
  if(!shown) h.push('<p class="rail-note">No journal matches &ldquo;'+esc(q)+'&rdquo;.</p>');
  else h.push('<p class="rail-note">Counts follow the filters above. The strip under each '+
         'name is one bar per week over the last year &mdash; the weeklies run flat, the '+
         'quarterlies arrive in spikes.</p>');
  $("#rail").innerHTML = h.join("");
  Array.prototype.forEach.call(document.querySelectorAll(".jrow"), function(b){
    b.addEventListener("click", function(){
      pickJournal(S.journal === b.dataset.j ? "" : b.dataset.j);
    });
  });
}
function pickJournal(k){
  S.journal = k; S.field = ""; S.limit = 60;
  var sel = $("#jpick"); if(sel) sel.value = k;
  render();
  var m = document.querySelector("main");
  if(m) m.scrollIntoView({block:"start", behavior:"smooth"});
}
function fillJournalPicker(counts){
  counts = counts || {};
  var total = J.reduce(function(s,j){ return s + (counts[j.k]||0); }, 0);
  var h = ['<option value="">All 27 journals — '+total.toLocaleString()+'</option>'];
  D.fields.forEach(function(f){
    h.push('<optgroup label="'+esc(f)+'">');
    J.filter(function(j){ return j.field===f; }).forEach(function(j){
      h.push('<option value="'+j.k+'">'+esc(j.name)+' — '+(counts[j.k]||0)+'</option>');
    });
    h.push('</optgroup>');
  });
  var sel = $("#jpick");
  sel.innerHTML = h.join("");
  sel.value = S.journal;
}

/* ------------------------------------------------------- journal dossier */
function dossierHTML(k){
  var j = JB[k];
  var mine = [], leads = [];
  for(var i=0;i<A.length;i++){
    if(A[i][C.j] !== k) continue;
    if(age[i] > S.days) continue;
    if(A[i][C.kind] === "book review") continue;
    mine.push(i);
    if(A[i][C.lead]) leads.push(i);
  }
  leads.sort(function(a,b){ return A[b][C.d] < A[a][C.d] ? -1 : 1; });
  var cited = mine.reduce(function(s,i){ return s + A[i][C.cited]; }, 0);
  var withab = mine.filter(function(i){ return A[i][C.ab].length > 120; }).length;

  var h = '<section class="dossier" style="--dossier-hue:'+hueVar(j.field)+'">'+
    '<div class="dtop"><h2>'+esc(j.name)+'</h2></div>'+
    '<div class="dsub"><span>'+esc(j.pub)+'</span><span class="sep">&middot;</span>'+
      '<span>ISSN '+esc(j.issn)+'</span><span class="sep">&middot;</span>'+
      '<span>'+esc(j.cadence)+'</span><span class="sep">&middot;</span>'+
      '<span>founded '+j.founded+'</span>'+
      (j.bookmarked ? '' : '<span class="sep">&middot;</span><span style="color:var(--accent-ink)">not bookmarked &mdash; here because it emails you</span>')+
    '</div>'+
    '<p class="dnote">'+esc(j.note)+'</p>'+
    '<div class="dstats">'+
      '<div class="dstat"><b>'+mine.length+'</b><span>in this window</span></div>'+
      '<div class="dstat"><b>'+leads.length+'</b><span>lead articles</span></div>'+
      '<div class="dstat"><b>'+(mine.length ? Math.round(100*withab/mine.length)+"%" : "&mdash;")+
        '</b><span>with an abstract</span></div>'+
      '<div class="dstat"><b>'+cited.toLocaleString()+'</b><span>citations</span></div>'+
      '<div class="dstat"><b>'+(j.newest ? agoLabel(daysAgo(j.newest)) : "&mdash;")+
        '</b><span>latest article</span></div>'+
      (j.alerts
        ? '<div class="dstat mail"><b>'+j.alerts+'/yr</b><span>emails you</span></div>'
        : '<div class="dstat none"><b>never emails you</b><span>no alert set up</span></div>')+
    '</div>'+
    '<div class="dact">'+
      '<a class="dlink primary" href="'+esc(j.home)+'" target="_blank" rel="noopener">Current issue at the publisher &rarr;</a>'+
      '<button class="dlink" type="button" data-leadonly="'+k+'">Show only its lead articles</button>'+
      '<button class="dlink" type="button" data-clearj="1">Back to all journals</button>'+
    '</div>';

  h += '<div class="dleads"><h4>Lead articles in this window</h4>';
  if(!leads.length){
    h += '<p class="dnolead">None in the last '+S.days+' days. Either the window is '+
         'too short for this journal&rsquo;s cadence, or the publisher deposits no '+
         'page numbers, without which the running order cannot be read.</p>';
  } else {
    h += '<ul class="leadlist">'+leads.slice(0,12).map(function(i){
      var r = A[i];
      return '<li><span class="lp">'+fmtDate(r[C.d])+(r[C.vol]?' &middot; v'+esc(r[C.vol]):'')+'</span>'+
        '<button type="button" data-jump="'+i+'">'+esc(r[C.t])+'</button></li>';
    }).join("")+'</ul>';
    if(leads.length > 12) h += '<p class="dnolead" style="margin-top:8px">'+
      (leads.length-12)+' more below.</p>';
  }
  h += '</div></section>';
  return h;
}
function wireDossier(){
  Array.prototype.forEach.call(document.querySelectorAll("[data-jump]"), function(b){
    b.addEventListener("click", function(){
      var li = document.querySelector('.art[data-i="'+b.dataset.jump+'"]');
      if(!li){ S.limit += 200; render();
               li = document.querySelector('.art[data-i="'+b.dataset.jump+'"]'); }
      if(li){
        li.scrollIntoView({block:"center", behavior:"smooth"});
        if(!li.classList.contains("open")) li.querySelector(".at").click();
      }
    });
  });
  var lo = document.querySelector("[data-leadonly]");
  if(lo) lo.addEventListener("click", function(){ S.lead = true; S.limit = 60; render(); });
  var cj = document.querySelector("[data-clearj]");
  if(cj) cj.addEventListener("click", function(){ pickJournal(""); });
}

/* ---------------------------------------------------------------- articles */
function badge(cls, txt, title){
  return '<span class="badge '+cls+'"'+(title?' title="'+esc(title)+'"':'')+'>'+esc(txt)+'</span>';
}
function articleHTML(i, showJournal){
  var r = A[i], j = JB[r[C.j]];
  var cite = [];
  if(showJournal !== false) cite.push('<span class="jname">'+esc(j.name)+'</span>');
  if(r[C.vol]) cite.push("Vol "+esc(r[C.vol]));
  if(r[C.iss]) cite.push("No "+esc(r[C.iss]));
  var pr = pageRange(r); if(pr) cite.push(pr);
  cite.push(fmtDate(r[C.d]));
  if(r[C.pos]) cite.push(ordinal(r[C.pos])+" of "+r[C.of]+" in the issue");
  var bad = "";
  if(r[C.lead]) bad += badge("b-lead","Lead article","First research article in this issue");
  if(r[C.emailed]) bad += badge("b-mail","✉ "+fmtDate(r[C.emailed]),"Named in a table-of-contents alert in your inbox");
  if(r[C.design]) bad += badge("b-design", r[C.design]);
  if(r[C.oa]) bad += badge("b-oa","Free");
  if(r[C.pe]) bad += badge("b-plain","Plain English");
  var fw = r[C.fwci];
  var metrics = "";
  if(r[C.cited] > 0){
    metrics = '<span class="cit">'+r[C.cited]+'</span>'+
      '<span class="citl">'+(r[C.cited]===1?"citation":"citations")+'</span>'+
      (fw!=null && fw>0 ? '<span class="fw" title="Field-weighted citation impact: 1.0 is the world average for this field, year and article type">FWCI '+fw.toFixed(1)+'</span>'+
        '<span class="fwbar"><i style="width:'+Math.min(100, r[C.fwpct]||0)+'%"></i></span>' : '');
  } else {
    metrics = '<span class="citl nocit" title="Nothing has cited it yet. Anything published in the last few months will read zero.">not yet cited</span>';
  }
  return '<li class="art'+(r[C.lead]?" is-lead":"")+'" data-i="'+i+'">'+
    '<span class="mark"><span class="fspine" style="background:'+hueVar(j.field)+
      '" title="'+esc(j.field)+'"></span></span>'+
    '<div class="abody"><h3 class="at" role="button" tabindex="0">'+esc(r[C.t])+'</h3>'+
      '<div class="aau">'+authorLine(r)+'</div>'+
      '<div class="acite">'+cite.map(function(c,k){ return (k?'<span class="sep">&middot;</span>':'')+c; }).join("")+
        (bad? ' '+bad : '')+'</div></div>'+
    '<div class="ametrics">'+metrics+'</div></li>';
}
function ordinal(n){
  var s=["th","st","nd","rd"], v=n%100;
  return n+(s[(v-20)%10]||s[v]||s[0]);
}
function detailHTML(i){
  var r = A[i], j = JB[r[C.j]];
  var h = '<div class="detail">';
  if(r[C.topics].length) h += '<div class="topics">'+r[C.topics].map(function(t){
    return '<span class="topic">'+esc(t)+'</span>'; }).join("")+'</div>';
  if(r[C.pe]) h += '<div class="plain"><h4>In plain English</h4><p>'+esc(r[C.pe])+'</p></div>';
  h += '<h4>Abstract'+(r[C.absrc]? ' &middot; as deposited to '+esc(r[C.absrc]) : '')+'</h4>';
  if(r[C.ab] && r[C.ab].length > 60){
    h += '<p class="abs">'+esc(r[C.ab])+'</p>';
  } else {
    h += '<p class="abs none">'+esc(j.name)+' does not deposit abstracts for this article, so there is '+
         'nothing to show or translate here. The link below opens the article itself.</p>';
  }
  h += '<div class="dgrid">'+
    '<a class="dlink primary" href="'+esc(r[C.url])+'" target="_blank" rel="noopener">Read the article &rarr;</a>'+
    '<a class="dlink" href="'+esc(j.home)+'" target="_blank" rel="noopener">'+esc(j.name)+' &mdash; current issue</a>'+
    (r[C.id].indexOf("10.")===0 ? '<a class="dlink" href="https://scholar.google.com/scholar?q='+
      encodeURIComponent(r[C.t])+'" target="_blank" rel="noopener">Who cites it</a>' : '')+
    '<span class="dmeta">'+(r[C.id].indexOf("10.")===0 ? "doi "+esc(r[C.id]) : "")+
      '<br>'+esc(j.publisher)+' &middot; ISSN '+esc(j.issn)+'</span>'+
    '</div></div>';
  return h;
}

/* ------------------------------------------------------------------ render */
var currentIdxCache = [];
function render(){
  currentIdxCache = currentIdx();
  var idx = currentIdxCache.slice().sort(SORTS[S.sort]);
  drawRail(); drawChips(); drawTally(idx.length);
  var v = $("#view");
  if(S.view === "about"){ v.innerHTML = aboutHTML(); wireAbout(); return; }

  // With one journal picked, the page becomes that journal's front page: who
  // publishes it, how it behaves, and its lead articles, above the list.
  var head = S.journal ? dossierHTML(S.journal) : "";
  if(!idx.length){
    v.innerHTML = head + '<div class="empty"><b>Nothing here matches that.</b>'+
      (S.journal ? esc(JB[S.journal].name)+' has nothing in this window with the filters you have set. '+
                   'Try a longer window.' : 'Try a longer window, or clear the filters.')+
      '</div>';
    if(head) wireDossier();
    return;
  }
  v.innerHTML = head + ((S.view === "issues") ? issuesHTML(idx) : listHTML(idx));
  if(head) wireDossier();
  wireList();
}
function listHTML(idx){
  var slice = idx.slice(0, S.limit);
  var h = '<ul class="list">'+slice.map(function(i){ return articleHTML(i); }).join("")+'</ul>';
  if(idx.length > S.limit)
    h += '<button class="more" id="more">Show '+Math.min(60, idx.length-S.limit)+
         ' more &mdash; '+(idx.length-S.limit)+' still hidden</button>';
  return h;
}
function issuesHTML(idx){
  var groups = {}, order = [];
  idx.slice().sort(SORTS.issue).forEach(function(i){
    var r = A[i], key = r[C.j]+"|"+r[C.vol]+"|"+r[C.iss];
    if(!groups[key]){ groups[key] = []; order.push(key); }
    groups[key].push(i);
  });
  order.sort(function(a,b){
    var na = Math.max.apply(null, groups[a].map(function(i){ return A[i][C.d]; }));
    var nb = Math.max.apply(null, groups[b].map(function(i){ return A[i][C.d]; }));
    var da = groups[a].map(function(i){ return A[i][C.d]; }).sort().pop();
    var db = groups[b].map(function(i){ return A[i][C.d]; }).sort().pop();
    return db < da ? -1 : db > da ? 1 : 0;
  });
  var h = "", shown = 0;
  for(var k=0; k<order.length && shown < S.limit; k++){
    var key = order[k], g = groups[key], r0 = A[g[0]], j = JB[r0[C.j]];
    var latest = g.map(function(i){ return A[i][C.d]; }).sort().pop();
    var label = r0[C.vol] ? "Vol "+r0[C.vol]+(r0[C.iss] ? " · No "+r0[C.iss] : "")
                          : "no issue number deposited";
    h += '<div class="issue-head"><h3>'+esc(j.name)+'</h3>'+
         '<span class="iss">'+esc(label)+' &middot; '+g.length+' item'+(g.length>1?"s":"")+
         ' &middot; '+fmtDate(latest)+'</span>'+
         '<a class="go" href="'+esc(j.home)+'" target="_blank" rel="noopener">at the publisher &rarr;</a></div>'+
         '<ul class="list">'+g.map(function(i){ return articleHTML(i, false); }).join("")+'</ul>';
    shown += g.length;
  }
  if(shown < idx.length)
    h += '<button class="more" id="more">Show more issues &mdash; '+(idx.length-shown)+' articles still hidden</button>';
  return h;
}
function wireList(){
  Array.prototype.forEach.call(document.querySelectorAll(".art"), function(li){
    var t = li.querySelector(".at");
    function toggle(){
      var open = li.classList.toggle("open");
      if(open){
        li.insertAdjacentHTML("beforeend", detailHTML(+li.dataset.i));
      } else {
        var dt = li.querySelector(".detail"); if(dt) dt.remove();
      }
    }
    t.addEventListener("click", toggle);
    t.addEventListener("keydown", function(e){
      if(e.key === "Enter" || e.key === " "){ e.preventDefault(); toggle(); }
    });
  });
  var m = $("#more");
  if(m) m.addEventListener("click", function(){ S.limit += 60; render(); });
}

/* ------------------------------------------------------------------- chips */
function countIf(pred){
  var n=0;
  for(var i=0;i<A.length;i++){ if(age[i]<=S.days && pred(A[i])) n++; }
  return n;
}
function drawChips(){
  $("#f-lead").querySelector(".cn").textContent = countIf(function(r){ return r[C.lead]; });
  $("#f-mail").querySelector(".cn").textContent = countIf(function(r){ return r[C.emailed]; });
  $("#f-plain").querySelector(".cn").textContent = countIf(function(r){ return r[C.pe]; });
  $("#f-oa").querySelector(".cn").textContent = countIf(function(r){ return r[C.oa]; });
  $("#f-lead").setAttribute("aria-pressed", S.lead);
  $("#f-mail").setAttribute("aria-pressed", S.mail);
  $("#f-plain").setAttribute("aria-pressed", S.plain);
  $("#f-oa").setAttribute("aria-pressed", S.oa);
  var dirty = S.q||S.journal||S.field||S.lead||S.mail||S.plain||S.oa||S.kind;
  $("#clear").hidden = !dirty;
}
function drawTally(n){
  var bits = [];
  bits.push("<b>"+n.toLocaleString()+"</b> article"+(n===1?"":"s"));
  if(S.journal) bits.push("in "+esc(JB[S.journal].name));
  $("#tally").innerHTML = bits.join(" ");
}

/* ------------------------------------------------------------------- about */
function aboutHTML(){
  var mx = {}, tot = {};
  D.fields.forEach(function(f){
    mx[f] = Math.max.apply(null, D.rhythm[f]) || 1;
    tot[f] = D.rhythm[f].reduce(function(a,b){ return a+b; }, 0);
  });
  var h = '<div class="panel"><h3>How the shelf fills up</h3>'+
    '<p>One bar per week for the last year, counting research and review articles only. '+
    'Each panel is on its own scale &mdash; the point is the rhythm, not the height. '+
    'Medicine arrives every week; philosophy and political science land in quarterly blocks.</p>'+
    '<div class="rhythm">';
  D.fields.forEach(function(f){
    var w = D.rhythm[f], m = mx[f], n = w.length, bw = 300/n, bars = "";
    for(var i=0;i<n;i++){
      if(!w[i]) continue;
      var bh = Math.max(1.5, (w[i]/m)*54);
      bars += '<rect x="'+(i*bw).toFixed(2)+'" y="'+(56-bh).toFixed(2)+'" width="'+
              Math.max(1.4,bw-1).toFixed(2)+'" height="'+bh.toFixed(2)+
              '" fill="'+hueVar(f)+'" opacity="0.85"><title>'+esc(D.weeks[i])+': '+w[i]+' articles</title></rect>';
    }
    h += '<div class="rh"><h5><span class="swatch" style="background:'+hueVar(f)+'"></span>'+
      '<span class="fname">'+esc(f)+'</span></h5>'+
      '<div class="rhn">'+tot[f].toLocaleString()+' articles &middot; peak '+m+' in a week</div>'+
      '<svg viewBox="0 0 300 60" style="width:100%;height:60px;display:block" role="img" '+
      'aria-label="Weekly article counts for '+esc(f)+'">'+bars+
      '<line x1="0" y1="56.5" x2="300" y2="56.5" stroke="var(--rule)" stroke-width="1"></line></svg>'+
      '<div class="rhn" style="display:flex;justify-content:space-between;margin-top:2px">'+
      '<span>'+fmtDate(D.weeks[0])+'</span><span>'+fmtDate(D.weeks[D.weeks.length-1])+'</span></div></div>';
  });
  h += '</div></div>';

  var mailed = J.filter(function(j){ return j.alerts; });
  h += '<div class="panel"><h3>Which of these actually tell you when a new issue is out</h3>'+
    '<p>'+esc(D.alertNote)+'</p><div class="alertgrid">'+
    J.map(function(j){
      return '<div class="ag"><span class="tick '+(j.alerts?"yes":"no")+'">'+(j.alerts?"&#9993;":"&mdash;")+
        '</span><span class="nm" title="'+esc(j.name)+'">'+esc(j.name)+'</span>'+
        (j.alerts?'<span class="n">'+j.alerts+'/yr</span>':'')+'</div>';
    }).join("")+'</div>'+
    '<p style="margin-top:12px">Journals that email: '+mailed.map(function(j){
      return esc(j.name)+' (last '+fmtDate(j.lastalert)+')'; }).join(", ")+'. '+
    'The other '+(J.length-mailed.length)+' arrive silently.</p></div>';

  h += '<div class="panel"><h3>Every journal, and what came back for it</h3>'+
    '<p>Where a shelf looks thin, it is almost always the publisher’s metadata rather than '+
    'the journal. Chicago deposits no abstracts at all; Wiley deposits Econometrica in late '+
    'batches; the Philosophy Documentation Center runs months behind. The abstract column is '+
    'the honest measure of how much of a shelf you can actually read here.</p>'+
    '<div class="scroller"><table class="src"><thead><tr>'+
    '<th>Journal</th><th>Publisher</th><th>Since</th><th>Cadence</th>'+
    '<th style="text-align:right">Articles</th><th style="text-align:right">Reviews</th>'+
    '<th style="text-align:right">With abstract</th><th style="text-align:right">Issues</th>'+
    '<th style="text-align:right">Citations</th><th>Latest</th></tr></thead><tbody>'+
    J.map(function(j){
      return '<tr><td><span class="fdot" style="display:inline-block;width:7px;height:7px;border-radius:2px;'+
        'background:'+hueVar(j.field)+';margin-right:6px"></span>'+esc(j.name)+
        (j.bookmarked?"":' <span class="badge b-lead" style="margin-left:4px">by email only</span>')+
        '<div style="font-size:11.5px;color:var(--ink-faint);max-width:52ch;line-height:1.45">'+esc(j.note)+'</div></td>'+
        '<td style="font-size:11.5px;color:var(--ink-soft)">'+esc(j.pub)+'</td>'+
        '<td class="num">'+j.founded+'</td>'+
        '<td style="font-size:11.5px;color:var(--ink-soft)">'+esc(j.cadence)+'</td>'+
        '<td class="num">'+j.research+'</td><td class="num">'+(j.reviews||"—")+'</td>'+
        '<td class="num">'+(j.research?Math.round(100*j.withab/Math.max(1,j.n))+"%":"—")+'</td>'+
        '<td class="num">'+(j.issues||"—")+'</td>'+
        '<td class="num">'+j.cited.toLocaleString()+'</td>'+
        '<td class="num" style="text-align:left">'+(j.newest?fmtDate(j.newest):"nothing indexed")+'</td></tr>';
    }).join("")+'</tbody></table></div></div>';

  h += '<div class="panel"><h3>What was in the folder but is not a journal</h3>'+
    '<p>The bookmark folder holds these too. They are set aside rather than deleted, '+
    'so you can see the call that was made.</p><div class="scroller"><table class="src"><tbody>'+
    D.ignored.map(function(x){
      return '<tr><td style="width:34%"><a href="'+esc(x.u)+'" target="_blank" rel="noopener">'+esc(x.t)+'</a></td>'+
        '<td style="color:var(--ink-soft)">'+esc(x.why)+'</td></tr>'; }).join("")+
    '</tbody></table></div></div>';
  return h;
}
function wireAbout(){}

/* -------------------------------------------------------------------- wire */
function setView(v){
  S.view = v; S.limit = 60;
  Array.prototype.forEach.call(document.querySelectorAll('[role="tab"]'), function(b){
    b.setAttribute("aria-selected", b.dataset.view === v);
  });
  render();
}
Array.prototype.forEach.call(document.querySelectorAll('[role="tab"]'), function(b){
  b.addEventListener("click", function(){ setView(b.dataset.view); });
});
var qt;
$("#q").addEventListener("input", function(e){
  clearTimeout(qt);
  qt = setTimeout(function(){ S.q = e.target.value.trim().toLowerCase(); S.limit=60; render(); }, 140);
});
$("#sort").addEventListener("change", function(e){ S.sort = e.target.value; S.limit=60; render(); });
$("#jpick").addEventListener("change", function(e){ pickJournal(e.target.value); });
var jft;
$("#jfilter").addEventListener("input", function(e){
  clearTimeout(jft);
  jft = setTimeout(function(){ S.jfilter = e.target.value.trim().toLowerCase(); drawRail(); }, 120);
});
$("#kind").addEventListener("change", function(e){ S.kind = e.target.value; S.limit=60; render(); });
Array.prototype.forEach.call(document.querySelectorAll("#window button"), function(b){
  b.addEventListener("click", function(){
    S.days = +b.dataset.days; S.limit=60;
    Array.prototype.forEach.call(document.querySelectorAll("#window button"), function(x){
      x.setAttribute("aria-pressed", x === b);
    });
    render();
  });
});
[["#f-lead","lead"],["#f-mail","mail"],["#f-plain","plain"],["#f-oa","oa"]].forEach(function(p){
  $(p[0]).addEventListener("click", function(){ S[p[1]] = !S[p[1]]; S.limit=60; render(); });
});
$("#clear").addEventListener("click", function(){
  S.q=""; S.journal=""; S.field=""; S.lead=S.mail=S.plain=S.oa=false; S.kind="";
  $("#q").value=""; $("#kind").value=""; $("#jpick").value=""; S.limit=60; render();
});
document.addEventListener("keydown", function(e){
  if(e.key === "/" && document.activeElement !== $("#q")){ e.preventDefault(); $("#q").focus(); }
  if(e.key === "Escape" && document.activeElement === $("#q")){ $("#q").blur(); }
});
$("#theme").addEventListener("click", function(){
  var cur = document.documentElement.getAttribute("data-theme");
  var next = cur === "dark" ? "light" : cur === "light" ? "dark" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  try{ localStorage.setItem("radar-theme", next); }catch(err){}
});
try{
  var t = localStorage.getItem("radar-theme");
  if(t) document.documentElement.setAttribute("data-theme", t);
}catch(err){}

/* ----------------------------------------------------------------- chrome */
(function(){
  var nRes = A.filter(function(r){ return r[C.kind] !== "book review"; }).length;
  var nLead = A.filter(function(r){ return r[C.lead]; }).length;
  var recent = A.filter(function(r,i){ return age[i] <= 120 && r[C.kind] !== "book review"; }).length;
  var figs = [
    [nRes.toLocaleString(), "articles"],
    [String(J.length), "journals"],
    [recent.toLocaleString(), "last 4 months"],
    [String(nLead), "lead articles"],
    [String(D.nTranslated), "in plain english"]
  ];
  $("#figs").innerHTML = figs.map(function(f){
    return '<div class="fig"><b>'+f[0]+'</b><span>'+f[1]+'</span></div>'; }).join("");
  $("#k-built").textContent = "· harvested "+fmtDate(D.built);
  $("#foot-a").innerHTML =
    "<b>Where this comes from.</b> Article records are merged from three open sources on "+
    fmtDate(D.built)+", covering "+fmtDate(D.window[0])+" to "+fmtDate(D.window[1])+": "+
    "<b>OpenAlex</b> for authors, pagination, citation counts and field-weighted impact; "+
    "<b>Crossref</b> for abstracts and pagination in the humanities and social sciences; "+
    "<b>PubMed</b> for abstracts and publication types in the five medical journals, which is "+
    "the only source that can tell an Original Article from a letter to the editor. "+
    "The email column comes from your own Gmail. Citation counts for anything published in "+
    "the last few months are necessarily near zero — that is the world, not a gap in the data.";
  $("#foot-b").innerHTML =
    "<b>What is mine and what is theirs.</b> Abstracts are the authors’ own words as their "+
    "publisher deposited them. The plain-English paragraphs were drafted with an AI assistant and checked, and cover "+
    D.nTranslated+" articles chosen for leading an issue, being widely cited, or arriving in "+
    "your inbox, and are summaries rather than quotations — read the abstract, then the article, "+
    "before relying on either. Nothing here is medical or financial advice. "+
    "Built " + fmtDate(D.built) + ".";
})();

setView("articles");
})();
</script>
"""

if __name__ == "__main__":
    build()

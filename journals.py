# -*- coding: utf-8 -*-
"""The journal registry.

Seeded from the `Journals` bookmark folder as it exists in BOTH Firefox
(places.sqlite, profile ag1c53rs.default-release) and Chrome (Default/AccountBookmarks).
The two folders hold the same set -- Chrome's was imported from Firefox -- so the
union is 25 unique peer-reviewed journals plus a handful of non-journal links.

Two further journals are included that are NOT bookmarked: the owner receives their
University of Chicago Press table-of-contents alerts by email. They carry
bookmarked=False so the dashboard can label them.
"""

FIELDS = ["Philosophy", "Economics", "Political science", "Medicine & psychiatry"]

JOURNALS = [
    # ---------------------------------------------------------------- Philosophy
    dict(key="nous", name=u"Noûs", field="Philosophy", publisher="Wiley",
         issn=["0029-4624", "1468-0068"], openalex="S170801797",
         home="https://onlinelibrary.wiley.com/journal/14680068",
         cadence="Quarterly", founded=1967,
         note="General analytic philosophy; also publishes the Philosophical "
              "Perspectives and Philosophical Issues supplements."),
    dict(key="ethics", name="Ethics", field="Philosophy", publisher="University of Chicago Press",
         issn=["0014-1704", "1539-297X"], openalex="S184849641",
         home="https://www.journals.uchicago.edu/toc/et/current",
         cadence="Quarterly", founded=1890,
         note="Moral, political and legal philosophy, with a standing book-review "
              "section at the back of each issue."),
    dict(key="philstudies", name="Philosophical Studies", field="Philosophy", publisher="Springer",
         issn=["0031-8116", "1573-0883"], openalex="S147022693",
         home="https://link.springer.com/journal/11098",
         cadence="Monthly", founded=1950,
         note="The highest-volume philosophy journal in the set: analytic work "
              "across the board, published continuously rather than in themed issues."),
    dict(key="mind", name="Mind", field="Philosophy", publisher="Oxford University Press",
         issn=["0026-4423", "1460-2113"], openalex="S37480348",
         home="https://academic.oup.com/mind/issue",
         cadence="Quarterly", founded=1876,
         note="The oldest journal on the shelf. Long articles plus substantial "
              "Critical Notice and Book Review sections."),
    dict(key="philreview", name="The Philosophical Review", field="Philosophy",
         publisher="Duke University Press", issn=["0031-8108", "1558-1470"], openalex="S35579339",
         home="https://read.dukeupress.edu/the-philosophical-review",
         cadence="Quarterly", founded=1892,
         note="Edited at Cornell. Notoriously selective -- four or five articles "
              "an issue and little else."),
    dict(key="jphil", name="The Journal of Philosophy", field="Philosophy",
         publisher="Journal of Philosophy, Inc.", issn=["0022-362X"], openalex="S41650241",
         home="https://www.pdcnet.org/pdc/bvdb.nsf/journal?openform&journal=pdc_jphil",
         cadence="Monthly", founded=1904,
         note="Distributed through the Philosophy Documentation Center, which "
              "deposits metadata late -- expect this shelf to lag the others."),
    dict(key="aristotelian", name="Proceedings of the Aristotelian Society", field="Philosophy",
         publisher="Oxford University Press", issn=["0066-7374", "1467-9264"], openalex="S4210167481",
         home="https://academic.oup.com/aristotelian",
         cadence="Three issues a year", founded=1888,
         note="Papers read to the Society in London and then printed. Small, "
              "deliberate output."),
    dict(key="jhp", name="Journal of the History of Philosophy", field="Philosophy",
         publisher="Johns Hopkins University Press", issn=["0022-5053", "1538-4586"],
         openalex="S80702723", home="https://jhp.wisc.edu/contents.html",
         cadence="Quarterly", founded=1963,
         note="History of Western philosophy from the Presocratics forward."),
    dict(key="philtopics", name="Philosophical Topics", field="Philosophy",
         publisher="University of Arkansas Press", issn=["0276-2080"], openalex="S117069359",
         home="https://www.uapress.com/philosophical-topics-journal/",
         cadence="Twice yearly, themed", founded=1970,
         note="Every issue is a guest-edited theme. Publishes irregularly and "
              "deposits metadata rarely, so it can show nothing for a whole year."),
    dict(key="imprint", name=u"Philosophers’ Imprint", field="Philosophy",
         publisher="Michigan Publishing", issn=["1533-628X"], openalex="S988140095",
         home="https://www.philosophersimprint.org/",
         cadence="Continuous", founded=2001,
         note="Diamond open access -- free to read and free to publish in. Every "
              "article here opens without a login."),
    dict(key="synthese", name="Synthese", field="Philosophy", publisher="Springer",
         issn=["0039-7857", "1573-0964"], openalex="S255146",
         home="https://link.springer.com/journal/11229",
         cadence="Continuous", founded=1936,
         note="Epistemology, philosophy of science, logic and language. Very high "
              "volume, much of it in guest-edited topical collections."),
    dict(key="ppr", name="Philosophy and Phenomenological Research", field="Philosophy",
         publisher="Wiley", issn=["0031-8205", "1933-1592"], openalex="S204374153",
         home="https://onlinelibrary.wiley.com/journal/19331592",
         cadence="Bimonthly", founded=1940,
         note="Despite the name, a general analytic journal. Known for its book "
              "symposia, where several philosophers respond to one new book."),
    dict(key="pq", name="The Philosophical Quarterly", field="Philosophy",
         publisher="Oxford University Press", issn=["0031-8094", "1467-9213"], openalex="S81959571",
         home="https://academic.oup.com/pq",
         cadence="Quarterly", founded=1950,
         note="General analytic philosophy with a large, well-regarded book-review "
              "section."),
    dict(key="analysis", name="Analysis", field="Philosophy",
         publisher="Oxford University Press", issn=["0003-2638", "1467-8284"], openalex="S121299002",
         home="https://academic.oup.com/analysis",
         cadence="Quarterly", founded=1933,
         note="Famously short papers -- the house limit is around 4,000 words, so "
              "an average article here is a single argument, start to finish."),

    # ---------------------------------------------------------------- Economics
    dict(key="jpe", name="Journal of Political Economy", field="Economics",
         publisher="University of Chicago Press", issn=["0022-3808", "1537-534X"],
         openalex="S95323914", home="https://www.journals.uchicago.edu/toc/jpe/current",
         cadence="Monthly", founded=1892, alerts=True,
         note="One of the 'top five' in economics. Its Chicago table-of-contents "
              "alert arrives in the inbox on the first of the month."),
    dict(key="econometrica", name="Econometrica", field="Economics",
         publisher="Econometric Society / Wiley", issn=["0012-9682", "1468-0262"],
         openalex="S95464858", home="https://onlinelibrary.wiley.com/journal/14680262",
         cadence="Bimonthly", founded=1933,
         note="Economic theory and econometric method. Wiley deposits its metadata "
              "in large, late batches, so this shelf runs months behind the others."),
    dict(key="aer", name="American Economic Review", field="Economics",
         publisher="American Economic Association", issn=["0002-8282", "1944-7981"],
         openalex="S23254222", home="https://www.aeaweb.org/journals/aer",
         cadence="Monthly", founded=1911,
         note="The AEA's flagship, including the Papers & Proceedings issue each May."),
    dict(key="qje", name="The Quarterly Journal of Economics", field="Economics",
         publisher="Oxford University Press", issn=["0033-5533", "1531-4650"],
         openalex="S203860005", home="https://academic.oup.com/qje",
         cadence="Quarterly", founded=1886,
         note="The oldest English-language economics journal, and consistently the "
              "highest-cited per article of the top five."),
    dict(key="jole", name="Journal of Labor Economics", field="Economics",
         publisher="University of Chicago Press", issn=["0734-306X", "1537-5307"],
         openalex="S8557221", home="https://www.journals.uchicago.edu/toc/jole/current",
         cadence="Quarterly", founded=1983, bookmarked=False, alerts=True,
         note="Not in the bookmark folder. It is here because its Chicago "
              "table-of-contents alert arrives in the inbox."),

    # -------------------------------------------------------- Political science
    dict(key="ajps", name="American Journal of Political Science", field="Political science",
         publisher="Midwest Political Science Association / Wiley",
         issn=["0092-5853", "1540-5907"], openalex="S90314269",
         home="https://onlinelibrary.wiley.com/journal/15405907",
         cadence="Quarterly", founded=1957,
         note="Quantitative and formal political science, with a strict replication "
              "policy."),
    dict(key="arps", name="Annual Review of Political Science", field="Political science",
         publisher="Annual Reviews", issn=["1094-2939", "1545-1577"], openalex="S8194976",
         home="https://www.annualreviews.org/journal/polisci",
         cadence="Annual", founded=1998,
         note="Commissioned review essays rather than original research. One volume "
              "a year, so the whole shelf refills at once."),
    dict(key="apt", name="American Political Thought", field="Political science",
         publisher="University of Chicago Press", issn=["2161-1580", "2161-1599"],
         openalex="S2735640579", home="https://www.journals.uchicago.edu/toc/apt/current",
         cadence="Quarterly", founded=2012, bookmarked=False, alerts=True,
         note="Not in the bookmark folder. It is here because its Chicago "
              "table-of-contents alert arrives in the inbox."),

    # --------------------------------------------------- Medicine & psychiatry
    dict(key="lancet", name="The Lancet", field="Medicine & psychiatry", publisher="Elsevier",
         issn=["0140-6736", "1474-547X"], openalex="S49861241", pubmed="Lancet",
         home="https://www.thelancet.com/journals/lancet/issue/current",
         cadence="Weekly", founded=1823,
         note="Weekly, and only a fraction of each issue is research. Articles, "
              "Reviews and Seminars are kept on the shelf; Correspondence, News and "
              "Obituaries are set aside."),
    dict(key="nejm", name="The New England Journal of Medicine", field="Medicine & psychiatry",
         publisher="Massachusetts Medical Society", issn=["0028-4793", "1533-4406"],
         openalex="S62468778", pubmed="N Engl J Med",
         home="https://www.nejm.org/",
         cadence="Weekly", founded=1812,
         note="Weekly, filtered the same way as The Lancet: Original Articles and "
              "Review Articles kept, Perspective and Correspondence set aside."),
    dict(key="lancetpsych", name="The Lancet Psychiatry", field="Medicine & psychiatry",
         publisher="Elsevier", issn=["2215-0366", "2215-0374"], openalex="S2531556786",
         pubmed="Lancet Psychiatry",
         home="https://www.thelancet.com/journals/lanpsy/issue/current",
         cadence="Monthly", founded=2014,
         note="Psychiatry and mental-health research in the Lancet family."),
    dict(key="jamapsych", name="JAMA Psychiatry", field="Medicine & psychiatry",
         publisher="American Medical Association", issn=["2168-622X", "2168-6238"],
         openalex="S2495708506", pubmed="JAMA Psychiatry",
         home="https://jamanetwork.com/journals/jamapsychiatry/",
         cadence="Monthly", founded=1959,
         note="Formerly Archives of General Psychiatry."),
    dict(key="ajph", name="American Journal of Public Health", field="Medicine & psychiatry",
         publisher="American Public Health Association", issn=["0090-0036", "1541-0048"],
         openalex="S168049282", pubmed="Am J Public Health",
         home="https://ajph.aphapublications.org/",
         cadence="Monthly", founded=1911,
         note="Reached the folder through a single saved 2015 article rather than a "
              "journal link, but it is peer reviewed, so it gets a shelf."),
]

# Links that sat in the Journals folders but are not peer-reviewed journals.
IGNORED = [
    ("Forthcoming Books, Harvard University Press",
     "https://www.hup.harvard.edu/results-list.php?new=f&sortby=title&skip=50",
     "A book publisher's catalogue. Already covered by The Season Ahead dashboard."),
    ("Sam Berstler", "https://samberstler.com/",
     "A philosopher's personal website."),
    ("American Poetry Review", "https://aprweb.org/",
     "A literary magazine. Edited, but not peer reviewed."),
    ("Data Solutions Analyst, Bloomberg Careers",
     "https://careers.bloomberg.com/job/detail/110924",
     "A job posting."),
    ("quarterly journal of economics, Google Search",
     "https://www.google.com/search?q=quarterly+journal+of+economics",
     "A search-results page. The journal itself is on the shelf."),
    ("Station Eleven, Metacritic",
     "https://www.metacritic.com/tv/station-eleven/season-1",
     "Television reviews."),
    ("ADP ReThink Quarterly", "https://rethinkq.adp.com/issue-5-out-of-office/",
     "Corporate content marketing."),
    ("Statistical Modeling, Causal Inference, and Social Science",
     "https://statmodeling.stat.columbia.edu/",
     "Andrew Gelman's blog. Excellent, but not peer reviewed."),
    ("Philosophical Topics on JSTOR", "https://www.jstor.org/journal/philtopics",
     "An archive mirror of a journal already on the shelf."),
]

for _j in JOURNALS:
    _j.setdefault("bookmarked", True)
    _j.setdefault("alerts", False)
    _j.setdefault("pubmed", None)

BY_KEY = {j["key"]: j for j in JOURNALS}

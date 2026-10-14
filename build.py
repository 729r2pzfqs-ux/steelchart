"""Render steelchart.org into docs/ (GitHub Pages).

    python build.py

Data: data/*.json (built by tools/build_data.py from data/source/). Templates: templates/*.html (Jinja2).
SVG charts: svg.py. All prose on steel/compare/knife pages is generated from the data, so every
number on a page comes from data/.

Pages: / , /chart/, /steel/, /steel/<id>/, /compare/, /compare/<a>-vs-<b>/ (+ reverse-order redirect stubs),
/knife/, /knife/<id>/, /brand/, /brand/<id>/, /category/<id>/, /guide/<slug>/, /about/, /privacy/, /terms/,
/affiliate-disclosure/, 404. Plus sitemap.xml, robots.txt, ads.txt, search-index.json, CNAME, favicons.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from statistics import mean
from urllib.parse import quote_plus

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

import svg

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
DATA = ROOT / "data"
SITE_URL = "https://steelchart.org"
DOMAIN = "steelchart.org"
SITE_NAME = "SteelChart"
CONTACT_EMAIL = "info@steelchart.org"
ADSENSE_PUB = "ca-pub-5861928596436289"
GA_ID = "G-1B8ZG0EDPL"            # GA4 measurement id; GA tags are omitted while empty
AD_SLOTS: dict[str, str] = {}    # TODO: AdSense slot ids {"inline": "...", "side": "..."}; empty = auto ads only
TODAY = date.today()

RATING_KEYS = [k for k, _ in svg.AXES]
RATING_NAMES = dict(svg.AXES)
CAT_PHRASE = {"stainless": "conventional stainless steel", "stainless-pm": "powder metallurgy stainless steel",
              "tool": "tool steel", "tool-pm": "powder metallurgy tool steel",
              "high-speed-pm": "powder metallurgy high-speed steel", "carbon": "carbon steel"}
WIN_PHRASE = {"edge_retention": "holds an edge longer", "toughness": "is tougher",
              "corrosion_resistance": "resists corrosion better", "ease_of_sharpening": "is easier to sharpen"}
CHOOSE_PHRASE = {"edge_retention": "edge retention", "toughness": "toughness",
                 "corrosion_resistance": "corrosion resistance", "ease_of_sharpening": "easy sharpening"}


# ------------------------------------------------------------------ helpers
def load(name: str):
    return json.loads((DATA / name).read_text())


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.3f}".rstrip("0").rstrip(".")
    return str(v)


def level(v: int) -> str:
    return "very high" if v >= 9 else "high" if v >= 7 else "moderate" if v >= 5 else "low" if v >= 3 else "very low"


def fit_desc(d: str, n: int = 158) -> str:
    d = re.sub(r"\s+", " ", d).strip()
    if len(d) <= n:
        return d
    cut = d[:n]
    dot = cut.rfind(". ")
    return cut[:dot + 1] if dot >= 90 else cut[:n - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def model_name(k: dict) -> str:
    return re.sub(r"\s*\(.*?\)", "", k["model"]).strip()


def comp_value(s: dict, el: str):
    return s["composition"].get(el)


# ------------------------------------------------------------------ prose generated from data
def steel_answer(s: dict) -> str:
    r = s["ratings"]
    maker = s.get("manufacturer") or ""
    by = "" if not maker or "generic" in maker.lower() or "various" in maker.lower() else f" from {maker.split(' (')[0]}"
    return (f"{s['name']} is a {CAT_PHRASE[s['category']]}{by}. It rates {r['edge_retention']}/10 for edge retention, "
            f"{r['toughness']}/10 for toughness and {r['corrosion_resistance']}/10 for corrosion resistance, "
            f"and is usually hardened to {s['hrc_min']}–{s['hrc_max']} HRC.")


def steel_chemistry(s: dict) -> list[str]:
    c = s["composition"]
    paras = []
    C, Cr, V, Mo, W, Co, Nb, N = (c.get(e) or 0 for e in ("C", "Cr", "V", "Mo", "W", "Co", "Nb", "N"))
    bits = []
    if C:
        bits.append(f"{fmt(C)}% carbon" + (", a high level that supports high hardness and a large volume of hard carbides"
                                          if C >= 1.4 else ", enough to reach typical knife hardness" if C >= 0.6
                                          else ", a low level that favours toughness and corrosion resistance"))
    if Cr:
        if s["category"].startswith("stainless"):
            bits.append(f"{fmt(Cr)}% chromium for corrosion resistance")
        elif Cr >= 10:
            bits.append(f"{fmt(Cr)}% chromium, though much of it is tied up in carbides, so the steel is not fully stainless")
        elif Cr >= 1:
            bits.append(f"{fmt(Cr)}% chromium, too little for stainless behaviour")
    if bits:
        paras.append(f"{s['name']} contains " + "; ".join(bits) + ".")
    more = []
    if V >= 2:
        more.append(f"Its {fmt(V)}% vanadium forms vanadium carbides, among the hardest carbides in knife steels, which "
                    f"drive wear resistance and slow edge loss but also make the steel slower to sharpen")
    elif V > 0:
        more.append(f"A small vanadium addition ({fmt(V)}%) mainly refines grain size")
    if Nb:
        more.append(f"niobium ({fmt(Nb)}%) forms fine, very hard niobium carbides")
    if W >= 1:
        more.append(f"tungsten ({fmt(W)}%) adds hard carbides and helps the steel keep its hardness")
    if Mo >= 0.5:
        more.append(f"molybdenum ({fmt(Mo)}%) improves hardenability" + (" and pitting resistance" if s["category"].startswith("stainless") else ""))
    if Co:
        more.append(f"cobalt ({fmt(Co)}%) strengthens the matrix")
    if N:
        more.append(f"nitrogen ({fmt(N)}%) partly takes the place of carbon, which helps corrosion resistance")
    if more:
        first = more[0][0].upper() + more[0][1:]
        paras.append(first + ("; " + "; ".join(more[1:]) if more[1:] else "") + ".")
    if "pm" in s["category"] or "powder" in (s.get("process") or "").lower():
        paras.append("It is made by powder metallurgy: the alloy is atomised into fine powder and consolidated, which keeps "
                     "the carbides small and evenly spread. That is what lets a highly alloyed steel stay tough enough for a knife blade.")
    if s.get("notes"):
        note = re.sub(r"\s*P and S are maximums\.?", "", s["notes"]).strip()
        if note:
            paras.append(note)
    return paras


def sharpening(s: dict) -> str:
    e = s["ratings"]["ease_of_sharpening"]
    if e >= 8:
        return (f"{s['short']} is easy to sharpen ({e}/10). Aluminium-oxide and water stones work well, and it takes a fine "
                f"edge quickly; a ceramic rod or strop keeps it going between sharpenings.")
    if e >= 5:
        return (f"{s['short']} is moderately easy to sharpen ({e}/10). Water stones and ceramics work; diamond plates "
                f"speed up reprofiling or repairing a damaged edge.")
    c = s["composition"]
    if (c.get("V") or 0) >= 2 or (c.get("W") or 0) >= 3:
        kinds = " and ".join(n for n, e, lim in (("vanadium", "V", 2), ("tungsten", "W", 3)) if (c.get(e) or 0) >= lim)
        why = (f"Its {kinds} carbides are harder than the aluminium oxide in conventional stones, so diamond "
               f"or CBN plates cut it far more efficiently.")
    else:
        why = ("Its large volume of hard carbides makes conventional stones slow going; diamond plates cut it much faster.")
    return f"{s['short']} is slow to sharpen ({e}/10). {why} Once sharp, it needs touch-ups less often."


def rust_answer(s: dict) -> str:
    c = s["ratings"]["corrosion_resistance"]
    if c >= 9:
        return f"Very little. {s['short']} rates {c}/10 for corrosion resistance, among the best of any knife steel, and suits salt water and humid climates."
    if c >= 7:
        return f"Not in normal use. {s['short']} rates {c}/10 for corrosion resistance; wipe it dry after contact with salt or acidic food."
    if c >= 5:
        return f"It can. {s['short']} rates {c}/10: stain-resistant rather than rust-proof, so it can spot if left wet or salty."
    if c >= 3:
        return f"Yes, if neglected. {s['short']} rates only {c}/10; keep it dry and lightly oiled, especially in humid weather."
    return f"Yes. {s['short']} rates {c}/10 and will rust or patina without care; dry it after use and keep a thin coat of oil on it."


def steel_faq(s: dict) -> list[dict]:
    r = s["ratings"]
    strengths = sorted(RATING_KEYS, key=lambda k: -r[k])
    return [
        {"q": f"Is {s['short']} a good knife steel?",
         "a": f"{s['short']} is strongest in {RATING_NAMES[strengths[0]].lower()} ({r[strengths[0]]}/10) and weakest in "
              f"{RATING_NAMES[strengths[-1]].lower()} ({r[strengths[-1]]}/10). Its average across the four ratings is "
              f"{mean(r.values()):.1f}/10, and it sits in the {s['price_tier'].lower()} price tier."},
        {"q": f"Does {s['short']} rust?", "a": rust_answer(s)},
        {"q": f"Is {s['short']} hard to sharpen?", "a": sharpening(s)},
        {"q": f"What hardness is {s['short']}?",
         "a": f"Knives in {s['short']} are usually hardened to {s['hrc_min']}–{s['hrc_max']} HRC. Makers can run it outside "
              f"that range; harder means better edge retention but lower toughness."},
    ]


def verdict(a: dict, b: dict) -> tuple[str, list[str]]:
    ra, rb = a["ratings"], b["ratings"]
    wa = [k for k in RATING_KEYS if ra[k] > rb[k]]
    wb = [k for k in RATING_KEYS if rb[k] > ra[k]]

    def join(ks):
        p = [WIN_PHRASE[k] for k in ks]
        return p[0] if len(p) == 1 else ", ".join(p[:-1]) + " and " + p[-1]
    parts = []
    if wa:
        parts.append(f"{a['short']} {join(wa)}")
    if wb:
        parts.append(f"{b['short']} {join(wb)}")
    if not parts:
        main = f"{a['short']} and {b['short']} rate the same on all four properties."
    else:
        main = "; ".join(parts) + "."
        main = main[0].upper() + main[1:]
    choose = []
    if wa:
        top = max(wa, key=lambda k: ra[k] - rb[k])
        choose.append(f"Choose {a['short']} for {CHOOSE_PHRASE[top]}")
    if wb:
        top = max(wb, key=lambda k: rb[k] - ra[k])
        choose.append(f"{b['short']} for {CHOOSE_PHRASE[top]}")
    tail = (", ".join(choose) + ".") if choose else "The choice comes down to price and the knives available in each."
    return main, [tail]


def property_breakdown(a: dict, b: dict) -> list[dict]:
    out = []
    for k, name in svg.AXES:
        va, vb = a["ratings"][k], b["ratings"][k]
        if va == vb:
            txt = f"Both rate {va}/10 for {name.lower()}."
        else:
            hi, lo = (a, b) if va > vb else (b, a)
            txt = (f"{hi['short']} {WIN_PHRASE[k]}: {hi['ratings'][k]}/10 against {lo['ratings'][k]}/10 for {lo['short']}, "
                   f"a {abs(va - vb)}-point gap.")
        ca, cb = a["composition"], b["composition"]
        if k == "edge_retention" and (ca.get("V") or 0) != (cb.get("V") or 0):
            txt += f" Vanadium: {fmt(ca.get('V') or 0)}% vs {fmt(cb.get('V') or 0)}%; more vanadium carbide generally means more wear resistance."
        if k == "corrosion_resistance" and (ca.get("Cr") or 0) != (cb.get("Cr") or 0):
            txt += f" Chromium: {fmt(ca.get('Cr') or 0)}% vs {fmt(cb.get('Cr') or 0)}%, though what matters is the chromium left in solution, not the total."
        if k == "toughness" and (a["hrc_max"] != b["hrc_max"]):
            txt += f" Typical hardness: {a['hrc_min']}–{a['hrc_max']} vs {b['hrc_min']}–{b['hrc_max']} HRC; harder blades trade toughness for edge holding."
        out.append({"name": name, "text": txt, "a": va, "b": vb})
    return out


# ------------------------------------------------------------------ affiliate links
def bladehq(query: str) -> str:
    return "https://www.bladehq.com/?search=" + quote_plus(query)


def amazon(query: str) -> str:
    return "https://www.amazon.com/s?k=" + quote_plus(query)


def knife_links(k: dict) -> list[dict]:
    q = f"{k['brand']} {model_name(k)}"
    return [{"name": "Blade HQ", "url": bladehq(q)}, {"name": "Amazon", "url": amazon(q + " knife")}]


# ------------------------------------------------------------------ site
class Site:
    def __init__(self):
        self.steels = load("steels.json")
        self.knives = load("knives.json")
        self.comps = load("comparisons.json")
        self.brands = load("brands.json")
        self.cats = load("categories.json")
        self.equivs = load("equivalents.json")
        self.S = {s["id"]: s for s in self.steels}
        self.C = {c["id"]: c for c in self.cats}
        self.B = {b["name"]: b for b in self.brands}
        for k in self.knives:
            k["name"] = f"{k['brand']} {model_name(k)}"
            k["steel"] = self.S[k["steel_id"]]
            k["brand_id"] = self.B[k["brand"]]["id"]
            k["links"] = knife_links(k)
        for s in self.steels:
            s["knives"] = [k for k in self.knives if k["steel_id"] == s["id"]]
            s["comparisons"] = sorted([c for c in self.comps if s["id"] in (c["steel_a"], c["steel_b"])],
                                      key=lambda c: -(c["search_volume"] or 0))
            s["avg"] = round(mean(s["ratings"].values()), 1)
            s["equivalents"] = [g for g in self.equivs if s["id"] in g["in_scope"]]
        for c in self.comps:
            c["a"], c["b"] = self.S[c["steel_a"]], self.S[c["steel_b"]]
            c["title"] = f"{c['a']['short']} vs {c['b']['short']}"
        for b in self.brands:
            b["knives"] = [k for k in self.knives if k["brand"] == b["name"]]
            ids = []
            for k in b["knives"]:
                if k["steel_id"] not in ids:
                    ids.append(k["steel_id"])
            b["steels"] = [self.S[i] for i in ids]
        for cat in self.cats:
            cat["steels"] = sorted([s for s in self.steels if s["category"] == cat["id"]], key=lambda s: -s["avg"])
            ids = {s["id"] for s in cat["steels"]}
            cat["comparisons"] = [c for c in self.comps if c["steel_a"] in ids or c["steel_b"] in ids]
        self.urls: list[tuple[str, float]] = []
        self.search: list[dict] = []
        self.env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html"]),
                               trim_blocks=True, lstrip_blocks=True, extensions=["jinja2.ext.do"])
        self.env.filters["fmt"] = fmt
        self.env.filters["level"] = level
        self.env.globals.update(svg=svg, ad=self.ad, site_url=SITE_URL, site_name=SITE_NAME, email=CONTACT_EMAIL,
                                adsense_pub=ADSENSE_PUB, ga_id=GA_ID, year_now=TODAY.year, rating_keys=RATING_KEYS,
                                rating_names=RATING_NAMES, cats=self.cats, cat_by_id=self.C, steels_by_id=self.S,
                                steel_id_by_name={s['name']: s['id'] for s in self.steels},
                                elements=svg.ELEMENT_ORDER, element_names=svg.ELEMENT_NAMES, bladehq=bladehq,
                                top_comps=sorted(self.comps, key=lambda c: -(c["search_volume"] or 0))[:8])

    @staticmethod
    def ad(name: str):
        slot = AD_SLOTS.get(name)
        if not slot:
            return ""
        return Markup(f'<div class="ad-slot"><ins class="adsbygoogle" style="display:block" data-ad-client="{ADSENSE_PUB}" '
                      f'data-ad-slot="{slot}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
                      f'<script>(adsbygoogle=window.adsbygoogle||[]).push({{}});</script></div>')

    def render(self, tpl: str, path: str, title: str, description: str, crumbs=(), jsonld=(), priority=0.5, **ctx):
        assert len(title) <= 60, (path, len(title), title)
        description = fit_desc(description)
        ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/"}] if path != "/" else []
        ld += list(jsonld)
        if crumbs:
            ld.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": label, "item": SITE_URL + href}
                for i, (href, label) in enumerate(crumbs)]})
        html = self.env.get_template(tpl).render(path=path, title=title, description=description, crumbs=list(crumbs),
                                                 jsonld=ld, **ctx)
        out = DOCS / ("404.html" if path == "/404.html" else path.lstrip("/") + "index.html")
        write(out, html)
        if path != "/404.html":
            self.urls.append((path, priority))

    # ---------------- pages
    def home(self):
        ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/",
               "potentialAction": {"@type": "SearchAction", "target": SITE_URL + "/?q={search_term_string}",
                                   "query-input": "required name=search_term_string"}},
              {"@context": "https://schema.org", "@type": "Organization", "name": SITE_NAME, "url": SITE_URL + "/",
               "email": CONTACT_EMAIL, "logo": SITE_URL + "/favicon-512.png"}]
        featured = [k for k in self.knives if k["id"] in ("spyderco-para-3", "benchmade-bugout", "civivi-elementum",
                                                          "qsp-penguin", "kershaw-leek", "hogue-deka")]
        self.render("home.html", "/", "SteelChart: Knife Steel Chart, Ratings & Comparisons",
                    f"Compare {len(self.steels)} knife steels by composition, hardness, edge retention, toughness and "
                    f"corrosion resistance, with {len(self.comps)} head-to-head comparisons and the knives that use each.",
                    jsonld=ld, priority=1.0, featured=featured, steels=self.steels,
                    popular=sorted(self.comps, key=lambda c: -(c["search_volume"] or 0))[:12])
        self.search.append({"t": "Knife steel chart", "u": "/chart/", "d": "All steels, sortable"})

    def chart(self):
        rows = sorted(self.steels, key=lambda s: s["short"].lower())
        ld = [{"@context": "https://schema.org", "@type": "Dataset", "name": "Knife steel chart",
               "description": "Composition, hardness range and 1-10 performance ratings for popular knife steels.",
               "url": SITE_URL + "/chart/", "creator": {"@type": "Organization", "name": SITE_NAME},
               "variableMeasured": ["carbon", "chromium", "vanadium", "molybdenum", "HRC"] + [RATING_NAMES[k] for k in RATING_KEYS]}]
        self.render("chart.html", "/chart/", f"Knife Steel Chart: {len(self.steels)} Steels Compared",
                    f"Knife steel chart: {len(self.steels)} steels with carbon, chromium, vanadium and molybdenum content, "
                    f"HRC range and 1-10 ratings for edge retention, toughness, corrosion and sharpening. Sortable.",
                    crumbs=[("/", "Home"), ("/chart/", "Steel chart")], jsonld=ld, priority=0.9, rows=rows)

    def steel_pages(self):
        groups = [(c, [s for s in self.steels if s["category"] == c["id"]]) for c in self.cats]
        self.render("steel_index.html", "/steel/", "Knife Steels A-Z by Category",
                    f"All {len(self.steels)} knife steels on SteelChart, grouped by type: stainless, powder metallurgy, "
                    f"tool, high-speed and carbon steels, each with ratings and composition.",
                    crumbs=[("/", "Home"), ("/steel/", "Steels")], priority=0.8, groups=groups)
        for s in self.steels:
            title = f"{s['short']} Steel: Composition, HRC & Ratings"
            if len(title) > 60:
                title = f"{s['short']}: Specs & Ratings"
            r = s["ratings"]
            desc = (f"{s['short']} is a {CAT_PHRASE[s['category']]} ({s['hrc_min']}-{s['hrc_max']} HRC) with "
                    f"{r['edge_retention']}/10 edge retention and {r['corrosion_resistance']}/10 corrosion resistance. "
                    f"Composition, ratings and knives.")
            faq = steel_faq(s)
            ld = [{"@context": "https://schema.org", "@type": "TechArticle", "headline": f"{s['name']} steel",
                   "description": steel_answer(s), "about": {"@type": "Thing", "name": s["name"]},
                   "author": {"@type": "Organization", "name": SITE_NAME}, "dateModified": TODAY.isoformat()},
                  {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                      {"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["a"]}} for q in faq]}]
            cat = self.C[s["category"]]
            related = [x for x in cat["steels"] if x["id"] != s["id"]][:6]
            self.render("steel.html", f"/steel/{s['id']}/", title, desc,
                        crumbs=[("/", "Home"), ("/steel/", "Steels"), (f"/steel/{s['id']}/", s["short"])],
                        jsonld=ld, priority=0.9, s=s, answer=steel_answer(s), chemistry=steel_chemistry(s),
                        sharpen=sharpening(s), faq=faq, cat=cat, related=related)
            self.search.append({"t": f"{s['name']} steel", "u": f"/steel/{s['id']}/", "d": CAT_PHRASE[s["category"]],
                                "k": " ".join(s["aliases"])})

    def compare_pages(self):
        ordered = sorted(self.comps, key=lambda c: (-(c["search_volume"] or 0), c["id"]))
        self.render("compare_index.html", "/compare/", f"Knife Steel Comparisons: {len(self.comps)} Pairs",
                    f"{len(self.comps)} head-to-head knife steel comparisons, from 14C28N vs D2 to M390 vs MagnaCut: "
                    f"composition, ratings and verdict for each pair.",
                    crumbs=[("/", "Home"), ("/compare/", "Compare")], priority=0.9, comps=ordered)
        for c in self.comps:
            a, b = c["a"], c["b"]
            main, choose = verdict(a, b)
            title = f"{c['title']} Steel Comparison"
            if len(title) > 60:
                title = c["title"]
            related = [x for x in self.comps if x["id"] != c["id"] and
                       ({x["steel_a"], x["steel_b"]} & {c["steel_a"], c["steel_b"]})]
            related.sort(key=lambda x: -(x["search_volume"] or 0))
            faq = [{"q": f"Which is better, {a['short']} or {b['short']}?", "a": main + " " + " ".join(choose)},
                   {"q": f"Which is harder, {a['short']} or {b['short']}?",
                    "a": f"{a['short']} is typically run at {a['hrc_min']}–{a['hrc_max']} HRC and {b['short']} at "
                         f"{b['hrc_min']}–{b['hrc_max']} HRC."},
                   {"q": f"Is {a['short']} or {b['short']} more rust resistant?",
                    "a": (f"{a['short']} ({a['ratings']['corrosion_resistance']}/10)" if a['ratings']['corrosion_resistance'] > b['ratings']['corrosion_resistance']
                          else f"{b['short']} ({b['ratings']['corrosion_resistance']}/10)" if b['ratings']['corrosion_resistance'] > a['ratings']['corrosion_resistance']
                          else f"Neither: both rate {a['ratings']['corrosion_resistance']}/10")
                         + f". {a['short']} is a {CAT_PHRASE[a['category']]}; {b['short']} is a {CAT_PHRASE[b['category']]}."}]
            ld = [{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                      {"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["a"]}} for q in faq]},
                  {"@context": "https://schema.org", "@type": "ItemList", "name": c["title"], "itemListElement": [
                      {"@type": "ListItem", "position": 1, "name": a["name"], "url": f"{SITE_URL}/steel/{a['id']}/"},
                      {"@type": "ListItem", "position": 2, "name": b["name"], "url": f"{SITE_URL}/steel/{b['id']}/"}]}]
            self.render("compare.html", f"/compare/{c['id']}/", title, f"{c['title']}: {main} Composition, HRC, ratings and knives in each.",
                        crumbs=[("/", "Home"), ("/compare/", "Compare"), (f"/compare/{c['id']}/", c["title"])],
                        jsonld=ld, priority=0.8, c=c, a=a, b=b, verdict=main, choose=choose,
                        breakdown=property_breakdown(a, b), related=related[:8], faq=faq)
            # reverse-order URL -> canonical
            rev = f"{c['steel_b']}-vs-{c['steel_a']}"
            write(DOCS / "compare" / rev / "index.html", redirect_stub(f"/compare/{c['id']}/", c["title"]))
            self.search.append({"t": c["title"], "u": f"/compare/{c['id']}/", "d": "Steel comparison"})

    def knife_pages(self):
        self.render("knife_index.html", "/knife/", f"Knife Specs & Steels: {len(self.knives)} Popular Knives",
                    f"Specs for {len(self.knives)} popular pocket knives, including the Para 3, Bugout and Elementum: "
                    f"blade steel, blade length, weight, lock and list price. Sortable.",
                    crumbs=[("/", "Home"), ("/knife/", "Knives")], priority=0.8, knives=self.knives)
        for k in self.knives:
            s = k["steel"]
            title = f"{k['name']} Specs & Steel"
            desc = (f"{k['name']}: {s['short']} steel, {fmt(k['blade_length_in'])}\" blade, {fmt(k['weight_oz'])} oz, "
                    f"{(k['lock_type'] or '').lower()}. Full specs, steel ratings and where to buy.")
            same_steel = [x for x in self.knives if x["steel_id"] == k["steel_id"] and x["id"] != k["id"]]
            same_brand = [x for x in self.knives if x["brand"] == k["brand"] and x["id"] != k["id"]]
            price = k.get("msrp_usd") or 0
            similar_price = [x for x in self.knives if x["id"] != k["id"] and x not in same_brand and price and
                             x.get("msrp_usd") and abs(x["msrp_usd"] - price) <= 0.3 * price][:5]
            prod = {"@context": "https://schema.org", "@type": "Product", "name": k["name"],
                    "brand": {"@type": "Brand", "name": k["brand"]}, "material": s["name"],
                    "category": "Pocket knife" if "Fixed" not in (k.get("category") or "") else "Fixed-blade knife",
                    "additionalProperty": [{"@type": "PropertyValue", "name": n, "value": v} for n, v in (
                        ("Blade length (in)", k.get("blade_length_in")), ("Weight (oz)", k.get("weight_oz")),
                        ("Lock", k.get("lock_type")), ("Handle", k.get("handle_material"))) if v],
                    "offers": {"@type": "Offer", "price": k.get("msrp_usd"), "priceCurrency": "USD",
                               "url": k.get("verified_url")}}
            # Google needs an offer for a valid Product; without a list price, leave the Product off
            self.render("knife.html", f"/knife/{k['id']}/", title, desc,
                        crumbs=[("/", "Home"), ("/knife/", "Knives"), (f"/knife/{k['id']}/", k["name"])],
                        jsonld=[prod] if k.get("msrp_usd") else [], priority=0.7, k=k, s=s, same_steel=same_steel, same_brand=same_brand,
                        similar_price=similar_price, brand=self.B[k["brand"]], checked="2026-10-14",
                        steel_comps=s["comparisons"][:5])
            self.search.append({"t": k["name"], "u": f"/knife/{k['id']}/", "d": f"{s['short']} steel", "k": k["model"]})

    def brand_pages(self):
        self.render("brand_index.html", "/brand/", "Knife Brands and the Steels They Use",
                    f"{len(self.brands)} knife brands and the steels in their popular models, from Spyderco and Benchmade "
                    f"to Civivi and Buck.", crumbs=[("/", "Home"), ("/brand/", "Brands")], priority=0.6, brands=self.brands)
        for b in self.brands:
            steels = ", ".join(s["short"] for s in b["steels"])
            self.render("brand.html", f"/brand/{b['id']}/", f"{b['name']} Knives: Steels & Models",
                        f"{b['name']} knives on SteelChart: {len(b['knives'])} model{'s' if len(b['knives']) != 1 else ''} "
                        f"in {steels}. Specs, steel ratings and where to buy.",
                        crumbs=[("/", "Home"), ("/brand/", "Brands"), (f"/brand/{b['id']}/", b["name"])],
                        priority=0.6, b=b)
            self.search.append({"t": f"{b['name']} knives", "u": f"/brand/{b['id']}/", "d": "Brand"})

    def category_pages(self):
        for cat in self.cats:
            names = ", ".join(s["short"] for s in cat["steels"][:4])
            title = f"{cat['name']} for Knives: Chart & Ratings"
            if len(title) > 60:
                title = f"{cat['name']}: Chart & Ratings"
            self.render("category.html", f"/category/{cat['id']}/", title,
                        f"{cat['description']} Compare {len(cat['steels'])} of them, including {names}.",
                        crumbs=[("/", "Home"), ("/steel/", "Steels"), (f"/category/{cat['id']}/", cat["name"])],
                        priority=0.7, cat=cat)
            self.search.append({"t": cat["name"], "u": f"/category/{cat['id']}/", "d": "Steel category"})

    def guide_pages(self):
        by = lambda k: sorted(self.steels, key=lambda s: (-s["ratings"][k], s["short"]))
        balanced = sorted(self.steels, key=lambda s: (-s["avg"], s["short"]))
        tiers = []
        for t in ("Budget", "Mid-range", "Premium", "Ultra-premium"):
            ts = [s for s in balanced if s["price_tier"] == t]
            if ts:
                tiers.append((t, ts))
        edc = sorted([s for s in self.steels if s["ratings"]["corrosion_resistance"] >= 6 and s["ratings"]["toughness"] >= 4],
                     key=lambda s: (-(s["ratings"]["edge_retention"] + s["ratings"]["toughness"]), s["short"]))
        carbon = [s for s in self.steels if s["category"] == "carbon"]
        stainless = [s for s in self.steels if s["category"].startswith("stainless")]
        avg = lambda xs, k: round(mean(s["ratings"][k] for s in xs), 1)
        guides = [
            ("best-knife-steels-ranked", "Best Knife Steels Ranked by Property",
             f"The best knife steels ranked by edge retention, toughness, corrosion resistance and ease of sharpening, "
             f"plus a balanced ranking of {len(self.steels)} steels.", "guide_ranked.html"),
            ("knife-steel-types-explained", "Knife Steel Types Explained",
             "Stainless, powder metallurgy, tool, high-speed and carbon knife steels explained: what defines each type "
             "and which steels belong to it.", "guide_types.html"),
            ("carbon-vs-stainless", "Carbon vs Stainless Steel for Knives",
             f"Carbon steels average {avg(carbon, 'corrosion_resistance')}/10 for corrosion resistance against "
             f"{avg(stainless, 'corrosion_resistance')}/10 for stainless, but sharpen more easily. Full comparison.",
             "guide_carbon.html"),
            ("best-steel-for-edc", "Best Steel for EDC Knives",
             "Which knife steels suit everyday carry: steels that balance edge retention and toughness and resist "
             "rust, by price tier, with knives that use them.", "guide_edc.html"),
        ]
        self.guides = [{"slug": g[0], "title": g[1], "summary": g[2]} for g in guides]
        for slug, title, summary, tpl in guides:
            ld = [{"@context": "https://schema.org", "@type": "Article", "headline": title, "description": summary,
                   "dateModified": TODAY.isoformat(), "author": {"@type": "Organization", "name": SITE_NAME},
                   "publisher": {"@type": "Organization", "name": SITE_NAME}, "mainEntityOfPage": f"{SITE_URL}/guide/{slug}/"}]
            self.render(tpl, f"/guide/{slug}/", title, summary,
                        crumbs=[("/", "Home"), ("/guide/", "Guides"), (f"/guide/{slug}/", title)], jsonld=ld, priority=0.7,
                        g={"slug": slug, "title": title, "summary": summary}, by=by, balanced=balanced, tiers=tiers,
                        edc=edc, carbon=carbon, stainless=stainless, avg=avg, steels=self.steels, knives=self.knives,
                        guides=self.guides)
            self.search.append({"t": title, "u": f"/guide/{slug}/", "d": "Guide"})
        self.render("guide_index.html", "/guide/", "Knife Steel Guides",
                    "Guides to choosing a knife steel: rankings by property, steel types, carbon vs stainless and the best steels for EDC.",
                    crumbs=[("/", "Home"), ("/guide/", "Guides")], priority=0.6, guides=self.guides)

    def static_pages(self):
        for slug, title, desc in (
                ("about", "About SteelChart", "About SteelChart: where the knife steel data comes from, how the 1-10 ratings work and how to report an error."),
                ("privacy", "Privacy Policy", "SteelChart privacy policy: what data is collected, cookies, advertising and analytics."),
                ("terms", "Terms of Use", "SteelChart terms of use: information only, no warranty, trademarks and affiliate links."),
                ("affiliate-disclosure", "Affiliate Disclosure", "SteelChart affiliate disclosure: how buy links work and how they affect (and do not affect) our data.")):
            self.render(f"page_{slug.replace('-', '_')}.html", f"/{slug}/", f"{title} | {SITE_NAME}" if len(title) < 45 and SITE_NAME not in title else title,
                        desc, crumbs=[("/", "Home"), (f"/{slug}/", title)], priority=0.3, heading=title,
                        updated=TODAY.isoformat(), steel_count=len(self.steels))
        self.render("404.html", "/404.html", f"Page Not Found | {SITE_NAME}", "Page not found.",
                    crumbs=[("/", "Home"), ("/404.html", "Page not found")])

    def finish(self):
        sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        sm += [f"  <url><loc>{SITE_URL}{u}</loc><lastmod>{TODAY.isoformat()}</lastmod><priority>{p:.1f}</priority></url>"
               for u, p in sorted(self.urls)]
        sm.append("</urlset>")
        write(DOCS / "sitemap.xml", "\n".join(sm) + "\n")
        write(DOCS / "robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")
        write(DOCS / "ads.txt", f"google.com, {ADSENSE_PUB.replace('ca-', '')}, DIRECT, f08c47fec0942fa0\n")
        write(DOCS / "search-index.json", json.dumps(self.search, separators=(",", ":"), ensure_ascii=False))
        write(DOCS / "CNAME", DOMAIN + "\n")
        write(DOCS / "disavow.txt", f"# Disavow file for {DOMAIN}\n# Upload via Google Search Console > Disavow links tool.\n"
                                    "# One entry per line: domain:example.com or a full URL. Lines starting with # are comments.\n")
        write(DOCS / ".nojekyll", "")
        shutil.copytree(ROOT / "static", DOCS / "static")
        fav = ROOT / "favicon"
        if fav.exists():
            for f in fav.iterdir():
                shutil.copy2(f, DOCS / f.name)


def redirect_stub(target: str, label: str) -> str:
    url = SITE_URL + target
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>{label}</title>'
            f'<link rel="canonical" href="{url}"><meta name="robots" content="noindex">'
            f'<meta http-equiv="refresh" content="0; url={target}"></head>'
            f'<body><p>Moved to <a href="{target}">{label}</a>.</p></body></html>\n')


def main() -> int:
    if DOCS.exists():
        shutil.rmtree(DOCS)
    DOCS.mkdir()
    site = Site()
    site.home()
    site.chart()
    site.steel_pages()
    site.compare_pages()
    site.knife_pages()
    site.brand_pages()
    site.category_pages()
    site.guide_pages()
    site.static_pages()
    site.finish()
    print(f"built {len(site.urls)} pages into docs/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

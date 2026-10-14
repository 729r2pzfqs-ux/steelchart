"""Build the Phase 0 data files in data/ from the compiled source datasets in data/source/.

    python tools/build_data.py

Sources (data/source/, compiled 2026-10-14 for the site plan):
  knife_steels_database.json  128 steels: composition (wt%), HRC range, 1-10 ratings, aliases, equivalence groups
  knives.json                 76 knife models: specs, steel, prices
  knives_added.json           knives added after Phase 0 so every steel has knives; each record was checked
                              against the maker's page (or a dealer listing) and carries its verified_url

Phase 0 scope (from the site plan): the 30 most-searched steels, the 20 most popular knives, the top
comparison pairs by US search volume. Knife specs are then overridden with values verified against the
manufacturer's product page (KNIFE_VERIFIED below), each with the URL it was checked against.

Writes data/steels.json, knives.json, comparisons.json, brands.json, categories.json, equivalents.json.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "source"
OUT = ROOT / "data"

# source steel name -> site slug (the plan's 30 Phase 0 steels)
STEELS = {
    "CPM MagnaCut": "magnacut", "D2": "d2", "CPM S30V": "s30v", "CPM S35VN": "s35vn", "CPM S45VN": "s45vn",
    "M390": "m390", "CPM 20CV": "20cv", "14C28N": "14c28n", "VG-10": "vg-10", "8Cr13MoV": "8cr13mov",
    "1095": "1095", "440C": "440c", "154CM": "154cm", "Nitro-V": "nitro-v", "Elmax": "elmax",
    "CPM S90V": "s90v", "CPM CruWear": "cruwear", "CPM 3V": "3v", "AEB-L": "aeb-l", "80CrV2": "80crv2",
    "AUS-8": "aus-8", "N690": "n690", "CTS-XHP": "cts-xhp", "CPM M4": "m4", "LC200N": "lc200n",
    "420HC": "420hc", "ZDP-189": "zdp-189", "HAP40": "hap40", "SG2 / R2": "sg2", "Shirogami #2": "shirogami-2",
}
# short display names used in titles and comparisons
SHORT = {"CPM MagnaCut": "MagnaCut", "CPM S30V": "S30V", "CPM S35VN": "S35VN", "CPM S45VN": "S45VN",
         "CPM 20CV": "20CV", "CPM S90V": "S90V", "CPM CruWear": "CruWear", "CPM 3V": "CPM 3V", "CPM M4": "CPM M4",
         "SG2 / R2": "SG2 (R2)"}
# US monthly search volume for "<steel> steel" (site plan, Ahrefs); None = not in the plan's top list
STEEL_VOLUME = {"d2": 4900, "8cr13mov": 3500, "magnacut": 3100, "14c28n": 2800, "m390": 2400, "1095": 2000,
                "nitro-v": 1900, "s30v": 1800, "vg-10": 1500, "s35vn": 1400, "154cm": 1300, "440c": 1300,
                "80crv2": 1200, "420hc": 1100, "elmax": 1100}

# (source id, slug) for the 20 Phase 0 knives: the plan's 10 named models + 10 popular models whose steel is in scope.
# The Manix 2 was dropped: Spyderco now makes it in MagnaMax, which is not one of the 30 Phase 0 steels.
KNIVES = [(1, "spyderco-para-3"), (3, "spyderco-paramilitary-2"), (13, "benchmade-bugout"), (17, "benchmade-940-osborne"),
          (33, "civivi-elementum"), (56, "qsp-penguin"), (27, "kershaw-leek"), (48, "zero-tolerance-0562cf"),
          (69, "chris-reeve-large-sebenza-31"), (58, "hogue-deka"),
          (4, "spyderco-delica-4"), (5, "spyderco-endura-4"), (10, "spyderco-tenacious"), (15, "benchmade-griptilian"),
          (18, "benchmade-bailout"), (20, "benchmade-adamas"), (28, "kershaw-blur"), (29, "kershaw-link"),
          (50, "zero-tolerance-0450cf"), (42, "buck-110-folding-hunter")]
KNIFE_STEEL = {"CPM S45VN": "s45vn", "CPM S30V": "s30v", "CPM S35VN": "s35vn", "VG-10": "vg-10", "8Cr13MoV": "8cr13mov",
               "CPM 3V": "3v", "CPM CruWear": "cruwear", "D2": "d2", "14C28N": "14c28n", "CPM 20CV": "20cv",
               "CPM MagnaCut": "magnacut", "420HC": "420hc", "CPM M4": "m4"}
KNIFE_FIELDS = ("id", "brand", "model", "steel_id", "blade_length_in", "overall_length_in", "blade_thickness_in", "weight_oz",
                "lock_type", "handle_material", "blade_shape", "msrp_usd", "category", "opening_mechanism",
                "country_of_origin", "notes", "verified_url")
# Overrides from manufacturer pages (filled from the verification pass): slug -> {field: value, "verified_url": ...}
KNIFE_VERIFIED: dict[str, dict] = {
    # Checked 2026-10-14 against the maker's product page (Buck and Hogue block automated access, so their values
    # come from KnifeCenter's listing). msrp_usd = the maker's list price. Fields a page does not list keep the
    # compiled-dataset value.
    "spyderco-para-3": {"blade_length_in": 2.93, "overall_length_in": 7.2, "blade_thickness_in": 0.145, "weight_oz": 3.4,
                        "msrp_usd": 263, "verified_url": "https://www.spyderco.com/products/c223g-para%C2%AE-3"},
    "spyderco-paramilitary-2": {"blade_length_in": 3.45, "overall_length_in": 8.26, "blade_thickness_in": 0.145,
                                "weight_oz": 3.8, "msrp_usd": 279, "verified_url": "https://www.spyderco.com/products/para-military%C2%AE-2"},
    "spyderco-delica-4": {"model": "Delica 4 Lightweight (C11FPBK)", "blade_length_in": 2.9, "overall_length_in": 7.11,
                          "blade_thickness_in": 0.098, "weight_oz": 2.4, "lock_type": "Back lock", "handle_material": "FRN",
                          "msrp_usd": 132, "verified_url": "https://www.spyderco.com/products/c11flt-delica%C2%AE-4-lightweight-flat-ground"},
    "spyderco-endura-4": {"model": "Endura 4 Lightweight (C10FPBK)", "steel": "VG-10", "blade_length_in": 3.8,
                          "overall_length_in": 8.7, "blade_thickness_in": 0.118, "weight_oz": 3.3, "lock_type": "Back lock",
                          "handle_material": "FRN", "country_of_origin": "Japan", "msrp_usd": 143,
                          "verified_url": "https://www.spyderco.com/products/c10flt-endura%C2%AE-4-lightweight-flat-ground"},
    "spyderco-tenacious": {"blade_length_in": 3.39, "overall_length_in": 7.77, "blade_thickness_in": 0.118, "weight_oz": 4.2,
                           "lock_type": "Liner lock", "handle_material": "G-10", "msrp_usd": 91,
                           "verified_url": "https://www.spyderco.com/products/c122g-tenacious%C2%AE"},
    "benchmade-bugout": {"model": "Bugout 535", "blade_length_in": 3.24, "overall_length_in": 7.46, "blade_thickness_in": 0.09,
                         "weight_oz": 1.85, "lock_type": "AXIS lock", "handle_material": "Grivory", "blade_shape": "Drop point",
                         "msrp_usd": 200, "verified_url": "https://www.benchmade.com/products/535"},
    "benchmade-940-osborne": {"blade_length_in": 3.4, "overall_length_in": 7.87, "blade_thickness_in": 0.115, "weight_oz": 2.9,
                              "lock_type": "AXIS lock", "handle_material": "6061-T6 aluminum", "blade_shape": "Reverse tanto",
                              "msrp_usd": 300, "verified_url": "https://www.benchmade.com/products/940"},
    "benchmade-griptilian": {"model": "Griptilian 551-S30V", "blade_length_in": 3.45, "overall_length_in": 8.07,
                             "blade_thickness_in": 0.115, "weight_oz": 3.88, "lock_type": "AXIS lock", "handle_material": "Nylon",
                             "blade_shape": "Drop point", "msrp_usd": 175, "verified_url": "https://www.benchmade.com/products/551-s30v"},
    "benchmade-bailout": {"model": "Bailout 537GY-1", "steel": "CPM M4", "blade_length_in": 3.38, "overall_length_in": 8.09,
                          "blade_thickness_in": 0.09, "weight_oz": 2.7, "lock_type": "AXIS lock", "handle_material": "6061-T6 aluminum",
                          "blade_shape": "Tanto", "msrp_usd": 350, "notes": "Earlier versions used CPM 3V.",
                          "verified_url": "https://www.benchmade.com/products/537gy-1-bailout"},
    "benchmade-adamas": {"model": "Adamas 275GY-03", "steel": "CPM MagnaCut", "blade_length_in": 3.82, "overall_length_in": 8.93,
                         "blade_thickness_in": 0.14, "weight_oz": 6.54, "lock_type": "AXIS lock", "handle_material": "G10",
                         "blade_shape": "Drop point", "msrp_usd": 325, "notes": "Earlier Adamas versions used D2 and later CPM CruWear; all current versions are MagnaCut.",
                         "verified_url": "https://www.benchmade.com/products/275gy-03"},
    "civivi-elementum": {"model": "Elementum C907A", "blade_length_in": 2.96, "overall_length_in": 6.99, "blade_thickness_in": 0.12,
                         "weight_oz": 2.89, "lock_type": "Liner lock", "handle_material": "G10", "msrp_usd": 59,
                         "verified_url": "https://civivi.com/products/civivi-elementum-c907a"},
    "qsp-penguin": {"model": "Penguin QS130", "steel": "D2", "blade_length_in": 3.06, "overall_length_in": 7.06,
                    "blade_thickness_in": 0.118, "weight_oz": 3.14, "lock_type": "Liner lock", "handle_material": "Micarta or G10",
                    "blade_shape": "Sheepsfoot", "msrp_usd": None,
                    "notes": "All QS130 versions are D2; QSP's 14C28N Penguins are the Mini, Button Lock and Slip Joint models. Weight is for the Micarta version (G10: 3.53 oz).",
                    "verified_url": "https://qspknife.com/products/qsp-penguin-liner-lock-pocket-knife-d2-blade-micarta-handle"},
    "kershaw-leek": {"blade_length_in": 3.0, "overall_length_in": 7.0, "blade_thickness_in": 0.09, "weight_oz": 3.0,
                     "lock_type": "Frame lock", "handle_material": "410 stainless steel", "blade_shape": "Drop point",
                     "msrp_usd": 124.99, "verified_url": "https://kershaw.kaiusa.com/leek.html"},
    "kershaw-blur": {"blade_length_in": 3.4, "overall_length_in": 7.9, "blade_thickness_in": 0.121, "weight_oz": 3.9,
                     "lock_type": "Liner lock", "handle_material": "6061-T6 aluminum with Trac-Tec inserts", "blade_shape": "Recurve",
                     "msrp_usd": 159.99, "verified_url": "https://kershaw.kaiusa.com/blur-black.html"},
    "kershaw-link": {"model": "Link 1776OLSW", "steel": "CPM MagnaCut", "blade_length_in": 3.25, "overall_length_in": 7.6,
                     "blade_thickness_in": 0.106, "weight_oz": 4.7, "lock_type": "Liner lock", "handle_material": "6061-T6 aluminum",
                     "blade_shape": "Drop point", "msrp_usd": 209.99,
                     "notes": "Older Links used 420HC and then CPM 20CV; current production is CPM MagnaCut.",
                     "verified_url": "https://kershaw.kaiusa.com/link-olive-stonewashed.html"},
    "zero-tolerance-0562cf": {"steel": "CPM MagnaCut", "blade_length_in": 3.5, "overall_length_in": 8.3, "blade_thickness_in": 0.156,
                              "weight_oz": 5.5, "lock_type": "Titanium frame lock", "handle_material": "Carbon fiber front, titanium back",
                              "blade_shape": "Drop point", "msrp_usd": 375, "notes": "Older 0562CFs used CPM 20CV; current production is CPM MagnaCut.",
                              "verified_url": "https://zt.kaiusa.com/0562cf.html"},
    "zero-tolerance-0450cf": {"blade_length_in": 3.25, "overall_length_in": 7.4, "blade_thickness_in": 0.121, "weight_oz": 2.45,
                              "lock_type": "Titanium frame lock", "handle_material": "Carbon fiber front, titanium back",
                              "blade_shape": "Drop point", "msrp_usd": 295, "verified_url": "https://zt.kaiusa.com/0450cf.html"},
    "chris-reeve-large-sebenza-31": {"blade_length_in": 3.61, "overall_length_in": 8.40, "blade_thickness_in": 0.12, "weight_oz": 4.7,
                                     "lock_type": "Reeve Integral Lock", "handle_material": "6Al4V titanium", "blade_shape": "Drop point",
                                     "msrp_usd": 500, "notes": "Chris Reeve Knives may ship CPM S45VN instead of MagnaCut depending on steel availability.",
                                     "verified_url": "https://chrisreeve.com/products/sebenza-31-plain"},
    "hogue-deka": {"blade_length_in": 3.25, "overall_length_in": 7.5, "blade_thickness_in": 0.094, "weight_oz": 2.1,
                   "lock_type": "ABLE Lock", "handle_material": "Polymer", "blade_shape": "Clip point", "msrp_usd": 184.95,
                   "verified_url": "https://www.knifecenter.com/item/HO24376"},
    "buck-110-folding-hunter": {"blade_length_in": 3.75, "overall_length_in": 8.625, "blade_thickness_in": 0.12, "weight_oz": 7.2,
                                "lock_type": "Lockback", "handle_material": "Ebony wood", "msrp_usd": 120,
                                "verified_url": "https://www.knifecenter.com/item/BU110"},
}

# Comparison pairs from the site plan with US monthly search volume (None = listed in the 60-199/mo band)
PAIRS = [
    ("14c28n", "d2", 1170), ("m390", "magnacut", 1000), ("s30v", "magnacut", 960), ("elmax", "magnacut", 800),
    ("s90v", "magnacut", 760), ("20cv", "magnacut", 680), ("440c", "d2", 660), ("cruwear", "magnacut", 610),
    ("s35vn", "magnacut", 530), ("nitro-v", "d2", 520), ("s30v", "s90v", 500),
    ("8cr13mov", "d2", 470), ("m390", "s90v", 450), ("3v", "magnacut", 420), ("154cm", "d2", 360),
    ("s30v", "s35vn", 350), ("d2", "s30v", 350), ("vg-10", "d2", 330), ("aus-8", "d2", 320), ("s30v", "s45vn", 300),
    ("154cm", "14c28n", 300), ("elmax", "m390", 290), ("154cm", "s35vn", 270), ("m390", "s30v", 270),
    ("154cm", "s30v", 260), ("sg2", "vg-10", 250), ("s35vn", "s45vn", 240), ("1095", "d2", 240),
    ("m4", "magnacut", 210), ("cruwear", "s30v", 210), ("20cv", "s30v", 250),
    ("m390", "s35vn", None), ("nitro-v", "s35vn", None), ("s35vn", "d2", None), ("80crv2", "1095", None),
    ("8cr13mov", "14c28n", None), ("14c28n", "s35vn", None), ("20cv", "s35vn", None), ("vg-10", "s30v", None),
    ("n690", "m390", None),
]
# Ten more pairs between in-scope steels with obvious buyer overlap (no volume data; same class or same price tier)
EXTRA_PAIRS = [("20cv", "m390"), ("s45vn", "magnacut"), ("14c28n", "aeb-l"), ("14c28n", "nitro-v"),
               ("sg2", "zdp-189"), ("8cr13mov", "aus-8"), ("lc200n", "magnacut"),
               ("elmax", "s35vn"), ("cts-xhp", "s30v"), ("hap40", "m4")]

CATEGORIES = {
    "stainless": ("Stainless steels", "Conventional (ingot) stainless steels with enough free chromium, roughly 12% or more, to resist rust in everyday use."),
    "stainless-pm": ("Powder metallurgy stainless steels", "Stainless steels made by powder metallurgy, which keeps carbides small and evenly spread so high-alloy steels stay tough enough for knives."),
    "tool": ("Tool steels", "Ingot tool steels designed for dies and cutting tools; high wear resistance, limited corrosion resistance."),
    "tool-pm": ("Powder metallurgy tool steels", "Powder metallurgy tool steels that combine high toughness with wear resistance, with little corrosion resistance."),
    "high-speed-pm": ("High-speed powder steels", "Powder metallurgy high-speed steels with tungsten, molybdenum and vanadium; very high hardness and edge retention, low corrosion resistance."),
    "carbon": ("Carbon steels", "Simple carbon and low-alloy steels: easy to sharpen and often tough, but they rust and patina without care."),
}
BRANDS = {
    "Spyderco": ("spyderco", "USA", "Golden, Colorado knife maker known for the round thumb hole, leaf-shaped blades and the Compression Lock."),
    "Benchmade": ("benchmade", "USA", "Oregon knife maker best known for the AXIS lock and the Bugout and Griptilian lines."),
    "Civivi": ("civivi", "China", "Budget-to-midrange brand from WE Knife, known for value folders such as the Elementum."),
    "QSP": ("qsp", "China", "Value-focused Chinese brand; the Penguin is its best-known design."),
    "Kershaw": ("kershaw", "USA", "Oregon brand of KAI USA making assisted-opening and budget-to-midrange folders."),
    "Zero Tolerance": ("zero-tolerance", "USA", "KAI USA's premium brand of hard-use folders, made in Oregon."),
    "Chris Reeve Knives": ("chris-reeve-knives", "USA", "Boise, Idaho maker of the Sebenza, the integral-lock titanium folder."),
    "Hogue": ("hogue", "USA", "California grips maker whose knife line includes the Deka with the ABLE Lock."),
    "Buck": ("buck", "USA", "Idaho maker of the Buck 110 Folding Hunter, made since 1963."),
    # brands of the knives in data/source/knives_added.json
    "Microtech": ("microtech", "USA", "North Carolina maker best known for its Ultratech and UTX out-the-front automatics, now built with Böhler M390MK blades."),
    "WE Knife": ("we-knife", "China", "Yangjiang-based premium brand (parent of Civivi) producing titanium-handled folders in M390 and CPM 20CV."),
    "Demko": ("demko", "USA", "Andrew Demko's Pennsylvania company, maker of the Shark Lock AD20.5 series, with production knives manufactured in Taiwan."),
    "Fällkniven": ("fallkniven", "Sweden", "Boden-based Swedish company whose F1 pilot survival knife has been issued to the Swedish Air Force since 1995."),
    "Pro-Tech": ("pro-tech", "USA", "Santa Fe Springs, California maker of American-made automatic knives such as the Godfather, Malibu and TR-series."),
    "Cold Steel": ("cold-steel", "USA", "Ventura, California-based maker of hard-use fixed blades, folders and swords, known for the Tri-Ad lock and the SRK and Trail Master lines."),
    "Böker": ("boker", "Germany", "Solingen cutlery house founded in 1869 whose Böker Germany line is made in Solingen; Böker Plus and Magnum are imported sub-brands."),
    "Böker Plus": ("boker-plus", "Germany", "Böker's value line, designed in Solingen and produced outside Germany (mostly Asia), covering designer-collaboration folders and fixed blades."),
    "Fox Knives": ("fox-knives", "Italy", "Maniago-based cutler (Oreste Frati S.r.l.) known for Italian-made folders, karambits and tactical knives, many in Böhler N690Co."),
    "Rockstead": ("rockstead", "Japan", "Sakai, Osaka maker of mirror-polished, convex-ground high-end folders built around ZDP-189 and other Japanese super steels."),
    "ESEE": ("esee", "USA", "Idaho-based maker of 1095 carbon steel survival and bushcraft fixed blades backed by an unconditional lifetime warranty."),
    "Ontario Knife Company": ("ontario-knife-company", "USA", "Long-running US knife maker (RAT folders, Air Force Survival Knife) whose RAT series is produced in Taiwan."),
    "SOG": ("sog", "USA", "Oregon-based brand founded in 1986 around the SEAL and SEAL Pup fixed blades, now making folders, fixed blades and multi-tools."),
    "CRKT": ("crkt", "USA", "Columbia River Knife & Tool, an Oregon company producing designer-collaboration folders and fixed blades, mostly made in Taiwan and China."),
    "Bradford Knives": ("bradford-knives", "USA", "Small US maker best known for the Guardian series of compact fixed blades offered in a range of steels."),
    "Winkler Knives": ("winkler-knives", "USA", "Boone, North Carolina shop founded by bladesmith Daniel Winkler, making 80CrV2 fixed blades for military and outdoor use."),
    "Shun": ("shun", "Japan", "Kai's premium kitchen knife brand, handcrafted in Seki City with VG-MAX, SG2 and Dual Core blades."),
    "Miyabi": ("miyabi", "Japan", "Zwilling's Seki-made Japanese kitchen knife brand, built around SG2 (MC63) and FC61 powder-steel cores."),
    "Sukenari": ("sukenari", "Japan", "Toyama Prefecture kitchen knife maker known for working with hard powder steels such as HAP40 and ZDP-189."),
    "Hatsukokoro": ("hatsukokoro", "Japan", "Japanese kitchen knife brand that commissions blades from workshops in Seki, Tosa and Sanjo in a range of carbon and high-speed steels."),
    "Yoshikane": ("yoshikane", "Japan", "Sanjo City hammon workshop known for thin, hammer-forged stainless-clad White #2 and SKD gyutos."),
    "Masamoto": ("masamoto", "Japan", "Tokyo knife maker founded in the 1800s whose KS-series White #2 gyuto is a benchmark among professional chefs."),
    "Sakai Takayuki": ("sakai-takayuki", "Japan", "Sakai, Osaka cutlery house (Aoki Hamono) producing hand-forged traditional and modern kitchen knives."),
}


def main() -> None:
    src = json.loads((SRC / "knife_steels_database.json").read_text())
    by_name = {s["name"]: s for s in src["steels"]}
    slug_of = dict(STEELS)
    steels = []
    for name, slug in STEELS.items():
        s = by_name[name]
        steels.append({
            "id": slug, "name": name, "short": SHORT.get(name, name), "aliases": s.get("aliases", []),
            "manufacturer": s.get("manufacturer"), "country": s.get("country"), "category": s["category"],
            "process": s.get("process"), "composition": s["composition"],
            "composition_confidence": s.get("composition_confidence"),
            "hrc_min": s["hrc_min"], "hrc_max": s["hrc_max"], "hardness_note": s.get("hardness_note"),
            "ratings": s["ratings"], "brands": s.get("brands", []), "price_tier": s.get("price_tier"),
            "notes": s.get("notes"), "search_volume": STEEL_VOLUME.get(slug),
        })
    (OUT / "steels.json").write_text(json.dumps(steels, indent=1, ensure_ascii=False) + "\n")

    groups = []
    for g in src["equivalence_groups"]:
        members = [m for m in g["members"]]
        in_scope = [slug_of[m] for m in members if m in slug_of]
        if in_scope:
            groups.append({"group": g["group"], "members": members, "in_scope": in_scope,
                           "confidence": "identical" if g["group"] == "M390 class" else "similar"})
    (OUT / "equivalents.json").write_text(json.dumps(groups, indent=1, ensure_ascii=False) + "\n")

    ksrc = {k["id"]: k for k in json.loads((SRC / "knives.json").read_text())["knives"]}
    knives = []
    for sid, slug in KNIVES:
        k = dict(ksrc[sid])
        rec = {"id": slug, "brand": k["brand"], "model": k["model"], "steel_id": KNIFE_STEEL[k["steel"]],
               "blade_length_in": k.get("blade_length_in"), "overall_length_in": k.get("overall_length_in"),
               "blade_thickness_in": k.get("blade_thickness_in"), "weight_oz": k.get("weight_oz"),
               "lock_type": k.get("lock_type"), "handle_material": k.get("handle_material"),
               "blade_shape": k.get("blade_shape"), "msrp_usd": k.get("msrp_usd"),
               "street_price_usd": k.get("street_price_usd"), "category": k.get("category"),
               "opening_mechanism": k.get("opening_mechanism"), "country_of_origin": k.get("country_of_origin"),
               "notes": k.get("notes"), "verified_url": None}
        over = dict(KNIFE_VERIFIED.get(slug, {}))
        if "steel" in over:
            rec["steel_id"] = KNIFE_STEEL[over.pop("steel")]
        rec.update(over)
        rec.pop("street_price_usd")  # compiled estimate, not verifiable; the site shows the maker's list price
        assert rec["steel_id"] in slug_of.values(), (slug, rec["steel_id"])
        knives.append(rec)
    # knives added after Phase 0 (one JSON record per knife, already in the output format, all verified)
    added = json.loads((SRC / "knives_added.json").read_text())
    for k in added["knives"]:
        rec = {f: k.get(f) for f in KNIFE_FIELDS}
        assert rec["steel_id"] in slug_of.values(), (rec["id"], rec["steel_id"])
        assert rec["verified_url"] and rec["id"] not in {x["id"] for x in knives}, rec["id"]
        knives.append(rec)
    (OUT / "knives.json").write_text(json.dumps(knives, indent=1, ensure_ascii=False) + "\n")

    comps, seen = [], set()
    for a, b, vol in PAIRS + [(a, b, "extra") for a, b in EXTRA_PAIRS]:
        a, b = sorted((a, b))
        if (a, b) in seen:
            continue
        seen.add((a, b))
        comps.append({"id": f"{a}-vs-{b}", "steel_a": a, "steel_b": b,
                      "search_volume": vol if isinstance(vol, int) else None,
                      "priority": "high" if isinstance(vol, int) and vol >= 500 else
                                  "medium" if isinstance(vol, int) else "low" if vol is None else "related"})
    assert len(comps) == 50, len(comps)
    (OUT / "comparisons.json").write_text(json.dumps(comps, indent=1) + "\n")

    used = {k["brand"] for k in knives}
    assert used <= set(BRANDS), used - set(BRANDS)
    brands = [{"id": v[0], "name": n, "country": v[1], "description": v[2]} for n, v in BRANDS.items() if n in used]
    (OUT / "brands.json").write_text(json.dumps(brands, indent=1) + "\n")
    cats = [{"id": c, "name": v[0], "description": v[1]} for c, v in CATEGORIES.items()
            if any(s["category"] == c for s in steels)]
    (OUT / "categories.json").write_text(json.dumps(cats, indent=1) + "\n")
    print(f"steels {len(steels)}, knives {len(knives)}, comparisons {len(comps)}, brands {len(brands)}, "
          f"categories {len(cats)}, equivalence groups {len(groups)}")


if __name__ == "__main__":
    main()

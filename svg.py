"""Inline SVG diagrams for steelchart.org. Every function returns a Markup string.

Colours come from CSS custom properties (--c-a, --c-b, --grid, --fg, --muted) so charts follow
light/dark mode. All charts use viewBox + width 100% and carry <title>/<desc> for accessibility.
"""
from __future__ import annotations

import math
from html import escape

from markupsafe import Markup

AXES = [("edge_retention", "Edge retention"), ("toughness", "Toughness"),
        ("corrosion_resistance", "Corrosion resistance"), ("ease_of_sharpening", "Ease of sharpening")]
SHORT_AXES = {"edge_retention": "Edge", "toughness": "Toughness", "corrosion_resistance": "Corrosion",
              "ease_of_sharpening": "Sharpening"}
ELEMENT_ORDER = ["C", "Cr", "V", "Mo", "W", "Co", "Nb", "N", "Ni", "Mn", "Si", "Cu", "P", "S"]
ELEMENT_NAMES = {"C": "Carbon", "Cr": "Chromium", "V": "Vanadium", "Mo": "Molybdenum", "W": "Tungsten",
                 "Co": "Cobalt", "Nb": "Niobium", "N": "Nitrogen", "Ni": "Nickel", "Mn": "Manganese",
                 "Si": "Silicon", "Cu": "Copper", "P": "Phosphorus", "S": "Sulfur"}


def _f(x: float) -> str:
    return f"{x:.1f}".rstrip("0").rstrip(".")


def _v(x: float) -> str:
    """A composition value as printed in the data (up to 3 decimals)."""
    return f"{x:.3f}".rstrip("0").rstrip(".")


def radar(sets: list[tuple[str, dict, str]], title: str) -> Markup:
    """sets: [(label, ratings, css colour var)], 1 or 2 entries. 4 axes on a 1-10 scale."""
    cx, cy, r = 200, 185, 115
    n = len(AXES)
    pt = lambda i, v: (cx + r * v / 10 * math.sin(2 * math.pi * i / n), cy - r * v / 10 * math.cos(2 * math.pi * i / n))
    out = [f'<svg viewBox="-60 0 520 {410 if len(sets) > 1 else 375}" width="100%" role="img" aria-labelledby="rt rd" class="chart radar">',
           f'<title id="rt">{escape(title)}</title>',
           '<desc id="rd">' + escape("; ".join(f"{lab}: " + ", ".join(f"{name} {rt[k]}/10" for k, name in AXES)
                                               for lab, rt, _ in sets)) + "</desc>"]
    for ring in (2, 4, 6, 8, 10):
        pts = " ".join(f"{_f(x)},{_f(y)}" for x, y in (pt(i, ring) for i in range(n)))
        out.append(f'<polygon points="{pts}" fill="none" stroke="var(--grid)" stroke-width="1"/>')
    for i, (key, name) in enumerate(AXES):
        x, y = pt(i, 10)
        out.append(f'<line x1="{cx}" y1="{cy}" x2="{_f(x)}" y2="{_f(y)}" stroke="var(--grid)" stroke-width="1"/>')
        # label block: name (wrapped to two lines on the side axes when long) then the values
        vals = " / ".join(str(rt[key]) for _, rt, _ in sets)
        words = name.split(" ")
        lines = [" ".join(words[:-1]), words[-1]] if i % 2 and len(words) > 1 else [name]
        if i == 0:
            lx, anchor, y0 = cx, "middle", cy - r - 36
        elif i == 2:
            lx, anchor, y0 = cx, "middle", cy + r + 32
        else:
            lx, anchor = (cx + r + 14, "start") if i == 1 else (cx - r - 14, "end")
            y0 = cy - 12 * len(lines)
        for j, ln in enumerate(lines):
            out.append(f'<text x="{_f(lx)}" y="{_f(y0 + 23 * j)}" text-anchor="{anchor}" class="ax">{ln}</text>')
        out.append(f'<text x="{_f(lx)}" y="{_f(y0 + 23 * len(lines))}" text-anchor="{anchor}" class="axv">{vals}</text>')
    for lab, rt, col in sets:
        pts = " ".join(f"{_f(x)},{_f(y)}" for x, y in (pt(i, rt[k]) for i, (k, _) in enumerate(AXES)))
        out.append(f'<polygon points="{pts}" fill="var({col})" fill-opacity="0.28" stroke="var({col})" stroke-width="2.5"/>')
        for i, (k, _) in enumerate(AXES):
            x, y = pt(i, rt[k])
            out.append(f'<circle cx="{_f(x)}" cy="{_f(y)}" r="3.5" fill="var({col})"/>')
    if len(sets) > 1:
        lx = 200 - 100 * (len(sets) - 1)
        for j, (lab, _, col) in enumerate(sets):
            x = lx + j * 200
            out.append(f'<rect x="{x - 80}" y="383" width="18" height="18" rx="3" fill="var({col})"/>'
                       f'<text x="{x - 54}" y="399" class="lg">{escape(lab)}</text>')
    out.append("</svg>")
    return Markup("".join(out))


def composition(sets: list[tuple[str, dict, str]], title: str) -> Markup:
    """Horizontal bars per element (wt%). With two sets, grouped bars per element."""
    keys = [e for e in ELEMENT_ORDER if any((c.get(e) or 0) > 0 for _, c, _ in sets)]
    vmax = max((c.get(e) or 0) for _, c, _ in sets for e in keys)
    scale_max = 5 if vmax <= 5 else 10 if vmax <= 10 else 15 if vmax <= 15 else 25
    bar_h = 14 if len(sets) == 1 else 11
    row_h = bar_h * len(sets) + 12
    left, width = 128, 214
    h = 30 + row_h * len(keys) + (26 if len(sets) > 1 else 6)
    desc = "; ".join(f"{lab}: " + ", ".join(f"{e} {c[e]}%" for e in keys if c.get(e)) for lab, c, _ in sets)
    out = [f'<svg viewBox="0 0 400 {h}" width="100%" role="img" aria-labelledby="ct cd" class="chart comp">',
           f'<title id="ct">{escape(title)}</title><desc id="cd">{escape(desc)}</desc>']
    for t in range(0, scale_max + 1, 5 if scale_max > 10 else (1 if scale_max <= 5 else 2)):
        x = left + width * t / scale_max
        out.append(f'<line x1="{_f(x)}" y1="18" x2="{_f(x)}" y2="{h - (26 if len(sets) > 1 else 6)}" stroke="var(--grid)"/>'
                   f'<text x="{_f(x)}" y="13" text-anchor="middle" class="tick">{t}%</text>')
    for i, e in enumerate(keys):
        y0 = 26 + i * row_h
        out.append(f'<text x="{left - 8}" y="{y0 + bar_h * len(sets) / 2 + 4}" text-anchor="end" class="el">'
                   f'{ELEMENT_NAMES[e]} ({e})</text>')
        for j, (lab, c, col) in enumerate(sets):
            v = c.get(e) or 0
            y = y0 + j * bar_h
            w = max(width * v / scale_max, 0 if v == 0 else 1.5)
            out.append(f'<rect x="{left}" y="{y}" width="{_f(w)}" height="{bar_h - 2}" rx="2" fill="var({col})"/>')
            out.append(f'<text x="{_f(left + w + 5)}" y="{y + bar_h - 4}" class="val">{_v(v) if v else "–"}</text>')
    if len(sets) > 1:
        for j, (lab, _, col) in enumerate(sets):
            x = left + j * 150
            out.append(f'<rect x="{x}" y="{h - 18}" width="12" height="12" rx="2" fill="var({col})"/>'
                       f'<text x="{x + 17}" y="{h - 8}" class="lg">{escape(lab)}</text>')
    out.append("</svg>")
    return Markup("".join(out))


def hrc_gauge(sets: list[tuple[str, int, int, str]], title: str) -> Markup:
    """HRC range bars on a 50-70 scale with reference marks at 55/60/65."""
    left, width = 16, 368
    x = lambda v: left + width * (v - 50) / 20
    h = 44 + 22 * len(sets)
    out = [f'<svg viewBox="0 0 400 {h}" width="100%" role="img" aria-labelledby="ht hd" class="chart hrc">',
           f'<title id="ht">{escape(title)}</title><desc id="hd">' +
           escape("; ".join(f"{lab}: {a}-{b} HRC" for lab, a, b, _ in sets)) + "</desc>",
           f'<rect x="{left}" y="20" width="{width}" height="{22 * len(sets) + 4}" rx="4" fill="var(--track)"/>']
    for v, name in ((55, "55 soft"), (60, "60 mid"), (65, "65 very hard")):
        out.append(f'<line x1="{_f(x(v))}" y1="16" x2="{_f(x(v))}" y2="{26 + 22 * len(sets)}" stroke="var(--grid)" stroke-dasharray="3 3"/>'
                   f'<text x="{_f(x(v))}" y="12" text-anchor="middle" class="tick">{name}</text>')
    for v in (50, 70):
        out.append(f'<text x="{_f(x(v))}" y="{h - 4}" text-anchor="{"start" if v == 50 else "end"}" class="tick">{v}</text>')
    for i, (lab, a, b, col) in enumerate(sets):
        y = 24 + 22 * i
        out.append(f'<rect x="{_f(x(a))}" y="{y}" width="{_f(max(x(b) - x(a), 4))}" height="16" rx="3" fill="var({col})"/>'
                   f'<text x="{_f((x(a) + x(b)) / 2)}" y="{y + 12}" text-anchor="middle" class="hv">{a}–{b}</text>')
    out.append("</svg>")
    return Markup("".join(out))


def diff_chart(a_name: str, a: dict, b_name: str, b: dict) -> Markup:
    """Diverging bars: rating difference per property; right = steel A better, left = steel B better."""
    mid, unit = 235, 16
    h = 34 + 50 * len(AXES)
    out = [f'<svg viewBox="0 0 470 {h}" width="100%" role="img" aria-labelledby="dt dd" class="chart diff">',
           f'<title id="dt">{escape(a_name)} vs {escape(b_name)}: rating differences</title>',
           '<desc id="dd">' + escape("; ".join(f"{n}: {a_name} {a[k]}, {b_name} {b[k]}" for k, n in AXES)) + "</desc>",
           f'<text x="{mid - 8}" y="18" text-anchor="end" class="tick">← {escape(b_name)} better</text>',
           f'<text x="{mid + 8}" y="18" class="tick">{escape(a_name)} better →</text>',
           f'<line x1="{mid}" y1="26" x2="{mid}" y2="{h - 4}" stroke="var(--fg)" stroke-width="1.2"/>']
    for i, (k, n) in enumerate(AXES):
        y = 34 + 50 * i
        d = a[k] - b[k]
        out.append(f'<text x="4" y="{y + 14}" class="el">{n}</text>')
        y += 20
        if d:
            w = abs(d) * unit
            xx = mid if d > 0 else mid - w
            col = "--c-a" if d > 0 else "--c-b"
            out.append(f'<rect x="{xx}" y="{y + 3}" width="{w}" height="16" rx="2" fill="var({col})"/>'
                       f'<text x="{mid + w + 6 if d > 0 else mid - w - 6}" y="{y + 15}" text-anchor="{"start" if d > 0 else "end"}" class="val">{"+" if d > 0 else "−"}{abs(d)}</text>')
        else:
            out.append(f'<text x="{mid + 6}" y="{y + 15}" class="val">tie</text>')
    out.append("</svg>")
    return Markup("".join(out))


BLADES = {  # simple blade profiles, spine on top, tip to the right, in a 300x80 box
    "drop point": "M10,30 L210,30 C250,30 280,38 292,50 C250,62 200,66 150,66 L10,66 Z",
    "clip point": "M10,30 L190,30 L240,40 L292,50 C250,63 200,66 150,66 L10,66 Z",
    "leaf": "M10,32 C120,26 220,30 292,50 C230,66 140,68 10,64 Z",
    "spear point": "M10,32 L200,32 C240,32 270,40 292,50 C270,60 240,66 200,66 L10,66 Z",
    "sheepsfoot": "M10,30 L240,30 C270,30 290,44 292,66 L10,66 Z",
    "tanto": "M10,30 L240,30 L292,48 L262,66 L10,66 Z",
    "wharncliffe": "M10,30 L170,30 L292,64 L292,66 L10,66 Z",
}


def blade(shape: str | None, length_in: float | None, label: str) -> Markup:
    s = (shape or "").lower()
    key = next((k for k in ("wharncliffe", "sheepsfoot", "tanto", "spear", "clip", "leaf", "drop") if k in s), "drop")
    key = {"spear": "spear point", "clip": "clip point", "drop": "drop point"}.get(key, key)
    path = BLADES[key]
    cap = (f"{shape} blade" if shape else "Blade") + (f', {length_in}" long' if length_in else "")
    return Markup(
        f'<svg viewBox="0 0 400 110" width="100%" role="img" aria-labelledby="bt" class="chart blade">'
        f'<title id="bt">{escape(label)}: {escape(cap)} (generic profile, not to scale)</title>'
        f'<rect x="16" y="38" width="70" height="20" rx="8" fill="var(--muted)" opacity="0.55"/>'
        f'<g transform="translate(86,0)"><path d="{path}" fill="var(--steel)" stroke="var(--fg)" stroke-width="1.5"/></g>'
        f'<line x1="96" y1="88" x2="378" y2="88" stroke="var(--muted)"/><line x1="96" y1="83" x2="96" y2="93" stroke="var(--muted)"/>'
        f'<line x1="378" y1="83" x2="378" y2="93" stroke="var(--muted)"/>'
        f'<text x="237" y="105" text-anchor="middle" class="tick">{escape(cap)}</text></svg>')


CAT_COLOURS = {"stainless": "--cat-stainless", "stainless-pm": "--cat-spm", "tool": "--cat-tool",
               "tool-pm": "--cat-tpm", "high-speed-pm": "--cat-hss", "carbon": "--cat-carbon"}


def scatter(steels: list[dict], title: str) -> Markup:
    """Edge retention (x) vs toughness (y); dot size = corrosion resistance; colour = category.

    Steels sharing a cell sit side by side, with their names stacked under the dots.
    """
    left, top, w, h = 50, 14, 530, 440
    X = lambda v: left + w * (v - 0.5) / 10
    Y = lambda v: top + h - h * (v - 0.5) / 10
    out = [f'<svg viewBox="0 0 600 520" width="100%" role="img" aria-labelledby="st sd" class="chart scatter">',
           f'<title id="st">{escape(title)}</title><desc id="sd">' +
           escape("; ".join(f"{s['short']}: edge {s['ratings']['edge_retention']}, toughness {s['ratings']['toughness']}"
                            for s in steels)) + "</desc>"]
    for v in range(1, 11):
        out.append(f'<line x1="{_f(X(v))}" y1="{top}" x2="{_f(X(v))}" y2="{top + h}" stroke="var(--grid)"/>'
                   f'<line x1="{left}" y1="{_f(Y(v))}" x2="{left + w}" y2="{_f(Y(v))}" stroke="var(--grid)"/>'
                   f'<text x="{_f(X(v))}" y="{top + h + 18}" text-anchor="middle" class="tick">{v}</text>'
                   f'<text x="{left - 8}" y="{_f(Y(v) + 4)}" text-anchor="end" class="tick">{v}</text>')
    out.append(f'<text x="{left + w / 2}" y="{top + h + 42}" text-anchor="middle" class="el">Edge retention →</text>'
               f'<text x="16" y="{top + h / 2}" text-anchor="middle" class="el" transform="rotate(-90 16 {top + h / 2})">Toughness →</text>')
    cells: dict[tuple, list] = {}
    for s in steels:
        cells.setdefault((s["ratings"]["edge_retention"], s["ratings"]["toughness"]), []).append(s)
    for (e, t), group in cells.items():
        cx, cy = X(e), Y(t)
        n = len(group)
        for i, s in enumerate(group):
            rad = 3 + s["ratings"]["corrosion_resistance"] * 0.55
            dx = (i - (n - 1) / 2) * 13
            col = CAT_COLOURS.get(s["category"], "--muted")
            out.append(f'<a href="/steel/{s["id"]}/"><circle cx="{_f(cx + dx)}" cy="{_f(cy)}" r="{_f(rad)}" fill="var({col})" '
                       f'fill-opacity="0.8" stroke="var(--bg)"><title>{escape(s["short"])}</title></circle>'
                       f'<text x="{_f(cx)}" y="{_f(cy + 19 + i * 11)}" text-anchor="middle" class="dot">{escape(s["short"])}</text></a>')
    out.append("</svg>")
    return Markup("".join(out))

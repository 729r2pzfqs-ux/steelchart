#!/usr/bin/env python3
"""Generate the 1200x630 social preview image (og:image) for steelchart.org.

Same mark and colours as the favicon (scripts/make_favicons.py): the blade on the dark header colour,
with the wordmark, a tagline and a row of rating bars. Output: static/og-image.png (committed);
build.py copies static/ into docs/. Needs rsvg-convert (brew install librsvg):

    python3 scripts/make_og.py
"""
import subprocess
import tempfile
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "static" / "og-image.png"
DARK, STEEL, ORANGE, GREY, MUTED = "#1b2230", "#d5dbe4", "#fb923c", "#7a8597", "#9aa6b8"
FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"
BARS = [("Edge retention", 7), ("Toughness", 8), ("Corrosion resistance", 9), ("Ease of sharpening", 5)]


def svg() -> str:
    # favicon blade (512 box) scaled into the left side
    mark = ('<g transform="translate(80,135) scale(0.7)">'
            f'<path d="M30,400 L70,360 L178,470 L138,510 Z" fill="{GREY}"/>'
            f'<path d="M70,360 L310,140 C360,96 412,72 456,56 C444,140 404,232 344,300 L178,470 Z" fill="{STEEL}"/>'
            f'<path d="M178,470 L344,300 C404,232 444,140 456,56 C424,150 378,226 316,286 L142,440 Z" fill="{ORANGE}"/></g>')
    bars = []
    for i, (name, v) in enumerate(BARS):
        y = 368 + i * 46
        bars.append(f'<text x="520" y="{y + 15}" font-size="22" fill="{MUTED}">{name}</text>'
                    f'<rect x="790" y="{y}" width="300" height="18" rx="9" fill="#2a3240"/>'
                    f'<rect x="790" y="{y}" width="{v * 30}" height="18" rx="9" fill="{ORANGE if i == 2 else STEEL}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" font-family="{FONT}">'
            f'<rect width="1200" height="630" fill="{DARK}"/>'
            f'<rect y="610" width="1200" height="20" fill="{ORANGE}"/>{mark}'
            f'<text x="520" y="215" font-size="88" font-weight="800" fill="#fff" letter-spacing="-2">Steel'
            f'<tspan fill="{ORANGE}">Chart</tspan></text>'
            f'<text x="522" y="275" font-size="32" fill="{STEEL}">Knife steel chart, ratings &amp; comparisons</text>'
            + "".join(bars) +
            f'<text x="522" y="580" font-size="24" fill="{MUTED}">steelchart.org</text></svg>\n')


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "og.svg"
        src.write_text(svg())
        subprocess.run(["rsvg-convert", "-w", "1200", "-h", "630", "-o", str(OUT), str(src)], check=True)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

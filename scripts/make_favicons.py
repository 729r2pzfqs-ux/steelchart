#!/usr/bin/env python3
"""Generate the favicon pack for steelchart.org.

The mark is a knife blade in profile: a steel-grey drop-point blade with an
orange edge bevel on the site's dark header colour. Small sizes (16/32 px) use
a bolder, simpler blade with no bevel line.

Output lands in favicon/ (committed); build.py copies it to the site root.
Needs rsvg-convert and ImageMagick (brew install librsvg imagemagick):

    python3 scripts/make_favicons.py
"""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "favicon"
DARK, STEEL, ORANGE = "#1b2230", "#d5dbe4", "#fb923c"


def svg(small: bool = False, full_bleed: bool = False) -> str:
    bg = (f'<rect width="512" height="512" fill="{DARK}"/>' if full_bleed
          else f'<rect width="512" height="512" rx="104" fill="{DARK}"/>')
    # blade pointing up-right: spine on the upper-left, curved edge on the lower-right with an orange bevel band
    blade = "M70,360 L310,140 C360,96 412,72 456,56 C444,140 404,232 344,300 L178,470 Z"
    bevel = f'<path d="M178,470 L344,300 C404,232 444,140 456,56 C424,150 378,226 316,286 L142,440 Z" fill="{ORANGE}"/>'
    handle = '<path d="M30,400 L70,360 L178,470 L138,510 Z" fill="#7a8597"/>'
    if small:
        blade = "M40,340 L300,120 C356,74 414,50 470,34 C456,130 410,236 344,306 L170,490 Z"
        bevel = f'<path d="M170,490 L344,306 C410,236 456,130 470,34 C432,150 378,236 306,302 L120,454 Z" fill="{ORANGE}"/>'
        handle = ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">{bg}{handle}'
            f'<path d="{blade}" fill="{STEEL}"/>{bevel}</svg>\n')


def png(src: Path, size: int, dest: Path) -> None:
    subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), "-o", str(dest), str(src)], check=True)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / "favicon.svg").write_text(svg())
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "small.svg").write_text(svg(small=True))
        (t / "bleed.svg").write_text(svg(full_bleed=True))
        for size in (16, 32, 48):
            png(t / "small.svg" if size < 48 else OUT / "favicon.svg", size, t / f"{size}.png")
        shutil.copy(t / "16.png", OUT / "favicon-16x16.png")
        shutil.copy(t / "32.png", OUT / "favicon-32x32.png")
        subprocess.run(["magick", str(t / "16.png"), str(t / "32.png"), str(t / "48.png"), str(OUT / "favicon.ico")], check=True)
        png(t / "bleed.svg", 180, OUT / "apple-touch-icon.png")
    png(OUT / "favicon.svg", 192, OUT / "favicon-192.png")
    png(OUT / "favicon.svg", 512, OUT / "favicon-512.png")
    (OUT / "site.webmanifest").write_text(json.dumps({
        "name": "SteelChart", "short_name": "SteelChart",
        "icons": [{"src": "/favicon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "/favicon-512.png", "sizes": "512x512", "type": "image/png"}],
        "theme_color": DARK, "background_color": "#f6f7f9", "display": "browser"}, indent=2) + "\n")
    for p in sorted(OUT.iterdir()):
        print(f"{p.name:24s} {p.stat().st_size:7d} bytes")


if __name__ == "__main__":
    main()

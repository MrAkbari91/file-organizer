"""Generate original, consistent 24px outline icons and the Windows app icon."""

from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1] / "src/file_organizer/gui/assets"
ROOT.mkdir(parents=True, exist_ok=True)
# Original geometric artwork; no third-party icon licensing dependency.
shapes = {
    "folder": [
        ("line", (3, 7, 10, 7, 12, 10, 21, 10, 21, 20, 3, 20, 3, 7)),
        ("line", (3, 7, 3, 5, 10, 5, 12, 7, 20, 7, 20, 10)),
    ],
    "home": [
        ("line", (3, 10, 12, 3, 21, 10)),
        ("line", (5, 9, 5, 21, 10, 21, 10, 14, 14, 14, 14, 21, 19, 21, 19, 9)),
    ],
    "copies": [("rect", (7, 7, 21, 21)), ("line", (17, 7, 17, 3, 3, 3, 3, 17, 7, 17))],
    "settings": [
        ("line", (3, 6, 21, 6)),
        ("line", (3, 12, 21, 12)),
        ("line", (3, 18, 21, 18)),
        ("circle", (7, 4, 11, 8)),
        ("circle", (14, 10, 18, 14)),
        ("circle", (6, 16, 10, 20)),
    ],
    "history": [("arc", (3, 3, 21, 21)), ("line", (12, 7, 12, 12, 16, 14))],
    "category": [
        ("rect", (3, 3, 10, 10)),
        ("rect", (14, 3, 21, 10)),
        ("rect", (3, 14, 10, 21)),
        ("rect", (14, 14, 21, 21)),
    ],
    "file": [
        ("line", (5, 3, 14, 3, 20, 9, 20, 21, 5, 21, 5, 3)),
        ("line", (14, 3, 14, 9, 20, 9)),
        ("line", (8, 14, 16, 14)),
        ("line", (8, 17, 14, 17)),
    ],
    "calendar": [
        ("rect", (3, 5, 21, 21)),
        ("line", (3, 10, 21, 10)),
        ("line", (7, 3, 7, 7)),
        ("line", (17, 3, 17, 7)),
    ],
    "scan": [("circle", (3, 3, 16, 16)), ("line", (15, 15, 22, 22))],
    "watch": [
        ("line", (2, 12, 6, 6, 12, 3, 18, 6, 22, 12, 18, 18, 12, 21, 6, 18, 2, 12)),
        ("circle", (9, 9, 15, 15)),
    ],
    "sun": [
        ("circle", (7, 7, 17, 17)),
        ("line", (12, 1, 12, 4)),
        ("line", (12, 20, 12, 23)),
        ("line", (1, 12, 4, 12)),
        ("line", (20, 12, 23, 12)),
    ],
    "arrow": [("line", (3, 12, 21, 12)), ("line", (15, 6, 21, 12, 15, 18))],
    "undo": [("line", (3, 10, 15, 10, 20, 14, 20, 20)), ("line", (8, 5, 3, 10, 8, 15))],
}
for name, elements in shapes.items():
    for mode, ink in [("light", "#52627A"), ("dark", "#A5B4CF")]:
        im = Image.new("RGBA", (96, 96))
        d = ImageDraw.Draw(im)
        for kind, values in elements:
            v = tuple(x * 4 for x in values)
            if kind == "line":
                d.line(v, fill=ink, width=7, joint="curve")
            elif kind == "rect":
                d.rounded_rectangle(v, radius=5, outline=ink, width=7)
            elif kind == "circle":
                d.ellipse(v, outline=ink, width=7)
            else:
                d.arc(v, 0, 360, fill=ink, width=7)
        im.save(ROOT / f"{name}-{mode}.png")
im = Image.new("RGBA", (256, 256))
d = ImageDraw.Draw(im)
d.rounded_rectangle((8, 8, 248, 248), radius=54, fill="#0F192B")
d.rounded_rectangle((44, 70, 212, 198), radius=20, fill="#22D3EE")
d.rounded_rectangle((44, 53, 121, 103), radius=15, fill="#22D3EE")
d.line((95, 142, 121, 168, 168, 115), fill="#0B1220", width=16, joint="curve")
im.save(ROOT / "app.png")
im.save(ROOT / "app.icns")
im.save(
    ROOT / "app.ico",
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)

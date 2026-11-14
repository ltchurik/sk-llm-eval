"""Render the GitHub social preview (1280x640) for sk-llm-eval.

Usage: python assets/make_social_preview.py assets/social-preview.png
Needs Pillow and the Ubuntu Sans + DejaVu fonts (paths below)."""
import sys
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1]
S = 2  # supersample
W, H = 1280 * S, 640 * S

BG = (13, 17, 28)
PANEL = (22, 28, 44)
LINE = (44, 53, 76)
TEXT = (236, 240, 247)
MUTED = (148, 160, 184)
RED = (240, 98, 98)
GREEN = (74, 214, 140)
FLAG = [(255, 255, 255), (11, 78, 162), (238, 28, 37)]  # Slovak tricolour

SANS = "/usr/share/fonts/truetype/ubuntu/UbuntuSans[wdth,wght].ttf"
MONO = "/usr/share/fonts/truetype/ubuntu/UbuntuSansMono[wght].ttf"


def font(path, size, weight):
    f = ImageFont.truetype(path, size * S)
    try:
        axes = f.get_variation_axes()
        vals = [weight if a["name"] in (b"Weight", "Weight") else a["default"] for a in axes]
        f.set_variation_by_axes(vals)
    except Exception:
        pass
    return f


img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# tricolour bar on the left edge
bw = 10 * S
for i, c in enumerate(FLAG):
    d.rectangle([0, i * H // 3, bw, (i + 1) * H // 3], fill=c)

x0 = 84 * S
# repo name
d.text((x0, 84 * S), "sk-llm-eval", font=font(MONO, 30, 600), fill=MUTED)

# headline
hf = font(SANS, 62, 750)
y = 140 * S
for line in ["Does your LLM", "write correct", "Slovak?"]:
    d.text((x0, y), line, font=hf, fill=TEXT)
    y += 74 * S

# subline
sf = font(SANS, 25, 450)
y += 22 * S
d.text((x0, y), "207 tasks · grammar · vykanie · diacritics", font=sf, fill=MUTED)
y2 = y + 36 * S
part1 = "formatting · facts · EN"
d.text((x0, y2), part1, font=sf, fill=MUTED)
ax = x0 + d.textlength(part1, font=sf) + 3 * S
af = font("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22, 400)
d.text((ax, y2 + 3 * S), "→", font=af, fill=MUTED)
d.text((ax + d.textlength("→", font=af) + 3 * S, y2), "SK translation", font=sf, fill=MUTED)

# footer
ff = font(SANS, 21, 500)
d.text((x0, 560 * S), "Zero dependencies · any OpenAI-compatible API · Ollama", font=ff, fill=MUTED)

# right panel with real model errors
px0, py0, px1, py1 = 700 * S, 76 * S, 1196 * S, 576 * S
d.rounded_rectangle([px0, py0, px1, py1], radius=22 * S, fill=PANEL, outline=LINE, width=2 * S)
d.text((px0 + 34 * S, py0 + 28 * S), "Real mistakes models make", font=font(SANS, 22, 650), fill=MUTED)

rows = [
    ("Bola ste na porade?", "Boli ste na porade?"),
    ("sympatický", "súcitný", "sympathetic"),
    ("vtáči spev", "vtáčí spev"),
    ("21.9.1990", "21. 9. 1990"),
    ("sester", "sestier"),
]
rf = font(SANS, 27, 520)
mf = font(SANS, 27, 700)
ry = py0 + 80 * S
hint_f = font(SANS, 21, 450)
for row in rows:
    wrong, right = row[0], row[1]
    d.line([px0 + 34 * S, ry - 16 * S, px1 - 34 * S, ry - 16 * S], fill=LINE, width=S)
    # wrong (struck through)
    cx = px0 + 34 * S
    d.text((cx, ry), "✗", font=font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24, 700), fill=RED)
    tx = cx + 30 * S
    d.text((tx, ry - 2 * S), wrong, font=rf, fill=RED)
    tw = d.textlength(wrong, font=rf)
    mid = ry + 17 * S
    d.line([tx, mid, tx + tw, mid], fill=RED, width=2 * S)
    # right
    ry2 = ry + 34 * S
    d.text((cx, ry2), "✓", font=font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24, 700), fill=GREEN)
    d.text((tx, ry2 - 2 * S), right, font=mf, fill=GREEN)
    if len(row) > 2:
        d.text((tx + d.textlength(right, font=mf) + 14 * S, ry2 + 4 * S), f"(EN: {row[2]})", font=hint_f, fill=MUTED)
    ry += 80 * S

img = img.resize((1280, 640), Image.LANCZOS)
img.save(OUT, optimize=True)
print(OUT)

# LIFESPAN: permanent
"""Draws flat pictures for the invented bullion catalogue (a coin is a ring, a bar is a slab). No photos are shipped.   python scripts/make_images.py build/img"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
GOLD, SILVER, BG = ("#d4a937", "#a8b0b8", "#1f2a33")
ITEMS = {  # file name: (kind, metal colour, label)
    "gold-bar-1oz": ("bar", GOLD, "1 oz"), "gold-bar-100g": ("bar", GOLD, "100 g"), "gold-bar-10g": ("bar", GOLD, "10 g"),
    "gold-coin-1oz": ("coin", GOLD, "1 oz"), "gold-coin-half": ("coin", GOLD, "1/2 oz"), "gold-coin-tenth": ("coin", GOLD, "1/10 oz"),
    "silver-bar-1kg": ("bar", SILVER, "1 kg"), "silver-bar-10oz": ("bar", SILVER, "10 oz"), "silver-bar-100oz": ("bar", SILVER, "100 oz"),
    "silver-coin-1oz": ("coin", SILVER, "1 oz"), "silver-coin-tube": ("coin", SILVER, "x 25"), "silver-bar-1oz": ("bar", SILVER, "1 oz"),
}
try:
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 64)
except OSError:
    font = ImageFont.load_default()
for name, (kind, colour, label) in ITEMS.items():
    img = Image.new("RGB", (800, 800), BG)
    d = ImageDraw.Draw(img)
    if kind == "coin":
        d.ellipse((150, 150, 650, 650), fill=colour, outline="#ffffff", width=6)
        d.ellipse((200, 200, 600, 600), outline=BG, width=5)
    else:
        d.polygon([(130, 520), (210, 300), (590, 300), (670, 520)], fill=colour, outline="#ffffff", width=6)
    w = d.textlength(label, font=font)
    d.text(((800 - w) / 2, 370 if kind == "coin" else 380), label, fill=BG, font=font)
    img.save(OUT / f"{name}.png", optimize=True)
print("wrote", len(ITEMS), "pictures to", OUT)

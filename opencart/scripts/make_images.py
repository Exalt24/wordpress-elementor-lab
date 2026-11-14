"""Draws six flat product pictures for the sample catalogue (no photos are shipped, and none are needed to test markup)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
ITEMS = {"backpacks": ("Backpacks", "#2f5d50"), "cookware": ("Camp Cookware", "#b5651d"), "summit-30": ("Summit 30", "#2f5d50"),
         "trail-20": ("Trail 20", "#3d7a68"), "ridge-55": ("Ridge 55", "#244a40"), "spark-stove": ("Spark Stove", "#b5651d"),
         "nest-pot": ("Nest 900", "#8f4f16"), "fold-mug": ("Fold Mug", "#c9772a")}
try:
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 46)
except OSError:
    font = ImageFont.load_default()
for name, (label, colour) in ITEMS.items():
    img = Image.new("RGB", (600, 600), colour)
    draw = ImageDraw.Draw(img)
    w = draw.textlength(label, font=font)
    draw.text(((600 - w) / 2, 270), label, fill="#ffffff", font=font)
    img.save(OUT / f"{name}.png")
print("wrote", len(ITEMS), "pictures to", OUT)

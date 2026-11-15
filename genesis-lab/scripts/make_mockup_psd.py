"""Writes a layered Photoshop file for a made up landing page mock-up: ../docs/mockup.psd.

pytoshop writes pixel layers only (no type layers), so each layer's NAME carries its role and its text:
    bg | hero-band | headline: <text> | sub: <text> | cta: <text> | photo
A real design file would carry type layers; psd_to_page.py reads the same names, so a designer's file only needs the same layer names.
"""
import os

import numpy as np
import pytoshop
from pytoshop import enums
from pytoshop.user import nested_layers

W, H = 1280, 720
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "mockup.psd")


def rect(w, h, rgb):
    """A fully opaque rectangle as the (R, G, B, A) channel planes pytoshop wants."""
    planes = [np.full((h, w), c, dtype=np.uint8) for c in rgb] + [np.full((h, w), 255, dtype=np.uint8)]
    return planes


def layer(name, left, top, w, h, rgb):
    ch = rect(w, h, rgb)
    return nested_layers.Image(name=name, top=top, left=left, bottom=top + h, right=left + w,
                               channels={0: ch[0], 1: ch[1], 2: ch[2], -1: ch[3]})


layers = [
    layer("cta: Book a free call", 80, 470, 260, 64, (232, 93, 4)),
    layer("sub: Text reminders the day before a visit. Set up in a week.", 80, 340, 560, 90, (200, 214, 229)),
    layer("headline: Fewer no-shows, fewer empty chairs", 80, 180, 620, 140, (255, 255, 255)),
    layer("photo", 760, 120, 440, 480, (123, 158, 168)),
    layer("hero-band", 0, 60, 1280, 600, (16, 42, 67)),
    layer("bg", 0, 0, 1280, 720, (244, 247, 250)),
]
doc = nested_layers.nested_layers_to_psd(layers, color_mode=enums.ColorMode.rgb, size=(W, H), compression=enums.Compression.raw)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "wb") as fh:
    doc.write(fh)
print("wrote", OUT, os.path.getsize(OUT), "bytes,", len(layers), "layers")

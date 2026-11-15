"""Turns the layered PSD mock-up into the HTML of a page: python scripts/psd_to_page.py docs/mockup.psd > docs/mockup-page.html

It reads the file the way a developer reads a design hand-off: canvas size, each layer's box and fill colour, and the role and text in the
layer name (see make_mockup_psd.py). Boxes decide the layout: layers whose centre sits left of the canvas middle go in the text column, the
rest in the picture column, and the order inside a column follows the vertical position. Colours become CSS variables. The result is a
two column band on a wide screen that stacks on a phone, not a pixel copy of the canvas.
"""
import html
import sys

from psd_tools import PSDImage


def layer_info(layer):
    box = layer.bbox
    px = layer.composite()
    r, g, b = px.convert("RGB").getpixel((px.width // 2, px.height // 2))
    role, _, text = layer.name.strip("\x00 ").partition(":")
    return {"role": role.strip(), "text": text.strip(), "left": box[0], "top": box[1], "w": box[2] - box[0], "h": box[3] - box[1], "rgb": (r, g, b)}


def css_rgb(rgb):
    return "#%02x%02x%02x" % rgb


def build(path):
    psd = PSDImage.open(path)
    W, H = psd.width, psd.height
    layers = [layer_info(l) for l in psd.descendants() if not l.is_group()]
    by = {l["role"]: l for l in layers}
    for need in ("bg", "hero-band", "headline", "cta", "photo"):
        if need not in by:
            raise SystemExit("the mock-up has no layer named %s" % need)
    left = sorted([l for l in layers if l["role"] in ("headline", "sub", "cta")], key=lambda l: l["top"])
    right = [l for l in layers if l["role"] == "photo"]
    # every text layer must sit in the left half, and the picture in the right: the layout rests on that
    assert all(l["left"] + l["w"] / 2 < W / 2 for l in left), "a text layer sits right of the middle"
    assert all(l["left"] + l["w"] / 2 > W / 2 for l in right), "the picture sits left of the middle"
    band_share = round(100 * by["hero-band"]["h"] / H)
    out = []
    out.append("<style>")
    out.append(":root{--mock-bg:%s;--mock-band:%s;--mock-headline:%s;--mock-sub:%s;--mock-cta:%s;--mock-photo:%s}" % tuple(
        css_rgb(by[k]["rgb"]) for k in ("bg", "hero-band", "headline", "sub", "cta", "photo")))
    out.append(".mock{background:var(--mock-bg);padding:%dpx 0}" % round(by["hero-band"]["top"] / W * 100))
    out.append(".mock-band{background:var(--mock-band);display:grid;grid-template-columns:%d%% %d%%;gap:%dpx;align-items:center;padding:%dpx %dpx}" % (
        round(100 * (by["photo"]["left"] - by["headline"]["left"]) / (W - 2 * by["headline"]["left"])),
        round(100 * by["photo"]["w"] / (W - 2 * by["headline"]["left"])),
        round(by["photo"]["left"] - by["headline"]["left"] - by["headline"]["w"]),
        round(by["headline"]["top"] - by["hero-band"]["top"]), by["headline"]["left"]))
    out.append(".mock-text h1{color:var(--mock-headline);font-size:clamp(28px,4vw,48px);margin:0 0 16px}")
    out.append(".mock-text p{color:var(--mock-sub);font-size:18px;margin:0 0 24px}")
    out.append(".mock-text a{display:inline-block;background:var(--mock-cta);color:#fff;padding:18px 32px;border-radius:6px;text-decoration:none;font-weight:700}")
    out.append(".mock-photo{background:var(--mock-photo);min-height:%dpx;border-radius:6px}" % round(by["photo"]["h"] * 0.6))
    out.append("@media (max-width:700px){.mock-band{grid-template-columns:1fr;padding:32px 20px}}")
    out.append("</style>")
    out.append('<section class="mock" data-band-share="%d"><div class="mock-band"><div class="mock-text">' % band_share)
    for l in left:
        t = html.escape(l["text"])
        out.append({"headline": "<h1>%s</h1>", "sub": "<p>%s</p>", "cta": '<a href="/contact/">%s</a>'}[l["role"]] % t)
    out.append('</div><div class="mock-photo" role="img" aria-label="Photo placeholder"></div></div></section>')
    return "\n".join(out), {"canvas": (W, H), "layers": layers}


if __name__ == "__main__":
    page, _ = build(sys.argv[1])
    sys.stdout.write(page + "\n")

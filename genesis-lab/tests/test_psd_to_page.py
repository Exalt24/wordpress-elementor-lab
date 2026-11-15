"""Tests for scripts/psd_to_page.py, the PSD mock-up to page converter, in both directions, with mutation controls.

What can go wrong is in the converter's output, so each check reads the HTML it makes from a PSD written here in a temp folder:
the colours must be the PSD's, the text must be escaped, the band must be marked full width for a classic theme, the layout must
rest on the layer positions, and a PSD missing a layer must be refused. The controls change a copy of the converter in known ways
and every change must break at least one check. Two of the breaks are real ones met while building it: a full width hack made
of 100vw that spilled past the screen, and a band that stayed inside the parent theme's narrow column.
    python tests/test_psd_to_page.py
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile

import numpy as np
from pytoshop import enums
from pytoshop.user import nested_layers

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
CONVERTER = os.path.join(LAB, "scripts", "psd_to_page.py")
W, H = 640, 360
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("PASS " if ok else "FAIL ") + name + ((" | " + detail) if detail and not ok else ""))
    if not ok:
        failures.append(name)


def layer(name, left, top, w, h, rgb):
    planes = [np.full((h, w), c, dtype=np.uint8) for c in rgb] + [np.full((h, w), 255, dtype=np.uint8)]
    return nested_layers.Image(name=name, top=top, left=left, bottom=top + h, right=left + w,
                               channels={0: planes[0], 1: planes[1], 2: planes[2], -1: planes[3]})


def write_psd(path, headline="Fewer no-shows", skip=None, text_side="left", colours=None):
    c = {"bg": (244, 247, 250), "band": (16, 42, 67), "head": (255, 255, 255), "sub": (200, 214, 229), "cta": (232, 93, 4), "photo": (123, 158, 168)}
    c.update(colours or {})
    text_left = 40 if text_side == "left" else 400
    photo_left = 380 if text_side in ("left", "both-right") else 20
    if text_side == "both-right":
        text_left = 400
    layers = [
        layer("cta: Book a call", text_left, 235, 130, 32, c["cta"]),
        layer("sub: Reminders the day before.", text_left, 170, 280, 45, c["sub"]),
        layer("headline: " + headline, text_left, 90, 310, 70, c["head"]),
        layer("photo", photo_left, 60, 220, 240, c["photo"]),
        layer("hero-band", 0, 30, 640, 300, c["band"]),
        layer("bg", 0, 0, 640, 360, c["bg"]),
    ]
    layers = [l for l in layers if not (skip and l.name.startswith(skip))]
    doc = nested_layers.nested_layers_to_psd(layers, color_mode=enums.ColorMode.rgb, size=(W, H), compression=enums.Compression.raw)
    with open(path, "wb") as fh:
        doc.write(fh)


def load(converter_path):
    spec = importlib.util.spec_from_file_location("psd_to_page_under_test", converter_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_checks(converter_path, tmp, quiet=False):
    """Every check against one copy of the converter. Returns the number of failing checks."""
    before = len(failures)
    mod = load(converter_path)
    psd = os.path.join(tmp, "ok.psd")
    write_psd(psd)
    html, info = mod.build(psd)
    check("the band is marked alignfull so a classic theme does not hold it in a narrow column", 'class="mock alignfull"' in html)
    check("no 100vw full width hack (it spilled past the screen on a vertical scrollbar)", "100vw" not in html)
    check("the band, button and picture colours are the PSD's", all(x in html for x in ("--mock-band:#102a43", "--mock-cta:#e85d04", "--mock-photo:#7b9ea8")))
    check("the headline text is the layer text", "<h1>Fewer no-shows</h1>" in html)
    check("a phone breakpoint stacks the columns", "@media (max-width:700px)" in html and "grid-template-columns:1fr" in html)
    check("the canvas size is read from the file", info["canvas"] == (W, H))
    # hostile layer text must come out escaped
    hostile = os.path.join(tmp, "hostile.psd")
    write_psd(hostile, headline="<script>alert(1)</script>")
    hh, _ = mod.build(hostile)
    check("layer text is escaped", "<script>alert" not in hh and "&lt;script&gt;" in hh)
    # a different colour must come through, so the colours are read and not constant
    other = os.path.join(tmp, "other.psd")
    write_psd(other, colours={"band": (1, 2, 3)})
    oh, _ = mod.build(other)
    check("a changed band colour changes the page", "--mock-band:#010203" in oh and "--mock-band:#102a43" not in oh)
    # a missing layer is refused, and text on the wrong side is refused
    missing = os.path.join(tmp, "missing.psd")
    write_psd(missing, skip="cta")
    try:
        mod.build(missing)
        check("a PSD with no cta layer is refused", False)
    except SystemExit as e:
        check("a PSD with no cta layer is refused", "cta" in str(e))
    wrong = os.path.join(tmp, "wrong.psd")
    write_psd(wrong, text_side="both-right")     # text AND picture on the right: only the text assertion can refuse it
    try:
        mod.build(wrong)
        check("text on the right half is refused", False)
    except AssertionError as e:
        check("text on the right half is refused", "text layer" in str(e))
    swapped = os.path.join(tmp, "swapped.psd")
    write_psd(swapped, text_side="right")        # text on the right, picture on the left: refused by either assertion
    try:
        mod.build(swapped)
        check("a swapped layout is refused", False)
    except AssertionError:
        check("a swapped layout is refused", True)
    return len(failures) - before


MUTATIONS = [
    ("drop the alignfull class", 'class="mock alignfull"', 'class="mock"'),
    ("bring back the 100vw hack", '.mock{background:var(--mock-bg);padding:%dpx 0}', '.mock{background:var(--mock-bg);padding:%dpx 0;width:100vw;margin-left:calc(50%% - 50vw)}'),
    ("stop escaping layer text", "t = html.escape(l[\"text\"])", "t = l[\"text\"]"),
    ("read no colours (use the band colour for all)", "css_rgb(by[k][\"rgb\"]) for k in", "css_rgb(by[\"hero-band\"][\"rgb\"]) for k in"),
    ("drop the phone breakpoint", "@media (max-width:700px)", "@media (max-width:0px)"),
    ("accept a missing layer", "raise SystemExit(\"the mock-up has no layer named %s\" % need)", "continue"),
    ("drop the side assertion for text", "assert all(l[\"left\"] + l[\"w\"] / 2 < W / 2 for l in left), \"a text layer sits right of the middle\"", "pass"),
]


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="psd-test-")
    try:
        n = run_checks(CONVERTER, tmp)
        print("\nbaseline: %d failing check(s)" % n)
        if n:
            return 1
        source = open(CONVERTER, encoding="utf-8").read()
        caught = 0
        for name, old, new in MUTATIONS:
            if old not in source:
                print(f"FAIL control {name}: the anchor is not in the converter, the mutation did not apply")
                return 1
            work = tempfile.mkdtemp(prefix="psd-mut-")
            try:
                path = os.path.join(work, "psd_to_page.py")
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(source.replace(old, new, 1))
                saved = list(failures)
                broke = False
                try:
                    import io
                    import contextlib
                    with contextlib.redirect_stdout(io.StringIO()):
                        broke = run_checks(path, work) > 0
                except BaseException:   # a mutant that crashes the converter is caught too
                    broke = True
                failures[:] = saved
                print(("PASS " if broke else "FAIL ") + f"control {name}: " + ("a check broke" if broke else "every check still passed"))
                caught += broke
            finally:
                shutil.rmtree(work, ignore_errors=True)
        print(f"\n{caught}/{len(MUTATIONS)} converter mutations caught")
        return 0 if caught == len(MUTATIONS) and not failures else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

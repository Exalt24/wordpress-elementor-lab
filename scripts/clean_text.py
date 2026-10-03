"""Replaces the broken dash glyph a Windows console leaves in saved audit output, so the files read cleanly. python scripts/clean_text.py <file> [<file> ...]"""
import sys

for path in sys.argv[1:]:
    text = open(path, "rb").read().decode("utf-8", errors="replace").replace("�", "-")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("cleaned", path)

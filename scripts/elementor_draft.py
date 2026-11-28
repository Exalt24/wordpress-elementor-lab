# LIFESPAN: permanent
"""Manifest to a verified Elementor draft on the lab WordPress.

    python scripts/elementor_draft.py push elementor/seller-audit.layout.json            # build, save as a draft, check in the editor
    python scripts/elementor_draft.py push elementor/seller-audit.layout.json --promote  # publish it only when the check passed
    python scripts/elementor_draft.py push-tree tree.json --title T --slug s             # a raw element tree, skipping the builder (to show a bad tree is caught)

Steps: build the tree (a manifest that breaks the schema or names an unknown token stops here, before any request), save it through the
lab/v1/elementor-draft route as a draft, open the draft in the real Elementor editor in a headless browser and read the elements back
(scripts/verify_in_editor.cjs). A mismatch or an editor error deletes the draft and nothing is promoted. Standard library only.
Needs the lab running (bash scripts/setup.sh) and an application password in LAB_APP_PASSWORD or .lab_app_password.
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import manifest_to_elementor as m2e  # noqa: E402

ROOT = m2e.ROOT


def credentials():
    password = os.environ.get("LAB_APP_PASSWORD")
    if not password:
        path = os.path.join(ROOT, ".lab_app_password")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                password = fh.read().strip()
    if not password:
        raise SystemExit("no application password: set LAB_APP_PASSWORD or run scripts/setup.sh, which writes .lab_app_password")
    user = os.environ.get("LAB_USER", "admin")
    return "Basic " + base64.b64encode((user + ":" + password).encode("utf-8")).decode("ascii")


def call(base, method, path, auth, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(base + "/wp-json/lab/v1" + path, data=data, method=method,
                                 headers={"Authorization": auth, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        except ValueError:
            return exc.code, {"message": "HTTP " + str(exc.code)}


def verify(base, post_id, tree_path, shot=None):
    cmd = ["node", os.path.join(ROOT, "scripts", "verify_in_editor.cjs"), str(post_id), tree_path, "--base", base]
    if shot:
        cmd += ["--shot", shot]
    done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=240)
    lines = [ln for ln in done.stdout.splitlines() if ln.strip()]
    try:
        result = json.loads(lines[-1])
    except (IndexError, ValueError):
        result = {"ok": False, "editorErrors": ["the verifier printed nothing readable: " + (done.stderr or "")[:200]], "mismatches": [], "elements": 0}
    return done.returncode, result


def run(args):
    base = args.base.rstrip("/")
    if args.command == "push":
        try:
            manifest = m2e.load_json(args.source)
            tree = m2e.build(manifest)
        except m2e.ManifestError as exc:
            print("REFUSED before any request: " + str(exc))
            return 1
        page = manifest["page"]
    else:
        tree = m2e.load_json(args.source)
        page = {"title": args.title, "slug": args.slug, "excerpt": ""}
    auth = credentials()
    sent = m2e.tree_json(tree)
    status, body = call(base, "POST", "/elementor-draft", auth,
                        {"title": page["title"], "slug": page["slug"], "excerpt": page.get("excerpt", ""), "data_json": sent})
    if status != 200:
        print("DRAFT NOT SAVED (%d): %s" % (status, body.get("message", body)))
        return 1
    post_id, stored_hash = body["id"], body["hash"]
    print("draft %d saved, hash %s" % (post_id, stored_hash[:16]))
    tree_path = os.path.join(os.environ.get("TMPDIR") or os.environ.get("TEMP") or "/tmp", "lab_tree_%d.json" % post_id)
    with open(tree_path, "w", encoding="utf-8") as fh:
        fh.write(sent)
    try:
        code, result = verify(base, post_id, tree_path, args.shot)
    finally:
        os.remove(tree_path)
    ok = code == 0 and result.get("ok") and stored_hash == m2e.tree_hash(tree)
    if not ok:
        reasons = result.get("editorErrors", []) + result.get("mismatches", [])
        if stored_hash != m2e.tree_hash(tree):
            reasons.append("the stored data hashes differently from what was sent")
        print("EDITOR CHECK FAILED, %d problem(s):" % len(reasons))
        for line in reasons[:8]:
            print("  " + line)
        d_status, d_body = call(base, "DELETE", "/elementor-draft/%d" % post_id, auth)
        print("draft %d deleted (%d), nothing promoted" % (post_id, d_status) if d_status == 200 else "DRAFT NOT DELETED (%d): %s" % (d_status, d_body))
        return 1
    print("EDITOR CHECK PASSED: %d elements read back from the real editor match what was sent" % result["elements"])
    if args.promote:
        p_status, p_body = call(base, "POST", "/elementor-draft/%d/promote" % post_id, auth, {"verified_hash": m2e.tree_hash(tree)})
        if p_status != 200:
            print("NOT PROMOTED (%d): %s" % (p_status, p_body.get("message", p_body)))
            return 1
        print("promoted: draft %d is now published at %s/?page_id=%d" % (post_id, base, post_id))
    else:
        print("left as a draft (use --promote to publish)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("push", "push-tree"):
        sp = sub.add_parser(name)
        sp.add_argument("source")
        sp.add_argument("--base", default=os.environ.get("LAB_BASE", "http://localhost:8087"))
        sp.add_argument("--promote", action="store_true")
        sp.add_argument("--shot")
        if name == "push-tree":
            sp.add_argument("--title", required=True)
            sp.add_argument("--slug", required=True)
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())

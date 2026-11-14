#!/usr/bin/env bash
# Runs Lighthouse (mobile, performance only) N times against one shop page from a container on the lab's own network, and prints a summary.
#   bash bullion-shop/scripts/run_lighthouse.sh <label> [path] [runs]      e.g.  run_lighthouse.sh before /shop/ 3
# The raw reports stay in build/lighthouse (ignored by git); the summary goes to stdout.
set -euo pipefail
cd "$(dirname "$0")/.."
export MSYS_NO_PATHCONV=1
label="$1"; page="${2:-/shop/}"; runs="${3:-3}"
mkdir -p build/lighthouse
docker image inspect bullion-lighthouse >/dev/null 2>&1 || docker build -t bullion-lighthouse lighthouse
out="$(cd build/lighthouse && (pwd -W 2>/dev/null || pwd))"
files=()
for i in $(seq 1 "$runs"); do
  docker run --rm --network bullion_default -v "$out:/out" bullion-lighthouse \
    lighthouse "http://wordpress$page" --only-categories=performance --output=json --output-path="/out/$label-$i.json" \
    --chrome-flags="--headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage" --quiet
  files+=("build/lighthouse/$label-$i.json")
done
python scripts/lh_summary.py "${files[@]}"

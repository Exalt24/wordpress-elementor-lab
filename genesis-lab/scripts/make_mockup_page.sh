#!/usr/bin/env bash
# Builds the page from the PSD mock-up on DEV: writes the PSD, converts it to HTML, creates (or replaces) the page /mockup/.
#   bash scripts/make_mockup_page.sh      then  bash scripts/sync_dev_to_prod.sh  to move it to PROD
set -euo pipefail
cd "$(dirname "$0")/.."
export MSYS_NO_PATHCONV=1
dev() { docker compose --profile tools run --rm -T cli-dev wp --path=/var/www/html "$@"; }
python scripts/make_mockup_psd.py
python scripts/psd_to_page.py docs/mockup.psd > docs/mockup-page.html
old=$(dev post list --post_type=page --name=mockup --field=ID 2>/dev/null | tail -1 || true)
[ -n "$old" ] && dev post delete "$old" --force
cat docs/mockup-page.html | dev post create - --post_type=page --post_title="Mock-up" --post_name=mockup --post_status=publish --porcelain
echo "page at http://localhost:8091/mockup/"

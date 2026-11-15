#!/usr/bin/env bash
# Moves DEV to PROD the safe way: a backup of PROD first, DEV's database in, every DEV address rewritten to PROD's, caches flushed. Uploads are not copied: the lab holds none.
#   bash scripts/sync_dev_to_prod.sh            runs it
#   bash scripts/sync_dev_to_prod.sh --dry-run  prints what would change and writes nothing
# PROD is never edited by hand: the only road into it is this script, which keeps a dated backup in backups/ before it touches anything.
set -euo pipefail
cd "$(dirname "$0")/.."
export MSYS_NO_PATHCONV=1
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
dev()  { docker compose --profile tools run --rm -T cli-dev  wp --path=/var/www/html "$@"; }
prod() { docker compose --profile tools run --rm -T cli-prod wp --path=/var/www/html "$@"; }
DEV_URL=http://localhost:8091
PROD_URL=http://localhost:8092
STAMP=$(date +%Y%m%d-%H%M%S)
THEME="$(cat .theme 2>/dev/null || echo lab-classic)"
mkdir -p backups

dev core is-installed || { echo "DEV is not installed: run scripts/setup.sh first"; exit 2; }
echo "DEV posts: $(dev post list --post_type=case_study --format=count), theme $THEME"
if [ "$DRY" = 1 ]; then
  echo "dry run: would back up PROD to backups/prod-$STAMP.sql, import DEV, rewrite $DEV_URL to $PROD_URL (uploads are not copied: this lab has none)"
  exit 0
fi

# code is deployed separately from content: PROD carries the same parent theme and the same plugin, DEV's database only carries content and settings
if ! prod core is-installed 2>/dev/null; then
  prod core install --url="$PROD_URL" --title="Lab PROD" --admin_user=admin --admin_password=admin-local-only --admin_email=lab@example.com --skip-email
fi
prod db export "/backups/prod-$STAMP.sql"
echo "PROD backed up to backups/prod-$STAMP.sql"
if [ "$THEME" = "lab-child" ]; then
  prod theme is-installed genesis 2>/dev/null || prod theme install /vendor/genesis.zip
else
  prod theme is-installed twentytwentyone 2>/dev/null || prod theme install twentytwentyone
fi
prod plugin is-installed advanced-custom-fields 2>/dev/null || prod plugin install advanced-custom-fields

dev db export "/backups/dev-$STAMP.sql"
prod db import "/backups/dev-$STAMP.sql"
prod search-replace "$DEV_URL" "$PROD_URL" --all-tables --skip-columns=guid --quiet
prod option update home "$PROD_URL"
prod option update siteurl "$PROD_URL"
prod option update blogname "Lab PROD"   # settings that belong to PROD are put back after DEV's database comes in: its address and its name
prod theme activate "$THEME"
prod plugin activate advanced-custom-fields 2>/dev/null || true
prod rewrite flush --hard
prod cache flush
echo "synced: PROD now has $(prod post list --post_type=case_study --format=count) case studies at $PROD_URL"

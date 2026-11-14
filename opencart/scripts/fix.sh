#!/usr/bin/env bash
# Applies the fix: the settings (store name, home title and description, SEO URLs) and the events that load the SEO Lab extension.
# Run scripts/setup.sh to go back to the stock store.
set -euo pipefail
cd "$(dirname "$0")/.."
DB="docker compose -p oclab exec -T db mariadb -uoc -poc-local-only oc"
$DB < scripts/fix_settings.sql
$DB < scripts/events.sql
echo "fix applied"

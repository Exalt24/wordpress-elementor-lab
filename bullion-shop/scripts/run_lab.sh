#!/usr/bin/env bash
# One run, start to finish. Three states of the same shop are measured the same way:
#   before  the price integration written the obvious way (a feed call for every price read), stock theme assets, no hardening
#   cache   one saved reading for the prices, still stock assets, still no hardening
#   after   the saved reading, the hardening, and the lean assets
# then the feed's bad days. Writes bullion-shop/docs/*.txt. Needs Docker, Python 3, bash and curl. Takes about twenty minutes.
set -euo pipefail
cd "$(dirname "$0")/.."
export MSYS_NO_PATHCONV=1
wp() { docker compose run --rm -T --no-deps cli wp --path=/var/www/html "$@"; }
mkdir -p docs

docker compose ps --status running --services 2>/dev/null | grep -q wordpress || bash scripts/setup.sh
wp eval-file /lab-scripts/seed.php > /dev/null   # the front page and products as the current seed defines them

# The probes log in as the lab admin. The password lives in build/ (ignored by git); a lab made before that is given a fresh one here.
mkdir -p build
if [ ! -s build/admin_password.txt ]; then
  python -c "import secrets; print(secrets.token_urlsafe(14))" > build/admin_password.txt
  wp user update admin --user_pass="$(cat build/admin_password.txt)" > /dev/null
fi
export BULLION_ADMIN_PASSWORD="$(cat build/admin_password.txt)"

set_mode() {  # price mode, hardening, assets
  BULLION_PRICE_MODE="$1" BULLION_HARDENING="$2" BULLION_ASSETS="$3" docker compose up -d --force-recreate wordpress
  for _ in $(seq 1 40); do
    [ "$(curl -s -w '%{http_code}' http://localhost:8089/shop/ | tail -c 3)" = "200" ] && break
    sleep 2
  done
  wp transient delete --all >/dev/null
  curl -s http://localhost:8089/shop/ > /dev/null
}

measure() {  # label, with-hardening-probes yes|no
  if [ "$2" = "yes" ]; then
    python scripts/hardening_check.py http://localhost:8089 --user admin > "docs/hardening_$1.txt" || true
    wp transient delete --all >/dev/null
  fi
  python scripts/measure_pages.py http://localhost:8089 http://localhost:8090 > "docs/pages_$1.txt"
  bash scripts/run_lighthouse.sh "$1" /shop/ 3 > "docs/lighthouse_$1.txt"
  cat "docs/pages_$1.txt" "docs/lighthouse_$1.txt"
}

curl -s "http://localhost:8090/control?reset=1" > /dev/null
set_mode naive off stock
measure before yes
set_mode cached off stock
measure cache no
set_mode cached on lean
measure after yes
python scripts/schema_check.py http://localhost:8089/product/gold-bar-1oz/ > docs/schema_check.txt || true
{
  echo "### Merchant Center feed, first item"
  curl -s "http://localhost:8089/?bullion_feed=merchant" | grep -o '<item>.*</item>' | sed 's#</item>.*#</item>#'
  echo
  echo "### REST route and its cache header"
  curl -si http://localhost:8089/wp-json/bullion/v1/spot | grep -i -E '^(HTTP|cache-control)|^\{'
} > docs/feed_and_rest.txt
wp transient delete --all >/dev/null
python scripts/live_checks.py http://localhost:8089 http://localhost:8090 > docs/live_checks.txt || true
tail -3 docs/live_checks.txt

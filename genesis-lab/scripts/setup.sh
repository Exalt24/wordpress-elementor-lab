#!/usr/bin/env bash
# Stands up DEV (8091) and PROD (8092) from nothing: WordPress on one MariaDB, the shared lab-core mu-plugin, Advanced Custom Fields,
# a child theme and three sample case studies on DEV. Two themes, one set of functionality:
#   THEME=lab-classic (default)  a child of the plain Twenty Twenty-One parent, placed with WordPress's own hooks
#   THEME=lab-child              a child of the Genesis Framework: needs vendor/genesis.zip, requested free at https://www.studiopress.com/get-genesis/
#   bash scripts/setup.sh        then  bash scripts/sync_dev_to_prod.sh        then  python scripts/check_lab.py
set -euo pipefail
cd "$(dirname "$0")/.."
export MSYS_NO_PATHCONV=1   # Git Bash on Windows rewrites /var/www/html into a Windows path otherwise
THEME="${THEME:-lab-classic}"
if [ "$THEME" = "lab-child" ] && [ ! -f vendor/genesis.zip ]; then
  echo "THEME=lab-child needs vendor/genesis.zip: request it free at https://www.studiopress.com/get-genesis/"; exit 2
fi
mkdir -p backups
dev()  { docker compose --profile tools run --rm -T cli-dev  wp --path=/var/www/html "$@"; }
prod() { docker compose --profile tools run --rm -T cli-prod wp --path=/var/www/html "$@"; }

docker compose up -d db dev prod
for port in 8091 8092; do
  for _ in $(seq 1 40); do
    code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port/" || true)
    [ "$code" != "000" ] && break
    sleep 3
  done
done

dev core is-installed 2>/dev/null || dev core install --url=http://localhost:8091 --title="Lab DEV" --admin_user=admin --admin_password=admin-local-only --admin_email=lab@example.com --skip-email
if [ "$THEME" = "lab-child" ]; then
  dev theme is-installed genesis 2>/dev/null || dev theme install /vendor/genesis.zip
else
  dev theme is-installed twentytwentyone 2>/dev/null || dev theme install twentytwentyone
fi
dev theme activate "$THEME"
dev plugin is-installed advanced-custom-fields 2>/dev/null || dev plugin install advanced-custom-fields
dev plugin activate advanced-custom-fields
dev rewrite structure '/%postname%/' --hard
dev option update show_on_front posts
echo "$THEME" > .theme

# three sample case studies, invented, with their fields and an industry each (skipped when DEV already has them)
add_case() {  # title, client, result, industry, body
  id=$(dev post create --post_type=case_study --post_title="$1" --post_status=publish --post_content="$5" --porcelain | tail -1)
  dev post meta update "$id" client_name "$2"
  dev post meta update "$id" _client_name field_lab_client_name
  dev post meta update "$id" headline_result "$3"
  dev post meta update "$id" _headline_result field_lab_headline_result
  dev term create industry "$4" >/dev/null 2>&1 || true
  dev post term set "$id" industry "$4"
}
if [ "$(dev post list --post_type=case_study --format=count)" = "0" ]; then
  add_case "Parts feed cleanup" "Northline Auto" "Duplicate listings fell from one in four to one in twenty." "Automotive" "Three supplier feeds became one catalog."
  add_case "Booking reminders" "Harbor Dental" "No-shows dropped by a third in the first month." "Healthcare" "Reminders by text the day before."
  add_case "Quote form rebuild" "Pinecrest Roofing" "Quote requests doubled after the form went from nine fields to four." "Construction" "A shorter form with a phone fallback."
fi
echo "DEV is at http://localhost:8091 on $THEME; PROD is installed by sync_dev_to_prod.sh at http://localhost:8092"

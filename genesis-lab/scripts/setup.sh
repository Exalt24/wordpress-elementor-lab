#!/usr/bin/env bash
# Stands up DEV (8091) and PROD (8092) from nothing: WordPress on one MariaDB, the Genesis Framework from vendor/genesis.zip,
# the Lab Child theme, Advanced Custom Fields, and three sample case studies on DEV.
#   1. get the free Genesis zip at https://www.studiopress.com/get-genesis/ and save it as genesis-lab/vendor/genesis.zip
#   2. bash scripts/setup.sh        3. bash scripts/sync_dev_to_prod.sh        4. python scripts/check_lab.py
set -euo pipefail
cd "$(dirname "$0")/.."
export MSYS_NO_PATHCONV=1   # Git Bash on Windows rewrites /var/www/html into a Windows path otherwise
[ -f vendor/genesis.zip ] || { echo "vendor/genesis.zip is missing: request it free at https://www.studiopress.com/get-genesis/"; exit 2; }
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

dev core install --url=http://localhost:8091 --title="Lab DEV" --admin_user=admin --admin_password=admin-local-only --admin_email=lab@example.com --skip-email
dev theme install /vendor/genesis.zip
dev theme activate lab-child
dev plugin install advanced-custom-fields --activate
dev rewrite structure '/%postname%/' --hard
dev option update show_on_front posts

# three sample case studies, invented, with their fields and an industry each
add_case() {  # title, client, result, industry
  id=$(dev post create --post_type=case_study --post_title="$1" --post_status=publish --post_content="$5" --porcelain | tail -1)
  dev post meta update "$id" client_name "$2"
  dev post meta update "$id" _client_name field_lab_client_name
  dev post meta update "$id" headline_result "$3"
  dev post meta update "$id" _headline_result field_lab_headline_result
  dev term create industry "$4" >/dev/null 2>&1 || true
  dev post term set "$id" industry "$4"
}
add_case "Parts feed cleanup" "Northline Auto" "Duplicate listings fell from one in four to one in twenty." "Automotive" "Three supplier feeds became one catalog."
add_case "Booking reminders" "Harbor Dental" "No-shows dropped by a third in the first month." "Healthcare" "Reminders by text the day before."
add_case "Quote form rebuild" "Pinecrest Roofing" "Quote requests doubled after the form went from nine fields to four." "Construction" "A shorter form with a phone fallback."
echo "DEV is at http://localhost:8091 ; PROD is installed by sync_dev_to_prod.sh at http://localhost:8092"

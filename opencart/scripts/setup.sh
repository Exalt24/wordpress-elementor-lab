#!/usr/bin/env bash
# Builds the stock OpenCart 4 store and fills it with the sample catalogue, in OpenCart's default state (the "before").
# Run from the opencart folder:  bash scripts/setup.sh        then:  bash scripts/fix.sh   for the "after".
set -euo pipefail
cd "$(dirname "$0")/.."
P="-p oclab"
DB="docker compose $P exec -T db mariadb -uoc -poc-local-only oc"

docker compose $P down -v >/dev/null 2>&1 || true
docker compose $P up -d --build

echo "waiting for the database"
until docker compose $P exec -T db healthcheck.sh --connect --innodb_initialized >/dev/null 2>&1; do sleep 2; done

docker compose $P exec -T -u www-data shop php install/cli_install.php install \
  --db_hostname db --db_username oc --db_password oc-local-only --db_database oc --db_driver mysqli --db_port 3306 \
  --username admin --password admin-local-only --email admin@example.test --http_server http://localhost:8088/

python scripts/make_images.py _img
cid=$(docker compose $P ps -q shop)
docker exec "$cid" mkdir -p image/catalog/pinewick
docker cp _img/. "$cid":/var/www/html/image/catalog/pinewick/
docker exec "$cid" chown -R www-data:www-data image/catalog/pinewick
rm -rf _img

$DB < scripts/seed.sql
echo "store: http://localhost:8088/   admin: http://localhost:8088/admin/  (admin / admin-local-only)"

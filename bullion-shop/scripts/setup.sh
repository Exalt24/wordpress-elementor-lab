#!/usr/bin/env bash
# Stands up the bullion shop lab from nothing: WordPress, MariaDB, WooCommerce, the Storefront theme, the stand-in price feed and twelve invented products.
#   bash bullion-shop/scripts/setup.sh      then the shop is at http://localhost:8089/ and the admin at /wp-admin (user admin, password in build/admin_password.txt)
set -euo pipefail
cd "$(dirname "$0")/.."
export MSYS_NO_PATHCONV=1   # Git Bash on Windows rewrites /var/www/html into a Windows path otherwise
wp() { docker compose run --rm -T --no-deps cli wp --path=/var/www/html "$@"; }

python scripts/make_images.py build/img
docker compose up -d db wordpress spot
for _ in $(seq 1 40); do
  code=$(curl -s -w "%{http_code}" http://localhost:8089/ | tail -c 3 || true)
  [ "$code" != "000" ] && break
  sleep 3
done

# The admin password is made fresh on this machine and kept in build/ (ignored by git), never written in a command line here.
mkdir -p build
[ -s build/admin_password.txt ] || python -c "import secrets; print(secrets.token_urlsafe(14))" > build/admin_password.txt
export LAB_ADMIN_PW="$(cat build/admin_password.txt)"
wp core install --url=http://localhost:8089 --title="Ledger Mint Lab" --admin_user=admin --admin_password="$LAB_ADMIN_PW" --admin_email=lab@example.com --skip-email
wp plugin install woocommerce --activate
wp theme install storefront --activate
wp rewrite structure '/%postname%/' --hard
wp option update woocommerce_currency GBP
wp option update woocommerce_default_country GB
wp option update woocommerce_coming_soon no
wp option update woocommerce_store_address "1 Lab Street"
wp option update woocommerce_store_city London
wp option update woocommerce_store_postcode "EC1A 1AA"
wp option update woocommerce_calc_taxes no
wp eval-file /lab-scripts/seed.php
wp rewrite flush --hard
echo "done: http://localhost:8089/shop/"

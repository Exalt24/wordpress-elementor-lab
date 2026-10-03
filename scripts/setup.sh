#!/usr/bin/env bash
# Stands up the lab from nothing: WordPress + MariaDB in Docker, Elementor and the Hello Elementor theme, the landing page shell, and the SEO fix.
#   bash scripts/setup.sh        then:  node scripts/build_page.cjs <out_dir> $(cat .page_id)   and   python scripts/seo_audit.py http://localhost:8087/seller-audit/
set -euo pipefail
cd "$(dirname "$0")/.."
export MSYS_NO_PATHCONV=1   # Git Bash on Windows rewrites /var/www/html into a Windows path otherwise
wp() { docker compose run --rm -T cli wp --path=/var/www/html "$@"; }

docker compose up -d db wordpress
for _ in $(seq 1 40); do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8087/ || true)
  [ "$code" != "000" ] && break
  sleep 3
done

wp core install --url=http://localhost:8087 --title="Seller Audit Lab" --admin_user=admin --admin_password=admin-local-only --admin_email=lab@example.com --skip-email
wp plugin install elementor --activate
wp theme install hello-elementor --activate
wp rewrite structure '/%postname%/' --hard

ID=$(wp post create --post_type=page --post_title="Amazon seller account audit" --post_name=seller-audit --post_status=publish --porcelain \
  --post_excerpt="A free written audit of your Amazon listings, advertising spend and account health, with the three changes most likely to lift sales ranked first." | tail -1)
wp post meta update "$ID" _elementor_edit_mode builder
wp post meta update "$ID" _wp_page_template elementor_canvas
echo "$ID" > .page_id
echo "page id $ID written to .page_id"

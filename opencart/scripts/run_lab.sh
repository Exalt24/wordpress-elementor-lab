#!/usr/bin/env bash
# One run, start to finish: build the stock store, audit it, apply the fix, audit it again, check the sitemap, robots and the old addresses.
# Writes docs/opencart_before.txt and docs/opencart_after.txt. Takes about two minutes.
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/setup.sh
bash scripts/audit_pages.sh before > ../docs/opencart_before.txt 2>&1 || true
bash scripts/fix.sh
bash scripts/audit_pages.sh after > ../docs/opencart_after.txt 2>&1 || true
{
  echo "### sitemap.xml"
  curl -s -i http://localhost:8088/sitemap.xml | head -20
  echo
  echo "### robots.txt"
  curl -s http://localhost:8088/robots.txt
  echo
  echo "### the old address of a product still answers, and its canonical points at the one address"
  curl -s "http://localhost:8088/index.php?route=product/product&language=en-gb&product_id=101&path=1&sort=p.price" | grep -o '<link href="[^"]*" rel="canonical"/>'
  echo
  echo "### JSON-LD on the product page"
  curl -s http://localhost:8088/en-gb/product/summit-30-daypack | grep -o '<script type="application/ld+json">.*</script>'
} > ../docs/opencart_checks.txt 2>&1
tail -4 ../docs/opencart_before.txt ../docs/opencart_after.txt

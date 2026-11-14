#!/usr/bin/env bash
# Runs the lab's 15 check audit on the store's home, category and product pages and prints one block per page.
#   bash scripts/audit_pages.sh before    (the store as OpenCart ships it: addresses are index.php?route=...)
#   bash scripts/audit_pages.sh after     (SEO URLs on, after scripts/fix.sh)
set -uo pipefail
cd "$(dirname "$0")/../.."
case "${1:-after}" in
  before) pages=("http://localhost:8088/" "http://localhost:8088/index.php?route=product/category&language=en-gb&path=1" "http://localhost:8088/index.php?route=product/product&language=en-gb&product_id=101") ;;
  after)  pages=("http://localhost:8088/" "http://localhost:8088/en-gb/catalog/backpacks" "http://localhost:8088/en-gb/product/summit-30-daypack") ;;
  *) echo "usage: audit_pages.sh before|after" >&2; exit 2 ;;
esac
for url in "${pages[@]}"; do
  echo "### $url"
  python scripts/seo_audit.py "$url"
  echo
done

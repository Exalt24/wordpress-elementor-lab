# What the OpenCart fix changed, and where

Moved out of the README to keep it short; the numbers are in the README and in `docs/opencart_before.txt` and `docs/opencart_after.txt`.

- **Settings and data** (`opencart/scripts/fix_settings.sql`): a store name, a home title and description, SEO URLs switched on (`/en-gb/product/summit-30-daypack` instead of `index.php?route=product/product&product_id=101`), and the home page modules pointed at products that exist.
- **Crawl and index**: `sitemap.xml` lists the home page, both categories and all six products, with the day each product changed. `robots.txt` keeps crawlers out of checkout, account, search and sorted listing addresses, and those pages also carry `noindex,follow`. The old `index.php?route=` address of a product still answers, and its canonical points at the one clean address, with sort and limit parameters dropped.
- **Structured data**: the Product node carries price, currency, SKU, image and stock, so the sold out Trail 20 Daypack reads `OutOfStock`. A missing image or SKU is left out, never invented. The JSON-LD is encoded so a product name containing `</script>` cannot end the block early, and a test proves it.
- **Headings and titles**: product card titles and footer column titles keep their look but move to `h2`, so the outline stops skipping levels. A short title gets the store name added, and a title over 65 characters is cut on a word.

The audit also had a bug of its own. On OpenCart's category page it reported a link as broken that a browser follows fine, because OpenCart sets `<base href>` and the audit resolved relative links against the page address instead. It now follows the base, with a test and a mutant for it.


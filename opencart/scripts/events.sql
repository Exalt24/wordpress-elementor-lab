-- Installs the extension the way the admin installer does (an install row and an extension row, which is what makes OpenCart autoload
-- extension/seolab) and wires its six events. Deleting these rows takes the whole change out again.
DELETE FROM oc_event WHERE code LIKE 'seolab_%';
DELETE FROM oc_extension WHERE extension = 'seolab';
DELETE FROM oc_extension_install WHERE code = 'seolab';
INSERT INTO oc_extension_install (extension_id, extension_download_id, name, description, code, version, author, link, status, date_added) VALUES
 (0, 0, 'SEO Lab technical fixes', 'Canonical links, meta descriptions, Open Graph tags, JSON-LD, a home page h1 and an XML sitemap for a stock OpenCart 4 storefront.', 'seolab', '1.0.0', 'Daniel Alexis Cruz', 'https://github.com/Exalt24/wordpress-elementor-lab', 1, NOW());
INSERT INTO oc_extension (extension, type, code) VALUES ('seolab', 'module', 'seo');
INSERT INTO oc_event (code, description, `trigger`, action, status, sort_order) VALUES
 ('seolab_head',   'SEO Lab: fill an empty meta description', 'catalog/controller/common/header/before', 'extension/seolab/event/seo.head',   1, 1),
 ('seolab_markup', 'SEO Lab: canonical, robots, Open Graph and JSON-LD in the head', 'catalog/view/common/header/after', 'extension/seolab/event/seo.markup', 1, 1),
 ('seolab_home',   'SEO Lab: home page template with an h1', 'catalog/view/common/home/before', 'extension/seolab/event/seo.home', 1, 1),
 ('seolab_thumb',  'SEO Lab: product card title h4 to h2', 'catalog/view/product/thumb/after', 'extension/seolab/event/seo.thumb', 1, 1),
 ('seolab_footer', 'SEO Lab: footer column titles h5 to h2', 'catalog/view/common/footer/after', 'extension/seolab/event/seo.footer', 1, 1),
 ('seolab_featured', 'SEO Lab: featured module title h3 to h2', 'catalog/view/extension/opencart/module/featured/after', 'extension/seolab/event/seo.featured', 1, 1);

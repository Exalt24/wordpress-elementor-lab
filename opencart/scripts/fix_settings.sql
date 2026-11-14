-- The settings and data half of the fix: a real title and description for the home page, a store name, SEO URLs switched on,
-- and the home page modules pointed at this catalogue (the default slideshow links to a demo product that is not in it, which is a 404).
SET NAMES utf8mb4;
DELETE FROM oc_setting WHERE `key` IN ('config_name','config_seo_url','config_meta_title','config_meta_description');
INSERT INTO oc_setting (store_id, code, `key`, value, serialized) VALUES
 (0, 'config', 'config_name', 'Pinewick Outfitters', 0),
 (0, 'config', 'config_seo_url', '1', 0),
 (0, 'config', 'config_meta_title', 'Pinewick Outfitters: daypacks, overnight packs and camp cookware', 0),
 (0, 'config', 'config_meta_description', 'Daypacks, overnight packs and camp cookware for people who hike and camp. Light, repairable gear with a rain cover and a hip belt on every pack.', 0);

-- Home page: drop the demo slideshow and the demo brands strip, and feature four real products.
DELETE FROM oc_layout_module WHERE layout_id = 1 AND code IN ('opencart.banner.3', 'opencart.banner.4');
UPDATE oc_module SET setting = '{"name":"Featured","product_name":"","product":["101","103","104","105"],"axis":"horizontal","limit":"4","width":"200","height":"200","status":"1"}' WHERE module_id = 2;

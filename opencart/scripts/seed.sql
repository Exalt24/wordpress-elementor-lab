-- Sample catalogue for the lab: a made-up outdoor shop with two categories and six products.
-- Settings stay at OpenCart's defaults here on purpose: scripts/fix_settings.sql is the settings half of the fix.
SET NAMES utf8mb4;
DELETE FROM oc_product; DELETE FROM oc_product_description; DELETE FROM oc_product_to_store; DELETE FROM oc_product_to_category;
DELETE FROM oc_category; DELETE FROM oc_category_description; DELETE FROM oc_category_path; DELETE FROM oc_category_to_store;
DELETE FROM oc_seo_url WHERE `key` IN ('product_id','path');

INSERT INTO oc_category (category_id, image, parent_id, sort_order, status) VALUES (1, 'catalog/pinewick/backpacks.png', 0, 1, 1), (2, 'catalog/pinewick/cookware.png', 0, 2, 1);
INSERT INTO oc_category_description (category_id, language_id, name, description, meta_title, meta_description, meta_keyword) VALUES
 (1, 1, 'Backpacks', '<p>Daypacks and overnight packs with a rain cover, a hip belt and a pocket for a water bottle.</p>', 'Backpacks', '', ''),
 (2, 1, 'Camp Cookware', '<p>Stoves, pots and mugs that pack down small enough to live inside the pot.</p>', 'Camp Cookware', '', '');
INSERT INTO oc_category_path (category_id, path_id, level) VALUES (1,1,0), (2,2,0);
INSERT INTO oc_category_to_store (category_id, store_id) VALUES (1,0), (2,0);

INSERT INTO oc_product (product_id, master_id, model, quantity, stock_status_id, image, manufacturer_id, shipping, price, tax_class_id, date_available, subtract, minimum, sort_order, status, date_added, date_modified) VALUES
 (101, 0, 'PW-DP30', 24, 7, 'catalog/pinewick/summit-30.png', 0, 1, 79.0000, 0, '2026-01-01', 1, 1, 1, 1, NOW(), NOW()),
 (102, 0, 'PW-DP20', 0,  5, 'catalog/pinewick/trail-20.png',  0, 1, 54.0000, 0, '2026-01-01', 1, 1, 2, 1, NOW(), NOW()),
 (103, 0, 'PW-OP55', 9,  7, 'catalog/pinewick/ridge-55.png',  0, 1, 189.0000, 0, '2026-01-01', 1, 1, 3, 1, NOW(), NOW()),
 (104, 0, 'PW-ST1',  40, 7, 'catalog/pinewick/spark-stove.png', 0, 1, 34.0000, 0, '2026-01-01', 1, 1, 1, 1, NOW(), NOW()),
 (105, 0, 'PW-PT9',  31, 7, 'catalog/pinewick/nest-pot.png',  0, 1, 29.0000, 0, '2026-01-01', 1, 1, 2, 1, NOW(), NOW()),
 (106, 0, 'PW-MG2',  60, 7, 'catalog/pinewick/fold-mug.png',  0, 1, 12.0000, 0, '2026-01-01', 1, 1, 3, 1, NOW(), NOW());
INSERT INTO oc_product_description (product_id, language_id, name, description, tag, meta_title, meta_description, meta_keyword) VALUES
 (101, 1, 'Summit 30 Daypack', '<p>A 30 litre daypack for long day hikes. It has a rain cover, a ventilated back panel and a pocket for a 2 litre water bladder.</p>', '', 'Summit 30 Daypack', '', ''),
 (102, 1, 'Trail 20 Daypack', '<p>A 20 litre daypack for short walks and commutes, light enough to forget you are carrying it.</p>', '', 'Trail 20 Daypack', '', ''),
 (103, 1, 'Ridge 55 Overnight Pack', '<p>A 55 litre pack for one to three nights out, with an adjustable torso length and a sleeping bag compartment.</p>', '', 'Ridge 55 Overnight Pack', '', ''),
 (104, 1, 'Spark Canister Stove', '<p>A canister stove that boils a litre of water in about four minutes and folds flat into a pocket.</p>', '', 'Spark Canister Stove', '', ''),
 (105, 1, 'Nest 900 ml Pot', '<p>A hard anodised aluminium pot with a lid that doubles as a pan. The stove and a small canister fit inside.</p>', '', 'Nest 900 ml Pot', '', ''),
 (106, 1, 'Fold Camp Mug', '<p>A 350 ml mug with fold-down handles that stacks inside the pot.</p>', '', 'Fold Camp Mug', '', '');
INSERT INTO oc_product_to_store (product_id, store_id) VALUES (101,0),(102,0),(103,0),(104,0),(105,0),(106,0);
INSERT INTO oc_product_to_category (product_id, category_id) VALUES (101,1),(102,1),(103,1),(104,2),(105,2),(106,2);

INSERT INTO oc_seo_url (store_id, language_id, `key`, `value`, keyword, sort_order) VALUES
 (0,1,'path','1','backpacks',0), (0,1,'path','2','camp-cookware',0),
 (0,1,'product_id','101','summit-30-daypack',0), (0,1,'product_id','102','trail-20-daypack',0), (0,1,'product_id','103','ridge-55-overnight-pack',0),
 (0,1,'product_id','104','spark-canister-stove',0), (0,1,'product_id','105','nest-900-ml-pot',0), (0,1,'product_id','106','fold-camp-mug',0);

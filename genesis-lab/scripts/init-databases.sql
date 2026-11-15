-- Two sites on one database server: a DEV copy to build on and a PROD copy that only a sync ever changes.
CREATE DATABASE IF NOT EXISTS wp_dev CHARACTER SET utf8mb4;
CREATE DATABASE IF NOT EXISTS wp_prod CHARACTER SET utf8mb4;
GRANT ALL PRIVILEGES ON wp_dev.* TO 'wp'@'%';
GRANT ALL PRIVILEGES ON wp_prod.* TO 'wp'@'%';
FLUSH PRIVILEGES;
